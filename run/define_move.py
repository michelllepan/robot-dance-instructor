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

    input("press enter to play move")
    redis_client.delete(cfg["redis"]["keys"]["move_list"])
    redis_client.lpush(cfg["redis"]["keys"]["move_list"], move_name)
    redis_client.set(cfg["redis"]["keys"]["execute_flag"], 1)


if __name__ == "__main__":
    main()
