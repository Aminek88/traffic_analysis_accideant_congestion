# Video Processing Pipeline with Apache Airflow
A comprehensive video processing and anomaly detection system built with Apache Airflow, featuring both batch and stream processing capabilities for real-time video analytics.
### Architecture Overview
This project implements a dual-pipeline architecture for video processing:

Batch Processing Pipeline

Video Ingestion: Collects video metadata (path, period, camera, date)
Processing: OpenCV + UltraLytics for computer vision tasks
Storage: MinIO for object storage
Analytics: Apache Spark for data quality checks and analysis
Reporting: Automated report generation
Archival: Apache Superset for long-term storage and visualization

Stream Processing Pipeline

Real-time Processing: Live video stream analysis with OpenCV + UltraLytics
Message Queue: Apache Kafka for reliable stream processing
Analytics: Apache Spark for real-time data processing
Caching: Redis provides fast access to data and temporarily stores stock data.
Visualization: Streamlit dashboard for real-time monitoring
Storage: Parquet format with MinIO integration

## Features

Real-time Video Processing: Live stream analysis and anomaly detection
Batch Video Analysis: Scheduled processing of stored video files
Data Quality Monitoring: Automated checks for data presence and quality
Scalable Architecture: Distributed processing with Apache Spark
Interactive Dashboards: Real-time visualization with Streamlit
Data Lake Storage: Efficient storage with MinIO and Parquet format
Comprehensive Reporting: Automated report generation and archival

## Technology Stack
### Orchestration

Apache Airflow: Workflow orchestration and scheduling

### Processing

OpenCV: Computer vision and video processing
UltraLytics: Advanced object detection and tracking
Apache Spark: Distributed data processing

### Storage & Messaging

MinIO: S3-compatible object storage
Apache Kafka: Stream processing and messaging
Redis: In-memory caching and data structure store
Apache Parquet: Columnar storage format

### Visualization & Monitoring

Streamlit: Real-time dashboard and monitoring
Apache Superset: Business intelligence, report and data visualization

### External Systems

Security Cameras: Video input sources
Monitoring Systems: External system integration

### Usage

Schedule batch jobs via Airflow UI.
Monitor real-time anomalies via Streamlit dashboard.
Generate reports using Superset.

# Models

This pipeline employs two deep learning-based methodologies for anomaly detection in traffic surveillance videos:

## Autoencoders CNN + LSTM with RBF
Description: Detects and localizes road accidents using a spatio-temporal autoencoder approach with Convolutional Neural Networks (CNN) and Long Short-Term Memory (LSTM) networks, followed by a Radial Basis Function (RBF) for binary classification.

### Methodology:
CNN Autoencoder: Compresses video frames (e.g., 224x224x3) into a latent representation (bottleneck, e.g., 14x14x128) to extract spatial features. Uses L2 loss to minimize reconstruction error.
LSTM Autoencoder: Captures temporal dependencies using a sliding window technique to process sequential latent representations, producing a bottleneck for anomaly detection.
RBF Classification: Applies a Gaussian RBF to classify sequences as normal or anomalous based on deviation from trained normal patterns.
Training: Trained on normal traffic videos (e.g., DoTA dataset with 4677 annotated videos) using unsupervised learning, avoiding the need for labeled accident data.
Reference: Inspired by Karishma Pawar and Vahida Attar (2021), "Deep Learning based detection and localization of road accidents from traffic surveillance videos."

## YOLOv8 with Kalman Filter
Description: Detects and tracks objects in real-time using YOLOv8, followed by a Kalman Filter and Hungarian algorithm for motion analysis and anomaly detection.

### Methodology:
YOLOv8 Object Detection: Identifies vehicles and other objects (e.g., cars, bicycles) with a 53-layer CNN architecture, including multi-scale detection and self-attention mechanisms.
Object Tracking: Uses the Kalman Filter to predict object positions (x, y, scale, aspect ratio, velocities) and the Hungarian algorithm to associate detections across frames, minimizing a cost function based on appearance, size, position, and intersection-over-union (IoU).
Anomaly Detection: Analyzes trajectories and motion patterns (e.g., speed, acceleration) to detect potential collisions.
Training: Utilizes preprocessed motion data (normalized x, y, width, height) fed into CNN and LSTM autoencoders for pattern learning.
Reference: Based on Hadi Ghahremannezhad et al. (2022), "Real-Time Accident Detection in Traffic Surveillance Using Deep Learning."

