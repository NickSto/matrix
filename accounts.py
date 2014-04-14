#!/usr/bin/env python
#TODO: turn into module
#TODO: deal with comments at the ends of lines  # like this
#      but somehow allow in things like "account #:" or "PIN#"
#TODO: deal with "[deleted]" and binary flags in general
from __future__ import division
import re
import os
import sys
import argparse
import accountslib

OPT_DEFAULTS = {'validate':True}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Parse the accounts.txt file."""
EPILOG = """"""

ACCOUNTS_FILE_DEFAULT = 'annex/Info/reference, notes/accounts.txt'
TOP_LEVEL_REGEX = r'^>>([^>]+)\s*$'
SECTION_REGEX = r'^>([^>]+)\s*$'
SITE_REGEX = r'^(\S(?:.*\S)):\s*$'
SITE_URL_REGEX = r'^((?:.+://)?[^.]+\.[^.]+.+):\s*$'
SITE_ALIAS_REGEX = r' \(([^)]+)\):\s*$'
ACCOUNT_NUM_REGEX = r'^\s+{account ?(\d+)}\s*$' # new account num format
SUBSECTION_REGEX1 = r'^\s*\[([\w#. -]+)\]\s*$'
SUBSECTION_REGEX2 = r'^ {3,5}(\S(?:.*\S)):\s*$'
KEYVAL_REGEX = r'^\s+(\S(?:.*\S)?):\s*(\S.*)$'
KEYVAL_NEW_REGEX = r'^\t(\S(?:.*\S)?):\t+(\S(?:.*\S)?)\s*$'
# Special cases
URL_LINE_REGEX = r'^((?:.+://)?[^.]+\.[^.]+.+)\s*$'
QLN_LINE_REGEX = r'^\s+([A-Z]{3})(?:\s+\S.*$|\s*$)'
CC_LINE_REGEX = r'\s*\*.*credit card.*\*\s*'

def main():

  parser = argparse.ArgumentParser(
    description=DESCRIPTION, usage=USAGE, epilog=EPILOG)
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
      output = '{message}:\n{data}\n'.format(**error)
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
    subsection = entry.default_subsection
    if account in entry.accounts():
      print "  {account"+str(account)+"}"
      print "    ["+subsection+"]"
    for (key, value) in entry.items():
      if account != key[1]:
        account = key[1]
        print "  {account"+str(account)+"}"
        subsection = key[2]
        print "    ["+subsection+"]"
      if subsection != key[2]:
        subsection = key[2]
        print "    ["+subsection+"]"
      print "\t{}:\t{}".format(key[0], value)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  main()
