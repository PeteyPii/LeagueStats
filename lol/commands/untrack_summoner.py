import cassiopeia as cass
import datapipelines

from lol import command


class UntrackSummonerCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name} <summoner_name>\n'
        'Removes a summoner from being tracked when running the "update" command.'
    )

  def _run_impl(self, args, **kwargs):
    if len(args) != 1:
      return self.print_invalid_usage()

    summoner_name = args[0]
    try:
      summoner = cass.Summoner(name=summoner_name).load()
      match = {'puuid': summoner.puuid}
    except datapipelines.common.NotFoundError:
      print(f'Summoner "{summoner_name}" does not exist. Attempting to match document by name (case-sensitive) in case the summoner name changed...')
      match = {'name': summoner_name}

    result = self.db.summoners.delete_one(match)
    if not result.deleted_count:
      print(f'Summoner "{summoner_name}" is already not tracked.')
