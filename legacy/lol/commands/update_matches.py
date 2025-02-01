import cassiopeia as cass
import datapipelines

from lol import command, encode


def prune_match_data(match_data):
  for team in match_data['teams']:
    # Available from match_data['participants']
    del team['participants']

  for participant in match_data['participants']:
    # Who cares?
    if 'matchHistoryUri' in participant:
      del participant['matchHistoryUri']


class UpdateMatchesCommand(command.Command):

    def __init__(self, name):
        super().__init__(name)

    def help_message(self):
        return (
            f"Usage: {self._PROGRAM} {self.name}\n"
            "Updates the database with the matches for all summoners being tracked."
        )

    def _run_impl(self, args):
        if args:
            return self.print_invalid_usage()

        for summoner in self.db.summoners.find():
            print(f'Updating matches for {summoner["name"]}...')
            last_updated_match_id = summoner["last_updated_match_id"]
            summoner = cass.Summoner(puuid=summoner["puuid"], region=summoner["region"])
            matches_to_insert = []
            latest_match_id = None
            for match in summoner.match_history:
                if latest_match_id is None:
                    latest_match_id = match.id
                if match.id == last_updated_match_id:
                    break
                if self.db.matches.find_one({"id": match.id}) is None:
                    try:
                        match_data = match.load().to_dict()
                        encode.bson_ready(match_data)
                        prune_match_data(match_data)
                        matches_to_insert.append(match_data)
                    except datapipelines.common.NotFoundError:
                        print(f"Failed to load match ID {match.id}")

            if matches_to_insert:
                self.db.matches.insert_many(matches_to_insert)
            self.db.summoners.update(
                {"puuid": summoner.puuid}, {"$set": {"last_updated_match_id": latest_match_id}}, upsert=False
            )
