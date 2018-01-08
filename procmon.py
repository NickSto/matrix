#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import time
import errno
import logging
import getpass
import argparse
import subprocess
assert sys.version_info.major >= 3, 'Python 3 required'

COLUMNS = {'cpu':2, 'mem':3, 'vsz':4, 'rss':5}

DESCRIPTION = """This will monitor the resource usage of a process (or set of processes) through
the ps command and print the maximum values once the processes have exited."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('command',
    help='Name of the command to monitor (like "samtools" or "script.py"). Only the end of the '
         'path will be used, so "script.py" will match the process "/path/to/script.py". Also, '
         'this will use the second argument if the first is a common interpreter like "python" '
         'or "bash".')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'),
    help='Write a full log of every statistic at every time point to this file.')
  parser.add_argument('-p', '--pause', type=float, default=5,
    help='How often to check the processes, in seconds. Default: %(default)s')
  parser.add_argument('-u', '--user', default=getpass.getuser(),
    help='Only monitor processes owned by this user (default "%(default)s").')
  parser.add_argument('-L', '--errlog', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.errlog, level=args.volume, format='%(message)s')
  tone_down_logger()

  maximums = {}

  try:
    while True:
      stats = read_ps(args.command, user=args.user)
      if not stats:
        # We didn't find any processes. Have we ever?
        if maximums:
          # Yes, we have in the past. They must have finished.
          break
        else:
          # Otherwise, we haven't seen them yet. Let's wait for them to start.
          continue
      if args.log:
        values = []
        for key in sorted(stats.keys()):
          values.append(stats[key])
        args.log.write('\t'.join([str(v) for v in values])+'\n')
      for key, value in stats.items():
        try:
          maximums[key] = max(maximums[key], value)
        except KeyError:
          maximums[key] = value
      time.sleep(args.pause)

  finally:
    if not maximums:
      logging.warning('Did not find the process {!r} run by user {!r}.'.format(args.command, args.user))

    for key in sorted(maximums.keys()):
      value = maximums[key]
      if key in ('cpu', 'mem'):
        value_formatted = '{:6.2f} %'.format(value)
      elif key in ('rss', 'vsz'):
        if value >= 100*1024:
          value_formatted = '{} Mb'.format(int(value/1024))
        elif value >= 10*1024:
          value_formatted = '{:0.1f} Mb'.format(value/1024)
        else:
          value_formatted = '{:0.2f} Mb'.format(value/1024)
      print(('{}:\t{}').format(key, value_formatted))


def read_ps(command, user=getpass.getuser()):
  proc_stats = []
  process = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE)
  for line_bytes in process.stdout:
    line = str(line_bytes, 'utf8')
    fields = line.split()
    if fields[0] != user:
      continue
    if get_command(fields[10:]) != command:
      continue
    proc_stat = {}
    for stat_name, column in COLUMNS.items():
      value_str = fields[column]
      try:
        value = int(value_str)
      except ValueError:
        try:
          value = float(value_str)
        except ValueError:
          value = None
      if value is not None:
        proc_stat[stat_name] = value
    proc_stats.append(proc_stat)
  if not proc_stats:
    # We didn't find any matching processes.
    return None
  totals = {}
  for stat_name in COLUMNS.keys():
    totals[stat_name] = 0
  for proc_stat in proc_stats:
    for stat_name, value in proc_stat.items():
      totals[stat_name] += value
  return totals


def get_command(command_line):
  if len(command_line) == 0:
    command_path = ''
  elif command_line[0] in ('sh', 'bash', 'python', 'perl', 'R', 'python2', 'python3'):
    if len(command_line) > 1:
      command_path = command_line[1]
    else:
      command_path = ''
  else:
    command_path = command_line[0]
  return os.path.basename(command_path)


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
