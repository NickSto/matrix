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

TIMESTAMP_FORMAT = '%a %b %d %H:%M:%S %Y'
TIME_LINE_REGEX = re.compile(r'^([A-Za-z]{3} [A-Za-z]{3} +\d{1,2} [0-9:]{8} [A-Za-z]{3} 2\d{3}): (.*)$')

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  # parser.add_argument('log_file', metavar='pm-suspend.log', nargs='?')
  parser.add_argument('-r', '--reverse', action='store_true',
    help='Print events from newest to oldest.')
  parser.add_argument('-d', '--log-dir',
    help='Default: %(default)s')
  parser.add_argument('-b', '--log-base',
    help='Default: %(default)s')
  parser.add_argument('-e', '--extension',
    help='Default: %(default)s')

  args = parser.parse_args(argv[1:])

  log_path_base = os.path.join(args.log_dir, args.log_base)

  log_paths = get_path_list(log_path_base, args.extension)

  if args.reverse:
    log_paths = reversed(log_paths)

  tz_cache = {}
  for log_path in log_paths:
    events = read_log(log_path, tz_cache=tz_cache)
    if args.reverse:
      events = reversed(events)
    print_events(events)


def get_path_list(path_base, ext):
  """Returns paths to all existing log files, in chronological order (oldest first).
  Assumes log files are appended with numbers in order, and, optionally, compression extensions:
  /var/log/pm-suspend.log
  /var/log/pm-suspend.log.1
  /var/log/pm-suspend.log.2
  /var/log/pm-suspend.log.3.gz
  /var/log/pm-suspend.log.4.gz"""
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
  return list(reversed(path_list))


def read_log(log_path, tz_cache={}):
  events = []
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
      timestamp = parse_date_str(match.group(1), tz_cache)
      if timestamp is None:
        continue
      events.append({'timestamp':timestamp, 'action':action})
  log.close()
  return events


def print_events(events):
  for event in events:
    print(event['timestamp'], event['action'], sep='\t')


def parse_date_str(date_str, tz_cache):
  """Parse a date string like 'Tue Feb  2 01:21:37 EST 2016' into a unix timestamp.
  Returns an int. On error, returns None.
  Avoids Python timezone bugs by outsourcing parsing to the date command. Caches timezone
  information so that it won't use the date command more than once per timezone.
  Will be incorrect in the edge case of a timezone whose legal definition changes (e.g. "After this
  date, CET is now UTC+2, not UTC+1!").
  The main Python timezone bug is that even when datetime.strptime() recognizes a timezone, it
  ignores it and assumes the local timezone instead."""
  # Get the timezone from the date string, then remove it.
  date_fields = date_str.split()
  tz_str = date_fields[4]
  del(date_fields[4])
  date_str_local = ' '.join(date_fields)
  # Get datetime's interpretation of the timestamp (always local).
  try:
    dt = datetime.datetime.strptime(date_str_local, TIMESTAMP_FORMAT)
  except ValueError:
    # On error, fall back on the "date" command.
    return parse_date_cmd(date_str)
  timestamp_local = int(time.mktime(dt.timetuple()))
  if tz_str in tz_cache:
    return timestamp_local - tz_cache[tz_str]
  else:
    # Get the real timestamp, including the actual timezone, from the ultimate authority:
    # the "date" command.
    timestamp = parse_date_cmd(date_str)
    if timestamp is None:
      return None
    # Cache the difference between datetime's interpretation and the "date" command's answer, so we
    # don't have to run the command again for this timezone.
    tz_cache[tz_str] = timestamp_local - timestamp
    return timestamp


def parse_date_cmd(date_str):
  """Use the "date" command to parse a date string.
  Returns an integer timestamp or None on error."""
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
