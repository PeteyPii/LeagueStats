from typing import Any

import pydantic


class TrackedSummoner(pydantic.BaseModel):
    id: int
    account_data: dict[str, Any]
    summoner_data: dict
    last_updated_match_id: str | None
