import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio

HISTORY_FILE = 'recordings/history.txt'  # Output file for the data

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

DEFINE_MOVE_KEY = "robot::define_move"
MOVE_LIST_KEY = "robot::move_list"
EXECUTE_FLAG_KEY = "robot::execute_flag"
MOVE_EXECUTED_KEY = "robot::move_executed"

RIGID_BODY_POSITION_KEYS = [
    "sai2::realsense::left_hand",
    "sai2::realsense::right_hand",
    "sai2::realsense::center_hips"
]
        
PANDA_RIGHT_HAND_POS = "mmp_panda::right_hand"
PANDA_LEFT_HAND_POS = "mmp_panda::realsense::left_hand"
PANDA_CENTER_HIPS_POS = "mmp_panda::realsense::center_hips"
move_id = input("enter move name: ")
move_ids = []
move_ids.append(move_id)
input("press enter to start recording")
start = time.time()
input("press enter to stop recording")
stop = time.time()
move = str(move_id) + ':' + str(start) + ':' + str(stop)
print("MOVE IS " + move)

redis_client.set(DEFINE_MOVE_KEY, str(move)) # single move to be defined
redis_client.set(MOVE_LIST_KEY, str(move_ids))

input("Press enter to start move replay!")
redis_client.set(EXECUTE_FLAG_KEY, "1")

# print(type(move[0]))
# redis_client.rpush(DEFINE_MOVE_KEY, move[0])
# redis_client.rpush(MOVE_LIST_KEY, move_id)
# redis_client.set(EXECUTE_FLAG_KEY, "1")