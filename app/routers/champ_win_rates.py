import asyncio
import logging
import pprint

import cassiopeia as cass
import fastapi
import pydantic
from datapipelines import common as dp_common
from psycopg import sql

from app import db, model, settings, validation
from app.routers import summoner as summoner_api

router = fastapi.APIRouter()

logger = logging.getLogger(__name__)

_GLOBAL_QUERY = sql.SQL(
    """
WITH map_step AS (
    SELECT match_data, JSONB_ARRAY_ELEMENTS(match_data -> 'participants') as participants
    FROM matches
), filter_step AS (
    SELECT *
    FROM map_step
    WHERE {filter_expr}
), reduce_step AS (
    SELECT
        (participants->'championId')::int AS champ_id,
        ANY_VALUE(participants->>'championName') AS champ_name,
        ANY_VALUE(match_data) AS match_data,
        SUM((participants->'stats'->'win')::bool::int) AS wins,
        COUNT(*) AS games
    FROM filter_step
    GROUP BY participants->'championId')
SELECT
    champ_id,
    champ_name,
    match_data->>'platform' AS platform,
    wins,
    games,
    wins::float/games AS win_rate
FROM reduce_step;
"""
)

_PER_SUMMONER_QUERY = sql.SQL(
    """
WITH map_step AS (
    SELECT match_data, JSONB_ARRAY_ELEMENTS(match_data -> 'participants') as participants
    FROM matches
), filter_step AS (
    SELECT *
    FROM map_step
    WHERE {filter_expr}
        AND participants->>'puuid' = ANY(%(puuid_list)s)
), reduce_step AS (
    SELECT
        participants->>'puuid' AS puuid,
        (participants->'championId')::int AS champ_id,
        ANY_VALUE(participants->>'championName') AS champ_name,
        ANY_VALUE(match_data) AS match_data,
        SUM((participants->'stats'->'win')::bool::int) AS wins,
        COUNT(*) AS games
    FROM filter_step
    GROUP BY puuid, participants->'championId')
SELECT
    puuid,
    champ_id,
    champ_name,
    match_data->>'platform' AS platform,
    wins,
    games,
    wins::float/games AS win_rate
FROM reduce_step;
"""
)


class ChampionWinRatesRequest(pydantic.BaseModel):
    summoners: list[model.Summoner] = pydantic.Field(default_factory=list)
    match_filters: model.MatchFilters = pydantic.Field(default_factory=model.MatchFilters)


class ChampionWinRate(pydantic.BaseModel):
    wins: int = 0
    games: int = 0
    rate: float = 0.0


class PerChampionWinRates(pydantic.BaseModel):
    per_champ: dict[str, ChampionWinRate] = pydantic.Field(default_factory=dict)


class PerSummonerWinRates(pydantic.BaseModel):
    per_summoner: dict[str, PerChampionWinRates] = pydantic.Field(default_factory=dict)


@router.post("/v1/query/champion_win_rates")
async def get_champ_win_rates(request: ChampionWinRatesRequest) -> PerSummonerWinRates:
    if not validation.are_unique(request.summoners):
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="Duplicate summoner")

    accounts: list[cass.Account] = []
    loop = asyncio.get_running_loop()
    summoner_map: dict[str, model.Summoner] = {}
    for summoner in request.summoners:
        try:
            accounts.append(await summoner_api.get_loaded_account(summoner))
            summoner_map[accounts[-1].puuid] = summoner
        except summoner_api.AccountNotFoundError as e:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(e))

    if not validation.are_unique(a.puuid for a in accounts):
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="Duplicate account")

    result = PerSummonerWinRates()
    global_win_rates = PerChampionWinRates()
    async with await db.async_connect() as conn:
        async for row in await conn.execute(
            _GLOBAL_QUERY.format(filter_expr=request.match_filters.sql_filter_expression()),
            request.match_filters.sql_filter_params(),
        ):
            try:
                champ = cass.Champion(id=row["champ_id"], region=cass.Region.from_platform(row["platform"]))
                champ_name = await loop.run_in_executor(None, lambda: champ.name)
            except dp_common.NotFoundError as e:
                champ_name = row["champ_name"]

            global_win_rates.per_champ[champ_name] = ChampionWinRate(
                wins=row["wins"], games=row["games"], rate=row["win_rate"]
            )
        result.per_summoner["*"] = global_win_rates

        async for row in await conn.execute(
            _PER_SUMMONER_QUERY.format(filter_expr=request.match_filters.sql_filter_expression()),
            request.match_filters.sql_filter_params() | {"puuid_list": [a.puuid for a in accounts]},
        ):
            try:
                champ = cass.Champion(id=row["champ_id"], region=cass.Region.from_platform(row["platform"]))
                champ_name = await loop.run_in_executor(None, lambda: champ.name)
            except dp_common.NotFoundError as e:
                champ_name = row["champ_name"]

            summoner_key = summoner_map[row["puuid"]].encode()

            if summoner_key not in result.per_summoner:
                result.per_summoner[summoner_key] = PerChampionWinRates()
            result.per_summoner[summoner_key].per_champ[champ_name] = ChampionWinRate(
                wins=row["wins"], games=row["games"], rate=row["win_rate"]
            )

    return result


if __name__ == "__main__":
    settings.apply_global_settings()
    logger.debug("Running /v1/query/champion_win_rates")
    result = asyncio.run(
        get_champ_win_rates(
            ChampionWinRatesRequest(
                summoners=[model.Summoner(name="BasicBananas", tagline="000", region=cass.Region.north_america)],
            )
        )
    )

    pprint.pprint(result.model_dump())
