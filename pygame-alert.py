#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import sys
import argparse
try:
  import pygame
except ImportError:
  sys.stderr.write('Error: This requires pygame.\n')
  raise

COLORS = {'red':[255,0,0], 'green':[0,255,0], 'blue':[0,0,255], 'yellow':[255,255,0],
          'purple':[255,0,255], 'teal':[0,255,255]}
ARG_DEFAULTS = {'message':'ALERT', 'size':(640,480), 'color':'red', 'pause':2, 'border':0}
USAGE = "%(prog)s [options]"
DESCRIPTION = """"""


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('-m', '--message',
    help='Default: %(default)s')
  parser.add_argument('-s', '--size', nargs=2, type=int,
    help='Width and height, in pixels, as two arguments: "-s 640 480". Default: %(default)s.')
  parser.add_argument('-c', '--color', choices=COLORS.keys(),
    help='Default: %(default)s')
  parser.add_argument('-p', '--pause', type=float,
    help='In seconds. Default: %(default)s')
  parser.add_argument('-r', '--red', type=int)
  parser.add_argument('-g', '--green', type=int)
  parser.add_argument('-b', '--blue', type=int)
  parser.add_argument('-B', '--border', type=int,
    help='Default: %(default)s')
  parser.add_argument('-t', '--timeout', type=int,
    help='End after this many seconds. If not given, it will not end.')

  args = parser.parse_args(argv[1:])

  rgb = COLORS[args.color]
  if args.red is not None:
    rgb[0] = args.red
  if args.green is not None:
    rgb[1] = args.green
  if args.blue is not None:
    rgb[2] = args.blue
  width, height = args.size

  pygame.init()
  screen = pygame.display.set_mode((width, height))
  pygame.display.set_caption(args.message)

  background = pygame.Surface(screen.get_size())
  background.fill((0, 0, 0))
  window_left = args.border
  window_top = args.border
  window_width = width-(args.border*2)
  window_height = height-(args.border*2)
  window_size = (window_left, window_top, window_width, window_height)

  total_time = 0
  half_pause = int(args.pause * 1000 / 2)
  while True:
    pygame.draw.rect(screen, rgb, window_size)
    pygame.display.flip()
    pygame.time.wait(half_pause)
    if check_for_quit():
      break
    pygame.draw.rect(screen, (0,0,0), window_size)
    pygame.display.flip()
    pygame.time.wait(half_pause)
    if check_for_quit():
      break
    total_time += args.pause
    if args.timeout and total_time >= args.timeout:
      break
  pygame.display.quit()


def check_for_quit():
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      return True
  return False


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
