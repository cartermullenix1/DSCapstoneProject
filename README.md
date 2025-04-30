# DSCapstoneProject

This repository contains the code and training assets for my senior capstone project in Data Science. The project focuses on detecting colored buoys in aquatic environments using computer vision and deep learning techniques. It integrates real-time object detection with ROS 2 and includes model training, evaluation, and deployment.

---

## Project Overview

The goal of this project is to enable reliable buoy detection and localization on an autonomous watercraft. The system processes real-time image and depth data using a YOLOv8-based object detection model deployed via ROS 2.

---

## Repository Structure

### 1. ROS 2 Packages

- **`cam_det_obj/`**:  
  Contains the main ROS 2 node (`vision_node.py`) and launch file (`camera.launch.py`) for running the detection pipeline.
  - `model_weights/`: Pretrained YOLOv8 model weights used for inference.
  - `scripts/`: Vision node logic.
  - `launch/`: ROS 2 launch configuration.

- **`custom_det_msgs/`**:  
  Custom ROS 2 message definitions (`DetObj.msg`) for publishing detection outputs.

### 2. Model Training and Evaluation

- **`model_training/training_code/`**:  
  YOLOv8 training scripts for different model sizes (nano, small, medium, large, x-large).

- **`model_training/weights/`**:  
  Trained model weights exported after training. (Except for the XL weights, which are too large for GitHub)

- **`model_training/runs/detect/`**:  
  Training outputs including performance curves, confusion matrices, batch visualizations, and metric CSVs for all model variants.

---

## Usage

### Prerequisites

- Ubuntu 22.04
- ROS2-Humble
- DepthAI-ROS2
- Python 3.8+
- `ultralytics` library for YOLOv8
- Oak-D camera connected to the system with POE (Power Over Ethernet) enabled.

### 1. Launch the Oak-D Camera

Command to run:

```bash
ros2 launch depthai_ros_driver camera.launch.py
```

This command launches the Oak-D camera node, which streams RGB Video, Depth, IMU data to the ROS 2 network. Ensure that the camera is connected and recognized by your system.

### 2. Launch the Detection Node

```bash
ros2 run cam_det_obj vision_node
```

This will start the detection node, which subscribes to the camera RGB, Depth, and IMU and publishes custom ROS2 detection messages.

### Acknowledgment of Resources

[DepthAI ROS2](https://docs.luxonis.com/projects/api/en/latest/) - Documentation for the DepthAI ROS2 driver.

[OpenCV](https://docs.opencv.org/4.x/) - Documentation for the OpenCV library used for image processing.

[Pytorch](https://pytorch.org/) - Documentation for the PyTorch library used in model training and inference.

[ROS 2](https://docs.ros.org/en/humble/index.html) - Documentation for ROS 2 and its ecosystem.

[Ultralytics YOLOv8](https://docs.ultralytics.com/) - Documentation for the YOLOv8 model and training scripts.
