#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import errno
import shutil
import logging
import argparse
import datetime
import subprocess
assert sys.version_info.major >= 3, 'Python 3 required'

TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
DESCRIPTION = """Transfer git history from one repo to another.
This will take commits from old_repo and commit them into new_repo.
It only works with a simple, linear series of commits and will fail if it encounters a merge
(a commit with more than one parent).
A better way to do this would be with git cherry-pick:
https://stackoverflow.com/questions/37471740/how-to-copy-commits-from-one-git-repo-to-another"""
EPILOG = 'Hold my beer.'


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
  parser.add_argument('old_repo')
  parser.add_argument('new_repo')
  #TODO: Allow specifying start/end with commit hashes.
  parser.add_argument('-s', '--start-time', type=parse_timestamps,
    help='Timestamp of earliest commit to migrate. Can be an ISO 8601 date & time (format '
         'YYYY-MM-DDTHH:MM:SS±ZZ:ZZ) or a Unix timestamp.')
  parser.add_argument('-e', '--end-time', type=parse_timestamps,
    help='Timestamp of latest commit to migrate.')
  parser.add_argument('-x', '--execute', action='store_true')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.INFO)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  work_tree = '--work-tree='+os.path.abspath(args.old_repo)
  git_dir = '--git-dir='+os.path.join(os.path.abspath(args.old_repo), '.git')
  work_tree_new = '--work-tree='+os.path.abspath(args.new_repo)
  git_dir_new = '--git-dir='+os.path.join(os.path.abspath(args.new_repo), '.git')

  git_log_output = stream_command(('git', work_tree, git_dir, 'log', '--date=iso-strict', '--parents'))

  old_history = parse_git_log(git_log_output)

  for commit in reversed(list(old_history)):
    if args.start_time and commit['datetime'] < args.start_time:
      continue
    elif args.end_time and commit['datetime'] > args.end_time:
      continue
    if len(commit['parents']) == 0:
      parent = None
    elif len(commit['parents']) > 1:
      fail('Don\'t know what to do with a commit with multiple parents.')
    else:
      parent = commit['parents'][0]
    changed_files = []
    creation_deletions = []
    if parent is not None:
      command = ('git', work_tree, git_dir, 'diff', '--name-only', parent, commit['hash'])
      changed_files = list(stream_command(command))
      command = ('git', work_tree, git_dir, 'diff', '--summary', parent, commit['hash'])
      creation_deletions = parse_git_diff_summary(stream_command(command))

    logging.info('\nOn commit {} ({}): {}'
                 .format(commit['hash'][:7], commit['date'][:10], commit['message'][:68]))
    logging.debug("""
parents:\t{}
author:\t\t{author} <{email}>
date:\t\t{date}
timestamp:\t{}""".format(parent, int(commit['datetime'].timestamp()), **commit))
    logging.debug('message:')
    for line in commit['message'].splitlines():
      logging.debug('\t'+line)
    logging.debug('changes:')
    for file in changed_files:
      try:
        change = creation_deletions[file]
        logging.debug('\t{action} ({mode}): {}'.format(file, **change))
      except KeyError:
        logging.debug('\tmodified:        '+file)

    logging.info('$ git checkout '+commit['hash'])
    command = ('git', work_tree, git_dir, 'checkout', commit['hash'])
    execute_command(command, execute=args.execute)
    for file in changed_files:
      change = creation_deletions.get(file, {'action':'modify'})
      src = os.path.join(args.old_repo, file)
      dest = os.path.join(args.new_repo, file)
      if change['action'] == 'create':
        dest_dirname = os.path.dirname(dest)
        if not os.path.isdir(dest_dirname):
          logging.info('($) mkdir '+dest_dirname)
          if args.execute:
            os.makedirs(dest_dirname)
      elif change['action'] == 'delete':
        logging.info('$ git rm '+dest)
        command = ('git', work_tree_new, git_dir_new, 'rm', file)
        execute_command(command, execute=args.execute)
      if change['action'] in ('create', 'modify'):
        logging.info('($) cp {} {}'.format(src, dest))
        if args.execute:
          shutil.copy2(src, dest)
        logging.info('$ git add '+file)
        command = ('git', work_tree_new, git_dir_new, 'add', file)
        execute_command(command, execute=args.execute)
    logging.info('$ git commit')
    command = ('git', work_tree_new, git_dir_new, 'commit', '--date', commit['date'], '-m',
               commit['message'])
    execute_command(command, execute=args.execute)


def parse_timestamps(timestamp_str):
  try:
    return parse_iso8601(timestamp_str)
  except (IndexError, ValueError):
    return datetime.datetime.fromtimestamp(int(timestamp_str))


def parse_iso8601(iso8601):
  fields = iso8601.split(':')
  new_iso8601 = ':'.join(fields[:3]) + fields[3]
  return datetime.datetime.strptime(new_iso8601, TIMESTAMP_FORMAT)


def stream_command(command):
  logging.debug('$ '+' '.join(command))
  process = subprocess.Popen(command, stdout=subprocess.PIPE)
  for line_bytes in process.stdout:
    line = line_bytes.decode(sys.getdefaultencoding())
    yield line.rstrip('\r\n')


def execute_command(command, execute=False):
  logging.debug('$ '+' '.join(command))
  if execute:
    subprocess.check_call(command)


def parse_git_log(git_log_output):
  # Parse output of $ git log --parents --date=iso-strict
  commit = {}
  message = ''
  for line in git_log_output:
    fields = line.split()
    if not fields:
      continue
    if line.startswith('    '):
      if message:
        message += '\n'+line[4:]
      else:
        message = line[4:]
    elif fields[0] == 'commit':
      if commit:
        commit['message'] = message
        yield commit
      commit = {}
      message = ''
      commit['hash'] = fields[1]
      parents = []
      for hash in fields[2:]:
        parents.append(hash)
      commit['parents'] = parents
    elif fields[0] == 'Author:':
      commit['author'] = fields[1]
      commit['email'] = fields[2].lstrip('<').rstrip('>')
    elif fields[0] == 'Date:':
      commit['date'] = fields[1]
      commit['datetime'] = parse_iso8601(commit['date'])
  if commit:
    commit['message'] = message
    yield commit


def parse_git_diff_summary(git_diff_output):
  # Parse output of $ git diff --summary
  changes = {}
  for line in git_diff_output:
    fields = line.split()
    if not fields:
      continue
    changes[fields[3]] = {'action':fields[0], 'mode':fields[2]}
  return changes


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
