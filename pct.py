#!/usr/bin/env python
from __future__ import division
import sys
import urllib
import argparse


OPT_DEFAULTS = {'preserve':''}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Percent-encode and decode strings (like in a URL).
This is a thin wrapper around urllib.quote() and urllib.unquote()."""
EPILOG = """WARNING: This currently cannot handle Unicode."""

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('operation', choices=('encode', 'decode'),
    help='Whether to "encode" or "decode".')
  parser.add_argument('string',
    help='The string to encode or decode.')
  parser.add_argument('-p', '--preserve',
    help='Preserve these characters instead of encoding them. This is in addition to the default '
         'preserved characters (letters, numbers, "_", ".", and "-").')

  args = parser.parse_args(argv[1:])

  if args.operation == 'encode':
    print urllib.quote(args.string, safe=args.preserve)
  elif args.operation == 'decode':
    print urllib.unquote(args.string)
  else:
    raise AssertionError('Operation must be "encode" or "decode".')


if __name__ == '__main__':
  sys.exit(main(sys.argv))
