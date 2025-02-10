import asyncio
import functools
import json
import logging.config
import sys
from typing import Any

import cassiopeia as cass

from app import db

SETTINGS_PATH = "settings.json"

logger = logging.getLogger(__name__)

@functools.cache
def get_dict():
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def riot_api_key() -> str:
    return get_dict()["pipeline"]["RiotAPI"]["api_key"]


def default_region() -> cass.Region:
    return cass.Region(get_dict()["global"]["default_region"])


def sql_conn_settings() -> dict[str, Any]:
    return get_dict()["sql"]["connection"]


def notifiarr_settings() -> dict[str, Any]:
    return get_dict()["notifiarr"]


def apply_global_settings():
    logging.config.dictConfig(get_dict()["logging"])
    cass.apply_settings(SETTINGS_PATH)

    db.validate_riot_api_key()

    if sys.platform == "win32":
        # Default doesn't work with psycopg3
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
