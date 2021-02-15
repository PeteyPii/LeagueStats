import datetime

from dateutil import tz
from lol import common_flag
from lol.command import Flag


class TimeFlags(object):

  def __init__(self, command):
    self.after = common_flag.CommonFlag(
        Flag(name='after',
             default='',
             description='Filters matches to those that started after or on the given date (e.g. "2020-09-30").'),
        command)
    self.before = common_flag.CommonFlag(
        Flag(name='before',
             default='',
             description='Filters matches to those that started before the given date (e.g. "2020-09-30").'), command)
    self.command = command

  def filter_steps(self):
    steps = []
    if self.command.flag('after'):
      after_epoch_secs = datetime.datetime.strptime(self.command.flag('after'),
                                                    '%Y-%m-%d').astimezone(tz.tzlocal()).timestamp()
      steps.append({'$match': {'gameCreation': {'$gt': 1000 * after_epoch_secs}}})
    if self.command.flag('before'):
      before_epoch_secs = datetime.datetime.strptime(self.command.flag('before'),
                                                     '%Y-%m-%d').astimezone(tz.tzlocal()).timestamp()
      steps.append({'$match': {'gameCreation': {'$lt': 1000 * before_epoch_secs}}})
    return steps
