import datetime
import enum
import logging
import re
from typing import Any

import cassiopeia as cass
import pymongo
from bson import int64
from psycopg import errors
from psycopg.types import json

from app import db, settings

logger = logging.getLogger(__name__)

EXPECTED_MATCH_FIELD_TYPES = {}
EXPECTED_PARTICIPANT_FIELD_TYPES = {}
EXPECTED_STATS_FIELD_TYPES = {}

OK_EXTRA_PARTICIPANT_FIELDS = {"masteries", "legacy_runes"}
OK_MISSING_PARTICIPANT_FIELDS = {
    # no idea
    "placement",
    "subteamPlacement",
    "playerSubteamId",
    "playerAugment1",
    "playerAugment2",
    "playerAugment3",
    "playerAugment4",
    "playerAugment5",
    "playerAugment6",
    # Prefer lowercase
    "PlayerScore0",
    "PlayerScore1",
    "PlayerScore2",
    "PlayerScore3",
    "PlayerScore4",
    "PlayerScore5",
    "PlayerScore6",
    "PlayerScore7",
    "PlayerScore8",
    "PlayerScore9",
    "PlayerScore10",
    "PlayerScore11",
    # Ping counts not tracked before
    "allInPings",
    "assistMePings",
    "basicPings",
    "baitPings",
    "commandPings",
    "dangerPings",
    "enemyMissingPings",
    "enemyVisionPings",
    "getBackPings",
    "holdPings",
    "needVisionPings",
    "onMyWayPings",
    "pushPings",
    "retreatPings",
    "visionClearedPings",
    # Wasn't tracked before
    "teamPosition",
    "individualPosition",
    "challenges",
    "riotIdTagline",
    "riotIdName",
    "teamEarlySurrendered",
    "endedInEarlySurrender",
    "endedInSurrender",
    "eligibleForProgression",
    "totalAllyJungleMinionsKilled",
    "totalEnemyJungleMinionsKilled",
    # Really old wasnt tracked
    "perks",
    "stat_perks",
    # After partial update
    "masteries",
    "legacy_runes",
}

OK_EXTRA_STATS_FIELDS = {
    "firstInhibitorAssist",
    "firstInhibitorKill",
    "neutralMinionsKilledEnemyJungle",
    "neutralMinionsKilledTeamJungle",
}
OK_MISSING_STATS_FIELDS = {
    "baronKills",
    "bountyLevel",
    "champExperience",
    "championTransform",
    "consumablesPurchased",
    "damageDealtToBuildings",
    "detectorWardsPlaced",
    "dragonKills",
    "firstBloodAssist",
    "firstBloodKill",
    "firstInhibitorAssist",
    "firstInhibitorKill",
    "firstTowerAssist",
    "firstTowerKill",
    "inhibitorsLost",
    "inhibitorTakedowns",
    "itemsPurchased",
    "lane",
    "neutralMinionsKilledEnemyJungle",
    "neutralMinionsKilledTeamJungle",
    "nexusKills",
    "nexusLost",
    "nexusTakedowns",
    "objectivesStolen",
    "objectivesStolenAssists",
    "role",
    "spell1Casts",
    "spell2Casts",
    "spell3Casts",
    "spell4Casts",
    "summoner1Casts",
    "summoner2Casts",
    "timePlayed",
    "totalDamageShieldedOnTeammates",
    "totalHealsOnTeammates",
    "totalTimeSpentDead",
    "turretsLost",
    "turretTakedowns",
    "wardsKilled",
    "wardsPlaced",
}


class DuplicateLegacyMatchError(Exception):
    pass


class GarbageInputError(Exception):
    pass


class ExtraFieldsAfterFixingError(Exception):
    pass


class MissingFieldsAfterFixingError(Exception):
    pass


class IncorrectTypeAfterFixingError(Exception):
    pass


def del_if_present(d: dict[str, Any], k: str):
    if k in d:
        del d[k]


def set_fallback(d: dict[str, Any], k: str, fallback_val: Any):
    if k not in d:
        d[k] = fallback_val


def fix_match(m: dict[str, Any]):
    if m["id"] == 0:
        raise GarbageInputError("match has id == 0")

    del m["_id"]
    if "platformId" in m:
        m["platform"] = m["platformId"]
        del m["platformId"]
    if "season" in m:
        del m["season"]
    if "region" in m:
        m["platform"] = cass.Platform.from_region(m["region"])
        del m["region"]
    if "continent" not in m:
        m["continent"] = cass.Platform(m["platform"]).continent

    if isinstance(m["id"], str):
        re_match = re.match(r"(.*)_(.*)", m["id"])
        m["id"] = int(re_match.group(2))
        m["matchId"] = int(re_match.group(2))

    if "matchId" not in m:
        m["matchId"] = m["id"]

    if "name" not in m:
        m["name"] = ""
    if "privateGame" not in m:
        m["privateGame"] = False
    if "tournamentCode" not in m:
        m["tournamentCode"] = ""
    if "endOfGameResult" not in m:
        m["endOfGameResult"] = "GameComplete"

    if "gameDuration" not in m:
        m["gameDuration"] = m["duration"]
    if isinstance(m["creation"], datetime.datetime):
        m["creation"] = m["creation"].timestamp()
    if "start" not in m:
        m["start"] = m["creation"]
    if isinstance(m["start"], datetime.datetime):
        m["start"] = m["start"].timestamp()
    if "gameStartTimestamp" not in m:
        m["gameStartTimestamp"] = int(m["start"] * 1000)
    if "gameEndTimestamp" not in m:
        m["gameEndTimestamp"] = m["gameStartTimestamp"] + m["duration"] * 1000

    for p in m["participants"]:
        fix_participant(p)

    if m.keys() - EXPECTED_MATCH_FIELD_TYPES.keys():
        raise ExtraFieldsAfterFixingError("match has extra fields ", m.keys() - EXPECTED_MATCH_FIELD_TYPES.keys())
    if EXPECTED_MATCH_FIELD_TYPES.keys() - m.keys():
        raise MissingFieldsAfterFixingError("match has missing fields ", EXPECTED_MATCH_FIELD_TYPES.keys() - m.keys())

    for key in m:
        if isinstance(m[key], int64.Int64):
            m[key] = int(m[key])

        if isinstance(m[key], enum.Enum):
            m[key] = m[key].value

        if type(m[key]) != EXPECTED_MATCH_FIELD_TYPES[key]:
            raise IncorrectTypeAfterFixingError(f"match[{key}] is type {type(m[key])}")


def fix_participant(p: dict[str, Any]):
    if p["championId"] > 3000:
        raise GarbageInputError("unknown champion")

    if p.get("accountId") == "0":
        set_fallback(p, "isBot", True)
        set_fallback(p, "puuid", "A_BOT")
        set_fallback(p, "summonerId", "A_BOT")
    else:
        set_fallback(p, "isBot", False)

    del_if_present(p, "timeline")
    if not p["platformId"]:
        p["platformId"] = p["currentPlatformId"]
    del_if_present(p, "currentPlatformId")
    del_if_present(p, "currentAccountId")
    del_if_present(p, "accountId")
    del_if_present(p, "rankLastSeason")

    set_fallback(p, "participantId", p.get("id"))
    del_if_present(p, "id")

    set_fallback(p, "riotIdGameName", p.get("summonerId"))
    p["platformId"] = p["platformId"].upper()
    if p["platformId"] in cass.Region:
        p["platformId"] = cass.Platform.from_region(p["platformId"])
    set_fallback(
        p, "championName", cass.Champion(id=p.get("championId"), region=cass.Platform(p["platformId"]).region).name
    )

    if "stat_runes" in p:
        p["stat_perks"] = {
            "offense": p["stat_runes"][0],
            "flex": p["stat_runes"][1],
            "defense": p["stat_runes"][2],
        }
        del p["stat_runes"]
    if "runes" in p:
        if isinstance(p["runes"], list):
            p["legacy_runes"] = p["runes"]
        else:
            p["perks"] = p["runes"]
        del p["runes"]
    if "currenPlatformId" in p:
        del p["currentPlatformId"]

    if "missions" not in p:
        p["missions"] = {f"playerScore{i}": p["stats"].get(f"playerScore{i}", 0) for i in range(12)}

    for i in range(12):
        set_fallback(p, f"playerScore{i}", p["stats"].get("playerScore{i}", 0))
        del_if_present(p["stats"], f"playerScore{i}")

    fix_stats(p["stats"])

    if p.keys() - EXPECTED_PARTICIPANT_FIELD_TYPES.keys() - OK_EXTRA_PARTICIPANT_FIELDS:
        raise ExtraFieldsAfterFixingError(
            "participant has extra fields ",
            p.keys() - EXPECTED_PARTICIPANT_FIELD_TYPES.keys() - OK_EXTRA_PARTICIPANT_FIELDS,
        )
    if EXPECTED_PARTICIPANT_FIELD_TYPES.keys() - OK_MISSING_PARTICIPANT_FIELDS - p.keys():
        raise MissingFieldsAfterFixingError(
            "participant has missing fields ",
            EXPECTED_PARTICIPANT_FIELD_TYPES.keys() - OK_MISSING_PARTICIPANT_FIELDS - p.keys(),
        )

    for key in p:
        if isinstance(p[key], int64.Int64):
            p[key] = int(p[key])

        if isinstance(p[key], enum.Enum):
            p[key] = p[key].value

        if key in OK_EXTRA_PARTICIPANT_FIELDS:
            continue

        if type(p[key]) != EXPECTED_PARTICIPANT_FIELD_TYPES[key]:
            raise IncorrectTypeAfterFixingError(f"participant[{key}] is type {type(p[key])}")


def fix_stats(s: dict[str, Any]):
    old_s = {k: v for k, v in s.items()}

    del_if_present(s, "participantId")
    del_if_present(s, "perkPrimaryStyle")
    del_if_present(s, "perkSubStyle")
    del_if_present(s, "objectivePlayerScore")
    del_if_present(s, "combatPlayerScore")
    del_if_present(s, "totalPlayerScore")
    del_if_present(s, "totalScoreRank")
    if s.get("turretKills", -1) is None:
        s["turretKills"] = 0
    if s.get("inhibitorKills", -1) is None:
        s["inhibitorKills"] = 0
    if s.get("nexusKills", -1) is None:
        s["nexusKills"] = 0
    if s.get("turretTakedowns", -1) is None:
        s["turretTakedowns"] = 0
    if s.get("inhibitorTakedowns", -1) is None:
        s["inhibitorTakedowns"] = 0
    if s.get("nexusTakedowns", -1) is None:
        s["nexusTakedowns"] = 0

    if "magicalDamageTaken" in s:
        s["magicDamageTaken"] = s["magicalDamageTaken"]
        del s["magicalDamageTaken"]

    if "totalTimeCrowdControlDealt" in s:
        s["totalTimeCCDealt"] = s["totalTimeCrowdControlDealt"]
        del s["totalTimeCrowdControlDealt"]

    if s.keys() - EXPECTED_STATS_FIELD_TYPES.keys() - OK_EXTRA_STATS_FIELDS:
        raise ExtraFieldsAfterFixingError(
            "stats has extra fields ", s.keys() - EXPECTED_STATS_FIELD_TYPES.keys() - OK_EXTRA_STATS_FIELDS
        )
    if EXPECTED_STATS_FIELD_TYPES.keys() - OK_MISSING_STATS_FIELDS - s.keys():
        raise MissingFieldsAfterFixingError(
            "stats has missing fields ", EXPECTED_STATS_FIELD_TYPES.keys() - OK_MISSING_STATS_FIELDS - s.keys()
        )

    for key in s:
        if isinstance(s[key], int64.Int64):
            s[key] = int(s[key])

        if isinstance(s[key], enum.Enum):
            s[key] = s[key].value

        if key in OK_EXTRA_STATS_FIELDS:
            continue

        if type(s[key]) != EXPECTED_STATS_FIELD_TYPES[key]:
            raise IncorrectTypeAfterFixingError(f"stats[{key}] is type {type(s[key])}")


def determine_expected_field_types():
    with db.connect() as conn:
        for row in conn.execute("SELECT id, match_data as m FROM matches"):
            current_m = row["m"]
            for field in current_m:
                EXPECTED_MATCH_FIELD_TYPES[field] = type(current_m[field])
            if all(p["isBot"] for p in current_m["participants"]):
                logger.warning(f"Deleting match {row["id"]} since it has all bots")
                conn.execute("DELETE FROM matches WHERE id = %s", (row["id"],))
            for participant in current_m["participants"]:
                for field in participant:
                    EXPECTED_PARTICIPANT_FIELD_TYPES[field] = type(participant[field])
                for field in participant["stats"]:
                    EXPECTED_STATS_FIELD_TYPES[field] = type(participant["stats"][field])


def import_legacy():
    determine_expected_field_types()

    client = pymongo.MongoClient()
    with client.start_session() as session, db.connect() as conn:
        match_cursor = client.lol.matches.find(no_cursor_timeout=True, session=session).batch_size(100)
        matches_processed = 0
        dupes_found = 0
        seen_ids = set()
        for match_data in match_cursor:
            try:
                fix_match(match_data)
                if match_data["id"] in seen_ids:
                    raise DuplicateLegacyMatchError(f"Match {match_data["id"]} seen multiple times")
                conn.execute(
                    "INSERT INTO matches(match_data) VALUES (%s)",
                    (json.Jsonb(match_data),),
                )
                seen_ids.add(match_data["id"])
                matches_processed += 1
                if matches_processed % 100 == 0:
                    logger.info(f"Processed {matches_processed} matches so far...")
            except errors.UniqueViolation:
                dupes_found += 1
                logger.debug(f"Tried to insert duplicate {match_data["id"]}")
                continue
            except GarbageInputError as e:
                # Don't import garbage data
                logger.error(e)
                continue
            except DuplicateLegacyMatchError as e:
                logger.error(e)
                continue

        logger.info(f"Processed {matches_processed} matches total")
        logger.info(f"Ignored {dupes_found} existing matches")


if __name__ == "__main__":
    settings.apply_global_settings()
    import_legacy()
