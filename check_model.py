from ultralytics import YOLO

model = YOLO("models/ppe_yolov8.pt")

print(model.names)