import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio
import ast

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

DEFINE_MOVE_KEY = "robot::define_move" # single move : separated to be defined
MOVE_LIST_KEY = "robot::move_list" #list of move ids [move1, move2]
EXECUTE_FLAG_KEY = "robot::execute_flag" # binary 0 or 1 to execute all in move_list_key
MOVE_EXECUTED_KEY = "robot::move_executed" #A list of move_id executed

def read_data(file_path):
    data = []
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file, delimiter='\t')
            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
    return data

def publish_to_redis(data, rate_hz=30):
    for row in data:
        timestamp = row.pop('timestamp', None)
        for key, value in row.items():
            new_key = "mmp_panda::" + key.split("::")[2]
            redis_client.set(new_key, value)
        print(timestamp)
        time.sleep(1.0 / rate_hz)

def execute_move(move_id):
    print("executing ", move_id)
    file_path = f"recordings/{move_id}_interpolated.txt"
    data = read_data(file_path)
    if data:
        publish_to_redis(data, rate_hz=120)

def replay_moves():
    while True:
        execute_flag = redis_client.get(EXECUTE_FLAG_KEY)
        if execute_flag == "1": 
            print("Begining move execution")
            move_list = redis_client.get(MOVE_LIST_KEY)
            for i in range(len(move_list)):
                move_id = move_list[i]
                next_move = move_list[i + 1] if i + 1 < len(move_list) else None
                execute_move(move_id, next_move)
                redis_client.rpush(MOVE_EXECUTED_KEY, move_id)
                interpolate_between_moves(move_id, next_move)
            print("Done with move execution!")
            redis_client.set(EXECUTE_FLAG_KEY, "0")
        
replay_moves()
