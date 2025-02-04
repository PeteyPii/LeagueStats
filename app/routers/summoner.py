import asyncio

import cassiopeia as cass
import fastapi
import pydantic
from datapipelines import common as dp_common
from fastapi import status
from psycopg import errors
from psycopg.types import json

from app import db, model, settings

router = fastapi.APIRouter()


class CreateTrackedSummonerRequest(pydantic.BaseModel):
    name: str
    tagline: str
    region: cass.Region


@router.post("/v1/summoners")
async def create_tracked_summoner(request: CreateTrackedSummonerRequest) -> model.TrackedSummoner:
    loop = asyncio.get_running_loop()
    try:
        account = cass.Account(name=request.name, tagline=request.tagline, region=request.region)
        await loop.run_in_executor(None, account.load)
    except dp_common.NotFoundError:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Account not found")

    try:
        summoner = account.summoner
        await loop.run_in_executor(None, summoner.load)
    except dp_common.NotFoundError:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Summoner not found")

    try:
        async with await db.async_connect() as conn:
            async for item in await conn.execute(
                """
                    INSERT INTO tracked_summoners(account_data, summoner_data)
                    VALUES (%s, %s)
                    RETURNING id, account_data, summoner_data;
                """,
                (json.Jsonb(account.to_dict()), json.Jsonb(summoner.to_dict())),
            ):
                return model.TrackedSummoner.model_construct(**item)
    except errors.UniqueViolation:
        return fastapi.HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already exists")

    return fastapi.HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == "__main__":
    settings.apply_global_settings()
    asyncio.run(
        create_tracked_summoner(
            CreateTrackedSummonerRequest(name="BasicBananas", tagline="000", region=cass.Region.north_america)
        )
    )
