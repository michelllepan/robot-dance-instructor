import argparse
from datetime import datetime
from typing import Sequence

import cv2

from instructor.detection import RealSenseCamera, MediaPipeDetector, PoseTracker


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream_outputs", "-s", action="store_true")
    args = parser.parse_args()

    tracker = PoseTracker(stream_outputs=args.stream_outputs,)
    while True:
        if not tracker.process_frame():
            break
        elif cv2.waitKey(1) & 0xFF == ord('q'): 
            break
