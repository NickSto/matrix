#!/usr/bin/env python3
import sys
import json
import logging
import argparse
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Compare two JSON objects. Give two files, each containing a single JSON object.
This will compare the two objects, and tell you if they differ. It won't give much information
beside that fact, though. This is a quick workaround to the problem of using the diff command when
the order of dictionaries is different in the file."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('json1')
  parser.add_argument('json2')
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

  with open(args.json1) as json1_file:
    json1 = json.load(json1_file)

  with open(args.json2) as json2_file:
    json2 = json.load(json2_file)

  if diff_objects(json1, json2):
    print('The objects differ!')
    return 1
  else:
    print('The objects are the same!')
    return 0


def diff_objects(obj1, obj2):
  """Returns True if they differ, False otherwise."""
  if obj1 == obj2:
    return False
  if type(obj1) != type(obj2):
    print('Different types: {} vs {}'.format(type(obj1).__name__, type(obj2).__name__))
    return True
  if isinstance(obj1, list):
    if len(obj1) != len(obj2):
      print('Different array lengths: {} vs {}.'.format(len(obj1), len(obj2)))
      return True
    different = False
    for element1, element2 in zip(obj1, obj2):
      if diff_objects(element1, element2):
        different = True
    return different
  elif isinstance(obj1, dict):
    if len(obj1) != len(obj2):
      print('Different number of keys: {} vs {}.'.format(len(obj1), len(obj2)))
      return
    keys1 = sorted(obj1.keys())
    keys2 = sorted(obj2.keys())
    different = False
    for key1, key2 in zip(keys1, keys2):
      if key1 != key2:
        print('Different keys: {!r} vs {!r}.'.format(key1, key2))
        return
      if diff_objects(obj1[key1], obj2[key2]):
        different = True
    return different
  else:
    # They're primitive types.
    print('Different values: {!r} vs {!r}'.format(obj1, obj2))
    return True


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
