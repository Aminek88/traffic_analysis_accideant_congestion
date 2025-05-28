FROM fil_rouge_1

WORKDIR /app

COPY vedio_reader.py yolo11n.pt vedio_car.mp4 /app/

CMD ["python", "vedio_reader.py", "/app/vedio_car.mp4", "traffic-data-1", "video1", "30"]