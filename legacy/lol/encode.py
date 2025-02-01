import datetime
import enum

import arrow


def bson_ready(a_dict):
    keys_to_delete = set()
    modifications = {}
    for key, val in a_dict.items():
        if isinstance(val, enum.Enum):
            a_dict[key] = val.value
        elif isinstance(val, arrow.Arrow):
            a_dict[key] = val.datetime
        elif isinstance(val, datetime.timedelta):
            a_dict[key] = val.seconds
        elif isinstance(val, list):
            bson_ready_list(val)
        elif isinstance(val, dict):
            bson_ready(val)

        if isinstance(key, int):
            modifications[str(key)] = val
            keys_to_delete.add(key)

    for key, val in modifications.items():
        a_dict[key] = val
    for key in keys_to_delete:
        del a_dict[key]


def bson_ready_list(a_list):
    for i, val in enumerate(a_list):
        if isinstance(val, enum.Enum):
            a_list[i] = val.value
        elif isinstance(val, arrow.Arrow):
            a_list[i] = val.datetime
        elif isinstance(val, datetime.timedelta):
            a_list[i] = val.seconds
        elif isinstance(val, list):
            bson_ready_list(val)
        elif isinstance(val, dict):
            bson_ready(val)
