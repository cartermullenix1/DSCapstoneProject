#!/usr/bin/env python3

import rclpy
from cam_det_obj.vision_module import VisionNode

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
