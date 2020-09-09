import cassiopeia as cass
import collections
import tabulate
# import datapipelines

from lol import command
from lol.flags.match_filtering import MatchFilteringFlags


class MatchupsCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name}\n'
        'Prints winrates of champions when facing with/against others.'
    )

  def _run_impl(self, args):
    if len(args) != 0:
      return self.print_invalid_usage()

    counts = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    champion_list = sorted(cass.get_champions(), key=lambda c: c.name)
    champ_id_to_name = {champ.id: champ.name for champ in champion_list}

    pipeline = self.match_filtering_flags.filter_steps() + [
     #  {'$match': {'participants.accountId': summoner.account_id}},
    ]
    for match in self.db.matches.aggregate(pipeline):
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

    print(tabulate.tabulate(table, headers='keys'))
