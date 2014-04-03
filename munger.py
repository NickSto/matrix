#!/usr/bin/env python
import sys


def get_field_value(line, field=None, tab=False, errors='silent'):
  """Return field given in "field", or the entire line if no field is given.
  If "field" is out of range for the line, return None, and take the action
  indicated by "errors". If it is "throw", an IndexError will be thrown. If it
  is "verbose", it will print a warning to stderr. If it's "silent", do nothing.
  """
  assert errors in ('silent', 'verbose', 'throw'), '"errors" parameter invalid.'
  if field is None:
    return line
  # split into fields
  if tab:
    fields = line.strip('\r\n').split('\t')
  else:
    fields = line.strip('\r\n').split()
  # return requested field
  try:
    return fields[field-1]
  except IndexError:
    if errors == 'throw':
      raise IndexError('Not enough fields. Requested {}, line had {}.'.format(
        field-1, len(fields)))
    elif errors == 'verbose':
      sys.stderr.write('Warning: not enough fields for line:\n'+line)
    return None