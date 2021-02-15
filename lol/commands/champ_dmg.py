import collections

import cassiopeia as cass
import statistics
from lol import command
from lol.flags.match_filtering import MatchFilteringFlags
from lol.flags.table_output import TableOutputFlags


class ChampionDmgCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)
    self.table_output_flags = TableOutputFlags(self)

  def help_message(self):
    return f'Usage: {self._PROGRAM} {self.name}\n' 'Outputs each champ\'s damage relative to others within a game.'

  def _run_impl(self, args):
    if len(args) != 0:
      return self.print_invalid_usage()

    champ_stats = collections.defaultdict(lambda: dict(games_played=0, top_dmg=0, pct_of_top_dmg=[]))

    pipeline = self.match_filtering_flags.filter_steps()
    for match in self.db.matches.aggregate(pipeline):
      each_dmg = [p['stats']['totalDamageDealtToChampions'] for p in match['participants']]
      highest_dmg = max(each_dmg)
      for participant in match['participants']:
        champ_stats[participant['championId']]['games_played'] += 1
        dmg = participant['stats']['totalDamageDealtToChampions']
        champ_stats[participant['championId']]['pct_of_top_dmg'].append(float(dmg) / highest_dmg)
        if dmg == highest_dmg:
          champ_stats[participant['championId']]['top_dmg'] += 1

    champion_list = cass.get_champions()
    champ_id_to_name = {champ.id: champ.name for champ in champion_list}

    table = []
    for champ_id, champ_name in sorted(champ_id_to_name.items(), key=lambda t: t[1]):
      if champ_stats[champ_id]['games_played'] > 0:
        most_dmg_games = f'{100.0 * champ_stats[champ_id]["top_dmg"] / champ_stats[champ_id]["games_played"] :.3f}%'
        relative_top_dmg = f'{100.0 * statistics.mean(champ_stats[champ_id]["pct_of_top_dmg"]) :.3f}%'
      else:
        most_dmg_games = '-'
        relative_top_dmg = '-'
      table.append(
          collections.OrderedDict([
              ('Champion', champ_name),
              ('Games Played', champ_stats[champ_id]['games_played']),
              ('Highest Damage Games', most_dmg_games),
              ('Average Relative Top Damage', relative_top_dmg),
          ]))

    self.table_output_flags.output_table(table)
