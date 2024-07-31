import argparse
import os
from datetime import datetime
from typing import Sequence

import cv2
import numpy as np
import redis

from src.camera import RealSenseCamera
from src.detector import MediaPipeDetector


REDIS_POS_KEY = "sai2::realsense::"
STREAMING_POINTS = ["left_hand", "right_hand", "center_hips"]


class PoseTracker:

    def __init__(
        self,
        stream_outputs: bool = False,
        write_to_file: bool = False,
        capture_length: int = -1,
        smoothing_factor: int = 1,
    ):
        self.camera = RealSenseCamera()
        self.detector = MediaPipeDetector()
        self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

        self.stream_outputs = stream_outputs
        self.write_to_file = write_to_file
        self.capture_length = capture_length
        self.smoothing_factor = smoothing_factor

        if self.write_to_file:
            os.mkdir("logs", exist_ok=True)
            self.filename = os.path.join("logs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
            header = ["timestamp"] + [REDIS_POS_KEY + p for p in STREAMING_POINTS]
            self.out_string = "\t".join(header)

        self.timesteps = 0

    def process_frame(self) -> bool:
        print(f"\nt={self.timesteps}")
        depth_frame, color_frame = self.camera.get_frames()

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03),cv2.COLORMAP_JET)
        
        depth_colormap_dim = depth_colormap.shape
        width, height, _ = depth_colormap_dim
        color_colormap_dim = color_image.shape

        if depth_colormap_dim != color_colormap_dim:
            color_image = cv2.resize(
                color_image, 
                dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                interpolation=cv2.INTER_AREA)

        detection_result = self.detector.run_detection(color_image)
        color_image = self.detector.draw_landmarks_on_image(color_image, detection_result)
        depth_colormap = self.detector.draw_landmarks_on_image(depth_colormap, detection_result)
        images = np.hstack((color_image, depth_colormap))

        landmark_dict = self.detector.parse_landmarks(detection_result)

        def get_depth_at_pixel(x, y):
            x, y = int(x * width), int(y * height)
            if x < 0 or x >= width or y < 0 or y >= height:
                return -1
            else:
                return 1e-3 * depth_image[x, y]

        if self.write_to_file:
            self.out_string += "\n" + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        for key in landmark_dict:
            landmark = landmark_dict[key]
            depth = get_depth_at_pixel(landmark[0], landmark[1])
            
            if depth == -1:
                landmark_dict[key] = None
                print(f"{key: <15}   null")
            else:
                # focal length of RealSense d455
                landmark[0] = width * (landmark[0] - 0.5) * (depth / 640)
                landmark[1] = height * (landmark[1] - 0.5) * (depth / 640)
                landmark[2] = depth

                if self.stream_outputs and key in STREAMING_POINTS:
                    self.redis_client.set(REDIS_POS_KEY + key, str(landmark))
                if self.write_to_file and key in STREAMING_POINTS:
                    self.out_string += "\t[" + ", ".join(map(str, landmark)) + "]"

                print(f"{key: <15}   x: {landmark[0]: 3.2f}  y: {landmark[1]: 3.2f}  z: {landmark[2]: 3.2f}")
                
        self.timesteps += 1
        if self.capture_length > 0 and self.timesteps > self.capture_length:
            return False

        cv2.imshow("RealSense", images)
        return True

    def close(self):
        print("\nclosing")
        if self.write_to_file:
            print(f"writing to file {self.filename}.txt")
            with open(self.filename + ".txt", "w") as file:
                file.write(self.out_string)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream_outputs", "-s", action="store_true")
    parser.add_argument("--write_to_file", "-w", action="store_true")
    parser.add_argument("--capture_length", "-c", type=int, default=-1)
    args = parser.parse_args()

    tracker = PoseTracker(
        stream_outputs=args.stream_outputs,
        write_to_file=args.write_to_file,
        capture_length=args.capture_length,
    )

    try:
        while True:
            if not tracker.process_frame():
                break
            elif cv2.waitKey(1) & 0xFF == ord('q'): 
                break
    finally:
        tracker.close()
