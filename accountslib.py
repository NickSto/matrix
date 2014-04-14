#!/usr/bin/env python
#TODO: Allow attributes to be set on individual values.
#TODO: deal with comments at the ends of lines  # like this
#      but somehow allow in things like "account #:" or "PIN#"
#TODO: Deal with "[deleted] notes"
#      For sites or accounts that are deleted, just add a 'deleted' key = True
from __future__ import division
import re
import collections

TOP_LEVEL_REGEX = r'^>>([^>]+)\s*$'
SUPER_SECTION_REGEX = r'^>([^>]+)\s*$'
SITE_REGEX = r'^(\S(?:.*\S)):\s*$'
SITE_URL_REGEX = r'^((?:.+://)?[^.]+\.[^.]+.+):\s*$'
SITE_ALIAS_REGEX = r' \(([^)]+)\):\s*$'
ACCOUNT_NUM_REGEX = r'^\s+{account ?(\d+)}\s*$' # new account num format
SECTION_REGEX1 = r'^\s+\[([\w#. -]+)\]\s*$'
SECTION_REGEX2 = r'^ {3,5}(\S(?:.*\S)):\s*$'
KEYVAL_REGEX = r'^\s+(\S(?:.*\S)?):\s*(\S.*)$'
KEYVAL_NEW_REGEX = r'^\t(\S(?:.*\S)?):\t+(\S(?:.*\S)?)\s*$'
# Special cases
URL_LINE_REGEX = r'^((?:.+://)?[^.]+\.[^.]+.+)\s*$'
QLN_LINE_REGEX = r'^\s+(QLN)(?:\s+\S.*$|\s*$)'
CC_LINE_REGEX = r'\s*\*.*credit card.*\*\s*'


class AccountsReader(list):
  def __init__(self, filepath):
    super(AccountsReader, self).__init__()
    self.errors = []
    self._parse_accounts(filepath)

  def _parse_accounts(self, filepath):
    """The parsing engine itself."""
    line_num = 0
    last_line = None
    top_level = None
    super_section = None
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
          super_section_match = re.search(SUPER_SECTION_REGEX, line)
          if super_section_match:
            super_section = super_section_match.group(1).lower()
            last_line = line
            continue

        # Parse 'online' top-level section (the one with the account info)
        if top_level == 'online' and super_section is None:

          # Are we at the start of an entry?
          site_match = re.search(SITE_REGEX, line)
          if site_match:
            # Store previous entry and initialize a new one
            if entry is not None:
              self.append(entry)
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
                    '" from site name "'+entry.site+'"')
                  self.errors.append(
                    {'message':message, 'line':line_num, 'data':line}
                  )
            account = 0
            section = 'default'
            last_line = line
            continue

          # If we don't know what entry we're in, skip the rest and get back to
          # looking for an entry header.
          if entry is None:
            last_line = line
            continue

          # What kind of data line are we on?
          account_num_match = re.search(ACCOUNT_NUM_REGEX, line)
          section_match1 = re.search(SECTION_REGEX1, line)
          section_match2 = re.search(SECTION_REGEX2, line)
          keyval_match = re.search(KEYVAL_REGEX, line)
          if account_num_match:
            account = int(account_num_match.group(1))
            section = 'default'
          elif section_match1 or section_match2:
            # start of section
            if section_match1:
              section = section_match1.group(1)
            else:
              section = section_match2.group(1)
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
            if (key, account, section) in entry:
              message = 'Duplicate key, section, or account'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )
            else:
              entry[(key, account, section)] = value
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
              self._add_qln(entry, account, section)
            elif cc_line_match:
              # "stored credit card" note
              entry[('stored credit card', account, section)] = True
            elif re.search(r'^\S', line):
              # If it's not indented, take the safe route and assume it could be
              # an unrecognized entry header. That means we no longer know which
              # entry we're in.
              entry = None
              message = 'Line is like an entry header, but malformed'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )
            else:
              # Unrecognized.
              message = 'Unrecognized line'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )

        last_line = line

    if top_level is None:
      message = 'Found no top-level section headings'
      self.errors.append(
        {'message':message, 'line':None, 'data':None}
      )


  def _add_qln(self, entry, account, section):
    entry[('username', account, section)] = 'qwerty0'
    entry[('password', account, section)] = 'least secure'
    entry[('email', account, section)] = 'nmapsy'


class AccountsEntry(collections.OrderedDict):
  """Keys must be either the field name string or a tuple of the field name, the
  account number, and the section name."""
  def __init__(self):
    super(AccountsEntry, self).__init__()
    self.site = None
    self.site_alias = None
    self.site_url = None
    self.default_account = 0
    self.default_section = 'default'

  def __getitem__(self, key):
    full_key = self.get_full_key(key)
    return collections.OrderedDict.__getitem__(self, key)

  def __setitem__(self, key, value):
    full_key = self.get_full_key(key)
    collections.OrderedDict.__setitem__(self, key, value)

  def __contains__(self, key):
    full_key = self.get_full_key(key)
    return collections.OrderedDict.__contains__(self, key)

  def get_full_key(self, key):
    """Return a proper, full key for indexing the dict.
    If the input is a string, assume the default account and section.
    If it's a proper 3-tuple, return it unaltered.
    If it's neither, throw an assertion error."""
    #TODO: allow other tuple-like types?
    is_str = isinstance(key, basestring)
    is_tuple = isinstance(key, tuple) and len(key) == 3
    assert is_str or is_tuple, '"key" must either be a str or tuple of len 3.'
    if is_str:
      key = (key, self.default_account, self.default_section)
    return key

  def accounts(self):
    """Return a tuple of the account numbers in the entry."""
    accounts = set()
    for (key, account, section) in self.keys():
      accounts.add(account)
    return tuple(accounts)

  def sections(self, this_account):
    """Return a tuple of the sections in the account."""
    sections = set()
    for (key, account, section) in self.keys():
      if account == this_account:
        sections.add(section)
    return tuple(sections)

  #TODO: a method to get data by account and/or section