#!/usr/bin/env python
"""A wrapper (lol) for textwrap, to simplify its usage."""
import textwrap

DEFAULT_WIDTH = 70

def wrap(text, width=None, indent=0, lspace=0, **kwargs):
  """Take any input text and return output where no line is longer than "width".
  It preserves existing newlines, unlike textwrap. So it will simply look at
  each line, and if it's longer than "width" it will break it there. This
  means that any pre-wrapped text will look terrible if wrapped to a smaller
  with, so remember not to pre-wrap!
  width
    The maximum line length. If "width" is not given, it will try to determine
  the current terminal width using termwidth(). If it cannot determine it, it
  will default to DEFAULT_WIDTH. But termwidth() requires Python 2.7 and it
  executes the external "stty" command each time, so if you're using this
  multiple times it's best to supply a width.
  lspace
    Number of spaces to prepend to each line. Counts toward the line width.
  indent
    Number of spaces to prepend to the first line (in addition to any lspace).
  Also counts toward line with.
  All other keyword arguments will be passed to textwrap.wrap(). N.B.: if
  "subsequent_indent" or "initial_indent" are given, then "lspace" and
  "indent" will be ignored."""
  if width is None:
    width = termwidth(DEFAULT_WIDTH)
  if not (kwargs.get('subsequent_indent') or kwargs.get('initial_indent')):
    kwargs['subsequent_indent'] = ' ' * lspace
    kwargs['initial_indent'] = (' ' * indent) + kwargs['subsequent_indent']
  # put it through textwrap
  wrapped = []
  wrapper = textwrap.TextWrapper(width, **kwargs)
  for line in text.split('\n'):
    wrapped.extend(wrapper.wrap(line))
  wrapped_str = '\n'.join(wrapped)
  return wrapped_str


def termwidth(default=None):
  """Get current terminal width, using stty command.
  If stty isn't available, or if it gives an error, return the default (or
  None, if no default was given).
  Note: requires Python 2.7"""
  import os
  import subprocess
  import distutils.spawn
  if not distutils.spawn.find_executable('stty'):
    return default
  devnull = open(os.devnull, 'wb')
  try:
    output = subprocess.check_output(['stty', 'size'], stderr=devnull)
  except OSError:
    devnull.close()
    return default
  devnull.close()
  return int(output.split()[1])


def wrapper(width=None, indent=0, lspace=0, **kwargs):
  """Return a function that performs wrapping with the same settings each time.
  Allows defining a shorthand for the full wrap function:
  wrap_short = simplewrapper.wrapper(width=70, indent=4)
  print wrap_short('Now you can just give this argument the text, and it will '
    +'wrap it to 70 characters with an indent of 4 each time.')"""
  return lambda text: wrap(text, width, indent, lspace, **kwargs)
