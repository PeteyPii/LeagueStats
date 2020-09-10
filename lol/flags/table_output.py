import csv
import tabulate

from lol import common_flag
from lol.command import Flag

class TableOutputFlags(object):
  def __init__(self, command):
    self.print = common_flag.CommonFlag(
        Flag(name='print',
             default=True,
             is_boolean=True,
             description='Prints table output to stdout.'),
        command)
    self.csv_file = common_flag.CommonFlag(
        Flag(name='csv_file',
             default='',
             description='CSV file to export the results to.'),
        command)
    self.command = command

  def output_table(self, rows):
    if self.command.flag('print'):
      print(tabulate.tabulate(rows, headers='keys'))

    if self.command.flag('csv_file') and rows:
      with open(self.command.flag('csv_file'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
          writer.writerow(row)
