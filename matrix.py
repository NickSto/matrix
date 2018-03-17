#!/usr/bin/env python
import sys
import time
import curses
import random


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
          if column['y'] == height or (column['x'] == width - 1 and column['y'] == height - 1):
            done.append(i)
            continue
          if dna:
            char = random.choice(('A', 'C', 'G', 'T'))
          else:
            char = chr(random.randrange(33, 127))
          try:
            # addch in the bottom-right corner raises an error.
            if column['y'] == height - 1 and column['y'] == width - 1:
              stdscr.insch(column['y'], column['x'], char, curses.color_pair(1))
            else:
              stdscr.addch(column['y'], column['x'], char, curses.color_pair(1))
            stdscr.refresh()
          except curses.error:
            scr = curses_screen()
            scr.stdscr = stdscr
            scr.__exit__(1, 2, 3)
            sys.stderr.write('curses error on {add,ins}chr({}, {}, "{}")\n'
                             .format(column['y'], column['x'], char))
            raise
          column['y'] += 1
          time.sleep(0.01)
        for i in done:
          del(columns[i])
        # time.sleep(0.2)
      except KeyboardInterrupt:
        break


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
