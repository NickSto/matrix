#!/usr/bin/env python
from __future__ import division
import os
import sys
import argparse
import accountslib2

OPT_DEFAULTS = {'keys':()}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Parse the accounts.txt file for selected information. And find formatting errors.
"""
EPILOG = """N.B.: The parser operates in strict-mode only. Any error will cause an exception (but
a line number and helpful message will be printed)."""

ACCOUNTS_PATH_DEFAULT = '~/annex/Info/reference, notes/accounts.txt'

def main():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('accounts_path', nargs='?',
    help='Default: '+ACCOUNTS_PATH_DEFAULT)
  parser.add_argument('-k', '--keys', type=lambda keys: keys.split(','),
    help='Keys to select. Will only print the key: value line. If there are multiple values, it '
         'will print them on multiple lines, repeating the key name (perfect for sort | uniq). '
         'Give in comma-delimited format.')
  parser.add_argument('-f', '--flag',
    help='Select values with this flag set. If --keys is given, select only the values for those '
         'keys. Otherwise, select all values with this flag, regardless of the key.')
  parser.add_argument('-a', '--print-all', action='store_true',
    help='Print all account information.')

  args = parser.parse_args()

  if args.accounts_path:
    accounts_path = args.accounts_path
  else:
    accounts_path = os.path.expanduser(ACCOUNTS_PATH_DEFAULT)

  with open(accounts_path) as accounts_file:
    for entry in accountslib2.parse(accounts_file):
      if args.print_all:
        print entry.name+':'
      for account in entry.accounts.values():
        # if account != entry.default_account:
        if args.print_all:
          print "  {account"+str(account.number)+"}"
        for section in account.sections.values():
          if args.print_all:
            print "    ["+section.name+"]"
          for key, values in section.items():
            if args.keys:
              if key in args.keys:
                for value in values:
                  print_value = False
                  if args.flag:
                    if args.flag in value.flags:
                      print_value = True
                  else:
                    print_value = True
                  if print_value:
                    print "\t{}:\t{}".format(key, value)
            elif args.print_all:
              print "\t{}:\t{}".format(key, format_values(values))
            elif args.flag:
              output_values = []
              for value in values:
                if args.flag in value.flags:
                  flags_str = ' '.join(['**{}**'.format(flag) for flag in value.flags])
                  output_values.append(str(value)+' '+flags_str)
              if output_values:
                print '\t{}:\t{}'.format(key, '; '.join(output_values))


def format_values(values):
  value_strs = []
  for value in values:
    value_str = str(value)
    for flag in value.flags:
      value_str += ' **'+flag+'**'
    value_strs.append(value_str)
  return '; '.join(value_strs)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  main()
