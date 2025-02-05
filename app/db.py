import hashlib
import logging
from typing import Any, Sequence

import psycopg as pg

from app import settings

logger = logging.getLogger(__name__)

_CREATE_HASHED_KEY = """
CREATE TABLE IF NOT EXISTS hashed_key (
    hashed_key  BYTEA
);
"""

_CREATE_TRACKED_SUMMONERS = """
CREATE TABLE IF NOT EXISTS tracked_summoners (
    id                      BIGSERIAL PRIMARY KEY,
    account_data            JSONB NOT NULL,
    summoner_data           JSONB NOT NULL,
    last_updated_match_id   TEXT
);
"""

_CREATE_TRACKED_SUMMONERS_INDICES = (
    """
CREATE UNIQUE INDEX IF NOT EXISTS idx_tracked_summoners_account_data_puuid ON tracked_summoners (
    (account_data -> 'puuid')
)
NULLS NOT DISTINCT;
""",
    """
CREATE UNIQUE INDEX IF NOT EXISTS idx_tracked_summoners_summoner_data_puuid ON tracked_summoners (
    (summoner_data -> 'puuid')
)
NULLS NOT DISTINCT;
""",
)

_CREATE_MATCHES = """
CREATE TABLE IF NOT EXISTS matches (
    id                      BIGSERIAL PRIMARY KEY,
    match_data              JSONB NOT NULL
);
"""

_CREATE_MATCHES_INDICES = (
    """
CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_uniqueness ON matches (
    (match_data -> 'region'),
    (match_data -> 'continent'),
    (match_data -> 'platform'),
    (match_data -> 'matchId'),
    (match_data -> 'id')
)
NULLS NOT DISTINCT;
""",
)


class InvalidRiotApiKeyError(Exception):
    pass


class MissingRiotApiKeyError(Exception):
    pass


def init():
    logger.info("Initializing DB")
    with connect() as conn:
        for query in (_CREATE_HASHED_KEY, _CREATE_TRACKED_SUMMONERS, _CREATE_MATCHES):
            conn.execute(query)
        for query in _CREATE_TRACKED_SUMMONERS_INDICES:
            conn.execute(query)
        for query in _CREATE_MATCHES_INDICES:
            conn.execute(query)

    insert_riot_api_key()


def validate_riot_api_key() -> True:
    expected_row = {"hashed_key": hashlib.sha256(settings.riot_api_key().encode()).digest()}
    with connect() as conn:
        for actual_row in conn.execute("SELECT hashed_key FROM hashed_key LIMIT 1"):
            if actual_row != expected_row:
                raise InvalidRiotApiKeyError("DB created with a different API key.")
            return True
    raise MissingRiotApiKeyError("DB has no API key.")


def insert_riot_api_key():
    try:
        if validate_riot_api_key():
            return
    except MissingRiotApiKeyError:
        hashed_key = hashlib.sha256(settings.riot_api_key().encode()).digest()
        with connect() as conn:
            conn.execute("INSERT INTO hashed_key VALUES (%s)", (hashed_key,))


class DictRowFactory:
    def __init__(self, cursor: pg.Cursor[Any]):
        if cursor.description:
            self.fields = [c.name for c in cursor.description]
        else:
            self.fields = []

    def __call__(self, values: Sequence[Any]) -> dict[str, Any]:
        return dict(zip(self.fields, values))


def connect(autocommit: bool = True) -> pg.Connection:
    return pg.Connection.connect(**settings.sql_conn_settings(), autocommit=autocommit, row_factory=DictRowFactory)


async def async_connect(autocommit: bool = True) -> pg.AsyncConnection:
    return await pg.AsyncConnection.connect(
        **settings.sql_conn_settings(), autocommit=autocommit, row_factory=DictRowFactory
    )


if __name__ == "__main__":
    init()
