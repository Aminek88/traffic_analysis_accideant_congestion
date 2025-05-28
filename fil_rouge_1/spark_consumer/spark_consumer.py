from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, explode, to_json, struct, concat, lit
from pyspark.sql.types import StructType, StructField, FloatType, IntegerType, StringType, ArrayType, TimestampType
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spark setup
try:
    logger.info("Initializing SparkSession")
    spark = SparkSession.builder \
        .appName("TrafficDataConsumer") \
        .master("local[*]") \
        .config("spark.default.parallelism", "100") \
        .config("spark.sql.shuffle.partitions", "100") \
        .config("spark.executor.memory", "4g") \
        .config("spark.driver.memory", "2g") \
        .config("spark.memory.offHeap.enabled", "true") \
        .config("spark.memory.offHeap.size", "2g") \
        .config("spark.redis.host", "redis") \
        .config("spark.redis.port", "6379") \
        .getOrCreate()
    logger.info("SparkSession initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SparkSession: {str(e)}")
    sys.exit(1)

# Schema
schema = StructType([
    StructField('timestamp', StringType(), True),
    StructField('vehicles', IntegerType(), True),
    StructField('frame_id', IntegerType(), True),
    StructField('elapsed_time_sec', FloatType(), True),
    StructField('source_id', StringType(), True),
    StructField('detections', ArrayType(StructType([
        StructField('x_min', FloatType(), True),
        StructField('y_min', FloatType(), True),
        StructField('x_max', FloatType(), True),
        StructField('y_max', FloatType(), True),
        StructField('track_id', FloatType(), True),
        StructField('conf', FloatType(), True),
        StructField('class_name', StringType(), True)
    ])), True)
])

# Kafka read
try:
    logger.info("Setting up Kafka readStream")
    data_stream = spark.readStream \
        .format('kafka') \
        .option('kafka.bootstrap.servers', 'kafka:9092') \
        .option('subscribe', 'traffic-data-1') \
        .option('startingOffsets', 'latest') \
        .option('failOnDataLoss', 'false') \
        .load()
    logger.info("Kafka readStream set up successfully")
except Exception as e:
    logger.error(f"Failed to set up Kafka readStream: {str(e)}")
    sys.exit(1)

# Parse and transform
parsed_data_stream = data_stream.select(
    from_json(col('value').cast('string'), schema).alias('data')
).select(
    col('data.timestamp').cast(TimestampType()).alias('timestamp'),
    col('data.frame_id'),
    col('data.vehicles'),
    col('data.elapsed_time_sec'),
    col('data.source_id').alias('camera'),
    col('data.detections')
)

# Explode detections and add transformations
detection_stream = parsed_data_stream.select(
    'timestamp', 'frame_id', 'vehicles', 'elapsed_time_sec', 'camera',
    explode(col('detections')).alias('detection')
).select(
    col('timestamp'),
    col('frame_id'),
    col('vehicles'),
    col('elapsed_time_sec'),
    col('camera'),
    col('detection.x_min').alias('x_min'),
    col('detection.y_min').alias('y_min'),
    col('detection.x_max').alias('x_max'),
    col('detection.y_max').alias('y_max'),
    col('detection.track_id').cast('integer').alias('track_id'),
    col('detection.conf').alias('confiance'),
    col('detection.class_name').alias('class_name'),
    lit('2025-05-24').alias('date'),
    lit('period1').alias('period'),
    ((col('x_max') + col('x_min')) / 2.0).alias('x_centre'),
    ((col('y_max') + col('y_min')) / 2.0).alias('y_centre')
)

# Filter out null track_ids
detection_stream = detection_stream.filter(col("track_id").isNotNull())

# Console sink
query_console = detection_stream.writeStream \
    .format("console") \
    .option("truncate", "false") \
    .option("checkpointLocation", "/app/checkpoint/console") \
    .trigger(processingTime="5 seconds") \
    .start()

# CSV sink
query_csv = detection_stream.writeStream \
    .format("csv") \
    .option("path", "/app/output/detection_stream") \
    .option("checkpointLocation", "/app/checkpoint/csv") \
    .trigger(processingTime="5 seconds") \
    .start()

# Redis sink
def write_to_redis(df, batch_id):
    try:
        logger.info(f"Writing batch {batch_id} to Redis")

        redis_df = df.withColumn(
            "redis_key",
            concat(
                lit("detection:"),
                col("timestamp").cast("string"),
                lit(":"),
                col("track_id").cast("string")
            )
        ).select(
            col("redis_key").alias("key"),
            to_json(struct([col(c) for c in df.columns])).alias("value")
        )

        row_count = redis_df.count()
        logger.info(f"Batch {batch_id} DataFrame row count: {row_count}")

        if row_count > 0:
            redis_df.select("key", "value").show(20, truncate=False)

            def write_partition(partition):
                try:
                    import redis
                    r = redis.Redis(
                        host="redis",
                        port=6379,
                        db=0,
                        decode_responses=True,
                        socket_timeout=5,
                        socket_connect_timeout=5
                    )
                    for row in partition:
                        try:
                            r.set(row["key"], row["value"], ex=900)
                        except Exception as e:
                            logger.error(f"Failed to set key {row['key']}: {str(e)}")
                    r.close()
                except Exception as e:
                    logger.error(f"Failed in partition: {str(e)}")
                    raise

            redis_df.rdd.foreachPartition(write_partition)
            logger.info(f"Successfully wrote batch {batch_id} to Redis with {row_count} rows")
        else:
            logger.warning(f"Batch {batch_id} is empty, skipping Redis write")

    except Exception as e:
        logger.error(f"Failed to write batch {batch_id} to Redis: {str(e)}", exc_info=True)
        raise

query_redis = detection_stream.writeStream \
    .option("checkpointLocation", "/app/checkpoint/redis") \
    .trigger(processingTime="5 seconds") \
    .foreachBatch(write_to_redis) \
    .start()

spark.streams.awaitAnyTermination()
