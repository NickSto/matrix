#!/usr/bin/env python3
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
  parser.add_argument('-q', '--fastq', type=argparse.FileType('r'))
  parser.add_argument('-a', '--fasta', type=argparse.FileType('r'))
  return parser


def main(argv):
  parser = make_argparser()
  args = parser.parse_args(argv[1:])
  if args.fasta:
    new_reads = getreads.getparser(args.fasta, 'fasta').parser()
    source = 'fastx'
  elif args.fastq:
    new_reads = getreads.getparser(args.fastq, 'fastq').parser()
    source = 'fastx'
  else:
    new_reads = None
    source = args.source
  start_the_show(args.drop_len, source, new_reads)


def start_the_show(drop_len, source, new_reads):
  with CursesScreen() as stdscr:
    height, width = stdscr.getmaxyx()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    drops = []
    idle_bases = []
    while True:
      try:
        # Make a new drop.
        drop = Drop(width, drop_len, source, idle_bases, new_reads)
        drops.append(drop)
        done = []
        for i, drop in enumerate(drops):
          if drop.y >= height + drop.length:
            done.append(i)
            idle_bases.append(drop.bases)
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
          time.sleep(0.002)
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
  def __init__(self, width, length=None, source=None, idle_bases=None, new_reads=None):
    self.x = random.randrange(width)
    self.y = 0
    self.source = source
    if length:
      self.length = length
    else:
      self.length = random.randrange(1, 40)
    # Global state
    self.idle_bases = idle_bases
    self.new_reads = new_reads
    # If the source is outside sequence, get a base generator for one read.
    if source == 'fastx':
      self.bases = self.get_bases()
    else:
      self.bases = None


  def get_bases(self):
    # Raises a StopIteration when there are no more reads.
    if self.idle_bases:
      return self.idle_bases.pop()
    else:
      read = next(self.new_reads)
    return char_generator(read.seq)


  def get_char(self):
    # Get the next base in the read, or start a new read, or end.
    # Raises a StopIteration when there are no more reads.
    if self.source == 'ascii':
      return chr(random.randrange(33, 127))
    elif self.source == 'dna':
      return random.choice(('A', 'C', 'G', 'T'))
    elif self.source == 'fastx':
      while True:
        bases = self.bases
        try:
          char = next(bases)
          return char
        except StopIteration:
          bases = self.get_bases(self.idle_bases, self.new_reads)
          self.bases = bases


def char_generator(string):
  for char in string:
    yield char


if __name__ == '__main__':
  sys.exit(main(sys.argv))
