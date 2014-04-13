#!/usr/bin/env python
#TODO: continue after format errors
#TODO: deal with comments at the ends of lines  # like this
#      but somehow allow in things like "account #:" or "PIN#"
#TODO: deal with "[deleted]" and binary flags in general
from __future__ import division
import re
import collections

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
QLN_LINE_REGEX = r'^\s+(QLN)(?:\s+\S.*$|\s*$)'
CC_LINE_REGEX = r'\s*\*.*credit card.*\*\s*'


class FormatError(Exception):
  def __init__(self, message=None):
    if message:
      Exception.__init__(self, message)


class AccountsReader(object):
  def __init__(self, filepath):
    self.errors = []
    self.entries = self._parse_accounts(filepath)

  def _parse_accounts(self, filepath):
    """The parsing engine itself.
    Returns a list of entries."""
    entries = []
    line_num = 0
    last_line = None
    top_level = None
    section = None
    entry = None
    with open(filepath, 'rU') as filehandle:
      for line_raw in filehandle:
        line_num+=1
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
            last_line = line
            continue

        # At a 2nd-level section heading?
        # (Previous line must contain at least 20 "-"s in a row.)
        if last_line is not None and '-' * 20 in last_line:
          section_match = re.search(SECTION_REGEX, line)
          if section_match:
            section = section_match.group(1).lower()
            last_line = line
            continue

        # Parse 'online' top-level section (the one with the account info)
        if top_level == 'online' and section is None:

          # Are we at the start of an entry?
          site_match = re.search(SITE_REGEX, line)
          if site_match:
            # Store previous entry and initialize a new one
            if entry is not None:
              entries.append(entry)
            entry = AccountsEntry()
            # Determine and set the site name, alias, and url
            entry.site = site_match.group(1)
            site_url_match = re.search(SITE_URL_REGEX, line)
            if site_url_match:
              entry.site = site_url_match.group(1)
              entry.site_alias = None
              site_alias_match = re.search(SITE_ALIAS_REGEX, line)
              if site_alias_match:
                entry.site_alias = site_alias_match.group(1)
                site_old = entry.site
                entry.site = site_old.replace(' ('+entry.site_alias+')', '')
                if entry.site == site_old:
                  message = ('Failed to remove alias "'+entry.site_alias+
                    '" from site name "'+entry.site+'".')
                  self.errors.append(
                    {'message':message, 'line':line_num, 'data':line}
                  )
            account = 0
            subsection = 'default'
            last_line = line
            continue

          # If we don't know what entry we're in, skip the rest and get back to
          # looking for an entry header.
          if entry is None:
            last_line = line
            continue

          # What kind of data line are we on?
          account_num_match = re.search(ACCOUNT_NUM_REGEX, line)
          subsection_match1 = re.search(SUBSECTION_REGEX1, line)
          subsection_match2 = re.search(SUBSECTION_REGEX2, line)
          keyval_match = re.search(KEYVAL_REGEX, line)
          if account_num_match:
            account = int(account_num_match.group(1))
            subsection = 'default'
          elif subsection_match1 or subsection_match2:
            # start of subsection
            if subsection_match1:
              subsection = subsection_match1.group(1)
            else:
              subsection = subsection_match2.group(1)
          elif keyval_match:
            # a key/value data line
            keyval_new_match = re.search(KEYVAL_NEW_REGEX, line)
            if keyval_new_match:
              key = keyval_new_match.group(1)
              value = keyval_new_match.group(2)
            else:
              key = keyval_match.group(1)
              value = keyval_match.group(2)
            if ';' in value:
              # multiple values?
              value = [elem.strip() for elem in value.split(';')]
            entry.add_keyval(key, value, account, subsection)
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
              entry.site_alias = site_last_match.group(1)
              entry.site = url_line_match.group(1)
            elif qln_match:
              # "QLN"-type shorthand
              self._add_qln(entry, account, subsection)
            elif cc_line_match:
              # "stored credit card" note
              entry.add_keyval('stored credit card', True, account, subsection)
            elif re.search(r'^\S', line):
              # If it's not indented, take the safe route and assume it could be
              # an unrecognized entry header. That means we no longer know which
              # entry we're in.
              entry = None
              message = 'Line is like an entry header, but malformed.'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )
            else:
              # Unrecognized.
              message = 'Unrecognized line.'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )

        last_line = line

    if top_level is None:
      message = 'Found no top-level section headings.'
      self.errors.append(
        {'message':message, 'line':None, 'data':None}
      )

    return entries

  def _add_qln(self, entry, account, subsection):
    entry.add_keyval('username', 'qwerty0', account, subsection)
    entry.add_keyval('password', 'least secure', account, subsection)
    entry.add_keyval('email', 'nmapsy', account, subsection)


#TODO: Make this inherit from OrderedDict itself
class AccountsEntry(object):
  def __init__(self):
    self._keyvals = collections.OrderedDict()
    self.site = None
    self.site_alias = None
    self.site_url = None

  def add_keyval(self, key, value, account=0, subsection='default'):
    self._keyvals[(key, account, subsection)] = value

  def get_val(self, key, account=0, subsection='default'):
    return self._keyvals[(key, account, subsection)]