import collections

import cassiopeia as cass
import datapipelines
from lol import command
from lol.flags.match_filtering import MatchFilteringFlags
from lol.flags.table_output import TableOutputFlags
from lol.flags.region import RegionFlag


class ChampionKdasCommand(command.Command):

  def __init__(self, name):
    super().__init__(name)
    self.match_filtering_flags = MatchFilteringFlags(self)
    self.table_output_flags = TableOutputFlags(self)
    self.region_flag = RegionFlag(self)

  def help_message(self):
    return (f'Usage: {self._PROGRAM} {self.name} <summoner_names>\n'
            'Outputs each summoner\'s KDA on all of the champions they have played.')

  def format_result(self, result):
    if result is None:
      return ''
    avg_kills = float(result['kills']) / result['games_played']
    avg_deaths = float(result['deaths']) / result['games_played']
    avg_assists = float(result['assists']) / result['games_played']
    return f'{result["kda"]:.3f}:1   {avg_kills:.1f} / {avg_deaths:.1f} / {avg_assists:.1f}   ({result["games_played"]})'

  def _run_impl(self, args):
    if len(args) != 1:
      return self.print_invalid_usage()

    summoner_names = args[0].split(',')
    summoners = []
    for name in summoner_names:
      if not name:
        print('Summoner name cannot be empty.')
        return
      try:
        summoners.append(cass.Summoner(name=name, region=self.region_flag.value).load())
      except datapipelines.common.NotFoundError:
        print(f'Summoner "{name}" not found.')
        return
    summoners.sort(key=lambda s: s.name)

    pipeline = self.match_filtering_flags.filter_steps() + [
        {'$project': {'participants': True}},
        {'$unwind': '$participants'},
        {'$match': {'participants.puuid': {'$in': [summoner.puuid for summoner in summoners]}}},
        {'$group': {'_id': {'championId': '$participants.championId',
                            'puuid': '$participants.puuid'},
                    'games_played': {'$sum': 1},
                    'kills': {'$sum': '$participants.stats.kills'},
                    'deaths': {'$sum': '$participants.stats.deaths'},
                    'assists': {'$sum': '$participants.stats.assists'},
                    }},
        {'$addFields': {'kda': {'$divide': [{'$add': ['$kills', '$assists']},
                                            {'$cond': [{'$lte': ['$deaths', 0]}, 1, '$deaths']}]}}},
    ]  # yapf: disable
    results = {
        (result['_id']['championId'], result['_id']['puuid']): result for result in self.db.matches.aggregate(pipeline)
    }

    global_pipeline = self.match_filtering_flags.filter_steps() + [
        {'$project': {'participants': True}},
        {'$unwind': '$participants'},
        {'$group': {'_id': {'championId': '$participants.championId'},
                    'games_played': {'$sum': 1},
                    'kills': {'$sum': '$participants.stats.kills'},
                    'deaths': {'$sum': '$participants.stats.deaths'},
                    'assists': {'$sum': '$participants.stats.assists'},
                    }},
        {'$addFields': {'kda': {'$divide': [{'$add': ['$kills', '$assists']},
                                            {'$cond': [{'$lte': ['$deaths', 0]}, 1, '$deaths']}]}}},
    ]  # yapf: disable
    global_results = {result['_id']['championId']: result for result in self.db.matches.aggregate(global_pipeline)}

    champion_list = cass.get_champions(region=self.region_flag.value)
    champ_id_to_name = {champ.id: champ.name for champ in champion_list}

    table = []
    for champ_id, champ_name in sorted(champ_id_to_name.items(), key=lambda t: t[1]):
      row = collections.OrderedDict({'Champion': champ_name})
      for summoner in summoners:
        row[summoner.name] = self.format_result(results.get((champ_id, summoner.puuid)))
      row['Global Avg'] = self.format_result(global_results.get(champ_id))
      table.append(row)
    self.table_output_flags.output_table(table)
