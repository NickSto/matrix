#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import os
import sys
import argparse
import accountslib

OPT_DEFAULTS = {'output':None}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Parse the accounts.txt file and print the selected information."""
EPILOG = """N.B.: The parser operates in strict-mode only. Any error will cause an exception (but
a line number and helpful message will be printed)."""

ACCOUNTS_PATH_DEFAULT = '~/annex/Info/reference, notes/accounts.txt'

def main():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('accounts_path', nargs='?',
    help='Default: '+ACCOUNTS_PATH_DEFAULT)
  parser.add_argument('-o', '--output', choices=('name', 'entry', 'keys', 'values'),
    help='What to print when a match is found. '
         '"name": print the entry name only. '
         '"entry": print the entire entry in human-readable format, like it would appear in '
         'accounts.txt. '
         '"keys": print individual key/values lines. '
         '"values": print key/value lines with one value per line. If a key with multiple values '
         'matches, one line will be printed per value (repeating the key). '
         'Default: "keys" when --keys, --values, or --flags is given, "entry" otherwise.')
  parser.add_argument('-t', '--tabs', action='store_true',
    help='Format output as tab-delimited, computer-readable lines. Flags are stripped from values.')
  filters = parser.add_argument_group(title='Filters', description='These arguments select which '
    'entry, keys, or values to print. A hit must match every filter given. For --keys, --values, '
    'and --flags, a hit can match any of the strings given.')
  filters.add_argument('-e', '--entry',
    help='The entry name.')
  filters.add_argument('-z', '--fuzzy-match',
    help='A string that must be present in the entry name or one of its keys (case-insensitive).')
  filters.add_argument('-k', '--keys', type=lambda keys: keys.split(','),
    help='Key name(s). Comma-delimited list.')
  filters.add_argument('-v', '--values', type=lambda values: values.split(','),
    help='Values. Comma-delimited list.')
  filters.add_argument('-f', '--flags', type=lambda values: values.split(','),
    help='Flags. Comma-delimited list.')

  args = parser.parse_args()

  if args.accounts_path:
    accounts_path = args.accounts_path
  else:
    accounts_path = os.path.expanduser(ACCOUNTS_PATH_DEFAULT)

  if args.output is not None:
    output = args.output
  elif args.keys or args.values or args.flags:
    output = 'keys'
  else:
    output = 'entry'

  with open(accounts_path) as accounts_file:
    for entry in accountslib.parse(accounts_file):
      if args.entry and args.entry != entry.name:
        continue
      elif args.fuzzy_match and not entry.fuzzy_matches(args.fuzzy_match):
        continue
      matched_entry = False
      for account in entry.accounts.values():
        for section in account.values():
          for key, values in section.items():
            if args.keys and key not in args.keys:
              continue
            for value in values:
              if value.matches(args.values, args.flags):
                if output == 'entry':
                  print(str(entry)+'\n')
                  matched_entry = True
                  break
                elif output == 'name':
                  print(entry.name)
                  matched_entry = True
                  break
                elif output == 'keys':
                  if args.tabs:
                    print(key, *[value.value for value in values], sep='\t')
                  else:
                    print('\t' + key + ':\t' + '; '.join(map(str, values)))
                  break
                elif output == 'values':
                  if args.tabs:
                    print(key, value.value, sep='\t')
                  else:
                    print('\t{}:\t{}'.format(key, value))
            if matched_entry:
              break
          if matched_entry:
            break
        if matched_entry:
          break


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  main()
