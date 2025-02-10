import asyncio
from typing import Any

import cassiopeia as cass
import fastapi
import pydantic
from datapipelines import common as dp_common
from fastapi import status
from psycopg import errors
from psycopg.types import json

from app import db, model, settings

router = fastapi.APIRouter()


class AccountNotFoundError(Exception):
    pass


class CreateTrackedSummonerRequest(model.Summoner):
    pass


class TrackedSummoner(pydantic.BaseModel):
    id: int
    account_data: dict[str, Any]
    summoner_data: dict
    last_updated_match_id: str | None


async def get_loaded_account(summoner_info: model.Summoner) -> cass.Account:
    loop = asyncio.get_running_loop()
    try:
        account = cass.Account(name=summoner_info.name, tagline=summoner_info.tagline, region=summoner_info.region)
        await loop.run_in_executor(None, account.load)
    except dp_common.NotFoundError:
        AccountNotFoundError("Account not found")

    try:
        summoner = account.summoner
        await loop.run_in_executor(None, summoner.load)
    except dp_common.NotFoundError:
        AccountNotFoundError("Summoner not found")

    return account


@router.post("/v1/summoners")
async def create_tracked_summoner(request: CreateTrackedSummonerRequest) -> TrackedSummoner:
    try:
        account = await get_loaded_account(request)
    except AccountNotFoundError as e:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        async with await db.async_connect() as conn:
            async for item in await conn.execute(
                """
                    INSERT INTO tracked_summoners(account_data, summoner_data)
                    VALUES (%s, %s)
                    RETURNING id, account_data, summoner_data;
                """,
                (json.Jsonb(account.to_dict()), json.Jsonb(account.summoner.to_dict())),
            ):
                return TrackedSummoner.model_construct(**item)
    except errors.UniqueViolation:
        raise fastapi.HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already exists")

    return fastapi.HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == "__main__":
    settings.apply_global_settings()
    asyncio.run(
        create_tracked_summoner(
            CreateTrackedSummonerRequest(name="BasicBananas", tagline="000", region=cass.Region.north_america)
        )
    )
