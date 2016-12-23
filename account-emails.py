#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import argparse
import accountslib
import collections

ARG_DEFAULTS = {'email':'nmapsy', 'accounts_path':'~/annex/Info/reference, notes/accounts.txt'}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Go through my accounts and find all the dot-variations of my spam email address
I've used."""


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('accounts_path', metavar='accounts.txt', nargs='?', type=os.path.expanduser,
    help='The accounts text file. Default: %(default)s.')
  parser.add_argument('-e', '--email',
    help='The email address to look for. Default: %(default)s')
  parser.add_argument('-c', '--choose', action='store_true',
    help='Just choose an unused email, or if all are used, the least-often used one.')
  parser.add_argument('-t', '--tabs', action='store_true',
    help='Print tab-delimited lines with no colons (computer-readable).')

  args = parser.parse_args(argv[1:])

  # Create all possible combinations of dots in the username.
  # (Only considers single dots between letters, not multiple.)
  basenames = collections.defaultdict(lambda: 0)
  # How many places are there for dots in-between characters in the email?
  places = len(args.email)-1
  # Make a format string like '{:05b}' that will print a binary sequence of 1's and 0's as wide as
  # the number of places.
  format_str = '{:0'+str(places)+'b}'
  # The number of possible dot combinations is 2**places.
  for i in range(2**places):
    email = ''
    # Get a string of 0's and 1's representing presence or absence of dots.
    pattern = format_str.format(i)
    # Build an email string with dots where there are 0's in the pattern string.
    for char, bit in zip(args.email, pattern):
      if bit == '0':
        email += char
      elif bit == '1':
        email += char + '.'
    email += args.email[-1]
    basenames[email] = 0

  with open(args.accounts_path, 'rU') as accounts_file:
    for entry in accountslib.parse(accounts_file):
      for account in entry.accounts.values():
        for section in account.values():
          for key, values in section.items():
            if key.lower() == 'email':
              for value in values:
                username = value.value.split('@')[0]
                basename = username.split('+')[0]
                if basename.replace('.', '') == args.email:
                  basenames[basename] += 1

  # Print all the used combinations.
  least_used = None
  uses_min = 999999999
  dots_min = len(args.email)
  basename_list = reversed(sorted(basenames.keys(), key=lambda basename: basenames[basename]))
  for basename in basename_list:
    if args.choose:
      # Track the email with the fewest uses, and if there are multiple with the fewest, find the
      # one out of those with the fewest dots.
      uses = basenames[basename]
      dots = len(basename) - len(args.email)
      if uses < uses_min:
        least_used = basename
        uses_min = uses
        dots_min = dots
      elif uses == uses_min:
        if dots < dots_min:
          least_used = basename
          dots_min = dots
    else:
      # If not --choose, just print every email.
      print_email(basename, basenames[basename], args.tabs)
  if args.choose:
    print_email(least_used, uses_min, args.tabs)


def print_email(email, uses, tabs=False):
  if tabs:
    print(email, uses, sep='\t')
  else:
    print('{:16s}{}'.format(email+':', uses))


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
