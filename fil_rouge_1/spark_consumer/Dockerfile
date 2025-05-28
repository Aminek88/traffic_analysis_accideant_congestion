FROM bitnami/spark:3.5.0

WORKDIR /app

USER root
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pyspark==3.5.0

# Installer redis-tools et le paquet Python redis
RUN apt-get update && apt-get install -y redis-tools && \
    /opt/bitnami/python/bin/pip install --no-cache-dir redis

COPY requirements.txt .
RUN /opt/bitnami/python/bin/pip install --no-cache-dir -r requirements.txt

COPY spark_consumer.py .

CMD ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,com.redislabs:spark-redis_2.12:3.1.0", "/app/spark_consumer.py"]