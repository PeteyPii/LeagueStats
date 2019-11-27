import sys


class Command(object):

  _PROGRAM = sys.argv[0]

  def __init__(self, name):
    self.name = name
    self.mongo_client = None
    self.db = None
    self._program = sys.argv[0]

  def set_mongo_client(self, client):
    self.mongo_client = client
    self.db = self.mongo_client.lol

  def help_message(self):
    raise NotImplementedError()

  def print_invalid_usage(self):
    usage = self.help_message().split('\n')[0]
    print(f'Invalid usage. {usage}')

  def run(self, args):
    raise NotImplementedError()

