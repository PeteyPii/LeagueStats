import functools
from tracemalloc import Snapshot

import cassiopeia as cass
import datapipelines
import pymongo

from lol import command, encode
from lol.commands import update_matches


@functools.cache
def _get_puuid_by_account_id(account_id, region):
  try:
    return cass.Summoner(account_id=account_id, region=region).puuid
  except datapipelines.NotFoundError:
    return None


@functools.cache
def _get_puuid_by_summoner_id(summoner_id, region):
  try:
    return cass.Summoner(id=summoner_id, region=region).puuid
  except datapipelines.NotFoundError:
    return None


@functools.cache
def _get_puuid_by_name(summoner_name, region):
    try:
        return cass.Summoner(name=summoner_name, region=region).puuid
    except datapipelines.NotFoundError:
        return None


class BackfillMatchParticipantPuuidsCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (f'Usage: {self._PROGRAM} {self.name}\n'
            'Updates databases for use with Riot API v5.')

  def is_expert_command(self):
    return True

  def _run_impl(self, args):
    if len(args) != 0:
      return self.print_invalid_usage()

    account_id_to_puuid = {}

    count = 0
    for match in self.db.matches.find():
      missing_data = False
      for participant in match['participants']:
        if participant.get('accountId') == '0':  # BOT account
          continue

        if 'puuid' not in participant:
          missing_data = True
        elif 'accountId' in participant:
          try:
            account_id_to_puuid[participant['accountId']] = participant['puuid']
          except:
            raise Exception('Something bad happened')

      if missing_data:
        count += 1

    print(f'Missing data for {count} matches.')

    with self.mongo_client.start_session() as session:
      match_cursor = self.db.matches.find(no_cursor_timeout=True, session=session).batch_size(100)
      for match in match_cursor:
        updated_match = False
        for participant in match['participants']:
          if participant.get('accountId') == '0':  # BOT account
            continue

          if 'puuid' not in participant:
            region = cass.Region.from_platform(match['platformId'])
            puuid = account_id_to_puuid.get(participant['accountId'])
            if not puuid:
              puuid = _get_puuid_by_account_id(participant['accountId'], region=region)
            if not puuid:
              puuid = _get_puuid_by_summoner_id(participant['summonerId'], region=region)
            if not puuid:
              puuid = _get_puuid_by_name(participant['summonerName'], region=region)

            if not puuid:
              raise Exception('Something bad happened')

            participant['puuid'] = puuid
            updated_match = True

        if updated_match:
          print('Updated match')
          self.db.matches.replace_one({'_id': match['_id']}, match)
