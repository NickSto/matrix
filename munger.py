#!/usr/bin/env python
import sys
NON_NUMBERS = (float('inf'), float('nan'))

def get_field(line, field=None, tab=False, cast=False, errors='silent'):
  """Return field given in "field", or the entire line if no field is given.
  If "field" is out of range for the line, return None, and take the action
  indicated by "errors". If it is "throw", an IndexError will be thrown. If it
  is "warn", it will print a warning to stderr. If it is "silent", do nothing.
  """
  assert errors in ('silent', 'warn', 'throw'), '"errors" parameter invalid.'
  if cast: raise NotImplementedError #TODO
  if field is None:
    return line
  # split into fields
  if tab:
    fields = line.strip('\r\n').split('\t')
  else:
    fields = line.strip('\r\n').split()
  # try to pull out requested field
  value = deindex_or_error(fields, field-1, errors, line=line)
  # try to cast value, if requested
  if cast:
    value = cast_or_error(value, errors, line=line)
  return value


def get_fields(line, fields=None, tab=False, cast=False, errors='silent'):
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
  # try to pull out requested field
  output = [None] * len(fields)
  for (i, field) in enumerate(fields):
    output[i] = deindex_or_error(line_fields, field-1, errors, line=line)
    # try to cast value, if requested
    if cast:
      output[i] = cast_or_error(output[i], errors, line=line)
  return output


def deindex_or_error(values, index, errors, line=None):
  """Pull a value from a list of fields, handling errors as requested."""
  try:
    return values[index]
  except IndexError:
    if errors == 'silent':
      return None
    message = 'Not enough fields. Requested {}, line had {}.'.format(
      index+1, len(values)
    )
    if line:
      message += ' Line:\n'+line
    if errors == 'throw':
      raise IndexError(message)
    elif errors == 'warn':
      sys.stderr.write('Warning: '+message)


def cast_or_error(value, errors, line=None):
  """Parse a str into a number, handling errors as requested."""
  try:
    return to_num(value)
  except ValueError:
    if errors == 'silent':
      return None
    message = 'Non-number "'+value+'" encountered'
    if line:
      message += ' on line:\n'+line
    else:
      message += '.'
    if errors == 'throw':
      raise ValueError(message)
    elif errors == 'warn':
      sys.stderr.write('Warning: '+message)


def to_num(num_str):
  """Parse a string into an int, if possible, or a float, failing that.
  If it cannot be parsed as a float, a ValueError will be thrown.
  The float values "inf" and "nan" are not counted as valid, and will
  raise a ValueError."""
  try:
    return int(num_str)
  except ValueError:
    num = float(num_str)
    if num in NON_NUMBERS:
      raise ValueError('"inf" and "nan" are not counted as valid numbers')
    else:
      return num
