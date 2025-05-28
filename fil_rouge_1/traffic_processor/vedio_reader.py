from ultralytics import YOLO
from kafka import KafkaProducer
import cv2
import json
import time
import sys
import datetime
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Kafka setup with retry
for attempt in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers='kafka:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info("Kafka connection successful")
        break
    except Exception as e:
        logger.error(f"Kafka connection error (attempt {attempt + 1}/10): {e}")
        time.sleep(2)
else:
    logger.error("Failed to connect to Kafka after 10 attempts")
    sys.exit(1)

# Load YOLO model
try:
    yolo_model = YOLO("yolo11n.pt") 
    yolo_model.verbose = False
    class_names = yolo_model.names
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"Error loading YOLO model: {e}")
    sys.exit(1)

def process_video(video_path, topic, source_id, fps=30):
    """Process a video file as a streaming source, sending frames to Kafka."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        sys.exit(1)

    frame_count = 0
    start_time = time.time()
    frame_interval = 1.0 / fps  # Time per frame in seconds

    logger.info(f"Starting video processing: {video_path} at {fps} FPS")

    while cap.isOpened():
        loop_start = time.time()

        ret, frame = cap.read()
        if not ret or frame is None:
            logger.info("End of video reached")
            break

        # Timing and metadata
        elapsed_time = time.time() - start_time
        datetime_cap = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Resize frame
        scale = 640 / max(frame.shape[:2])
        new_width = int(frame.shape[1] * scale)
        new_height = int(frame.shape[0] * scale)
        frame_res = cv2.resize(frame, (new_width, new_height))

        # YOLO detection and tracking
        try:
            results = yolo_model.track(frame_res, persist=True, verbose=False)
            detection = results[0].boxes.data.cpu().numpy()
        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            continue

        if detection.size == 0:
            num_vehicles = 0
            detections = []
        else:
            frame_df = pd.DataFrame(
                detection,
                columns=["x_min", "y_min", "x_max", "y_max", "track_id", "conf", "class"]
            )
            frame_df["class_name"] = frame_df["class"].apply(lambda x: class_names[int(x)])
            num_vehicles = frame_df['track_id'].nunique()
            detections = frame_df[["x_min", "y_min", "x_max", "y_max", "track_id", "conf", "class_name"]].to_dict('records')

        # Prepare Kafka message
        message = {
            "timestamp": datetime_cap,
            "vehicles": int(num_vehicles),
            "frame_id": frame_count,
            "elapsed_time_sec": round(elapsed_time, 2),
            "source_id": source_id,
            "detections": detections
        }

        # Send to Kafka
        try:
            producer.send(topic, message)
            producer.flush()
            logger.info(f"Sent frame {frame_count} from {source_id} to {topic}")
        except Exception as e:
            logger.error(f"Error sending to Kafka: {e}")
            continue

        frame_count += 1

        # Control frame rate
        elapsed_loop = time.time() - loop_start
        sleep_time = max(0, frame_interval - elapsed_loop)
        time.sleep(sleep_time)

        if frame_count % 100 == 0:
            logger.info(f"Processed {frame_count} frames")

    cap.release()
    producer.flush()
    logger.info(f"Processing complete for {source_id}. Total frames: {frame_count}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        logger.error("Usage: python vedio_reader.py <video_path> <kafka_topic> <source_id> <fps>")
        sys.exit(1)
    video_path, topic, source_id, fps = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    process_video(video_path, topic, source_id, fps)