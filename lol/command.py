import attr
import sys


TRUE_VALUES = ['y', 'yes', 'true', 't']
FALSE_VALUES = ['n', 'no', 'false', 'f']


@attr.s
class Flag(object):
  name = attr.ib()
  default = attr.ib(default=None)
  description = attr.ib(default="")
  value = attr.ib()
  is_boolean = attr.ib(default=False)
  @value.default
  def _value_default(self):
    return self.default


class Command(object):

  _PROGRAM = sys.argv[0]

  def __init__(self, name):
    self.name = name
    self.mongo_client = None
    self.db = None
    self._program = sys.argv[0]
    self._flags = {}

  def set_mongo_client(self, client):
    self.mongo_client = client
    self.db = self.mongo_client.lol

  def help_message(self):
    raise NotImplementedError()

  def help_message_flags(self):
    msg = []
    for flag in sorted(self._flags.keys()):
      if self._flags[flag].default == '':
        msg.append(f'--{flag}: {self._flags[flag].description}')
      else:
        msg.append(f'--{flag} (default={self._flags[flag].default}): {self._flags[flag].description}')
    return '\n'.join(msg)

  def print_invalid_usage(self):
    usage = self.help_message().split('\n')[0]
    print(f'Invalid usage. {usage}')

  def register_flag(self, flag):
    if flag.is_boolean and flag.default != False and flag.default != True:
      raise ValueError(f'Flag {flag.name} is boolean and has non boolean default.')
    self._flags[flag.name] = flag

  def flag(self, name):
    return self._flags[name].value

  def run(self, args):
    argv = []
    no_more_flags = False
    for arg in args:
      if no_more_flags:
        argv.append(arg)
        continue

      if arg == '--':
        no_more_flags = True
      elif arg.startswith('--'):
        flag_val = arg[2:].split('=', 1)
        if flag_val[0] not in self._flags:
          print(f'Unrecognized flag: {flag_val[0]}')
          self.print_invalid_usage()
          return
        if len(flag_val) == 2:
          if self._flags[flag_val[0]].is_boolean:
            if flag_val[1].lower() in TRUE_VALUES:
              self._flags[flag_val[0]].value = True
            elif flag_val[1].lower() in FALSE_VALUES:
              self._flags[flag_val[0]].value = False
            else:
              print(f'Flag value is supposed to be boolean: {flag_val[0]}')
              self.print_invalid_usage()
              return
          else:
            self._flags[flag_val[0]].value = flag_val[1]
        else:
          self._flags[flag_val[0]].value = True
      else:
        argv.append(arg)

    self._run_impl(argv)

  def _run_impl(self, args):
    raise NotImplementedError()

