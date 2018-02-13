#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import json
import shutil
import logging
import argparse
import subprocess
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Read and manipulate browsing sessions from Firefox."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('session', nargs='?', default=sys.stdin,
    help='The session file. Accepts Firefox\'s recovery.jsonlz4 and previous.jsonlz4 files, as '
         'well as Session Manager\'s .session files. It also works on the pure .json '
         'representation of either.')
  parser.add_argument('-t', '--titles', action='store_true',
    help='Print tab titles.')
  parser.add_argument('-u', '--urls', action='store_true',
    help='Print tab urls.')
  parser.add_argument('-H', '--human', action='store_const', const='human', dest='format',
    default='human',
    help='Print in human-readable format (default). If no fields are specified, this will only '
         'print the number of tabs per window, plus a total.')
  parser.add_argument('-T', '--tsv', action='store_const', const='tsv', dest='format',
    help='Print in the selected fields in tab-delimited columns, in this order: url, title. If no '
         'fields are specified, this will just print a tab-delimited list of the number of tabs '
         'per window.')
  parser.add_argument('-J', '--json', action='store_const', const='json', dest='format',
    help='Print output in the Firefox session JSON format.')
  parser.add_argument('-w', '--windows', metavar='window:tabs', nargs='*', default=(),
    help='Select a certain set of windows to print, instead of the entire session. Use the format '
         '"WindowNum:NumTabs" (e.g. "2:375"). The two, colon-delimited numbers are the window '
         'number, as displayed by this script, and the number of tabs in it (to make sure we\'re '
         'talking about the right window). Note: All the global session data will be included, no '
         'matter what windows are chosen.')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  targets = set()
  for window_spec in args.windows:
    target_window, target_tabs = parse_window_spec(window_spec)
    targets.add((target_window, target_tabs))

  session = read_session_file(args.session)
  session = filter_session(session, targets)

  if args.format == 'json':
    json.dump(session, sys.stdout)
  else:
    output = format_contents(session, args.titles, args.urls, args.format)
    print(*output, sep='\n')


def parse_window_spec(window_spec):
  fields = window_spec.split(':')
  assert len(fields) == 2, 'Invalid format for --window (must be 2 colon-delimited fields)'
  try:
    target_window = int(fields[0])
    target_tabs = int(fields[1])
  except ValueError:
    fail('Invalid format for --window (WindowNum and NumTabs must be integers).')
  return target_window, target_tabs


def read_session_file(session_arg):
  if session_arg is sys.stdin:
    # If it's coming into stdin, assume it's already pure JSON.
    return json.load(session_arg)
  elif session_arg.endswith('.jsonlz4'):
    # It's JSON compressed in Mozilla's custom format.
    if not shutil.which('dejsonlz4'):
      fail('Error: Cannot find "dejsonlz4" command to decompress session file.')
    process = subprocess.Popen(['dejsonlz4', session_arg, '-'], stdout=subprocess.PIPE)
    session_str = str(process.stdout.read(), 'utf8')
    return json.loads(session_str)
  elif session_arg.endswith('.session'):
    # It's a Session Manager .session file.
    return file_to_json(session_arg)
  elif session_arg.endswith('.json'):
    # It's a pure JSON file.
    with open(session_arg) as session_file:
      return json.load(session_file)
  else:
    ext = os.path.splitext(session_arg)[1]
    fail('Error: Unrecognized session file extension ".{}".'.format(ext))


def filter_session(session, targets):
  if not targets:
    return session
  # Make a shallow copy of the session dict, but empty the windows list.
  new_session = {}
  for key, value in session.items():
    if key == 'windows':
      new_session['windows'] = []
    else:
      new_session[key] = value
  # Insert the target windows.
  hits = set()
  for w, window in enumerate(session['windows']):
    tabs = len(window['tabs'])
    if (w+1, tabs) in targets:
      new_session['windows'].append(window)
      hits.add((w+1, tabs))
  # Check there weren't targets given with no match.
  if hits != targets:
    misses = targets - hits
    misses_str = '", "'.join(['{}:{}'.format(*miss) for miss in misses])
    fail('Error: No windows found that match the target(s) "{}".'.format(misses_str))
  return new_session


def file_to_json(path):
  line_num = 0
  with open(path, 'rU', encoding='utf8') as session_file:
    for line in session_file:
      line_num += 1
      if line_num == 5:
        return json.loads(line)


def format_contents(session, titles=False, urls=False, format='human'):
  output = []
  tab_counts = []
  for w, window in enumerate(session['windows']):
    tabs = len(window['tabs'])
    tab_counts.append(tabs)
    if format == 'human':
      output.append('Window {}: {:3d} tabs'.format(w+1, tabs))
    for tab in get_tabs(window):
      if not (titles or urls):
        continue
      elif format == 'human':
        if titles:
          output.append('  '+tab['title'])
        if urls:
          output.append('    '+tab['url'])
      elif format == 'tsv':
        fields = []
        if titles:
          fields.append(tab['title'])
        if urls:
          fields.append(tab['url'])
        if fields:
          output.append('\t'.join(fields))
    if format == 'human' and (titles or urls):
      output.append('')
  if format == 'human':
    output.append('Total:    {:3d} tabs'.format(sum(tab_counts)))
  elif format == 'tsv' and not (titles or urls):
    output.append('\t'.join([str(c) for c in tab_counts]))
  return output


def get_tabs(window):
  for tab in window['tabs']:
    last_history_item = tab['entries'][-1]
    title = last_history_item.get('title', '')
    url = last_history_item.get('url')
    yield {'title':title, 'url':url}


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
  except BrokenPipeError:
    pass
