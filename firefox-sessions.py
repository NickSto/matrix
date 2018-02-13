#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import time
import json
import shutil
import logging
import tempfile
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
  parser.add_argument('-c', '--compress',
    help='Compress output into jsonlz4 and write to this file. Only works with --json output.')
  parser.add_argument('-w', '--windows', metavar='window:tabs', nargs='*', default=(),
    help='Select a certain set of windows to print, instead of the entire session. Use the format '
         '"WindowNum:NumTabs" (e.g. "2:375"). The two, colon-delimited numbers are the window '
         'number, as displayed by this script, and the number of tabs in it (to make sure we\'re '
         'talking about the right window). Note: All the global session data will be included, no '
         'matter what windows are chosen. Also, closed windows cannot be selected, even with '
         '--closed.')
  parser.add_argument('-j', '--join', nargs='*', default=(),
    help='Combine the sessions from these files with the first one (after filtering by --windows).')
  parser.add_argument('-C', '--closed', action='store_true',
    help='Include closed windows in the human and tsv outputs.')
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

  if args.compress:
    if not args.format == 'json':
      fail('Error: Can only use --compress on --json output.')
    if not shutil.which('jsonlz4'):
      fail('Error: Cannot find "jsonlz4" command to --compress output.')

  targets = set()
  for window_spec in args.windows:
    target_window, target_tabs = parse_window_spec(window_spec)
    targets.add((target_window, target_tabs))

  session = read_session_file(args.session)
  session = filter_session(session, targets)

  for session_path in args.join:
    addition = read_session_file(session_path)
    session = join_sessions(session, addition)

  if args.format == 'json':
    if args.compress:
      write_jsonlz4(session, args.compress)
    else:
      json.dump(session, sys.stdout)
  else:
    output = format_contents(session, args.titles, args.urls, args.format, args.closed)
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
  ext = os.path.splitext(session_arg)[1]
  if ext == '.jsonlz4':
    # It's JSON compressed in Mozilla's custom format.
    if not shutil.which('dejsonlz4'):
      fail('Error: Cannot find "dejsonlz4" command to decompress session file.')
    process = subprocess.Popen(['dejsonlz4', session_arg, '-'], stdout=subprocess.PIPE)
    session_str = str(process.stdout.read(), 'utf8')
    return json.loads(session_str)
  elif ext == '.session':
    # It's a Session Manager .session file.
    return file_to_json(session_arg)
  elif ext in ('.json', '.js', '.bak'):
    # It's a pure JSON file.
    with open(session_arg) as session_file:
      return json.load(session_file)
  else:
    fail('Error: Unrecognized session file extension "{}".'.format(ext))


def file_to_json(path):
  line_num = 0
  with open(path, 'rU', encoding='utf8') as session_file:
    for line in session_file:
      line_num += 1
      if line_num == 5:
        return json.loads(line)


def filter_session(session, targets):
  """Filter the session to only include the windows listed in "targets".
  Warning: This returns a new session that's a shallow copy."""
  if not targets:
    return session
  # Make a shallow copy of the session dict, but empty the windows list and alter some of the global
  # variables.
  new_session = session.copy()
  new_session['windows'] = []
  new_session['selectedWindow'] = None
  if 'lastUpdate' in new_session.get('session', {}):
    new_session['session']['lastUpdate'] = int(time.time()*1000)
  # Insert the target windows.
  selected_window = session.get('selectedWindow', 1)
  hits = set()
  for w, window in enumerate(session['windows']):
    tabs = len(window['tabs'])
    if (w+1, tabs) in targets:
      new_session['windows'].append(window)
      hits.add((w+1, tabs))
      if w+1 == selected_window:
        new_session['selectedWindow'] = len(new_session['windows'])
  if new_session['selectedWindow'] is None:
    new_session['selectedWindow'] = 1
  # Check there weren't targets given with no match.
  if hits != targets:
    misses = targets - hits
    misses_str = '", "'.join(['{}:{}'.format(*miss) for miss in misses])
    fail('Error: No windows found that match the target(s) "{}".'.format(misses_str))
  return new_session


def join_sessions(session1, session2):
  """Combine two sessions.
  Append the window list of session 2 to that of session 1, and deal with the other keys in the
  most logical manner.
  Warning: This only performs shallow copies, so the merged session contains references to objects
  in the input sessions may be altered, which themselves may be altered."""
  new_session = {}
  # version key:
  for session in (session1, session2):
    if 'version' in session:
      version = session['version']
      try:
        if version[0] != 'sessionrestore' or version[1] != 1:
          fail('Error: Unrecognized "version" value: {!r}'.format(version))
      except (KeyError, IndexError, TypeError):
        fail('Error: Unrecognized "version" value: {!r}'.format(version))
  new_session['version'] = ['sessionrestore', 1]
  # windows key:
  if 'windows' not in session1 or 'windows' not in session2:
    fail('Error: empty session (no windows)!')
  windows1 = session1['windows']
  windows1.extend(session2['windows'])
  new_session['windows'] = windows1
  # _closedWindows key:
  closed_windows = session1.get('_closedWindows', [])
  for closed_window in session2.get('_closedWindows', []):
    if closed_window not in closed_windows:
      closed_windows.append(closed_window)
  new_session['_closedWindows'] = closed_windows
  # cookies key:
  if 'cookies' in session1 and 'cookies' in session2:
    new_session['cookies'] = join_cookies(session1['cookies'], session2['cookies'])
  elif 'cookies' in session1:
    new_session['cookies'] = session1['cookies']
  elif 'cookies' in session2:
    new_session['cookies'] = session2['cookies']
  else:
    new_session['cookies'] = []
  # session key:
  session_data1 = session1.get('session', {})
  session_data2 = session2.get('session', {})
  now = int(time.time()*1000)
  start_time = min(session_data1.get('startTime', now-1), session_data2.get('startTime', now-1))
  recent_crashes = max(session_data1.get('recentCrashes', 0), session_data2.get('recentCrashes', 0))
  new_session['session'] = session_data1
  new_session['session'].update(session_data2)
  new_session['session']['startTime'] = start_time
  new_session['session']['lastUpdate'] = now
  new_session['session']['recentCrashes'] = recent_crashes
  # global key:
  new_session['global'] = session1.get('global', {})
  new_session['global'].update(session2.get('global', {}))
  # scratchpads key:
  if 'scratchpads' in session1 or 'scratchpads' in session2:
    new_session['scratchpads'] = session1.get('scratchpads', [])
    new_session['scratchpads'].extend(session2.get('scratchpads', []))
  # browserConsole key:
  if 'browserConsole' in session1 or 'browserConsole' in session2:
    new_session['browserConsole'] = (session1.get('browserConsole', False) or
                                     session2.get('browserConsole', False))
  # selectedWindow key:
  # Arbitrarily choose the selectedWindow from the first session.
  new_session['selectedWindow'] = session1.get('selectedWindow', 1)
  # Copy the non-standard key/values.
  keys1 = set(session1.keys())
  keys2 = set(session2.keys())
  standard_keys = {'version', 'windows', 'selectedWindow', '_closedWindows', 'cookies', 'session',
                   'global', 'scratchpads', 'browserConsole'}
  other_keys = (keys1 | keys2) - standard_keys
  for key in other_keys:
    if key in session1 and key in session2:
      if session1[key] != session2[key]:
        fail('Error: Values for key {!r} in different sessions are different.'.format(key))
      else:
        new_session[key] = session1[key]
    elif key in session1:
      new_session[key] = session1[key]
    elif key in session2:
      new_session[key] = session2[key]
  return new_session


def join_cookies(cookie_list1, cookie_list2):
  #TODO: Double-check what actually makes a cookie unique.
  # Build cookie indices.
  cookies_index1 = index_cookies(cookie_list1)
  cookies_index2 = index_cookies(cookie_list2)
  new_cookies = []
  for cookie in cookie_list1 + cookie_list2:
    key = (cookie.get('host'), cookie.get('name'), cookie.get('path'))
    if key in cookies_index1:
      # If there's duplicate cookies, arbitrarily prefer the first one.
      new_cookies.append(cookies_index1[key])
    elif key in cookies_index2:
      new_cookies.append(cookies_index2[key])
  return new_cookies


def index_cookies(cookie_list):
  cookies_index = {}
  for cookie in cookie_list:
    key = (cookie.get('host'), cookie.get('name'), cookie.get('path'))
    cookies_index[key] = cookie
  return cookies_index


def write_jsonlz4(session, jsonlz4_path):
  dir_path = os.path.dirname(jsonlz4_path)
  json_file = tempfile.NamedTemporaryFile(mode='w', dir=dir_path, suffix='.json', delete=False)
  try:
    json.dump(session, json_file)
    json_file.close()
    subprocess.check_call(['jsonlz4', json_file.name, jsonlz4_path])
  finally:
    if not json_file.closed:
      json_file.close()
    if os.path.exists(json_file.name):
      os.remove(json_file.name)


def format_contents(session, titles=False, urls=False, format='human', closed=False):
  output = []
  window_lists = [session['windows']]
  prefixes = ('W',)
  if closed:
    closed_windows = session.get('_closedWindows', [])
    window_lists.append(closed_windows)
    prefixes = ('W', 'Closed w')
  tab_counts = []
  for window_list, prefix in zip(window_lists, prefixes):
    for w, window in enumerate(window_list):
      label = prefix+'indow {:3s}'.format(str(w+1)+':')
      if closed:
        label_width = '17'
      else:
        label_width = '8'
      format_str = '{:'+label_width+'s} {:3d} tabs'
      tabs = len(window['tabs'])
      tab_counts.append(tabs)
      if format == 'human':
        output.append(format_str.format(label, tabs))
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
    if closed:
      format_str = 'Total:            {:3d} tabs'
    else:
      format_str = 'Total:     {:3d} tabs'
    output.append(format_str.format(sum(tab_counts)))
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
