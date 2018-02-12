#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import json
import errno
import shutil
import logging
import argparse
import subprocess
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """"""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('session', metavar='session.json', nargs='?', default=sys.stdin,
    help='The uncompressed version of the recovery.jsonlz4 or previous.jsonlz4.')
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

  session = read_session_file(args.session)

  output = format_contents(session, args.titles, args.urls, args.format)
  print(*output, sep='\n')


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
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
