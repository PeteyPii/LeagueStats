import cassiopeia as cass
import collections
import tabulate
import datapipelines

from lol import command


class MostSeenCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name} <summoner_name> [top_n]\n'
        'Lists the most seen summoners in games with the specified summoner.'
    )

  def _run_impl(self, args, **kwargs):
    if len(args) < 1 or len(args) > 2:
      return self.print_invalid_usage()

    summoner_name = args[0]
    n = 50
    if len(args) == 2:
      n = int(args[1])

    try:
      summoner = cass.Summoner(name=summoner_name).load()
    except datapipelines.common.NotFoundError:
      print(f'Summoner "{summoner_name}" not found.')
      return

    counts = collections.defaultdict(lambda: collections.defaultdict(int))
    for match in self.db.matches.find({'participants.accountId': summoner.account_id}):
      for participant in match['participants']:
        if participant['accountId'] == summoner.account_id:
          team = participant['side']
          break
      for participant in match['participants']:
        if counts[participant['accountId']]['name'] == 0:
          counts[participant['accountId']]['name'] = set([participant['summonerName']])
        else:
          if False:
            counts[participant['accountId']]['name'].add(participant['summonerName'])
        counts[participant['accountId']]['games_played'] += 1
        same_team = team == participant['side']
        counts[participant['accountId']]['same_team'] += int(same_team)
        if same_team:
          counts[participant['accountId']]['wins_with'] += int(participant['stats']['win'])
        else:
          counts[participant['accountId']]['wins_against'] += int(not participant['stats']['win'])

    table = []
    for stats in counts.values():
      if stats['same_team'] > 0:
        win_rate_with = float(stats['wins_with']) / stats['same_team']
        wins_with = f'{stats["wins_with"]} / {stats["same_team"]} ({100 * win_rate_with:.3f})'
      else:
        wins_with = '-'

      if stats['same_team'] != stats['games_played']:
        win_rate_against = float(stats['wins_against']) / (stats['games_played'] - stats['same_team'])
        wins_against = f'{stats["wins_against"]} / {stats["games_played"] - stats["same_team"]} ({100 * win_rate_against:3f})'
      else:
        wins_against = '-'

      table.append(collections.OrderedDict([
          ('Summoner', ','.join(stats['name'])),
          ('Games Played', stats['games_played']),
          ('Wins With', wins_with),
          ('Wins Against', wins_against),
      ]))

    table.sort(key=lambda i: i['Games Played'])
    table.reverse()
    print(tabulate.tabulate(table[:n], headers='keys'))
