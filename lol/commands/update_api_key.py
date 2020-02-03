import cassiopeia as cass
import pymongo
import datapipelines

from lol import command
from lol import encode
from lol.commands import update_matches


class UpdateApiKeyCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name}\n'
        'Updates databases for use with a new API key.'
    )

  def run(self, args):
    if len(args) != 0:
      return self.print_invalid_usage()

    # --- PART 1 ---
    for summoner in self.db.summoners.find():
      new_summoner = cass.Summoner(name=summoner['name']).load()
      data = new_summoner.to_dict()
      data['last_updated_match_id'] = summoner['last_updated_match_id']
      if self.db.temp_summoners.find_one({'puuid': summoner['puuid']}):
        pass
      try:
        self.db.temp_summoners.insert_one(data)
      except pymongo.errors.DuplicateKeyError:
        pass

    already_updated_count = 0
    full_renew_count = 0
    partial_renew_count = 0
    partial_renew_failures = 0

    match_cursor = self.db.matches.find(no_cursor_timeout=True)
    for match in match_cursor:
      if self.db.temp_matches.find_one({'id': match['id']}):
        already_updated_count += 1
        continue
      try:
        match = cass.Match(id=match['id'], region=match['region']).load()
        match_data = match.to_dict()
        encode.bson_ready(match_data)
        update_matches.prune_match_data(match_data)
        full_renew_count += 1
        self.db.temp_matches.insert_one(match_data)
      except datapipelines.common.NotFoundError:
        print(f'Match {match["id"]} not found.')
        match['partial_migration'] = True
        for i, participant in enumerate(match['participants']):
          try:
            # Potentially someone could have switched their summoner name and
            # a different account could have stolen it but it is unlikely and
            # not very important for our purposes.
            summoner = cass.Summoner(name=participant['summonerName']).load()
            participant['summonerId'] = summoner.id
            participant['currentAccountId'] = summoner.account_id
            participant['accountId'] = summoner.account_id
            partial_renew_count += 1
          except datapipelines.common.NotFoundError:
            # Summoner changed their name and so our IDs will be incorrect, oh
            # well...
            print(f'Summoner "{participant["summonerName"]}" changed names.')
            partial_renew_failures += 1
        self.db.temp_matches.insert_one(match)
    match_cursor.close()

    print(f'White: {already_updated_count}, green: {full_renew_count}, '
          f'yellow: {partial_renew_count}, red: {partial_renew_failures}')

    # # -- PART 2 ---
    self.db.matches.rename('old_matches')
    self.db.summoners.rename('old_summoners')
    self.db.temp_matches.rename('matches')
    self.db.temp_summoners.rename('summoners')

    print('Don\'t forget to manually update the collection indices!')
