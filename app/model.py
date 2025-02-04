from typing import Any

import pydantic


class Empty(pydantic.BaseModel):
    pass


class TrackedSummoner(pydantic.BaseModel):
    id: int
    account_data: dict[str, Any]
    summoner_data: dict
    last_updated_match_id: str | None
