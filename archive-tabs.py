#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import errno
import urllib
import argparse
session_manager = __import__('session-manager')

ADD_URL = 'https://api.pinboard.in/v1/posts/add?auth_token={token}&url={url}&description={title}&tags=tab+automated&replace=no'.encode('utf8')
ARG_DEFAULTS = {}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Bookmark open tabs from a Firefox session with Pinboard."""

# API documentation: https://pinboard.in/api
# Get the auth token from https://pinboard.in/settings/password
# Limit: 1 request per 3 seconds. Check for 429 Too Many Requests response.

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('session', metavar='backup.session',
    help='Session Manager .session file.')
  parser.add_argument('-t', '--auth-token',
    help='Your Pinboard API authentication token. Available from '
         'https://pinboard.in/settings/password. Not required if only simulating.')
  parser.add_argument('-n', '--simulate', action='store_true',
    help='Only simulate the process, printing the tabs which will be archived but without actually '
         'doing it.')
  parser.add_argument('-b', '--begin',
    help='The title of the tab to start archiving at. Can use only the beginning of the title, but '
         'it must be unique.')
  parser.add_argument('-e', '--end',
    help='The title of the tab to end archiving at. Can use only the beginning of the title, but '
         'it must be unique.')

  args = parser.parse_args(argv[1:])

  if not args.auth_token and not args.simulate:
    fail('Error: An --auth-token is required if --simulate is not given.')

  session = session_manager.file_to_json(args.session)

  max_tabs = 0
  biggest_window = None
  for window in session['windows']:
    num_tabs = len(list(session_manager.get_tabs(window)))
    if num_tabs > max_tabs:
      max_tabs = num_tabs
      biggest_window = window
  print('Found biggest window: {} tabs.'.format(max_tabs))

  # Go through the tabs, determine which to archive.
  tabs = []
  begin_matches = []
  end_matches = []
  if args.begin:
    archiving = False
  else:
    archiving = True
  begin = False
  end = False
  for tab in session_manager.get_tabs(biggest_window):
    # Check when to start.
    if args.begin and tab['title'].startswith(args.begin):
      begin_matches.append(tab['title'])
      begin = True
    else:
      begin = False
    if not archiving:
      if begin:
        archiving = True
      else:
        continue
    # Archive this tab.
    tabs.append(tab)
    # Check when to stop.
    if args.end and tab['title'].startswith(args.end):
      end_matches.append(tab['title'])
      end = True
    else:
      end = False
    if archiving and args.end and end:
      break
  if len(begin_matches) > 1:
    fail('Error: --begin matches multiple tabs:\n'.encode('utf8')+
         '\n'.encode('utf8').join(begin_matches))
  if len(end_matches) > 1:
    fail('Error: --end matches multiple tabs:\n'.encode('utf8')+
         '\n'.encode('utf8').join(end_matches))

  print('Found {} tabs to archive.\n'.format(len(tabs)))

  for tab in tabs:
    print(tab['title'])
    if not args.simulate:
      fail('Error: Actual bookmarking not implemented yet.')
      # print(ADD_URL.format(token=args.auth_token, url=quote(tab['url']), title=quote(tab['title'])))


def quote(s):
  return urllib.quote(s, safe='')


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
