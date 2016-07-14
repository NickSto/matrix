#!/usr/bin/env python
from __future__ import division
import os
import sys
import argparse
import accountslib

OPT_DEFAULTS = {'keys':()}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Parse the accounts.txt file, find parsing errors, and print selected information.
"""
EPILOG = """N.B.: Binary flags (like for "**used credit card**") are not
currently output, though some are parsed properly with no formatting errors."""

ACCOUNTS_FILE_DEFAULT = '~/annex/Info/reference, notes/accounts.txt'

def main():

  parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('accounts_file', nargs='?',
    help='Default: '+ACCOUNTS_FILE_DEFAULT)
  parser.add_argument('-k', '--keys', type=lambda keys: keys.split(','),
    help='Keys to select. Will only print the key: value line. If there are multiple values, it '
         'will print them on multiple lines, repeating the key name (perfect for sort | uniq). '
         'Give in comma-delimited format.')
  parser.add_argument('-a', '--print-all', action='store_true',
    help='Print all account information.')
  parser.add_argument('-w', '--warn', action='store_true',
    help='Instead of failing on a parsing error (before printing any output), print a warning and '
         'continue.')
  parser.add_argument('-q', '--quiet', action='store_true',
    help='Don\'t print warnings.')
  parser.add_argument('-O', '--stdout', action='store_true',
    help='Suppress normal output and print warnings to stdout.')

  args = parser.parse_args()

  if args.warn:
    level = 'warn'
  else:
    level = 'die'
  if args.quiet:
    level = 'silent'
  if args.stdout:
    level = 'stdout'

  if args.accounts_file:
    accounts_file = args.accounts_file
  else:
    accounts_file = os.path.expanduser(ACCOUNTS_FILE_DEFAULT)

  accounts = accountslib.AccountsReader(accounts_file)

  for error in accounts.errors:
    # format output
    if error['data'] is None:
      output = '{message}.\n'.format(**error)
    else:
      output = '{message}:\n{line}:{data}\n'.format(**error)
    # perform appropriate action
    if level == 'stdout':
      sys.stdout.write(output)
    elif level == 'warn':
      sys.stderr.write('Warning: '+output)
    elif level == 'die':
      sys.stderr.write('Error: '+output)
      sys.exit(1)
    elif level == 'silent':
      pass

  if args.stdout:
    sys.exit(0)

  for entry in accounts:
    if args.print_all:
      if entry.site_alias is None:
        print "{}:".format(entry.site)
      else:
        print "{} ({}):".format(entry.site, entry.site_alias)
    account = entry.default_account
    section = entry.default_section
    for account in entry.accounts():
      # if account != entry.default_account:
      if args.print_all:
        print "  {account "+str(account)+"}"
      for section in entry.sections(account):
        if args.print_all and section != entry.default_section:
          print "    ["+section+"]"
        for (key, values) in entry.items(account=account, section=section):
          if args.keys:
            if key[2] in args.keys:
              for value in values:
                print "\t{}:\t{}".format(key[2], value)
          elif args.print_all:
            print "\t{}:\t{}".format(key[2], format_values(values))


def format_values(values):
  value_strs = []
  for value in values:
    flags = values[value]
    if len(flags) == 0:
      value_strs.append(str(value))
    else:
      print "found flags for "+value
      flag_strs = map(lambda x: '**'+x+'**', flags)
      flags_str = ' '.join(flag_strs)
      value_strs.append(str(value)+' '+flags_str)
  return '; '.join(value_strs)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  main()
