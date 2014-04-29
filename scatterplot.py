#!/usr/bin/env python
import os
import sys
import argparse
from matplotlib import pyplot
import munger

OPT_DEFAULTS = {'xfield':1, 'yfield':2, 'xlabel':'X Value',
  'ylabel':'Y Value', 'color':'cornflowerblue'}
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
      'should contain two numbers.')
  parser.add_argument('-x', '--xfield', type=int,
    help='Use numbers from this input column as the x values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  parser.add_argument('-y', '--yfield', type=int,
    help='Use numbers from this input column as the x values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  parser.add_argument('-f', '--field', type=int,
    help='1-dimensional data. Use this column as x values and set y as a '
      'constant (1).')
  parser.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')
  parser.add_argument('-o', '--out-file', metavar='OUTPUT_FILE',
    help='Save the plot to this file instead of displaying it. The image '
      'format will be inferred from the file extension.')
  parser.add_argument('-D', '--dpi', type=int,
    help='DPI of the image, if saving to a file. If not given, matplotlib\'s '
      'default will be used (seems to be about 100dpi).')
  parser.add_argument('-T', '--title',
    help='Plot title. Default: %(default)s')
  parser.add_argument('-X', '--xlabel',
    help='Label for the X axis. Default: %(default)s')
  parser.add_argument('-Y', '--ylabel',
    help='Label for the Y axis. Default: %(default)s')
  parser.add_argument('-C', '--color',
    help='Color for the data points. Can use any CSS color. Default: '
      '"%(default)s".')
  parser.add_argument('-r', '--xrange', type=float, nargs=2, metavar='BOUND',
    help='Range of the X axis and bins. Give the lower bound, then the upper.')
  parser.add_argument('-R', '--yrange', type=float, nargs=2, metavar='BOUND',
    help='Range of the Y axis and bins. Give the lower bound, then the upper.')
  args = parser.parse_args()

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  # read data into list, parse types into ints or skipping if not possible
  x = []
  y = []
  line_num = 0
  integers = True
  for line in input_stream:
    line_num+=1
    if args.field:
      xstr = munger.get_field(line, field=args.field, tab=args.tab,
        errors='warn')
      ystr = '1'
    else:
      (xstr, ystr) = munger.get_fields(line, fields=(args.xfield, args.yfield),
        tab=args.tab, errors='warn')
    if xstr is None or ystr is None:
      continue
    try:
      xval = to_num(xstr)
    except ValueError:
      sys.stderr.write('Warning: Non-number encountered on line %d: %s\n' %
        (line_num, line.rstrip('\r\n')))
      continue
    try:
      yval = to_num(ystr)
    except ValueError:
      sys.stderr.write('Warning: Non-number encountered on line %d: %s\n' %
        (line_num, line.rstrip('\r\n')))
      continue
    x.append(xval)
    y.append(yval)

  if input_stream is not sys.stdin:
    input_stream.close()

  assert len(x) == len(y), 'Length of x and y lists is different.'

  if len(x) == 0 or len(y) == 0:
    sys.exit(0)

  pyplot.scatter(x, y, c=args.color)
  pyplot.xlabel(args.xlabel)
  pyplot.ylabel(args.ylabel)
  if args.xrange:
    pyplot.xlim(*args.xrange)
  if args.yrange:
    pyplot.ylim(*args.yrange)
  elif args.field:
    pyplot.ylim(0, 2)
  if args.title:
    pyplot.title(args.title)
  if args.out_file:
    pyplot.savefig(args.out_file, dpi=args.dpi)
  else:
    pyplot.show()


def to_num(num_str):
  try:
    return int(num_str)
  except ValueError:
    return float(num_str)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == "__main__":
  main()
