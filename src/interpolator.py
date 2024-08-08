import argparse
import os

import numpy as np
from scipy import interpolate

from .utils import read_log, write_log


def interpolate_trajectory(
    trajectory: np.ndarray,
    num_points: int,
    smoothness: float = 0.2,
) -> np.ndarray:
    trajectory = np.unique(trajectory, axis=0)
    x, y, z = trajectory[:, 0], trajectory[:, 1], trajectory[:, 2]
    tck, u = interpolate.splprep([x, y, z], s=smoothness)
    x_i, y_i, z_i = interpolate.splev(np.linspace(0, 1, num_points), tck)
    return np.vstack([x_i, y_i, z_i]).T


def interpolate_file(
    filename: str,
    smoothness: float = 0.2,
    frequency: int = 120,
):
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

    interpolate_file(filename=args.filename, smoothness=args.smoothness)