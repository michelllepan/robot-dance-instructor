from datetime import datetime
from typing import Dict

import numpy as np


def read_log(filename: str) -> Dict[str, np.ndarray]:
    with open(filename, "r") as f:
        print("reading log from " + filename)
        lines = f.readlines()

        headers = lines[0].strip("\n").split("\t")
        log = {h: [] for h in headers}
        
        for l in lines[1:]:
            cols = l.strip("\n").split("\t")
            for i, val in enumerate(cols):
                if i == 0:
                    # handle timestamp
                    dt = datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f")
                    log[headers[i]].append(datetime.timestamp(dt))
                else:
                    # handle coordinates
                    log[headers[i]].append(np.array(eval(val)))

        for key in log:
            if key == "timestamp":
                continue
            log[key] = np.vstack(log[key])
        return log


def write_log(filename: str, log: Dict[str, np.ndarray]):
    # write headers
    out_string = "\t".join(log.keys())

    # write log data
    for entry in zip(*log.values()):
        dt = datetime.fromtimestamp(entry[0])
        out_string += "\n" + dt.strftime("%Y-%m-%d %H:%M:%S.%f")

        for e in entry[1:]:
            out_string += "\t[" + ", ".join(map(str, e)) + "]"

    with open(filename, "w") as f:
        f.write(out_string)
        print("writing log to " + filename)
