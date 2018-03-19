#!/usr/bin/env python3
import os
import sys
import time
import curses
import random
import argparse
from bfx import getreads


def make_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('positionals', nargs='*',
    help='Ignored.')
  parser.add_argument('-d', '--dna', dest='source', action='store_const', const='dna', default='ascii',
    help='Use random DNA bases instead of random ASCII.')
  parser.add_argument('-l', '--drop-len', type=int,
    help='Use constant-length drops this many characters long.')
  parser.add_argument('-q', '--fastq')
  parser.add_argument('-a', '--fasta')
  parser.add_argument('-s', '--speed', type=int, default=500,
    help='Drawing speed, in characters per second (globally). Default: %(default)d')
  return parser


def main(argv):
  parser = make_argparser()
  args = parser.parse_args(argv[1:])
  if args.fasta:
    bases_generator = BasesGenerator('fasta', args.fasta)
    source = 'fastx'
  elif args.fastq:
    bases_generator = BasesGenerator('fastq', args.fastq)
    source = 'fastx'
  else:
    bases_generator = None
    source = args.source
  start_the_show(args.speed, args.drop_len, source, bases_generator)


def start_the_show(speed, drop_len, source, bases_generator):
  with CursesScreen() as stdscr:
    height, width = stdscr.getmaxyx()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    drops = []
    while True:
      try:
        # Make a new drop.
        drop = Drop(width, drop_len, source, bases_generator)
        drops.append(drop)
        done = []
        for i, drop in enumerate(drops):
          if drop.y >= height + drop.length:
            done.append(i)
            drop.end()
            continue
          char = drop.get_char()
          try:
            # Draw the character.
            if drop.y < height:
              draw_char(stdscr, height, width, drop.y, drop.x, char)
            # Delete the character drop.length before this one.
            if drop.y - drop.length >= 0:
              draw_char(stdscr, height, width, drop.y - drop.length, drop.x, ' ')
            stdscr.refresh()
          except curses.error:
            scr = CursesScreen()
            scr.stdscr = stdscr
            scr.__exit__(1, 2, 3)
            sys.stderr.write('curses error on {{add,ins}}chr({}, {}, "{}")\n'
                             .format(drop.y, drop.x, char))
            raise
          drop.y += 1
          time.sleep(1/speed)
        for i in done:
          del(drops[i])
      except (KeyboardInterrupt, StopIteration):
        break


def draw_char(stdscr, height, width, y, x, char):
  if y == height - 1 and x == width - 1:
    # If it's the lower-right corner, addch() throws an error. Use insch() instead.
    stdscr.insch(y, x, char, curses.color_pair(1))
  else:
    stdscr.addch(y, x, char, curses.color_pair(1))


# Create a with context to encapsulate the setup and tear down.
# from http://ironalbatross.net/wiki/index.php?title=Python_Curses
class CursesScreen(object):
    def __enter__(self):
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.cbreak()
        curses.noecho()
        curses.curs_set(0)
        self.stdscr.keypad(1)
        return self.stdscr
    def __exit__(self, a, b, c):
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.curs_set(1)
        curses.endwin()


class Drop(object):
  def __init__(self, width, length, source, bases_generator=None):
    self.x = random.randrange(width)
    self.y = 0
    self.source = source
    if length:
      self.length = length
    else:
      self.length = random.randrange(1, 40)
    self.bases_generator = bases_generator
    # If the source is outside sequence, get a base generator for one read.
    if source == 'fastx':
      self.bases = self.bases_generator.get_bases()
    else:
      self.bases = None
    self.alive = True

  def end(self):
    self.alive = False
    if self.bases_generator:
      self.bases_generator.idle_bases.append(self.bases)

  def get_char(self):
    # Get the next base in the read, or start a new read, or end.
    # Raises a StopIteration when there are no more reads.
    assert self.alive, 'Error: get_char() called on dead Drop.'
    if self.source == 'ascii':
      return chr(random.randrange(33, 127))
    elif self.source == 'dna':
      return random.choice(('A', 'C', 'G', 'T'))
    elif self.source == 'fastx':
      while True:
        try:
          return next(self.bases)
        except StopIteration:
          # If that read ran out of bases, get a new one and try again.
          self.bases = self.bases_generator.get_bases()


def char_generator(string):
  for char in string:
    yield char


class BasesGenerator(object):
  def __init__(self, source_format, source_path):
    self.format = source_format
    self.path = source_path
    self.idle_bases = []
    self.done_files = set()
    self.latest_timestamp = None
    if self.format == 'fastq':
      self.exts = ('.fq', '.fastq')
    elif self.format == 'fasta':
      self.exts = ('.fa', '.fasta')
    if os.path.isfile(self.path):
      self.dir = False
      self.file = True
      current_file_path = self.path
    elif os.path.isdir(self.path):
      self.dir = True
      self.file = False
      current_file_path = self.get_file()
    else:
      raise ValueError('Input path must be a file or a directory. Received "{}"'.format(self.path))
    self.new_reads = self.start_new_file(current_file_path)
    self.preempted_files = []

  def start_new_file(self, new_file):
    self.current_file = open(new_file)
    return getreads.getparser(self.current_file, self.format).parser()

  def get_file(self):
    """Get a new file.
    If we're reading from a directory, return the most recently modified file this hasn't returned
    before."""
    if self.file:
      # We only had the one.
      raise StopIteration
    files = get_chronological_files(self.path, self.exts)
    for file in files:
      if file['path'] not in self.done_files:
        if self.latest_timestamp is None:
          self.latest_timestamp = file['mtime']
        else:
          self.latest_timestamp = max(file['mtime'], self.latest_timestamp)
        self.done_files.add(file['path'])
        return file['path']
    raise StopIteration

  def get_new_file(self):
    files = get_chronological_files(self.path, self.exts)
    for file in files:
      if self.latest_timestamp is None or file['mtime'] > self.latest_timestamp:
        self.latest_timestamp = file['mtime']
        self.done_files.add(file['path'])
        return file['path']
    return None

  def get_bases(self):
    """Get a base generator that yields the bases from one read.
    Algorithm for where it sources its reads:
    If we're reading from a directory and there's a new file in it, open it and start getting reads
    from it.
    Otherwise, if there are unused reads in self.idle_bases, return one of those.
    Otherwise, get a new read from the current file.
    If there are no more in this file, and we're reading from a directory, get one from a new file.
    If there are no more files, raise a StopIteration."""
    if self.dir:
      new_file = self.get_new_file()
      if new_file:
        self.preempted_files.append(self.new_reads)
        self.new_reads = self.start_new_file(new_file)
        read = next(self.new_reads)
        return char_generator(read.seq)
    if self.idle_bases:
      return self.idle_bases.pop()
    else:
      try:
        read = next(self.new_reads)
      except StopIteration:
        if self.preempted_files:
          self.new_reads = self.preempted_files.pop()
        else:
          self.current_file.close()
          new_file = self.get_file()
          self.new_reads = self.start_new_file(new_file)
        read = next(self.new_reads)
      return char_generator(read.seq)


def get_chronological_files(dirpath, exts=None):
  """Get a list of the files in a directory, sorted by modification time.
  Excludes empty files and those that don't end in the given extensions (case-insensitve, including
  the dot)."""
  files = []
  for filename in os.listdir(dirpath):
    if exts is not None:
      ext = os.path.splitext(filename)[1].lower()
      if ext not in exts:
        continue
    filepath = os.path.join(dirpath, filename)
    if not os.path.isfile(filepath):
      continue
    if not os.path.getsize(filepath):
      continue
    mtime = os.path.getmtime(filepath)
    files.append({'path':filepath, 'mtime':mtime})
  files.sort(reverse=True, key=lambda f: f['mtime'])
  return files


if __name__ == '__main__':
  sys.exit(main(sys.argv))
