import pymongo

from lol.commands import champ_winrates
from lol.commands import champ_kdas
from lol.commands import help_cmd
from lol.commands import list_summoners
from lol.commands import many_champ_winrates
from lol.commands import track_summoner
from lol.commands import untrack_summoner
from lol.commands import update_matches
from lol.commands import update_summoners


class CommandMap(object):
  def __init__(self):
    self.commands = {}

  def register_command(self, command):
    if command.name in self.commands:
      raise RuntimeError(f'Command "{command.name}" is already registered')
    self.commands[command.name] = command

  @staticmethod
  def get_default():
    command_map = CommandMap()

    command_map.register_command(help_cmd.HelpCommand('help', command_map))
    command_map.register_command(track_summoner.TrackSummonerCommand('track'))
    command_map.register_command(untrack_summoner.UntrackSummonerCommand('untrack'))
    command_map.register_command(list_summoners.ListSummonersCommand('list_summoners'))
    command_map.register_command(update_matches.UpdateMatchesCommand('update'))
    command_map.register_command(update_summoners.UpdateSummonersCommand('update_summoners'))
    command_map.register_command(champ_winrates.ChampionWinratesCommand('winrates'))
    command_map.register_command(many_champ_winrates.ManyChampionWinratesCommand('many_winrates'))
    command_map.register_command(champ_kdas.ChampionKdasCommand('kdas'))

    client = pymongo.MongoClient()
    for name, command in command_map.commands.items():
      command.set_mongo_client(client)

    return command_map
