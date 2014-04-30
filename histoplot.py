#!/usr/bin/env python
from __future__ import division
import os
import sys
import argparse
from matplotlib import pyplot
import matplotliblib
import munger

OPT_DEFAULTS = {'field':1, 'bins':10}
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
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain one number.')
  parser.add_argument('-f', '--field', type=int,
    help='Read this column from the input. Give a 1-based index. Columns are '
      'whitespace-delimited unless --tab is given. Default column: %(default)s.')
  parser.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')
  parser.add_argument('-o', '--out-file', metavar='OUTPUT_FILE',
    help='Save the plot to this file instead of displaying it. The image '
      'format will be inferred from the file extension.')
  parser.add_argument('-b', '--bins', type=int,
    help='Number of histogram bins. Default: %(default)s.')
  parser.add_argument('-B', '--bin-edges', nargs='+', type=float,
    help='Specify the exact edges of each bin. Give the value of each bin edge '
      'as a separate argument. Overrides --bins.')
  parser.add_argument('-r', '--range', type=float, nargs=2, metavar='BOUND',
    help='Range of the X axis and bins. Give the lower bound, then the upper.')
  parser.add_argument('-R', '--bin-range', type=float, nargs=2, metavar='BOUND',
    help='Range of the bins only. This will be used when calculating the size '
      'of the bins (unless -B is given), but it won\'t affect the scaling of '
      'the X axis. Give the lower bound, then the upper.')
  parser.add_argument('-S', '--x-range', type=float, nargs=2, metavar='BOUND',
    help='Range of the X axis only. This will change the scale of the X axis, '
      'but not the size of the bins. Give the lower bound, then the upper.')

  matplotliblib.add_arguments(parser)
  args = parser.parse_args()

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  # read data into list, parse types into ints or skipping if not possible
  data = []
  line_num = 0
  for line in input_stream:
    line_num+=1
    try:
      value = munger.get_field(line, field=args.field, tab=args.tab,
        errors='throw')
    except IndexError as ie:
      sys.stderr.write("Warning: "+str(ie)+'\n')
      continue
    try:
      num = int(value)
    except ValueError:
      try:
        num = float(value)
      except ValueError:
        sys.stderr.write('Warning: Non-number encountered on line %d: %s\n' %
          (line_num, line.rstrip('\r\n')))
        continue
    data.append(num)

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
  (dpi, figsize) = matplotliblib.scale(args)
  print dpi, figsize

  # make the actual plot
  pyplot.figure(dpi=dpi, figsize=figsize)
  pyplot.hist(data, bins=bins, range=bin_range, color=args.color)
  pyplot.xlabel(args.x_label)
  pyplot.ylabel(args.y_label)
  if x_range:
    pyplot.xlim(*x_range)
  if args.title:
    pyplot.title(args.title)
  if args.out_file:
    pyplot.savefig(args.out_file)
  else:
    pyplot.show()


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == "__main__":
  main()
