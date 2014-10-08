#!/usr/bin/env python
from __future__ import division
import re
import os
import sys
import argparse

OPT_DEFAULTS = {}
USAGE = "\n$ %(prog)s 'File (keyword1, key words 2) (source).jpg' [file2 [file3 [..]]]"
DESCRIPTION = """This will rename your files, converting things in the filename
that look like the old, loose way of specifying keywords to the new format.
It will prompt to accept each change."""
EPILOG = """"""

REGEX_DONE = r'(\[keys \S+[^\]]+\])|(\[src \S+[^\]]+\])'
REGEX_PAREN = r'\(([^)]+)\)'
REGEX_SINGLE_PAREN = r'\(([^)]+)\)\.[A-Za-z0-9]{1,5}$'
REGEX_MULTI_PAREN = r'\(([^)]+)\)\s+\(([^)]+)\)\.[A-Za-z0-9]{1,5}$'
REGEX_IMGUR_SRC = r'^[A-Za-z0-9]{5,7}$'
REGEX_DOMAIN_SRC = r'^([A-Za-z0-9-]+\.)+[A-Za-z0-9-]{2,}$'

def main():

  parser = argparse.ArgumentParser(description=DESCRIPTION, usage=USAGE)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('files', metavar='File', nargs='+',
    help='Files to rename.')
  parser.add_argument('-t', '--test', action='store_true',
    help='Don\'t make any changes, just print a list of files and intended '
      'edits (no prompts).')

  args = parser.parse_args()

  matcher = Matcher()
  for filename in args.files:
    print filename
    if matcher.match(REGEX_MULTI_PAREN, filename):
      print "\tmulti:     [keys {}] [src {}]".format(matcher.result.group(1),
                                                     matcher.result.group(2))
    elif matcher.match(REGEX_SINGLE_PAREN, filename):
      parenthetical = matcher.result.group(1)
      if is_src(parenthetical):
        print "\tsingle:    [src {}]".format(parenthetical)
      else:
        print "\tsingle:    [keys {}]".format(parenthetical)
    elif matcher.match(REGEX_DONE, filename):
      print "\tdone!"
    elif matcher.match(REGEX_PAREN, filename):
      print "\tunmatched: ({})".format(matcher.result.group(1))
    else:
      print "\tno parenthetical"
    # check for multiple parentheticals, if so, choose the 2nd to last one
    # otherwise use the only parenthetical
    # but first, check if it looks like a source:
    #   an imgur id?
    #   a domain name?


def is_src(src):
  matcher = Matcher()
  if matcher.match(REGEX_IMGUR_SRC, src):
    return True
  elif matcher.match(REGEX_DOMAIN_SRC, src):
    return True
  return False


class Matcher(object):
  def __init__(self):
    self.result = None

  def match(self, pattern, text):
    self.result = re.search(pattern, text)
    if self.result:
      return self.result
    else:
      self.result = None
      return False


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  main()
