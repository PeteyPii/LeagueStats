import cassiopeia as cass
import collections
import time

from datapipelines.common import NotFoundError
from lol import command
from lol.flags.match_filtering import MatchFilteringFlags
from lol.flags.region import RegionFlag
from lol.flags.table_output import TableOutputFlags


def full_matchups_table(command):
  counts = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
  champion_list = sorted(cass.get_champions(region=command.region_flag.value), key=lambda c: c.name)

  pipeline = command.match_filtering_flags.filter_steps()
  for match in command.db.matches.aggregate(pipeline):
    for participant_as in match['participants']:
      for participant_against in match['participants']:
        if participant_as['side'] == participant_against['side']:
          continue
        stats = counts[participant_as['championId']][participant_against['championId']]
        stats['games_played'] += 1
        stats['wins'] += participant_as['stats']['win']

  table = []
  for champ_as in champion_list:
    row = collections.OrderedDict()
    row['Champ As vs. Against'] = champ_as.name
    for champ_against in champion_list:
      stats = counts[champ_as.id][champ_against.id]
      if not stats.get('games_played'):
        row[champ_against.name] = '-'
      else:
        win_rate = float(stats['wins']) / stats['games_played']
        row[champ_against.name] = f'{stats["wins"]} / {stats["games_played"]} ({100 * win_rate:.3f})'
    table.append(row)
  return table


class MatchupsCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)
    self.table_output_flags = TableOutputFlags(self)
    self.region_flag = RegionFlag(self)

  def help_message(self):
    return (f'Usage: {self._PROGRAM} {self.name}\n'
            'Prints winrates of champions when facing with/against others.')

  def _run_impl(self, args):
    if len(args) != 0:
      return self.print_invalid_usage()

    table = full_matchups_table(self)
    self.table_output_flags.output_table(table)


class CurrentMatchupsCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)
    self.table_output_flags = TableOutputFlags(self)
    self.register_flag(
        command.Flag(name='wait',
                     default=True,
                     is_boolean=True,
                     description='Whether to wait for the summoner to be in a match.'))

  def help_message(self):
    return (f'Usage: {self._PROGRAM} {self.name} <summoner_name>\n'
            'Prints winrates of champion matchups in the current game.')

  def _run_impl(self, args):
    if len(args) != 1:
      return self.print_invalid_usage()

    summoner_name = args[0]

    match = None
    while match is None:
      try:
        match = cass.get_current_match(summoner_name)
      except NotFoundError:
        if not self.flag('wait'):
          print(f'{summoner_name} is not in a match.')
          return
        time.sleep(15)

    for team in match.teams:
      team.participants.sort(key=lambda p: p.summoner.name)

    is_team_0 = False
    for participant in match.teams[0].participants:
      if summoner_name == participant.summoner.name:
        is_team_0 = True
        break

    if not is_team_0:
      match.teams[0], match.teams[1] = match.teams[1], match.teams[0]

    full_table = full_matchups_table(self)
    champ_name_to_matchups = {}
    for row in full_table:
      champ_name_to_matchups[row['Champ As vs. Against']] = row

    table = []
    for participant_as in match.teams[0].participants:
      row = collections.OrderedDict()
      row['Champ As vs. Against'] = f'{participant_as.summoner.name} ({participant_as.champion.name})'
      for participant_against in match.teams[1].participants:
        row[f'{participant_against.summoner.name} ({participant_against.champion.name})'] = \
            champ_name_to_matchups[participant_as.champion.name][participant_against.champion.name]
      table.append(row)

    self.table_output_flags.output_table(table)
