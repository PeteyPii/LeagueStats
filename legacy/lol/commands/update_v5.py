import cassiopeia as cass
import datapipelines
import pymongo

from lol import command, encode
from lol.commands import update_matches


class UpdateV5Command(command.Command):

    def __init__(self, name):
        super().__init__(name)

    def help_message(self):
        return f"Usage: {self._PROGRAM} {self.name}\n" "Updates databases for use with Riot API v5."

    def is_expert_command(self):
        return True

    def _run_impl(self, args):
        if len(args) != 0:
            return self.print_invalid_usage()

        match_cursor = self.db.matches.find(no_cursor_timeout=True)
        for match in match_cursor:
            try:
                if match["id"] != match["matchId"]:
                    print(f'{match["id"]} -> {match["matchId"]}')
                    old_id = match["id"]
                    match["id"] = match["matchId"]
                    self.db.matches.replace_one({"id": old_id}, match)
            except KeyError:
                continue
