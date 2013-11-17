#!/usr/bin/env python
# 
# General strategy:
# Separate the truncation of long decimals and computing of label width. Decide
# which decimal place to round to, and THEN make the label strings and find the
# widest.
# 
# Rounding:
# Allow user to set number of significant digits to keep, and use a default.
# if highest_radix < keep_digits:
#   Round to the (highest_radix - sig_digits) decimal place
# else:
#   Round to whole number
# Examples (sig_digits = 4):                 max     min     round to
#   max    min         round to            22134   3.40     22134        3
#   100    10.0913     100.0     10.1        0.5   0.00098      0.5000   0.0001
#
# Precompute labels:
# Just create all the label strings beforehand and store in a second dict. Find
# the widest width that way. Also, this will move the code to be adaptable to
# arbitrary labels later (like the timestamps in upanalyze)
#
# Switching to integers:
# E.g. I don't want to show the decimal place in a 10-step range of 0 to 901
# (bin_size of 90.1) but I want to show it in a 6-step range of 0 to 15
# (bin_size of 2.5).
# However I do this, it should definitely be controllable by the user.
# 
import os
import sys
import subprocess
import distutils.spawn
from optparse import OptionParser

DEFAULT_LINES = 24
DEFAULT_COLUMNS = 80

OPT_DEFAULTS = {'file':'', 'lines':0, 'width':0, 'float':0.0, 'dummy':False,
  'debug':False}
USAGE = "USAGE: %prog [options]"
DESCRIPTION = """Print a quick histogram of the input data. Input format is one
number per line. If more than one value per line is encountered, it will split
on whitespace and take the first value. The histogram will be of the frequency
of the numbers."""
EPILOG = """Caution: It holds the entire dataset in memory, as a list."""

def main():

  parser = OptionParser(usage=USAGE, description=DESCRIPTION, epilog=EPILOG)

  parser.add_option('-f', '--file', dest='file',
    default=OPT_DEFAULTS.get('file'),
    help='Read from the given file instead of stdin.')
  parser.add_option('-l', '--lines', dest='lines', type='int',
    default=OPT_DEFAULTS.get('lines'),
    help='Height of the printed histogram, in lines. Default is the current '
    +'height of the terminal.')
  parser.add_option('-w', '--width', dest='width', type='int',
    default=OPT_DEFAULTS.get('width'),
    help='Width of the printed histogram, in columns (characters). Default is '
    +'the current width of the terminal.')
  parser.add_option('-D', '--dummy', dest='dummy', action='store_const',
    const=not OPT_DEFAULTS.get('dummy'), default=OPT_DEFAULTS.get('dummy'),
    help='Use dummy data: a random range of floats between 0.0 and 10.0, '
    +'including those two values.')
  parser.add_option('-d', '--debug', dest='debug', action='store_const',
    const=not OPT_DEFAULTS.get('debug'), default=OPT_DEFAULTS.get('debug'),
    help='Debug mode.')

  (options, arguments) = parser.parse_args()

  debug = options.debug

  (lines, columns) = term_size(DEFAULT_LINES, DEFAULT_COLUMNS)
  if options.lines > 0:
    lines = options.lines
  if options.width > 0:
    columns = options.width

  if options.dummy:
    input = dummy_data()
  elif options.file:
    input = open(options.file, 'r')
  else:
    input = sys.stdin

  # read data into list, find min and max
  data = []
  minimum = ''
  maximum = 0
  line_num = 0
  for line in input:
    line_num+=1
    fields = line.split()
    if not fields:
      continue
    try:
      value = float(fields[0])
    except ValueError:
      sys.stderr.write("Warning: Non-number encountered on line "+str(line_num)
        +': "'+line.rstrip('\r\n')+'"\n')
      continue
    data.append(value)
    minimum = min(minimum, value)
    maximum = max(maximum, value)

  if type(input) == file:
    input.close()

  if not data:
    sys.exit(0)

  # calculate bin size
  bin_size = (maximum - minimum)/lines
  if bin_size == int(bin_size) and minimum == int(minimum):
    bin_size = int(bin_size)
    minimum = int(minimum)
  int_label = False
  if bin_size >= 10:
    int_label = True
    print "setting int_label to True"
  if debug:
    print str(minimum)+" to "+str(maximum)+", step "+str(bin_size)

  # count histogram bin totals, store in dict
  hist = dict.fromkeys(range(lines), 0)
  for value in data:
    bin = int((value-minimum)/bin_size)
    # put maximum values into last bin
    if bin == lines:
      bin = lines-1
    hist[bin] = hist[bin] + 1
    # print str(bin)+": "+str(value)

  # what is the maximum bin total and label width?
  max_total = 0
  label_width = 0
  lowest_radix = ""
  longest_decimal = 0
  for bin in hist:
    max_total = max(max_total, hist[bin])
    bin_num = (bin + 1) * bin_size + minimum
    bin_label = str((bin + 1) * bin_size)
    lowest_radix = min(lowest_radix, radix_dist(bin_num))
    label_width = max(label_width, len(bin_label))
    parts = bin_label.split(".")
    if len(parts) > 1:
      longest_decimal = max(longest_decimal, len(parts[1]))

  # try to avoid unnecessarily long strings of decimals
  if longest_decimal > 1:
    highest_radix = max(radix_dist(maximum), radix_dist(minimum))
    if debug:
      sys.stdout.write("highest radix: "+str(highest_radix)
        +", lowest radix: "+str(lowest_radix))
    if int_label:
      label_width = min(label_width, highest_radix + 1)
    elif highest_radix > 1:
      label_width = min(label_width, highest_radix + 3)
    elif highest_radix < 1:
      label_width = min(label_width, abs(highest_radix)+5)
    else:
      label_width = min(label_width, 5)
    # allow for minus sign on negative numbers
    if minimum < 0:
      label_width+=1

  # print the histogram
  if debug:
    sys.stdout.write("columns: "+str(columns)
      +", label_width: "+str(label_width)+"\n")
  max_bar = columns - label_width - len(": ")
  label_format = "%"+str(label_width)+"s"
  for bin in hist:
    bin_num = minimum + (bin + 1) * bin_size
    if int_label:
      bin_num = int(bin_num)
    bin_label = (label_format % bin_num)[:label_width] + ": "
    bar_width = int(hist[bin]/float(max_total) * max_bar)
    print bin_label + "*" * bar_width



def term_size(default_lines=None, default_columns=None):
  """Get current terminal width, using stty command. If stty isn't available,
  or if it gives an error, return the default."""
  if not distutils.spawn.find_executable('stty'):
    return default
  devnull = open(os.devnull, 'wb')
  try:
    output = subprocess.check_output(['stty', 'size'], stderr=devnull)
  except OSError:
    devnull.close()
    return (default_lines, default_columns)
  except subprocess.CalledProcessError:
    devnull.close()
    return (default_lines, default_columns)
  devnull.close()
  try:
    (lines, columns) = output.split()
    return (int(lines), int(columns))
  except ValueError:
    return (default_lines, default_columns)


def radix_dist(num):
  """Return the "magnitude" of a decimal number: How far away from the radix
  (the decimal) its most significant digit is. Or, how many zeroes appear in it
  when rounded to the nearest tens (including the zero before the radix).
  Negative numbers mean to the right of the decimal, positive to the left."""
  import math
  if num == 0:
    return 0
  else:
    return int(math.floor(math.log10(abs(num))))


def dummy_data():
  import random
  dummy = [str(random.random()*10)[:4] for i in range(8)]
  dummy.append("0.0")
  dummy.append("10.0")
  return dummy


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == "__main__":
  main()