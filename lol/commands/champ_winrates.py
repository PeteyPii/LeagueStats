import cassiopeia as cass
import datapipelines

from lol import command
from lol.flags.match_filtering import MatchFilteringFlags
from lol.flags.table_output import TableOutputFlags


class ChampionWinratesCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)
    self.table_output_flags = TableOutputFlags(self)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name} <summoner_name>\n'
        'Outputs a summoner\'s winrate on all of the champions they have played.'
    )

  def _run_impl(self, args):
    if len(args) != 1:
      return self.print_invalid_usage()

    summoner_name = args[0]
    if not summoner_name:
      print(f'Summoner name cannot be empty.')
      return
    try:
      summoner = cass.Summoner(name=summoner_name).load()
    except datapipelines.common.NotFoundError:
      print(f'Summoner "{summoner_name}" not found.')
      return

    pipeline = self.match_filtering_flags.filter_steps() + [
        {'$project': {'participants': True}},
        {'$unwind': '$participants'},
        {'$match': {'participants.accountId': summoner.account_id}},
        {'$group': {'_id': {'championId': '$participants.championId'},
                    'games_played': {'$sum': 1},
                    'wins': {'$sum': {'$cond': ['$participants.stats.win', 1, 0]}}}},
        {'$addFields': {'win_rate': {'$divide': ['$wins', '$games_played']}}},
        {'$sort': {'win_rate': -1}},
    ]

    champion_list = cass.get_champions()
    champ_id_to_name = {champ.id: champ.name for champ in champion_list}
    table = [{
      'Champion': champ_id_to_name[result['_id']['championId']],
      'Wins': result['wins'],
      'Games Played': result['games_played'],
      'Win %': 100.0 * result['win_rate'],
    } for result in self.db.matches.aggregate(pipeline)]
    self.table_output_flags.output_table(table)
