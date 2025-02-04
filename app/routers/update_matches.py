import asyncio
import logging
import threading
import time

import cassiopeia as cass
import fastapi
import pydantic
from datapipelines import common as dp_common
from psycopg import errors
from psycopg.types import json

from app import async_utils, db, encode, settings

router = fastapi.APIRouter()

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


async def _update_matches_locked():
    loop = asyncio.get_running_loop()
    async with await db.async_connect() as conn:
        async for row in await conn.execute("SELECT id, summoner_data, last_updated_match_id FROM tracked_summoners"):
            id = row["id"]
            puuid = row["summoner_data"]["puuid"]
            region = row["summoner_data"]["region"]
            last_updated_match_id = row["last_updated_match_id"]
            summoner = cass.Summoner(puuid=puuid, region=region)
            latest_match_id = None
            async for match in async_utils.iterate_blocking(summoner.match_history):
                if str(match.id) == last_updated_match_id:
                    break
                if latest_match_id is None:
                    latest_match_id = match.id

                try:
                    await loop.run_in_executor(None, match.load)
                except dp_common.NotFoundError:
                    logger.warning(f"Could not retrieve data for {match}")
                    continue

                try:
                    await conn.execute(
                        "INSERT INTO matches(match_data) VALUES (%s)",
                        (json.Jsonb(encode.json_ready(match.to_dict())),),
                    )
                except errors.UniqueViolation:
                    logger.debug(f"Tried to insert duplicate {match}.")
                    continue

            if latest_match_id is not None:
                logger.info(f"Updated new matches for {row["summoner_data"]["name"]}")
                await conn.execute(
                    "UPDATE tracked_summoners SET last_updated_match_id = %s WHERE id = %s",
                    (latest_match_id, id),
                )


async def update_matches():
    if not _LOCK.acquire(blocking=False):
        return

    try:
        await _update_matches_locked()
    finally:
        _LOCK.release()


@router.post("/v1/update_matches")
async def update_matches_handler(
    _: pydantic.BaseModel, background_tasks: fastapi.BackgroundTasks
) -> pydantic.BaseModel:
    background_tasks.add_task(update_matches)
    return pydantic.BaseModel()


async def update_matches_loop(interval_seconds: int | float | None = None):
    if interval_seconds is None:
        interval_seconds = settings.get_dict()["updater"]["interval_seconds"]
    while True:
        start_time = time.monotonic()
        await update_matches()
        end_time = time.monotonic()
        if end_time - start_time > 0:
            await asyncio.sleep(interval_seconds - (end_time - start_time))


if __name__ == "__main__":
    settings.apply_global_settings()
    asyncio.run(update_matches())
