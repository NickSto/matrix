#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import re
import os
import sys
import gzip
import time
import datetime
import argparse
import subprocess

ARG_DEFAULTS = {'log_dir':'/var/log', 'log_base':'pm-suspend.log', 'extension':'gz'}
USAGE = "%(prog)s [options]"
DESCRIPTION = """This will print all the sleep and wake events from your log files, chronologically
(from earliest to latest). The output is tab-delimited, with the event's unix timestamp as the first
column and the event type ("sleep" or "wake") as the second column."""

TIMESTAMP_FORMAT = '%a %b %d %H:%M:%S %Z %Y'
TIME_LINE_REGEX = re.compile(r'^([A-Za-z]{3} [A-Za-z]{3} +\d{1,2} [0-9:]{8} [A-Za-z]{3} 2\d{3}): (.*)$')

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  # parser.add_argument('log_file', metavar='pm-suspend.log', nargs='?')
  parser.add_argument('-d', '--log-dir',
    help='Default: %(default)s')
  parser.add_argument('-b', '--log-base',
    help='Default: %(default)s')
  parser.add_argument('-e', '--extension',
    help='Default: %(default)s')

  args = parser.parse_args(argv[1:])

  log_path_base = os.path.join(args.log_dir, args.log_base)

  log_paths = get_path_list(log_path_base, args.extension)

  for log_path in reversed(log_paths):
    read_log(log_path)


def get_path_list(path_base, ext):
  path_list = []
  i = 1
  path_candidate = path_base
  path_candidate_compressed = ''
  while os.path.isfile(path_candidate) or os.path.isfile(path_candidate_compressed):
    if os.path.isfile(path_candidate):
      path_list.append(path_candidate)
    elif os.path.isfile(path_candidate_compressed):
      path_list.append(path_candidate_compressed)
    path_candidate = '{base}.{i}'.format(base=path_base, i=i)
    path_candidate_compressed = '{base}.{i}.{ext}'.format(base=path_base, i=i, ext=ext)
    i += 1
  return path_list


def read_log(log_path):
  if log_path.endswith('.gz'):
    log = gzip.open(log_path)
  else:
    log = open(log_path)
  for line in log:
    match = TIME_LINE_REGEX.search(line)
    if match:
      if match.group(2) == 'performing suspend':
        action = 'sleep'
      elif match.group(2) == 'Awake.':
        action = 'wake'
      else:
        continue
      timestamp = parse_date_str(match.group(1))
      if timestamp is None:
        continue
      print(timestamp, action, sep='\t')
  log.close()


def parse_date_str(date_str):
  """Parse a date string like 'Tue Feb  2 01:21:37 EST 2016' into a unix timestamp.
  Returns an int. On error, returns None.
  Avoids the Python bug recognizing timezone names by outsourcing parsing to the date command
  if the native Python method fails.
  The bug occurs when the timezone is not UTC, GMT, or the current one (returned by time.tzname):
  https://bugs.python.org/issue22377"""
  try:
    dt = datetime.datetime.strptime(date_str, TIMESTAMP_FORMAT)
    return int(time.mktime(dt.timetuple()))
  except ValueError:
    with open(os.devnull) as devnull:
      try:
        output = subprocess.check_output(['date', '-d', date_str, '+%s'], stderr=devnull)
      except OSError:
        return
      except subprocess.CalledProcessError:
        return
    try:
      return int(output.rstrip('\r\n'))
    except ValueError:
      return


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
