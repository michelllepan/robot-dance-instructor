import argparse
import os
import time
from datetime import datetime
from typing import Sequence

import cv2
import numpy as np
import redis
import scipy

from src.camera import RealSenseCamera
from src.detector import MediaPipeDetector


REDIS_POS_KEY = "sai2::realsense::"
STREAMING_POINTS = ["left_hand", "right_hand", "center_hips"]
EMA_BETA = 0.9

class PoseTracker:

    def __init__(
        self,
        stream_outputs: bool = False,
        write_to_file: bool = False,
        capture_length: int = -1,
        history_length: int = 1,
    ):
        self.camera = RealSenseCamera()
        self.detector = MediaPipeDetector()
        self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

        self.stream_outputs = stream_outputs
        self.write_to_file = write_to_file
        self.capture_length = capture_length
        self.history_length = history_length

        if self.write_to_file:
            os.makedirs("logs", exist_ok=True)
            self.filename = os.path.join("logs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
            header = ["timestamp"] + [REDIS_POS_KEY + p for p in STREAMING_POINTS]
            self.out_string = "\t".join(header)

        self.start_time = time.time()
        self.timesteps = 0

        # initialize history
        self.history = {}
        for key in STREAMING_POINTS:
            self.history[key] = np.empty((history_length, 3))
            self.history[key][:] = np.nan

    def smooth_values(self, key, new_value):
        # update history
        self.history[key] = np.concatenate((
            self.history[key][1:],
            np.array(new_value).reshape((1, 3))
        ))

        # create weights
        weights = (1 - EMA_BETA) * np.power(EMA_BETA, np.arange(self.history_length))

        # redistribute weights if values are nan
        for i in range(self.history_length):
            if np.isnan(self.history[key][i]).any():
                weights[i] = 0
        if sum(weights) == 0:
            return None
        weights = weights / sum(weights)

        # calculate smoothed values
        smoothed_values = np.dot(weights.T, np.nan_to_num(self.history[key]))
        return smoothed_values

    def process_frame(self) -> bool:
        print(f"\nt = {self.timesteps}")
        depth_frame, color_frame = self.camera.get_frames()

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        depth_image = scipy.signal.convolve2d(
            in1=depth_image,
            in2=np.ones((3, 3)) / 9,
            mode="same",
        )

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
                return None
            else:
                return 1e-3 * depth_image[x, y]

        if self.write_to_file:
            self.out_string += "\n" + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        for key in landmark_dict:
            if key not in STREAMING_POINTS:
                continue

            landmark = landmark_dict[key]
            depth = get_depth_at_pixel(landmark[0], landmark[1])

            if depth is None:
                smoothed = self.smooth_values(key, [np.nan] * 3)
            else:
                landmark[0] = width * (landmark[0] - 0.5) * (depth / 640)
                landmark[1] = height * (landmark[1] - 0.5) * (depth / 640)
                landmark[2] = depth
                smoothed = self.smooth_values(key, landmark)

            if smoothed is None:
                print(f"{key: <15}   null")
                continue

            if self.stream_outputs:
                self.redis_client.set(REDIS_POS_KEY + key, str(smoothed))
            if self.write_to_file:
                self.out_string += "\t[" + ", ".join(map(str, smoothed)) + "]"

            print(f"{key: <15}   x: {smoothed[0]: 3.2f}  y: {smoothed[1]: 3.2f}  z: {smoothed[2]: 3.2f}")
                
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

        print(f"average fps: {self.timesteps / (time.time() - self.start_time)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream_outputs", "-s", action="store_true")
    parser.add_argument("--write_to_file", "-w", action="store_true")
    parser.add_argument("--capture_length", "-c", type=int, default=-1)
    parser.add_argument("--history_length", "-l", type=int, default=5)
    args = parser.parse_args()

    tracker = PoseTracker(
        stream_outputs=args.stream_outputs,
        write_to_file=args.write_to_file,
        capture_length=args.capture_length,
        history_length=args.history_length,
    )

    try:
        while True:
            if not tracker.process_frame():
                break
            elif cv2.waitKey(1) & 0xFF == ord('q'): 
                break
    finally:
        tracker.close()
