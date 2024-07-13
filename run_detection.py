import argparse
from datetime import datetime

import cv2
import numpy as np
import redis

from src.camera import RealSenseCamera
from src.detector import MediaPipeDetector


REDIS_POS_KEY = "sai2::realsense::"
STREAMING_POINTS = ["left_hand", "right_hand", "center_hips"]

def main(
    stream_outputs: bool,
    write_to_file: bool,
):
    camera = RealSenseCamera()
    detector = MediaPipeDetector()
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

    if write_to_file:
        header = ["timestamp"] + [REDIS_POS_KEY + p for p in STREAMING_POINTS]
        file_string = "\t".join(header)

    while True:
        depth_frame, color_frame = camera.get_frames()

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

        detection_result = detector.run_detection(color_image)
        color_image = detector.draw_landmarks_on_image(color_image, detection_result)
        depth_colormap = detector.draw_landmarks_on_image(depth_colormap, detection_result)
        images = np.hstack((color_image, depth_colormap))

        landmark_dict = detector.parse_landmarks(detection_result)

        def get_depth_at_pixel(x, y):
            x, y = int(x * width), int(y * height)
            if x < 0 or x >= width or y < 0 or y >= height:
                return -1
            else:
                return 1e-3 * depth_image[x, y]

        if write_to_file:
            file_string += "\n" + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        for key in landmark_dict:
            landmark = landmark_dict[key]
            depth = get_depth_at_pixel(landmark[0], landmark[1])
            
            if depth == -1:
                landmark_dict[key] = None
                print(f"{key: <15}   null")
            else:
                # focal length of RealSense d435i: 640px
                landmark[0] = width * (landmark[0] - 0.5) * (depth / 640)
                landmark[1] = height * (landmark[1] - 0.5) * (depth / 640)
                landmark[2] = depth

                if stream_outputs and key in STREAMING_POINTS:
                    redis_client.set(REDIS_POS_KEY + key, str(landmark))
                if write_to_file and key in STREAMING_POINTS:
                    file_string += "\t[" + ", ".join(map(str, landmark)) + "]"

                print(f"{key: <15}   x: {landmark[0]: 3.2f}  y: {landmark[1]: 3.2f}  z: {landmark[2]: 3.2f}")
                
        print()

        cv2.imshow("RealSense", images)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    if write_to_file:
        with open(datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt", "w") as file:
            file.write(file_string)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream_outputs", "-s", action="store_true")
    parser.add_argument("--write_to_file", "-w", action="store_true")
    args = parser.parse_args()
    main(stream_outputs=args.stream_outputs, write_to_file=args.write_to_file)
