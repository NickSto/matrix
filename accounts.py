#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import os
import sys
import argparse
import accountslib

OPT_DEFAULTS = {'output':None, 'case':'sensitive'}
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
  parser.add_argument('-c', '--contains', action='store_true',
    help='Pass the filter if the value contains the filter string anywhere in it.')
  parser.add_argument('-i', '--case-insensitive', dest='case', action='store_const',
    const='insensitive',
    help='When comparing a value to a filter, do a case-insensitive match.')
  filters = parser.add_argument_group(title='Filters', description='These arguments select which '
    'entry, keys, or values to print. A hit must match every filter given. For --keys, --values, '
    'and --flags, a hit can match any of the strings given. The uppercase versions '
    '(-E, -K, -V, -F) are negations, meaning a hit cannot match any of those filters (even if it '
    'matches one of the positive filters).')
  filters.add_argument('-e', '--entry',
    help='The entry name.')
  filters.add_argument('-s', '--section',
    help='The [section name].')
  filters.add_argument('-k', '--keys', type=lambda keys: keys.split(','),
    help='Key name(s). Comma-delimited list.')
  filters.add_argument('-v', '--values', type=lambda values: values.split(','),
    help='Values. Comma-delimited list.')
  filters.add_argument('-f', '--flags', type=lambda values: values.split(','),
    help='Flags. Comma-delimited list.')
  filters.add_argument('-E', '--not-entry')
  filters.add_argument('-S', '--not-section')
  filters.add_argument('-K', '--not-keys', type=lambda values: values.split(','))
  filters.add_argument('-V', '--not-values', type=lambda values: values.split(','))
  filters.add_argument('-F', '--not-flags', type=lambda values: values.split(','))

  args = parser.parse_args()

  if args.accounts_path:
    accounts_path = args.accounts_path
  else:
    accounts_path = os.path.expanduser(ACCOUNTS_PATH_DEFAULT)

  if args.output is not None:
    output = args.output
  elif (args.section or args.keys or args.values or args.flags or args.not_section or args.not_keys
        or args.not_values or args.not_flags):
    output = 'keys'
  else:
    output = 'entry'

  with open(accounts_path) as accounts_file:
    for entry in accountslib.parse(accounts_file):
      if args.entry and not accountslib.matches(args.entry, entry.name, args.contains, args.case):
        continue
      if args.not_entry and accountslib.matches(args.not_entry, entry.name, args.contains, args.case):
        continue
      matched_entry = False
      for account in entry.accounts.values():
        for section in account.values():
          if args.section and not accountslib.matches(args.section, section.name, args.contains,
                                                      args.case):
            continue
          if args.not_section and accountslib.matches(args.not_section, section.name, args.contains,
                                                      args.case):
            continue
          for key, values in section.items():
            if args.keys and not accountslib.any_matches(key, args.keys, args.contains, args.case):
              continue
            if args.not_keys and accountslib.any_matches(key, args.not_keys, args.contains, args.case):
              continue
            for value in values:
              if ((args.values or args.flags) and
                  not value.matches(args.values, args.flags, args.contains, args.case)):
                continue
              if ((args.not_flags or args.not_values) and
                  value.matches(args.not_values, args.not_flags, args.contains, args.case)):
                continue
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
