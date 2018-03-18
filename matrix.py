#!/usr/bin/env python3
import sys
import time
import curses
import random

DROP_LEN = 20


def main(argv):
  dna = False
  if len(sys.argv) > 1:
    if sys.argv[1] == '-d':
      dna = True
  with curses_screen() as stdscr:
    (height, width) = stdscr.getmaxyx()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    columns = []
    while True:
      try:
        if random.random() < 0.75:
          columns.append({'x':random.randrange(width), 'y':0})
        done = []
        for (i, column) in enumerate(columns):
          if column['y'] >= height + DROP_LEN:
            done.append(i)
            continue
          if dna:
            char = random.choice(('A', 'C', 'G', 'T'))
          else:
            char = chr(random.randrange(33, 127))
          try:
            # Draw the character.
            if column['y'] < height:
              draw_char(stdscr, height, width, column['y'], column['x'], char)
            # Delete the character DROP_LEN before this one.
            if column['y'] - DROP_LEN >= 0:
              draw_char(stdscr, height, width, column['y'] - DROP_LEN, column['x'], ' ')
            stdscr.refresh()
          except curses.error:
            scr = curses_screen()
            scr.stdscr = stdscr
            scr.__exit__(1, 2, 3)
            sys.stderr.write('curses error on {{add,ins}}chr({}, {}, "{}")\n'
                             .format(column['y'], column['x'], char))
            raise
          column['y'] += 1
          time.sleep(0.01)
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


if __name__ == '__main__':
  sys.exit(main(sys.argv))
