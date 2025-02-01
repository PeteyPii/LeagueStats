import cassiopeia as cass

from lol import common_flag
from lol.command import Flag

QUEUE_ID_MAPPINGS = {
    "aram": [cass.Queue.aram],
    "ranked": [cass.Queue.ranked_flex_fives, cass.Queue.ranked_solo_fives],
    "normal": [cass.Queue.normal_draft_fives, cass.Queue.blind_fives],
    "urf": [cass.Queue.deprecated_all_random_urf, cass.Queue.all_random_urf_snow],
    "clash": [cass.Queue.clash],
}


class QueuesFlag(common_flag.CommonFlag):

    def __init__(self, command):
        super().__init__(
            Flag(
                name="queue",
                default="aram",
                description='Filters matches to those for the given queues (e.g. "aram,ranked").',
            ),
            command,
        )

    def filter_steps(self):
        if not self.command.flag("queue"):
            return []
        queues = sum((QUEUE_ID_MAPPINGS[q.lower()] for q in self.command.flag("queue").split(",")), [])
        queue_ids = list(set(q.id for q in queues))
        return [{"$match": {"queue": {"$in": queue_ids}}}]
