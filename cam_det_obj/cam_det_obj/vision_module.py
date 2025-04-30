#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, qos_profile_system_default
from message_filters import ApproximateTimeSynchronizer, Subscriber
from sensor_msgs.msg import Image, Imu, CameraInfo
from std_msgs.msg import Header
from custom_det_msgs.msg import DetObj

from cv_bridge import CvBridge
import cv2 as cv
import numpy as np
import math
from ultralytics import YOLO
from multiprocessing import Lock

class VisionNode(Node):
    def __init__(self):
        super().__init__("vision_node")

        # Initialize state and message cache
        self.message_cache = []
        self.last_rgb_img = None
        self.last_depth_img = None
        self.last_imu_msg = None
        self.last_info_msg = None

        self.prev_time = None
        self.roll_est = 0.0
        self.pitch_est = 0.0
        self.yaw_est = 0.0

        self.camera_matrix = None
        self.distortion_coeffs = None

        self.message_cache_mutex = Lock()
        self.cv2_bridge = CvBridge()

        # Load YOLOv8 model for detection
        self.yolo_model = YOLO('src/cam_det_obj/model_weights/yolov8l_buoy.pt')
        self.premade_colors = (np.random.rand(200, 3) * 255).astype('uint8')

        # Topic setup
        self.camera_topic_rgb = "/oak/rgb/image_raw"
        self.camera_topic_depth = "/oak/stereo/image_raw"
        self.camera_topic_info = "/oak/rgb/camera_info"
        self.camera_imu_topic = "/oak/imu/data"

        # Subscriptions using message_filters for synchronized access
        self.image_rgb_sub = Subscriber(self, Image, self.camera_topic_rgb)
        self.image_depth_sub = Subscriber(self, Image, self.camera_topic_depth)
        self.imu_sub = Subscriber(self, Imu, self.camera_imu_topic)
        self.camera_info_sub = Subscriber(self, CameraInfo, self.camera_topic_info)

        self.image_rgb_sub.registerCallback(self.cache_rgb_image)
        self.image_depth_sub.registerCallback(self.cache_depth_image)
        self.imu_sub.registerCallback(self.cache_imu_msg)
        self.camera_info_sub.registerCallback(self.cache_camera_info)

        # Publisher for detected object info
        self.detection_pub = self.create_publisher(DetObj, '/detected_objects', qos_profile=qos_profile_system_default)

        # Timer to process cached data at 5Hz
        self.timer = self.create_timer(1 / 5, self.vision_callback)

        self.get_logger().info(f'Vision node setup complete and running.')

    # Cache individual message types
    def cache_rgb_image(self, msg):
        with self.message_cache_mutex:
            self.message_cache.append((1, msg))

    def cache_depth_image(self, msg):
        with self.message_cache_mutex:
            self.message_cache.append((2, msg))

    def cache_imu_msg(self, msg):
        with self.message_cache_mutex:
            self.message_cache.append((3, msg))

    def cache_camera_info(self, msg):
        with self.message_cache_mutex:
            self.message_cache.append((4, msg))
        self.camera_matrix = np.array(msg.k).reshape(3, 3)
        self.distortion_coeffs = np.array(msg.d)

    # Main processing loop
    def vision_callback(self):
        with self.message_cache_mutex:
            cached_msgs = self.message_cache.copy()
            self.message_cache = []

        # Extract the most recent messages of each type
        for topic_id, msg in cached_msgs:
            if topic_id == 1:
                self.last_rgb_img = msg
            elif topic_id == 2:
                self.last_depth_img = msg
            elif topic_id == 3:
                self.last_imu_msg = msg
            elif topic_id == 4:
                self.last_info_msg = msg

        if not all([self.last_rgb_img, self.last_depth_img, self.last_imu_msg, self.last_info_msg]):
            return  # Incomplete data

        rgb_image = self.cv2_bridge.imgmsg_to_cv2(self.last_rgb_img)
        depth_image = self.cv2_bridge.imgmsg_to_cv2(self.last_depth_img)

        if rgb_image is None or depth_image is None:
            self.get_logger().error("RGB or Depth image is None after conversion.")
            return

        results = self.yolo_model.predict(rgb_image, device='cpu', stream=True)

        for result in results:
            boxes = result.boxes.cpu().numpy()
            if len(boxes) == 0:
                continue

            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                confidence = box.conf[0]
                cat = int(box.cls)

                # Bounding box processing for distance
                cx, cy = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                radius = int(min(x2 - x1, y2 - y1) * 0.4)
                x1_crop, x2_crop = max(0, cx - radius), min(depth_image.shape[1], cx + radius)
                y1_crop, y2_crop = max(0, cy - radius), min(depth_image.shape[0], cy + radius)
                roi = depth_image[y1_crop:y2_crop, x1_crop:x2_crop]

                mask = np.zeros_like(roi, dtype=np.uint8)
                cv.circle(mask, (radius, radius), radius, 255, thickness=-1)
                masked_roi = np.where(mask == 255, roi, np.nan)

                distance = np.nanmean(masked_roi) / 1000 if np.count_nonzero(~np.isnan(masked_roi)) else 0.0

                # Angular calculations
                if self.camera_matrix is not None:
                    fx, fy = self.camera_matrix[0, 0], self.camera_matrix[1, 1]
                    cx_cam, cy_cam = self.camera_matrix[0, 2], self.camera_matrix[1, 2]
                    az = math.degrees(math.atan2(cx - cx_cam, fx))
                    el = math.degrees(math.atan2(cy - cy_cam, fy))
                else:
                    az, el = 0.0, 0.0

                # IMU integration for orientation
                current_time = self.last_imu_msg.header.stamp
                if self.prev_time is None:
                    self.prev_time = current_time
                    return

                dt = (rclpy.time.Time.from_msg(current_time) - rclpy.time.Time.from_msg(self.prev_time)).nanoseconds * 1e-9
                self.prev_time = current_time

                gx, gy, gz = self.last_imu_msg.angular_velocity.x, self.last_imu_msg.angular_velocity.y, self.last_imu_msg.angular_velocity.z
                ax, ay, az_acc = self.last_imu_msg.linear_acceleration.x, self.last_imu_msg.linear_acceleration.y, self.last_imu_msg.linear_acceleration.z

                acc_roll = math.atan2(ay, az_acc)
                acc_pitch = math.atan2(-ax, math.sqrt(ay ** 2 + az_acc ** 2))
                gyro_roll = self.roll_est + gx * dt
                gyro_pitch = self.pitch_est + gy * dt
                gyro_yaw = self.yaw_est + gz * dt

                alpha = 0.98
                self.roll_est = alpha * gyro_roll + (1 - alpha) * acc_roll
                self.pitch_est = alpha * gyro_pitch + (1 - alpha) * acc_pitch
                self.yaw_est = gyro_yaw

                roll, pitch, yaw = map(math.degrees, [self.roll_est, self.pitch_est, self.yaw_est])

                # Object labeling
                names = {
                    0: 'Black, Buoy', 1: 'Blue, Buoy', 2: 'Green, Buoy', 3: 'Maroon, Buoy',
                    4: 'None, Or', 5: 'Orange, Buoy', 6: 'Red, Buoy', 7: 'None, Wader',
                    8: 'White, Buoy', 9: 'Yellow, Buoy', 10: 'Zebra, Buoy'
                }
                label = names.get(cat, "none, unknown")
                parts = [s.strip() for s in label.split(",", 1)]
                object_subclass, object_class = (parts + ["none"] * 2)[:2]  # Safe unpacking

                # Publish detection
                detection_msg = DetObj()
                detection_msg.header = Header(stamp=self.get_clock().now().to_msg(), frame_id="camera")
                detection_msg.dist = distance
                detection_msg.az = az
                detection_msg.el = el
                detection_msg.cam_pitch = pitch
                detection_msg.cam_roll = roll
                detection_msg.cam_yaw = yaw
                detection_msg.object_class = object_class
                detection_msg.object_subclass = object_subclass

                self.get_logger().info("Publishing DetObj message...")
                self.detection_pub.publish(detection_msg)
                self.get_logger().info(f"{detection_msg}")

        # Update internal time
        self.time_before = self.get_clock().now()


def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down VisionNode.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
