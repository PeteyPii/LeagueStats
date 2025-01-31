import cassiopeia as cass
import collections
import datapipelines

from lol import command
from lol.flags.match_filtering import MatchFilteringFlags
from lol.flags.region import RegionFlag
from lol.flags.table_output import TableOutputFlags


class MostSeenCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)
    self.table_output_flags = TableOutputFlags(self)
    self.region_flag = RegionFlag(self)
    self.register_flag(
        command.Flag(name='list_name_changes',
                     default=False,
                     is_boolean=True,
                     description='Lists all the names for every summoner.'))

  def help_message(self):
    return (f'Usage: {self._PROGRAM} {self.name} <summoner_name> [top_n]\n'
            'Lists the most seen summoners in games with the specified summoner.')

  def _run_impl(self, args):
    if len(args) < 1 or len(args) > 2:
      return self.print_invalid_usage()

    summoner_name = args[0]
    n = 50
    if len(args) == 2:
      n = int(args[1])

    try:
      summoner = cass.Summoner(name=summoner_name, region=self.region_flag.value).load()
    except datapipelines.common.NotFoundError:
      print(f'Summoner "{summoner_name}" not found.')
      return

    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    pipeline = self.match_filtering_flags.filter_steps() + [
      {'$match': {'participants.puuid': summoner.puuid}},
    ]  # yapf: disable
    for match in self.db.matches.aggregate(pipeline):
      for participant in match['participants']:
        if participant['puuid'] == summoner.puuid:
          team = participant['side']
          break
      for participant in match['participants']:
        if participant['puuid'] == '0':  # BOT account
          continue
        if not counts[participant['puuid']]['name']:
          counts[participant['puuid']]['name'] = set([participant['summonerName']])
        elif self.flag('list_name_changes'):
          counts[participant['puuid']]['name'].add(participant['summonerName'])
          pass
        counts[participant['puuid']]['games_played'] += 1
        same_team = team == participant['side']
        counts[participant['puuid']]['same_team'] += int(same_team)
        if same_team:
          counts[participant['puuid']]['wins_with'] += int(participant['stats']['win'])
        else:
          counts[participant['puuid']]['wins_against'] += int(not participant['stats']['win'])

    table = []
    for stats in counts.values():
      if stats['same_team'] > 0:
        win_rate_with = float(stats['wins_with']) / stats['same_team']
        wins_with = f'{stats["wins_with"]} / {stats["same_team"]} ({100 * win_rate_with:.3f})'
      else:
        wins_with = '-'

      if stats['same_team'] != stats['games_played']:
        win_rate_against = float(stats['wins_against']) / (stats['games_played'] - stats['same_team'])
        wins_against = f'{stats["wins_against"]} / {stats["games_played"] - stats["same_team"]} ({100 * win_rate_against:.3f})'
      else:
        wins_against = '-'

      table.append(
          collections.OrderedDict([
              ('Summoner', ','.join(stats['name'])),
              ('Games Played', stats['games_played']),
              ('Wins With', wins_with),
              ('Wins Against', wins_against),
          ]))

    table.sort(key=lambda i: i['Games Played'])
    table = table[-n:]
    table.reverse()
    self.table_output_flags.output_table(table)
