import cassiopeia as cass
import pymongo
import datapipelines

from lol import command
from lol.flags.region import RegionFlag


class TrackSummonerCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)
    self.region_flag = RegionFlag(self)

  def help_message(self):
    return (f'Usage: {self._PROGRAM} {self.name} <summoner_name>\n'
            'Adds a summoner to be tracked when running the "update" command.')

  def _run_impl(self, args):
    if len(args) != 1:
      return self.print_invalid_usage()

    summoner_name = args[0]
    try:
      summoner = cass.Summoner(name=summoner_name, region=self.region_flag.value).load()
    except datapipelines.common.NotFoundError:
      print(f'Summoner "{summoner_name}" not found.')
      return

    data = summoner.to_dict()
    data['last_updated_match_id'] = None
    try:
      self.db.summoners.insert_one(data)
    except pymongo.errors.DuplicateKeyError:
      print(f'Summoner "{summoner_name}" is already being tracked.')
