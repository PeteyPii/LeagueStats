import pymongo

from lol.commands import champ_dmg
from lol.commands import champ_kdas
from lol.commands import champ_pbs
from lol.commands import champ_winrates
from lol.commands import help_cmd
from lol.commands import list_summoners
from lol.commands import matchups
from lol.commands import most_seen
from lol.commands import track_summoner
from lol.commands import untrack_summoner
from lol.commands import update_api_key
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
    command_map.register_command(update_api_key.UpdateApiKeyCommand('update_api_key'))
    command_map.register_command(champ_winrates.ChampionWinratesCommand('winrates'))
    command_map.register_command(champ_kdas.ChampionKdasCommand('kdas'))
    command_map.register_command(champ_pbs.ChampionPersonalBestsCommand('pbs'))
    command_map.register_command(most_seen.MostSeenCommand('most_seen'))
    command_map.register_command(matchups.MatchupsCommand('matchups'))
    command_map.register_command(matchups.CurrentMatchupsCommand('current_matchups'))
    command_map.register_command(champ_dmg.ChampionDmgCommand('damage'))

    client = pymongo.MongoClient()
    for _, command in command_map.commands.items():
      command.set_mongo_client(client)

    return command_map
