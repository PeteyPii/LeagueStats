import sys


class Command(object):

  _PROGRAM = sys.argv[0]

  def __init__(self, name):
    self.name = name
    self.mongo_client = None
    self.db = None
    self._program = sys.argv[0]
    self.registered_flags = set()

  def set_mongo_client(self, client):
    self.mongo_client = client
    self.db = self.mongo_client.lol

  def help_message(self):
    raise NotImplementedError()

  def print_invalid_usage(self):
    usage = self.help_message().split('\n')[0]
    print(f'Invalid usage. {usage}')

  def register_flag(self, flag_name):
    self.registered_flags.add(flag_name)

  def run(self, args):
    argv = []
    kwargs = {}
    no_more_flags = False
    for arg in args:
      if no_more_flags:
        argv.append(arg)
        continue

      if arg == '--':
        no_more_flags = True
      elif arg.startswith('--'):
        flag = arg[2:].split('=', 1)
        if flag[0] not in self.registered_flags:
          print(f'Unrecognized flag: {flag[0]}')
          self.print_invalid_usage()
          return
        if len(flag) == 2:
          kwargs[flag[0]] = flag[1]
        else:
          kwargs[flag[0]] = True
      else:
        argv.append(arg)

    self._run_impl(argv, **kwargs)

  def _run_impl(self, args, **kwargs):
    raise NotImplementedError()

