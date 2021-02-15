class CommonFlag(object):

  def __init__(self, flag, command):
    self.flag = flag
    self.command = command
    self.command.register_flag(flag)
