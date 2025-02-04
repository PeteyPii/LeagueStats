import datetime
import enum

import arrow


def json_ready(a_dict):
    new = {}
    for key, val in a_dict.items():
        if isinstance(key, int):
            key = str(key)

        if isinstance(val, enum.Enum):
            new[key] = val.value
        elif isinstance(val, datetime.timedelta):
            new[key] = val.seconds
        elif isinstance(val, arrow.Arrow):
            new[key] = val.datetime.timestamp()
        elif isinstance(val, list):
            new[key] = json_ready_list(val)
        elif isinstance(val, dict):
            new[key] = json_ready(val)
        else:
            new[key] = val

    return new


def json_ready_list(a_list):
    new = []
    for val in a_list:
        if isinstance(val, enum.Enum):
            new.append(val.value)
        elif isinstance(val, datetime.timedelta):
            new.append(val.seconds)
        elif isinstance(val, arrow.Arrow):
            new.append(val.datetime.timestamp())
        elif isinstance(val, list):
            new.append(json_ready_list(val))
        elif isinstance(val, dict):
            new.append(json_ready(val))
        else:
            new.append(val)

    return new
