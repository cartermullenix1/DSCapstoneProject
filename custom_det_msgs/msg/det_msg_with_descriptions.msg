std_msgs/Header header         # Header of the msg (standard ros2 header)
float32 dist 0.0               # Distance from camera to object detection in meters
float32 az 0.0                 # azimuth relative to the front facing direction of the camera in deg
float32 el 0.0                 # elevation relative to the front facing direction of the camera in deg
float32 cam_pitch 0.0          # pitch of the camera IMU showing where the front facing direction is relative to the boat in deg
float32 cam_roll 0.0           # roll of the camera IMU showing where the front facing direction is relative to the boat in deg
float32 cam_yaw 0.0            # yaw of the camera IMU showing where the front facing direction is relative to the boat in deg
string object_class "None"     # object class from YOLO model (for example, a red buoy is given as "buoy" here)
string object_subclass "None"  # object subclass from the YOLO model (for example, a red buoy is given as "red" here)