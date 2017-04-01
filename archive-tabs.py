#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import time
import errno
import urllib.parse
import http.client
import argparse
import xml.etree.ElementTree
session_manager = __import__('session-manager')

API_DOMAIN = 'api.pinboard.in'
GET_API_PATH = '/v1/posts/get?auth_token={token}&url={url}'
ADD_API_PATH = '/v1/posts/add?auth_token={token}&url={url}&description={title}&tags=tab+automated&replace=no'
MAX_RESPONSE = 16384 # bytes
ARG_DEFAULTS = {'pause':3.05}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Bookmark open tabs from a Firefox session with Pinboard."""

# API documentation: https://pinboard.in/api
# Get the auth token from https://pinboard.in/settings/password

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
  parser.add_argument('-w', '--window',
    help='Specify the window to look for tabs in, instead of the default (the biggest window). '
         'Format: WindowNum:NumTabs (e.g. "2:375"). The two, colon-delimited numbers are the '
         'window number, as given by session-manager.py, and the number of tabs in it (to make '
         'sure we\'re talking about the right window).')
  parser.add_argument('-b', '--begin',
    help='The title of the tab to start archiving at (inclusive). You can use just the '
         'beginning of the title, but it must be unique. If not given, will start with the first '
         'tab.')
  parser.add_argument('-e', '--end',
    help='The title of the tab to end archiving at (inclusive). You can use just the beginning of '
         'the title, but it must be unique. If not given, will stop at the last tab.')
  parser.add_argument('-p', '--pause', type=float,
    help='How many seconds to wait in-between each request to the API. The policy in the '
         'documentation (https://pinboard.in/api) is no more than 1 every 3 seconds. You should '
         'get a 429 response if it\'s exceeded. Default: %(default)s.')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'),
    help='Write a log of tabs archived to this file.')
  parser.add_argument('-d', '--debug', action='store_true')

  args = parser.parse_args(argv[1:])

  if not args.auth_token and not args.simulate:
    fail('Error: An --auth-token is required if --simulate is not given.')

  session = session_manager.file_to_json(args.session)

  if args.window:
    target_window, target_tabs = parse_window_spec(args.window)
    window_num = 0
    for window in session['windows']:
      window_num += 1
      if window_num == target_window:
        num_tabs = len(list(session_manager.get_tabs(window)))
        if num_tabs == target_tabs:
          print('Found specified --window (number {}, with {} tabs).'
                .format(target_window, target_tabs))
          break
        else:
          fail('Error: Window that matches given --window number has wrong number of tabs '
               '(--window gave {}, but window {} has {}).'.format(target_tabs, target_window,
                                                                  num_tabs))
  else:
    window = get_biggest_window(session)
    print('Found biggest window: {} tabs.'.format(len(list(session_manager.get_tabs(window)))))

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
  for tab in session_manager.get_tabs(window):
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
    fail('Error: --begin matches multiple tabs:\n'+'\n'.join(begin_matches))
  if len(end_matches) > 1:
    fail('Error: --end matches multiple tabs:\n'+'\n'.join(end_matches))

  print('Found {} tabs to archive.\n'.format(len(tabs)))

  for tab in tabs:
    if not tab['title']:
      tab['title'] = '.'
    print('\t'+tab['title'][:91])
    if tab['url'].startswith('about:'):
      print('about: tab. Skipping.')
      continue
    if not args.simulate:
      request_path = GET_API_PATH.format(token=args.auth_token, url=quote(tab['url']))
      response = make_request(API_DOMAIN, request_path)
      done = check_response(response, 'get')
      if done:
        print('Tab already bookmarked. Skipping.')
      time.sleep(args.pause)
      if not done:
        request_path = ADD_API_PATH.format(token=args.auth_token, url=quote(tab['url']),
                                           title=quote(tab['title']))
        if args.debug:
          print('https://'+API_DOMAIN+request_path)
        response = make_request(API_DOMAIN, request_path)
        success = check_response(response, 'add')
        if success:
          print('success')
        else:
          print('FAILED')
          sys.exit(1)
      if args.log:
        if done:
          result = 'done'
        elif success:
          result = 'bookmarked'
        else:
          result = 'FAILED'
        args.log.write('{}\t{}\t{}\n'.format(result, tab['title'], tab['url']))
      time.sleep(args.pause)


def parse_window_spec(window_spec):
  fields = window_spec.split(':')
  assert len(fields) == 2, 'Invalid format for --window (must be 2 colon-delimited fields)'
  try:
    target_window = int(fields[0])
    target_tabs = int(fields[1])
  except ValueError:
    fail('Invalid format for --window (WindowNum and NumTabs must be integers).')
  return target_window, target_tabs


def get_biggest_window(session):
  max_tabs = 0
  biggest_window = None
  for window in session['windows']:
    num_tabs = len(list(session_manager.get_tabs(window)))
    if num_tabs > max_tabs:
      max_tabs = num_tabs
      biggest_window = window
  return biggest_window


def quote(string):
  return urllib.parse.quote_plus(string)


def make_request(domain, path):
  conex = http.client.HTTPSConnection(domain)
  #TODO: Both of these steps can throw exceptions. Deal with them.
  conex.request('GET', path)
  return conex.getresponse()


def check_response(response, request_type):
  if response.status == 429:
    # API rate limit reached.
    fail('Error: API rate limit reached (429 Too Many Requests).')
  response_body = response.read(MAX_RESPONSE)
  if request_type == 'get':
    return parse_get_response(response_body)
  elif request_type == 'add':
    return parse_add_response(response_body)


def parse_get_response(response_body):
  """Return True if url is already bookmarked, False if not."""
  try:
    root = xml.etree.ElementTree.fromstring(response_body)
  except xml.etree.ElementTree.ParseError:
    fail('Error 1: Parsing error in response from API:\n'+response_body)
  if root.tag == 'posts':
    if len(root) == 0:
      return False
    elif len(root) == 1:
      return True
    else:
      fail('Error: Too many hits when checking if tab is already bookmarked: {} hits'
           .format(len(root)))
  elif root.tag == 'result':
    if root.attrib.get('code') == 'something went wrong':
      fail('Error: Request failed when checking if tab is already bookmarked.')
    elif root.attrib.get('code') == 'done':
      fail('Error: "done" returned instead of result when checking if tab is already bookmarked.')
    elif 'code' in root.attrib:
      fail('Error: Received message "{}" when checking if tab is already bookmarked.'
           .format(root.attrib['code']))
    else:
      fail('Error 1: Unrecognized response from API:\n'+response_body)
  else:
    fail('Error 2: Unrecognized response from API:\n'+response_body)


def parse_add_response(response_body):
  try:
    root = xml.etree.ElementTree.fromstring(response_body)
  except xml.etree.ElementTree.ParseError:
    fail('Error 2: Parsing error in response from API:\n'+response_body)
  if root.tag == 'result':
    try:
      result = root.attrib['code']
    except KeyError:
      fail('Error 3: Unrecognized response from API:\n'+response_body)
    if result == 'done':
      return True
    elif result == 'something went wrong':
      return False
    else:
      fail('Error: Received message "{}" when adding bookmark.'.format(result))
  else:
    fail('Error 4: Unrecognized response from API:\n'+response_body)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
