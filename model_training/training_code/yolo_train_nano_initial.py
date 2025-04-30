from ultralytics import YOLO
import torch
import os

def train_yolov8_multi_gpu():
    # Check available GPUs
    # num_gpus = torch.cuda.device_count()
    # print(f"Training on {num_gpus} GPUs.")

    # Load model (choose yolov8n/yolov8s/yolov8m/yolov8l/yolov8x)
    model = YOLO("yolov8n.pt")  # Or yolov8s.pt, etc.

    # Train
    model.train(
        data="/u/cartmull/Aimm/big-boat-little-boat-1/data.yaml",
        epochs=150,
        imgsz=640,
        batch=-1,
        device = 0
        # device=list(range(num_gpus)),  # Multi-GPU
    )

    model.save("yolov8n_initial_buoy.pt")

if __name__ == "__main__":
    train_yolov8_multi_gpu()