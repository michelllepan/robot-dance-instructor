import argparse

import cv2
import numpy as np

from src.camera import RealSenseCamera
from src.detector import MediaPipeDetector


def main(stream_outputs: bool = False):
    camera = RealSenseCamera()
    detector = MediaPipeDetector()
    
    while True:
        depth_frame, color_frame = camera.get_frames()

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        
        depth_colormap_dim = depth_colormap.shape
        color_colormap_dim = color_image.shape

        if depth_colormap_dim != color_colormap_dim:
            color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]), interpolation=cv2.INTER_AREA)

        detection_result = detector.run_detection(color_image)
        color_image = detector.draw_landmarks_on_image(color_image, detection_result)
        depth_colormap = detector.draw_landmarks_on_image(depth_colormap, detection_result)
        images = np.hstack((color_image, depth_colormap))

        cv2.imshow("RealSense", images)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream_outputs", "-s", action="store_true")
    args = parser.parse_args()
    main(stream_outputs=args.stream_outputs)
