from lol.flags.time import TimeFlags


class MatchFilteringFlags(object):
  def __init__(self, command):
    self.command = command
    self.time_flags = TimeFlags(command)

  def filter_steps(self):
    steps = []
    steps += self.time_flags.filter_steps()
    return steps
