#!/usr/bin/env python
import sys


def get_field(line, field=None, tab=False, errors='silent'):
  """Return field given in "field", or the entire line if no field is given.
  If "field" is out of range for the line, return None, and take the action
  indicated by "errors". If it is "throw", an IndexError will be thrown. If it
  is "warn", it will print a warning to stderr. If it is "silent", do nothing.
  """
  assert errors in ('silent', 'warn', 'throw'), '"errors" parameter invalid.'
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
        field, len(fields)))
    elif errors == 'warn':
      sys.stderr.write('Warning: not enough fields for line:\n'+line)
    return None


def get_fields(line, fields=None, tab=False, errors='silent'):
  """Return fields given in "fields", or the entire line if no fields are given.
  If "fields" is out of range for the line, return None, and take the action
  indicated by "errors". If it is "throw", an IndexError will be thrown. If it
  is "warn", it will print a warning to stderr. If it is "silent", do nothing.
  """
  assert errors in ('silent', 'warn', 'throw'), '"errors" parameter invalid.'
  if fields is None:
    return line
  # split into fields
  if tab:
    line_fields = line.strip('\r\n').split('\t')
  else:
    line_fields = line.strip('\r\n').split()
  # get requested fields
  output = [None] * len(fields)
  for (i, field) in enumerate(fields):
    try:
      output[i] = line_fields[field-1]
    except IndexError:
      if errors == 'throw':
        raise IndexError('Not enough fields. Requested {}, line had {}.'.format(
          field, len(line_fields)))
      elif errors == 'warn':
        sys.stderr.write('Warning: not enough fields for line:\n'+line)
      return output
  return output
