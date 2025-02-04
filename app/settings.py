import asyncio
import functools
import json
import sys
from typing import Any

import cassiopeia as cass

SETTINGS_PATH = "settings.json"


@functools.cache
def get_dict():
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def riot_api_key() -> str:
    return get_dict()["pipeline"]["RiotAPI"]["api_key"]


def sql_conn_settings() -> dict[str, Any]:
    return get_dict()["sql"]["connection"]


def notifiarr_settings() -> dict[str, Any]:
    return get_dict()["notifiarr"]


def apply_global_settings():
    if sys.platform == "win32":
        # Default doesn't work with psycop3
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    cass.apply_settings(SETTINGS_PATH)
