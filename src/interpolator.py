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
    trajectory, indices = np.unique(trajectory, axis=0, return_index=True)
    trajectory = trajectory[np.argsort(indices)]
    x, y, z = trajectory[:, 0], trajectory[:, 1], trajectory[:, 2]
    tck, u = interpolate.splprep([x, y, z], s=smoothness)
    x_i, y_i, z_i = interpolate.splev(np.linspace(0, 1, num_points), tck)
    interpolated = np.vstack([x_i, y_i, z_i]).T

    # rescale to within joint limits
    # x: (0.4, 0.6)
    # y: (-0.5, 0.5)
    # z: (0.05, 0.85)
    # array_min = interpolated.min(axis=0)
    # normalized = (interpolated - array_min) / (interpolated - array_min).max(axis=0)

    # normalized *= np.array([1.0, 0.8, 0.1])
    # normalized += np.array([-0.5, 0.05, 0.45])
    # return normalized

    return interpolated


def interpolate_between_moves(
    move1: str,
    move2: str,
    smoothness: float = 0.2,
):
    log1 = read_log(f"recordings/{move1}_interpolated.txt")
    log2 = read_log(f"recordings/{move2}_interpolated.txt")    

    interpolated_log = {}
    interpolated_log["timestamp"] = np.linspace(0, 1, 360)

    for key in log1:
        if key == "timestamp":
            continue

        start = log1[key][-1]
        end = log2[key][0]

        # interpolated_log[key] = interpolate_trajectory(
        #     trajectory=np.array([start, end]),
        #     num_points=360,
        #     smoothness=smoothness)
        interpolated_log[key] = np.linspace(start, end, 360)
        
    filename = f"recordings/{move1}_to_{move2}.txt"
    write_log(filename, interpolated_log)


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