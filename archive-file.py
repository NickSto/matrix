#!/usr/bin/env python3
import os
import sys
import time
import shutil
import logging
import argparse
import datetime
assert sys.version_info.major >= 3, 'Python 3 required'

VERSION = 1.1
NOW = int(time.time())
PERIODS = {
  # 'minutely': 60,
  'hourly': 60*60,
  'daily':  24*60*60,
  'weekly': 7*24*60*60,
  'monthly':int(60*60*24*365.2425/12),
  'yearly': int(60*60*24*365.2425),
  'forever':NOW-1,
}
DESCRIPTION = """Archive copies of the target file. Keep a set of copies from different time
periods, like the last hour, day, week, month, etc."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('file',
    help='The file to back up.')
  parser.add_argument('-d', '--destination',
    help='The directory the archive is/should be stored in. Default is the same directory the '
         'target file lives in.')
  parser.add_argument('-a', '--archive-tracker')
  parser.add_argument('-e', '--ext',
    help='The extension of the file. You can use this to make sure the names of the archive files '
         'are like "example-2017-03-23-121700.tar.gz" instead of '
         '"example.tar-2017-03-23-121700.gz".')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = parser.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  if not os.path.exists(args.file):
    fail('Error: Target file {!r} not found.'.format(args.file))

  filename = os.path.basename(args.file)
  destination = args.destination or os.path.dirname(args.file)
  archive_tracker = args.archive_tracker or os.path.join(destination, '.archive-tracker')

  # Read the tracker file, get the section on our target file.
  if os.path.isfile(archive_tracker):
    with open(archive_tracker) as tracker_file:
      tracker = read_tracker(tracker_file, PERIODS, VERSION)
  else:
    tracker = {filename:{}}
  try:
    tracker_section = tracker[filename]
  except KeyError:
    fail('Error: Target file "{}" not found in tracker {}.'.format(filename, archive_tracker))

  # Determine which archive files are older than the time period they're serving as backups for.
  expired = get_expired(tracker_section, destination, PERIODS, NOW)
  if not expired:
    logging.info('No archiving needed.')
    return
  logging.info('Overdue archives: '+', '.join([period for period in expired]))

  # Then copy the target file into the archive directory.
  archive_file_path = get_archive_path(args.file, args.ext, NOW)
  shutil.copy2(args.file, archive_file_path)

  # Update the tracker section with the new file and remove old ones.
  new_tracker_section, files_to_delete = update_tracker(tracker_section, expired, archive_file_path,
                                                        NOW)
  if files_to_delete:
    logging.info('Deleting old archive files: "'+'", "'.join(files_to_delete)+'"')
  delete_files(files_to_delete, destination)
  tracker[filename] = new_tracker_section

  # Write the updated tracker file.
  write_tracker(tracker, archive_tracker, PERIODS, VERSION)


def read_tracker(tracker_file, periods, expected_version=2.0):
  """
  Tracker file format:
    >version=1.0
    filename.ext
    \tmonthly\t1380426173\tfilename-2013-09-10.ext
    \tweekly\t1380436173\tfilename-2013-09-17.ext
  Returned data structure:
    {'filename.ext': {
      'monthly': (1380426173, 'filename-2013-09-10.ext'),
      'weekly':  (1380436173, 'filename-2013-09-17.ext')
      }
    }
  "filename.ext" begins one section, and there can be many sections in one file.
  """
  version = None
  tracker = {}
  section = {}
  path = None
  for line_raw in tracker_file:
    # What kind of line is it?
    header = line_raw.startswith('>')
    section_header = not line_raw.startswith('\t')
    line = line_raw.strip()
    # Ignore empty lines.
    if not line:
      continue
    # Check version in header.
    if header:
      if line.startswith('>version='):
        version = float(line[9:])
        if version > expected_version or expected_version - version >= 1.0:
          fail('Error: tracker file is version {}, which is incompatible with the current version '
               '{}'.format(version, expected_version))
      continue
    # Start a new section.
    if section_header:
      if not version:
        fail('Error: no version specified in tracker file.')
      if section and path:
        tracker[path] = section
      section = {}
      path = line
    else:
      # Parse a data line.
      fields = line.split('\t')
      if len(fields) == 3:
        period = fields[0].lower()
        timestamp = fields[1]
        filename = fields[2]
      else:
        fail('Error in tracker file. Wrong number of fields ({}) on line\n{}'
             .format(len(fields), line_raw))
      if period not in periods:
        fail('Error in tracker file. Invalid period "{}" on line\n{}'.format(period, line))
      try:
        timestamp = int(timestamp)
      except ValueError:
        fail('Error in tracker file. Invalid timestamp {!r} on line\n{}'.format(timestamp, line))
      section[period] = {'timestamp':timestamp, 'file':filename}
  # Save the last section.
  if section and path:
    tracker[path] = section
  return tracker


def get_expired(tracker_section, destination, periods, now=NOW):
  """Determine which periods need archiving.
  Input: one section from the output of read_tracker().
  Output: a dict, keys = period needing archiving & values = files to replace.
  This will add to the list any period whose entry in the archive is older than the length of
  the period. It will also add any period whose archive file is missing. Any time period not found
  in the input will be put on the expired list, with a file value of empty string."""
  expired = {}
  for period in periods:
    archive_expired = False
    last_time = None
    last_file = None
    last_path = None
    last_archive = tracker_section.get(period)
    if last_archive:
      last_time = last_archive['timestamp']
      last_file = last_archive['file']
      last_path = os.path.join(destination, last_file)
      elapsed = now - last_time
    if not last_archive:
      logging.debug('{} archive isn\'t in the tracker file.'.format(period))
      archive_expired = True
    elif not os.path.exists(last_path):
      logging.debug('{} archive doesn\'t exist (file {!r}).'.format(period, last_path))
      archive_expired = True
    elif elapsed > periods[period]:
      logging.debug('{} archive too old ({} > {}).'.format(period, elapsed, periods[period]))
      archive_expired = True
    if archive_expired:
      expired[period] = last_file
  return expired


def get_archive_path(target_path, ext=None, now=NOW):
  if ext is None:
    base, ext = os.path.splitext(target_path)
  else:
    if not ext.startswith('.'):
      ext = '.'+ext
    if target_path.endswith(ext):
      base = target_path[:-len(ext)]
  time_str = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d-%H%M%S')
  return base+'-'+time_str+ext


def update_tracker(tracker_section, expired, new_path, now=NOW):
  """Create new tracker and figure out which files are no longer needed.
  Files to be deleted are ones in the expired list but not in the new archive list."""
  new_file = os.path.basename(new_path)
  new_tracker_section = {}
  files_to_delete = []
  # Build a new tracker.
  all_periods = list(tracker_section.keys()) + list(expired.keys())
  for period in all_periods:
    if period in expired:
      new_tracker_section[period] = {'timestamp':now, 'file':new_file}
    else:
      new_tracker_section[period] = tracker_section[period]
  # Determine which files are no longer needed.
  expired_files = [expired[period] for period in expired if expired[period] is not None]
  archive_files = [new_tracker_section[period]['file'] for period in new_tracker_section]
  for filename in expired_files:
    if filename not in archive_files and filename not in files_to_delete:
      files_to_delete.append(filename)
  return new_tracker_section, files_to_delete


def delete_files(files_to_delete, destination):
  for filename in files_to_delete:
    path = os.path.join(destination, filename)
    if os.path.isfile(path):
      logging.debug('Deleting old archive file {!r}'.format(filename))
      try:
        os.remove(path)
      except OSError:
        fail('Error: Could not delete file {!r}.'.format(path))
    else:
      logging.warning('Warning: Could not find file {!r}'.format(path))


def write_tracker(tracker, tracker_path, periods=PERIODS, version=VERSION):
  ordered_periods = []
  for period, age in sorted(periods.items(), key=lambda i: i[1]):
    ordered_periods.append(period)
  try:
    with open(tracker_path, 'w') as tracker_file:
      tracker_file.write('>version={}\n'.format(version))
      for path in tracker:
        tracker_file.write(path+'\n')
        for period in ordered_periods:
          if period not in tracker[path]:
            continue
          timestamp = tracker[path][period]['timestamp']
          filename  = tracker[path][period]['file']
          tracker_file.write('\t{}\t{}\t{}\n'.format(period, timestamp, filename))
  except IOError:
    fail('Could not open file {!r}'.format(tracker_path))


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
