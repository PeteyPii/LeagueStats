from lol import command


class ListSummonersCommand(command.Command):
  def __init__(self, name):
    super().__init__(name)

  def help_message(self):
    return (
        f'Usage: {self._PROGRAM} {self.name}\n'
        'Lists all the summoners that are being tracked.'
    )

  def run(self, args):
    if args:
      return self.print_invalid_usage()

    for summoner in self.db.summoners.find():
      print(f'{summoner["name"]}')
