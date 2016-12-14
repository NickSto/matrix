#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import json
import errno
import argparse

ARG_DEFAULTS = {'format':'human'}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Extract data from a Session Manager .session file."""


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('session', metavar='backup.session',
    help='The Session Manager .session file.')
  parser.add_argument('-t', '--titles', action='store_true',
    help='Print tab titles.')
  parser.add_argument('-u', '--urls', action='store_true',
    help='Print tab urls.')
  parser.add_argument('-H', '--human', action='store_const', const='human', dest='format',
    help='Print in human-readable format. If no fields are specified, this will only print the '
         'number of tabs per window, plus a total.')
  parser.add_argument('-T', '--tsv', action='store_const', const='tsv', dest='format',
    help='Print in the selected fields in tab-delimited columns, in this order: url, title. If no '
         'fields are specified, this will just print a tab-delimited list of the number of tabs '
         'per window.')

  args = parser.parse_args(argv[1:])

  summary_only = True
  if args.titles:
    summary_only = False
  elif args.urls:
    summary_only = False

  session = file_to_json(args.session)

  tab_counts = []
  for window in session['windows']:
    if args.format == 'human':
      print('Window {}: {} tabs'.format(len(tab_counts)+1, len(window['tabs'])))
    tab_counts.append(len(window['tabs']))
    tab_num = 0
    for tab in get_tabs(window):
      tab_num += 1
      title = tab['title']
      url = tab['url']
      if args.format == 'human':
        if args.titles:
          print('  '.encode('utf-8')+title)
        if args.urls:
          print('    '+url)
      elif args.format == 'tsv':
        output = []
        if args.urls:
          output.append(url)
        if args.titles:
          output.append(title)
        if output:
          print(*output, sep='\t')
    if args.format == 'human' and not summary_only:
      print()

  if args.format == 'human':
      print('Total:    {} tabs'.format(sum(tab_counts)))

  if summary_only and args.format == 'tsv':
      print(*tab_counts, sep='\t')


def file_to_json(path):
  line_num = 0
  with open(path, 'rU') as session_file:
    for line in session_file:
      line_num += 1
      if line_num == 5:
        return json.loads(line)


def get_tabs(window):
  for tab in window['tabs']:
    last_history_item = tab['entries'][-1]
    title = last_history_item.get('title', '').encode('utf-8')
    url = last_history_item.get('url')
    yield {'title':title, 'url':url}


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
