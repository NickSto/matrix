#!/usr/bin/env python
from __future__ import division
import os
import sys
import argparse
import accountslib

OPT_DEFAULTS = {'validate':True}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Parse the accounts.txt file.
Stderr will print lines that violate the format. Stdout will print the account
data in the new, proper format."""
EPILOG = """N.B.: Binary flags (like for "**used credit card**") are not
currently output, though some are parsed properly with no formatting errors."""

ACCOUNTS_FILE_DEFAULT = 'annex/Info/reference, notes/accounts.txt'

def main():

  parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('accounts_file', nargs='?',
    help='Default: ~/'+ACCOUNTS_FILE_DEFAULT)
  parser.add_argument('-v', '--validate', action='store_true',
    help='Just check the file to make sure it still conforms to the '
      'assumptions of the parser.')
  parser.add_argument('-q', '--quiet', action='store_true',
    help="""Don't print warnings.""")
  parser.add_argument('-O', '--stdout', action='store_true',
    help="""Suppress normal output and print warnings to stdout.""")

  args = parser.parse_args()

  if args.validate:
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
    home = os.path.expanduser('~')
    accounts_file = os.path.join(home, ACCOUNTS_FILE_DEFAULT)

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
    print entry.site+':'
    account = entry.default_account
    section = entry.default_section
    if account in entry.accounts():
      print "  {account"+str(account)+"}"
      print "    ["+section+"]"
    for (key, value) in entry.items():
      if account != key[1]:
        account = key[1]
        print "  {account"+str(account)+"}"
        section = key[2]
        print "    ["+section+"]"
      if section != key[2]:
        section = key[2]
        print "    ["+section+"]"
      if isinstance(value, list) or isinstance(value, tuple):
        value = '; '.join(map(str, value))
      print "\t{}:\t{}".format(key[0], value)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  main()
