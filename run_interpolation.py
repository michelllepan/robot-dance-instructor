import argparse
import os

import numpy as np

from src.utils import read_log, write_log, interpolate_trajectory


def main(filename: str, smoothness: float = 0.2, frequency: int = 120):
    log = read_log(filename)
    interpolated_log = {}

    timestamps = log["timestamp"]
    start, end = timestamps[0], timestamps[-1]
    num_points = int((end - start) * frequency)

    interpolated_log["timestamp"] = np.linspace(start, end, num_points)

    for key in log:
        if key == "timestamp":
            continue
        interpolated_log[key] = interpolate_trajectory(
            trajectory=log[key],
            num_points=num_points,
            smoothness=smoothness)

    interpolated_filename = filename.strip(".txt") + "_interpolated.txt"
    write_log(interpolated_filename, interpolated_log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str)
    parser.add_argument("--smoothness", "-s", type=float, default=0.2)
    args = parser.parse_args()

    main(filename=args.filename, smoothness=args.smoothness)