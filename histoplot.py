#!/usr/bin/env python
import os
import sys
import math
from matplotlib import pyplot
import argparse

OPT_DEFAULTS = {'bins':10, 'x_label':'Value', 'y_label':'Frequency',
  'color':'cornflowerblue'}
USAGE = """cat file.txt | %(prog)s [options]
       %(prog)s [options] file.txt"""
DESCRIPTION = """Display a quick histogram of the input data, using matplotlib.
"""
EPILOG = """Caution: It holds the entire dataset in memory, as a list."""

def main():

  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION,
    epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('file', nargs='?', metavar='file.txt',
    help='Data file. If omitted, data will be read from stdin. '
      'Should be one number per line. If more than one value per line is '
      'encountered, it will split on whitespace and take the first value.')
  parser.add_argument('-f', '--to-file', metavar='OUTPUT_FILE',
    help='Save the plot to this file instead of displaying it. The image '
      'format will be inferred from the file extension.')
  parser.add_argument('-b', '--bins', type=int,
    help='Number of histogram bins. Default: %(default)s')
  parser.add_argument('-B', '--bin-edges', nargs='+', type=float,
    help='Specify the exact edges of each bin. Give the value of each bin edge '
      'as a separate argument. Overrides --bins.')
  parser.add_argument('-D', '--dpi', type=int,
    help='DPI of the image, if saving to a file. If not given, matplotlib\'s '
      'default will be used (seems to be about 100dpi).')
  parser.add_argument('-T', '--title',
    help='Plot title. Default: %(default)s')
  parser.add_argument('-X', '--x-label',
    help='Label for the X axis. Default: %(default)s')
  parser.add_argument('-Y', '--y-label',
    help='Label for the Y axis. Default: %(default)s')
  parser.add_argument('-C', '--color',
    help='Color for the histogram bars. Can use any CSS color. Default: '
      '"%(default)s".')
  parser.add_argument('-r', '--range', type=float, nargs=2, metavar='BOUND',
    help='Range of the X axis and bins. Give the lower bound, then the upper.')
  parser.add_argument('-R', '--bin-range', type=float, nargs=2, metavar='BOUND',
    help='Range of the bins only. This will be used when calculating the size '
      'of the bins (unless -B is given), but it won\'t affect the scaling of '
      'the X axis. Give the lower bound, then the upper.')
  parser.add_argument('-S', '--x-range', type=float, nargs=2, metavar='BOUND',
    help='Range of the X axis only. This will change the scale of the X axis, '
      'but not the size of the bins. Give the lower bound, then the upper.')
  args = parser.parse_args()

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  # read data into list, parse types into ints or skipping if not possible
  data = []
  line_num = 0
  integers = True
  for line in input_stream:
    line_num+=1
    fields = line.split()
    if not fields:
      continue
    try:
      value = int(fields[0])
    except ValueError:
      try:
        value = float(fields[0])
        integers = False
      except ValueError:
        sys.stderr.write('Warning: Non-number encountered on line %d: %s\n' %
          (line_num, line.rstrip('\r\n')))
        continue
    data.append(value)

  if input_stream is not sys.stdin:
    input_stream.close()

  if len(data) == 0:
    sys.exit(0)

  # Compute plot settings from arguments
  if args.bin_edges:
    bins = args.bin_edges
  else:
    bins = args.bins
  if args.range:
    bin_range = args.range
    x_range = args.range
  else:
    bin_range = args.bin_range
    x_range = args.x_range

  pyplot.hist(data, bins=bins, range=bin_range, color=args.color)
  pyplot.xlabel(args.x_label)
  pyplot.ylabel(args.y_label)
  if x_range:
    pyplot.xlim(*x_range)
  if args.title:
    pyplot.title(args.title)
  if args.to_file:
    pyplot.savefig(args.to_file, dpi=args.dpi)
  else:
    pyplot.show()


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == "__main__":
  main()
