#!/usr/bin/env python
from __future__ import division
import sys
import argparse

OPT_DEFAULTS = {}
USAGE = """%(prog)s [-t binary] 01100010 01111001 01110100 01100101 01110011
%(prog)s [-t binary] 011000110110111101101110011000110110000101110100
%(prog)s [-t ascii] hello there
echo 01110011 01110100 01100100 01101001 01101110 | %(prog)s [-t binary]"""
DESCRIPTION = """Convert binary bytes to ASCII characters and vice versa."""


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION, usage=USAGE)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('input', nargs='*',
    help='Binary or ASCII data. Can omit to read from stdin.')
  parser.add_argument('-t', '--type', choices=('binary', 'ascii'),
    help='Force the input to be interpreted as binary or ASCII. Will be inferred if not specified.')

  args = parser.parse_args(argv[1:])

  if len(args.input) > 0:
    # Join arguments with spaces
    line = ' '.join(args.input)
    input_data = [line]
  else:
    input_data = sys.stdin

  if args.type:
    input_type = args.type
  else:
    input_type = None

  for line in input_data:
    if input_type is None:
      input_type = sniff(line)
    if input_type == 'binary':
      for word in line.split():
        i = 0
        while i <= len(word)-8:
          byte = word[i:i+8]
          sys.stdout.write(chr(int(byte, 2)))
          i += 8
    elif input_type == 'ascii':
      for char in line:
        sys.stdout.write('{0:08b} '.format(ord(char)))

  print


def sniff(data):
  for char in data[:100]:
    if char not in '01 \t\n\r':
      return 'ascii'
  return 'binary'


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
