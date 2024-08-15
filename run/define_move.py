import os
import time

from instructor.utils import get_config, make_redis_client


def main():
    cfg = get_config()
    redis_client = make_redis_client()

    move_name = input("enter move name: ")
    input("press enter to start recording")
    start = time.time()
    input("press enter to stop recording")
    stop = time.time()

    move = f"{move_name}:{start}:{stop}"
    print("move is " + move)
    redis_client.set(cfg["redis"]["keys"]["define_move"], move)


if __name__ == "__main__":
    main()
