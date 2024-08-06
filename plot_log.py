import argparse

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

from src.utils import read_log, write_log, interpolate_trajectory


def main(filename: str, key: str):
    log = read_log(filename)
    points = log["sai2::realsense::" + key].T

    timestamps = np.array(log["timestamp"])
    timestamps = (timestamps - timestamps[0]) / (timestamps[-1] - timestamps[0])
        
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(points[0], points[2], points[1], color="gray")
    ax.scatter(points[0], points[2], points[1], c=timestamps)
    ax.scatter(points[0][0], points[2][0], points[1][0], color="red")
    ax.tick_params(axis='both', which='major', labelsize=8)

    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_zlabel("y")

    plt.locator_params(axis='both', nbins=5) 
    plt.title(key)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str)
    parser.add_argument("key", type=str)
    args = parser.parse_args()

    main(filename=args.filename, key=args.key)