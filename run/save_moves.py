import redis
import time
import os
import csv
from datetime import datetime, timedelta
import asyncio
from instructor.moves.interpolation import interpolate_file
from instructor.utils import get_config, make_redis_client

cfg = get_config()
redis_client = make_redis_client()

recordings_dir = cfg["dirs"]["recordings"]
history_file = os.path.join(recordings_dir, "history.txt")

DEFINE_MOVE_KEY = cfg["redis"]["keys"]["define_move"]

def get_move_data(): #define single move
    move_data = redis_client.get(DEFINE_MOVE_KEY)
    
    parts = move_data.split(':')
    move_id = parts[0]
    start_time = float(parts[1])
    stop_time = float(parts[2])
    return {
        'move_id': move_id,
        'start_time': start_time,
        'stop_time': stop_time
    }

def extract_coordinates_for_move(start_time, stop_time):
    coordinates = []
    with open(history_file, 'r') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
            if start_time <= timestamp <= stop_time:
                coordinates.append(row)
    return coordinates

def save_move_coordinates(move_id, coordinates):
    output_file = f"recordings/{move_id}.txt"
    with open(output_file, 'w') as file:
        writer = csv.DictWriter(file, fieldnames=coordinates[0].keys(), delimiter='\t')
        writer.writeheader()
        writer.writerows(coordinates)

def process_moves():
    move = {}
    while True:
        move = redis_client.get(DEFINE_MOVE_KEY)
        if move:
            parts = move.split(':')
            move_id = parts[0]
            start_time = datetime.fromtimestamp(float(parts[1]))
            stop_time = datetime.fromtimestamp(float(parts[2]))
            coordinates = extract_coordinates_for_move(start_time, stop_time)
            if coordinates:
                save_move_coordinates(move_id, coordinates) # save move txt
                # Remove the processed move from the Redis list
                redis_client.set(DEFINE_MOVE_KEY, "")
            
                output_file = os.path.join(recordings_dir, move_id + ".txt")
                print("saved to " + output_file)
                interpolate_file(output_file, cfg["smoothness"], frequency=cfg["rate"])

process_moves()
