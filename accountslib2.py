#!/usr/bin/env python2
from __future__ import division
import re
import collections

FLAG_REGEX = r'\s\*\*([^*]+)\*\*'
VALUE_REGEX = r'^\s*(\S.*?)\s+\*\*[^*]+\*\*'

class FormatError(Exception):
  def __init__(self, message=None):
    if message:
      Exception.__init__(self, message)

def parse(lines):
  """A generator to parse the accounts file, line by line.
  Provide a file-like object, a list of lines, or anything else that can be
  iterated through to produce lines."""
  # Parse the file, line by line, using a state machine.
  state = 'start'
  section = None
  subsection = None
  entry = None
  line_num = 0
  for line_raw in lines:
    line_num += 1
    # All trailing whitespace is ignored.
    line = line_raw.rstrip()
    # Ignore # comments.
    if line.lstrip().startswith('#'):
      continue
    # Make sure we're in the right section.
    if line.startswith('=====') and line.count('=') >= 70:
      if state == 'section_label':
        state = 'section_end'
      else:
        state = 'section_start'
    elif state == 'section_start':
      if line.startswith('>>'):
        state = 'section_label'
        section = line.lstrip('>').lower()
      else:
        raise FormatError('Expected ">>" section label after "=====" line, at line {}:\n{}'
                          .format(line_num, line_raw))
    elif section == 'online':
      # Make sure we're in the right subsection.
      if line.startswith('-----') and line.count('-') >= 70:
        if state == 'subsection_label':
          state = 'subsection_end'
        else:
          state = 'subsection_start'
      elif state == 'subsection_start':
        if line.startswith('>'):
          state = 'subsection_label'
          subsection = line.lstrip('>').lower()
        else:
          raise FormatError('Expected ">" subsection label after "-----" line, at line {}:\n{}'
                            .format(line_num, line_raw))
      elif subsection == 'accounts':
        # Parse the actual accounts info.
        if line.endswith(':') and not (line.startswith('\t') or line.startswith(' ')):
          # We're at the start of a new entry.
          state = 'entry_heading'
          # Return the last account and start a new one.
          if entry is not None:
            yield entry
          entry_name = line.rstrip(':')
          entry = Entry(entry_name)
        elif line.startswith('\t') or line.startswith(' '):
          # We're inside an entry, on an indented line.
          # Strip the indentation.
          line = line.lstrip('\t ')
          if line.startswith('{account') and line.endswith('}'):
            # We're at a new account label.
            account_str = line[8:-1]
            try:
              account_num = int(account_str.strip())
            except ValueError:
              account_num = account_str.strip()
            entry.account = account_num
            entry.section = Entry.default_section
          elif line.startswith('[') and line.endswith(']'):
            # We're at a new section label.
            section_str = line[1:-1]
            entry.section = section_str
          elif line.startswith('**') and line.endswith('**'):
            # We're at a entry-level **flag**
            flag = line[2:-2]
            entry.flags.add(flag)
          else:
            # We're at a key/value line (or a [section] key/value one-liner).
            fields = line.split('\t')
            if len(fields) < 2:
              raise FormatError('Expected key/value delimited by tabs at line {}:\n{}'
                                .format(line_num, line_raw))
            elif len(fields) >= 3 and fields[0].startswith('[') and fields[0].endswith(']'):
              # It's a one-liner [section] key: value.
              section_str = fields[0][1:-1]
              if fields[1].endswith(':'):
                key = fields[1][:-1]
              else:
                raise FormatError('Malformed key/value at line {}:\n{}'.format(line_num, line_raw))
              values_str = fields[-1]
              values = _parse_values(values_str)
              if section_str == 'meta':
                entry.add_meta_values(key, values)
              else:
                entry.add_section_values(section_str, key, values)
            else:
              # It's a normal key: value line.
              key_str = fields[0]
              values_str = fields[-1]
              if key_str.endswith(':'):
                key = key_str.rstrip(':')
              else:
                raise FormatError('Malformed key/value at line {}:\n{}'.format(line_num, line_raw))
              values = _parse_values(values_str)
              if entry.section == 'meta':
                entry.add_meta_values(key, values)
              else:
                entry.add_values(key, values)
        elif line.strip():
          raise FormatError('Expected entry header, account or section label, or key/value at line '
                            '{}:\n{}'.format(line_num, line_raw))
  yield entry


def _parse_values(values_str):
  values_strs = values_str.split(';')
  values = []
  for value_str in values_strs:
    # The one use of regex :(
    flags = re.findall(FLAG_REGEX, value_str)
    if flags:
      match = re.search(VALUE_REGEX, value_str)
      if match:
        value = Value(match.group(1))
      else:
        raise FormatError('Malformed key/value line. Failed on values "{}"'.format(values_str))
    else:
      value = Value(value_str.strip())
    for flag in flags:
      value.flags.add(flag)
    values.append(value)
  return values


class Entry(object):
  def __init__(self, name, account=0, section='default'):
    self.name = name
    self.account = account
    self.section = section
    self.accounts = collections.OrderedDict()
    self.accounts[self.account] = Account(self.account, section=self.section)
    self.urls = []
    self.keys = []
    self.app = []
  @property
  def url(self):
    if len(self.urls) > 0:
      return self.urls[0]
  @property
  def flags(self):
    return self._get_section(self.account, self.section).flags
  @flags.setter
  def flags(self, flags):
    self._get_section(self.account, self.section).flags = flags
  def _set_values(self, account_num, section_name, key, values):
    """The basic set value implementation used by all other methods of setting values."""
    try:
      account = self.accounts[account_num]
    except KeyError:
      account = Account(account_num, section=section_name)
      self.accounts[account_num] = account
    try:
      section = account.sections[section_name]
    except KeyError:
      section = Section(section_name)
      account.sections[section_name] = section
    section[key] = values
  def _get_section(self, account_num, section_name):
    account = self.accounts[account_num]
    return account.sections[section_name]
  def __getitem__(self, key):
    account = self.accounts[self.account]
    section = account.sections[self.section]
    return section.get(key)
  def __setitem__(self, key, value):
    """The entry[key] = value notation.
    key and value are strings. This will auto-create a list of Values from the value string."""
    self._set_values(self.account, self.section, key, [Value(value)])
  def add_values(self, key, values):
    """Set the values for a key, using a manually created list of Values."""
    if len(values) > 0 and not isinstance(values[0], Value):
      raise ValueError('values must be a list of Value objects.')
    self._set_values(self.account, self.section, key, values)
  def add_section_value(self, section, key, value):
    """Set a value for a key, but for the given section, not the current one.
    value should be a string. A list of Values will be auto-created from it.
    Does not affect the current section of the Entry object."""
    self._set_values(self.account, section, key, [Value(value)])
  def add_section_values(self, section, key, values):
    """Set a value for a key, but for the given section, not the current one.
    Does not affect the current section of the Entry object."""
    self._set_values(self.account, section, key, values)
  def add_meta_values(self, key, values):
    if key == 'urls':
      self.urls = [value.value for value in values]
    elif key == 'keys':
      self.keys = [value.value for value in values]
    elif key == 'app':
      self.app = [value.value for value in values]
    self._set_values(None, 'meta', key, values)

class Account(object):
  def __init__(self, number, section='default'):
    self.number = number
    self.section = section
    self.sections = collections.OrderedDict()
    self.sections[self.section] = Section(self.section)
  def __str__(self):
    return 'Account {} (sections {})'.format(self.number, ', '.join(self.sections.keys()))

class Section(collections.OrderedDict):
  def __init__(self, name):
    self.name = name
    self.flags = set()
    super(Section, self).__init__()
  def __str__(self):
    return 'Section "'+self.name+'"'

class Value(object):
  def __init__(self, value):
    self.value = value
    self.flags = set()
  def __str__(self):
    return self.value
  def __repr__(self):
    return "{}.{}('{}')".format(type(self).__module__, type(self).__name__, self.value)
