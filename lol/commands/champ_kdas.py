import cassiopeia as cass
import collections
import tabulate
import datapipelines

from lol import command
from lol.flags.match_filtering import MatchFilteringFlags


class ChampionKdasCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name} <summoner_name>\n'
        'Outputs a summoner\'s KDA on all of the champions they have played.'
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
        {'$match': {'mode': 'ARAM'}},  # optional
        {'$project': {'participants': True}},
        {'$unwind': '$participants'},
        {'$match': {'participants.accountId': summoner.account_id}},
        {'$group': {'_id': {'championId': '$participants.championId'},
                    'games_played': {'$sum': 1},
                    'kills': {'$sum': '$participants.stats.kills'},
                    'deaths': {'$sum': '$participants.stats.deaths'},
                    'assists': {'$sum': '$participants.stats.assists'},
                    }},
        {'$addFields': {'kda': {'$divide': [{'$add': ['$kills', '$assists']},
                                            {'$cond': [{'$lte': ['$deaths', 0]}, 1, '$deaths']}]
                                            }}},
        {'$sort': {'kda': -1}},
    ]

    champion_list = cass.get_champions()
    champ_id_to_name = {champ.id: champ.name for champ in champion_list}

    table = []
    for result in self.db.matches.aggregate(pipeline):
      table.append(collections.OrderedDict([
          ('Champion', champ_id_to_name[result['_id']['championId']]),
          ('KDA', result['kda']),
          ('Games Played', result['games_played']),
      ]))
    print(tabulate.tabulate(table, headers='keys'))
