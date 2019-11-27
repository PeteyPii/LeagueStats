import cassiopeia as cass
import pymongo

from lol import command


class UpdateSummonersCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name}\n'
        'Updates the summoner info for all summoners that are being tracked.'
    )

  def run(self, args):
    if len(args) != 0:
      return self.print_invalid_usage()

    for summoner in self.db.summoners.find():
      updated_summoner = cass.Summoner(puuid=summoner['puuid']).load()
      self.db.summoners.update({'puuid': summoner['puuid']}, {'$set': updated_summoner.to_dict()})
