import datetime
import re
from typing import Any

import cassiopeia as cass
import pydantic
from psycopg import sql


class Empty(pydantic.BaseModel):
    pass


class Summoner(pydantic.BaseModel):
    name: str
    tagline: str
    region: cass.Region

    model_config = pydantic.ConfigDict(frozen=True)

    def encode(self):
        return f"{self.name}#{self.tagline} [{self.region.value}]"

    @classmethod
    def decode(cls, s: str):
        match = re.match(r"()#() (\[.*\])", s)
        if match is None:
            raise ValueError(f"'{s}' is not a valid summoner encoding")
        return cls.model_construct(name=match.group(1), tagline=match.group(2), region=match.group(3))


class MatchFilters(pydantic.BaseModel):
    region: cass.Region | None = None
    queue: cass.Queue | None = None
    after: datetime.datetime | None = None
    before: datetime.datetime | None = None

    def sql_filter_expression(self, src_table: str = "matches"):
        conjunctions = []
        if self.region is not None:
            conjunctions.append(
                sql.SQL("{0}.match_data -> 'platformId' = {1}").format(
                    sql.Identifier(src_table), sql.Placeholder("MatchFilters.region")
                )
            )
        if self.queue is not None:
            conjunctions.append(
                sql.SQL("{0}.match_data -> 'queue' = {1}").format(
                    sql.Identifier(src_table), sql.Placeholder("MatchFilters.queue")
                )
            )
        if self.after is not None:
            conjunctions.append(
                sql.SQL("{0}.match_data -> 'start' >= {1}").format(
                    sql.Identifier(src_table), sql.Placeholder("MatchFilters.after")
                )
            )
        if self.before is not None:
            conjunctions.append(
                sql.SQL("{0}.match_data -> 'start' <= {1}").format(
                    sql.Identifier(src_table), sql.Placeholder("MatchFilters.before")
                )
            )
        if not conjunctions:
            return sql.SQL("TRUE")

        return sql.SQL(" AND ").join(conjunctions)

    def sql_filter_params(self) -> dict[str, Any]:
        return {
            "MatchFilters.region": cass.Platform.from_region(self.region).value if self.region is not None else None,
            "MatchFilters.queue": self.queue.id if self.queue is not None else None,
            "MatchFilters.after": self.after,
            "MatchFilters.before": self.before,
        }
