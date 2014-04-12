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

  last_line = None
  top_level = None
  section = None
  with open(accounts_file, 'rU') as accounts_filehandle:
    for line_raw in accounts_filehandle:
      line = line_raw.rstrip('\r\n')
      # Skip blank or commented lines
      line_stripped = line.strip()
      if not line_stripped or line_stripped.startswith('#'):
        continue
      # At a top-level section heading?
      # (In addition to matching the regex, the previous line must contain
      # at least 20 "="s in a row.)
      if last_line is not None and '=' * 20 in last_line:
        top_level_match = re.search(TOP_LEVEL_REGEX, line)
        if top_level_match:
          top_level = top_level_match.group(1).lower()
          if not args.stdout: print '====='+top_level+'====='
          last_line = line
          continue
      # At a 2nd-level section heading?
      # (Previous line must contain at least 20 "-"s in a row.)
      if last_line is not None and '-' * 20 in last_line:
        section_match = re.search(SECTION_REGEX, line)
        if section_match:
          section = section_match.group(1).lower()
          if not args.stdout: print '-----'+section+'-----'
          last_line = line
          continue
      # Parse 'online' top-level section
      if top_level == 'online' and section is None:
        # What kind of line are we on?
        site_match = re.search(SITE_REGEX, line)
        account_num_match = re.search(ACCOUNT_NUM_REGEX, line)
        subsection_match1 = re.search(SUBSECTION_REGEX1, line)
        subsection_match2 = re.search(SUBSECTION_REGEX2, line)
        keyval_match = re.search(KEYVAL_REGEX, line)
        if site_match:
          # Start of a new entry
          site = site_match.group(1)
          site_url_match = re.search(SITE_URL_REGEX, line)
          if site_url_match:
            site = site_url_match.group(1)
            site_alias = None
            site_alias_match = re.search(SITE_ALIAS_REGEX, line)
            if site_alias_match:
              site_alias = site_alias_match.group(1)
              site_old = site
              site = site_old.replace(' ('+site_alias+')', '')
              if site == site_old:
                warn('Failed to remove alias from site name', line, 'die')
          if not args.stdout: print site+':'
          if site_alias and not args.stdout:
            print '('+site_alias+'):'
          subsection = None
          account_num = 0
        elif account_num_match:
          account_num = int(account_num_match.group(1))
          subsection = None
          if not args.stdout: print "{account"+str(account_num)+"}"
        elif subsection_match1 or subsection_match2:
          # start of subsection
          if subsection_match1:
            subsection = subsection_match1.group(1)
          else:
            subsection = subsection_match2.group(1)
          if not args.stdout: print '['+subsection+']'
        elif keyval_match:
          # a key/value data line
          keyval_new_match = re.search(KEYVAL_NEW_REGEX, line)
          if keyval_new_match:
            key = keyval_new_match.group(1)
            value = keyval_new_match.group(2)
            if not args.stdout: sys.stdout.write("(new) ")
          else:
            key = keyval_match.group(1)
            value = keyval_match.group(2)
            if not args.stdout: sys.stdout.write("(old) ")
          if ';' in value:
            # multiple values?
            value = [elem.strip() for elem in value.split(';')]
          if not args.stdout:
            print "{}:\t{}".format(key, value)
        elif '=' * 20 in line or '-' * 20 in line:
          # heading divider
          pass
        else:
          # Test for special case lines
          qln_match = re.search(QLN_LINE_REGEX, line)
          cc_line_match = re.search(CC_LINE_REGEX, line)
          url_line_match = re.search(URL_LINE_REGEX, line)
          site_last_match = re.search(SITE_REGEX, last_line)
          if url_line_match and site_last_match:
            # URL on line after entry heading
            site_alias = site_last_match.group(1)
            site = url_line_match.group(1)
            if not args.stdout: print "{}:\n({}):".format(site, site_alias)
          elif qln_match:
            # "QLN"-type shorthand
            qln = qln_match.group(1)
            if not args.stdout: print "QLN: "+str(qln)
          elif cc_line_match:
            # "stored credit card" note
            if not args.stdout: print "*stored credit card*"
          else:
            # Unrecognized.
            # If it looks suspiciously similar to an entry heading we didn't
            # catch, invalidate the current entry state.
            # (This is any line that doesn't start with whitespace.)
            if re.search(r'^\S', line):
              site = None
              subsection = None
            warn('Unrecognized line', line, level)

      last_line = line


  if top_level is None:
    warn('Found no top-level section headings.', level=level)

#TODO: make "warn" object to store level, total warnings, and even current line
def warn(message, line=None, level='warn'):
  assert level in ['silent', 'stdout', 'warn', 'die']
  if line is None:
    warning = message+'\n'
  else:
    warning = message+':\n'+line+'\n'
  if level == 'stdout':
    sys.stdout.write(warning)
  if level == 'silent':
    return
  if level == 'warn':
    sys.stderr.write('Warning: '+warning)
  elif level == 'die':
    sys.stderr.write('Error: '+warning)
    sys.exit(1)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  main()
