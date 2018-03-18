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
    source = args.source
  start_the_show(args.drop_len, source, new_reads)


def start_the_show(drop_len, source, new_reads):
  with curses_screen() as stdscr:
    (height, width) = stdscr.getmaxyx()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    columns = []
    idle_bases = []
    while True:
      try:
        # Make a new drop.
        if drop_len:
          drop_len = drop_len
        else:
          drop_len = random.randrange(1, 40)
        if source == 'fastx':
          bases = get_bases(idle_bases, new_reads)
          if bases is None:
            return
        else:
          bases = None
        columns.append({'x':random.randrange(width), 'y':0, 'len':drop_len, 'bases':bases})
        done = []
        for (i, column) in enumerate(columns):
          if column['y'] >= height + column['len']:
            done.append(i)
            idle_bases.append(column['bases'])
            continue
          if source == 'fastx':
            char = get_base(column, idle_bases, new_reads)
            if char is None:
              return
          elif source == 'dna':
            char = random.choice(('A', 'C', 'G', 'T'))
          else:
            char = chr(random.randrange(33, 127))
          try:
            # Draw the character.
            if column['y'] < height:
              draw_char(stdscr, height, width, column['y'], column['x'], char)
            # Delete the character column['len'] before this one.
            if column['y'] - column['len'] >= 0:
              draw_char(stdscr, height, width, column['y'] - column['len'], column['x'], ' ')
            stdscr.refresh()
          except curses.error:
            scr = curses_screen()
            scr.stdscr = stdscr
            scr.__exit__(1, 2, 3)
            sys.stderr.write('curses error on {{add,ins}}chr({}, {}, "{}")\n'
                             .format(column['y'], column['x'], char))
            raise
          column['y'] += 1
          time.sleep(0.002)
        for i in done:
          del(columns[i])
        # time.sleep(0.2)
      except KeyboardInterrupt:
        break


def draw_char(stdscr, height, width, y, x, char):
  if y == height - 1 and x == width - 1:
    # If it's the lower-right corner, addch() throws an error. Use insch() instead.
    stdscr.insch(y, x, char, curses.color_pair(1))
  else:
    stdscr.addch(y, x, char, curses.color_pair(1))


# Create a with context to encapsulate the setup and tear down.
# from http://ironalbatross.net/wiki/index.php?title=Python_Curses
class curses_screen:
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


def get_bases(idle_bases, new_reads):
  if idle_bases:
    return idle_bases.pop()
  else:
    try:
      read = next(new_reads)
    except StopIteration:
      return None
  return char_generator(read.seq)


def get_base(column, idle_bases, new_reads):
  # Get the next base in the read, or start a new read, or end.
  while True:
    bases = column['bases']
    try:
      char = next(bases)
      return char
    except StopIteration:
      bases = get_bases(idle_bases, new_reads)
      if bases is None:
        return None
      else:
        column['bases'] = bases


def char_generator(string):
  for char in string:
    yield char


if __name__ == '__main__':
  sys.exit(main(sys.argv))
