#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import time
import errno
import urllib
import httplib
import argparse
import xml.etree.ElementTree
session_manager = __import__('session-manager')

API_DOMAIN = 'api.pinboard.in'
GET_API_PATH = '/v1/posts/get?auth_token={token}&url={url}'.encode('utf8')
ADD_API_PATH = '/v1/posts/add?auth_token={token}&url={url}&description={title}&tags=tab+automated&replace=no'.encode('utf8')
MAX_RESPONSE = 4096 # bytes
SLEEP_TIME = 3.1
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
    help='The title of the tab to start archiving at (inclusive). You can use just the '
         'beginning of the title, but it must be unique. If not given, will start with the first '
         'tab.')
  parser.add_argument('-e', '--end',
    help='The title of the tab to end archiving at (inclusive). You can use just the beginning of '
         'the title, but it must be unique. If not given, will stop at the last tab.')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'),
    help='Write a log of tabs archived to this file.')

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
    print('\t'.encode('utf8')+tab['title'][:91])
    if not args.simulate:
      request_path = GET_API_PATH.format(token=args.auth_token, url=quote(tab['url']))
      response = make_request(API_DOMAIN, request_path)
      done = check_response(response, 'get')
      if done:
        print('Tab already bookmarked. Skipping.')
        time.sleep(SLEEP_TIME)
        continue
      request_path = ADD_API_PATH.format(token=args.auth_token, url=quote(tab['url']),
                                         title=quote(tab['title']))
      response = make_request(API_DOMAIN, request_path)
      success = check_response(response, 'add')
      if success:
        print('success')
        if args.log:
          args.log.write(tab['title'])
          args.log.write('\n')
      else:
        print('FAILED')
        sys.exit(1)
      time.sleep(SLEEP_TIME)


def quote(string):
  return urllib.quote_plus(string)


def make_request(domain, path):
  conex = httplib.HTTPSConnection(domain)
  #TODO: Both of these steps can throw exceptions. Deal with them.
  conex.request('GET', path)
  return conex.getresponse()


def check_response(response, request_type):
  if response.status == 429:
    # API rate limit reached.
    fail('Error: API rate limit reached (429 Too Many Requests).')
  response_body = response.read(MAX_RESPONSE)
  if request_type == 'add':
    return parse_add_response(response_body)
  elif request_type == 'get':
    return parse_get_response(response_body)


def parse_get_response(response_body):
  """Return True if url is already bookmarked, False if not."""
  try:
    root = xml.etree.ElementTree.fromstring(response_body)
  except xml.etree.ElementTree.ParseError:
    fail('Error: Parsing error in response from API:\n'+response_body)
  if root.tag == 'posts':
    if len(root) == 0:
      return False
    elif len(root) == 1:
      return True
    else:
      fail('Error: Too many hits when checking if tab is already bookmarked: {} hits'
           .format(len(root)))
  elif root.tag == 'result' and root.attrib.get('code') == 'something went wrong':
    fail('Error: Request failed when checking if tab is already bookmarked.')
  else:
    fail('Error: Unrecognized response from API:\n'+response_body)


def parse_add_response(response_body):
  try:
    root = xml.etree.ElementTree.fromstring(response_body)
  except xml.etree.ElementTree.ParseError:
    fail('Error: Parsing error in response from API:\n'+response_body)
  if root.tag == 'result':
    try:
      result = root.attrib['code']
    except KeyError:
      fail('Error: Unrecognized response from API:\n'+response_body)
    if result == 'done':
      return True
    elif result == 'something went wrong':
      return False
  else:
    fail('Error: Unrecognized response from API:\n'+response_body)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
