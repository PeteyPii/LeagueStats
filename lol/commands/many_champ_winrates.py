import cassiopeia as cass
import tabulate
import datapipelines
import collections
import time

from lol import command


class ManyChampionWinratesCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name} <summoner_names>\n'
        'Outputs each summoner\'s winrate on all of the champions they have played.'
    )

  def format_result(self, result):
    if result is None:
      return ''
    return f'{100.0 * result["win_rate"]:.3f} ({result["games_played"]})'

  def _run_impl(self, args):
    if len(args) != 1:
      return self.print_invalid_usage()

    summoner_names = args[0].split(',')
    summoners = []
    for name in summoner_names:
      if not name:
        print(f'Summoner name cannot be empty.')
        return
      try:
        summoners.append(cass.Summoner(name=name).load())
      except datapipelines.common.NotFoundError:
        print(f'Summoner "{name}" not found.')
        return
    summoners.sort(key=lambda s: s.name)

    pipeline = [
        {'$match': {'mode': 'ARAM'}},  # optional
        # {'$match': {'gameCreation': {'$gt': 1000 * (time.time() - 14 * 24 * 60 * 60)  }}},
        {'$project': {'participants': True}},
        {'$unwind': '$participants'},
        {'$group': {'_id': {'championId': '$participants.championId',
                            'accountId': '$participants.accountId'},
                    'games_played': {'$sum': 1},
                    'wins': {'$sum': {'$cond': ['$participants.stats.win', 1, 0]}}}},
        {'$addFields': {'win_rate': {'$divide': ['$wins', '$games_played']}}},
    ]
    results = {(result['_id']['championId'], result['_id']['accountId']): result
               for result in self.db.matches.aggregate(pipeline)}

    global_pipeline = [
        {'$match': {'mode': 'ARAM'}},  # optional
        # {'$match': {'gameCreation': {'$gt': 1000 * (time.time() - 14 * 24 * 60 * 60)  }}},
        {'$project': {'participants': True}},
        {'$unwind': '$participants'},
        {'$group': {'_id': {'championId': '$participants.championId'},
                    'games_played': {'$sum': 1},
                    'wins': {'$sum': {'$cond': ['$participants.stats.win', 1, 0]}}}},
        {'$addFields': {'win_rate': {'$divide': ['$wins', '$games_played']}}},
    ]
    global_results = {result['_id']['championId']: result
                      for result in self.db.matches.aggregate(global_pipeline)}

    champion_list = cass.get_champions()
    champ_id_to_name = {champ.id: champ.name for champ in champion_list}

    table = []
    for champ_id, champ_name in sorted(champ_id_to_name.items(), key=lambda t: t[1]):
      row = collections.OrderedDict({'Champion': champ_name})
      for summoner in summoners:
        row[summoner.name] = self.format_result(results.get((champ_id, summoner.account_id)))
      row['Global Avg'] = self.format_result(global_results.get(champ_id))
      table.append(row)

    print(tabulate.tabulate(table, headers='keys'))
