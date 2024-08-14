import argparse

from instructor.mapping.interpolator import interpolate_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str)
    parser.add_argument("--smoothness", "-s", type=float, default=0.2)
    args = parser.parse_args()

    interpolate_file(filename=args.filename, smoothness=args.smoothness)