#!/usr/bin/env python
from __future__ import division
import re
import os
import sys
import time
import datetime
import argparse
try:
  import exifread
except ImportError:
  exifread = None
  sys.stderr.write('Warning: Need to install exifread for full functionality.\n')

OPT_DEFAULTS = {'max_diff':60, 'max_tz_diff':60}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Properly set the timestamp on images with common filename
formats. Compares the timestamp in the filename with the date modified, sets the
date modified to the filename timestamp if there is a difference. N.B.: It
ignores differences likely due to time zones (an even number of hours
difference)."""

NAME_FORMATS = [
  # Samsung Galaxy S2 camera
  r'^(?:IMG|VID|PANO)_(20\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.(?:jpg|mp4)$',
  # Ubuntu screenshot automatic filenames
  r'^Screenshot from (20\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.(?:jpg|png)$',
  # Ubuntu cheese webcam automatic filenames
  r'^(20\d{2})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})\.jpg$',
  r'^(20\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.(?:jpg|mp4)$',
  r'^C360_(20\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-\d{3}\.jpg$',
]

# Won't raise a warning about names like this.
IGNORE_FORMATS = [
  r'^\d{5}\.MTS$',
  r'^HPIM\d{4}\.jpg$',
  r'^P\d{6,7}\.(?:JPG|MOV)$',
]


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('images', metavar='image.jpg', nargs='+',
    help='Image files to fix.')
  parser.add_argument('-n', '--no-edit', action='store_true',
    help='Simulation: don\'t make any modifications.')
  parser.add_argument('-d', '--max-diff', type=int,
    help='Maximum allowed discrepancy between the filename timestamp and the '
      'date modified, in seconds. Set to 0 to allow no discrepancy. Default: '
      '%(default)s')
  parser.add_argument('-D', '--max-tz-diff', type=int,
    help='Tolerance (in seconds) when determining a discrepancy is likely due '
      'to a timezone difference. Set to 0 to turn off timezone allowance. '
      'Default: %(default)s')

  args = parser.parse_args(argv[1:])

  for image_path in args.images:
    if not os.path.isfile(image_path):
      continue
    image_name = os.path.split(image_path)[1]
    # Get timestamp by parsing filename
    title_time = None
    for name_format in NAME_FORMATS:
      match = re.search(name_format, image_name)
      if match:
        dt = datetime.datetime(year=int(match.group(1)),
                               month=int(match.group(2)),
                               day=int(match.group(3)),
                               hour=int(match.group(4)),
                               minute=int(match.group(5)),
                               second=int(match.group(6)))
        title_time = time.mktime(dt.timetuple())
        break
    # Otherwise, try to get it from EXIF data
    if not title_time and exifread:
      title_time = get_exif_time(image_path)
    if not title_time:
      recognized = False
      for name_format in IGNORE_FORMATS:
        if re.search(name_format, image_name):
          recognized = True
      if not recognized:
        print "Unrecognized name format: "+image_name
      continue
    # Compare with date modified
    mod_time = os.path.getmtime(image_name)
    time_diff = int(round(abs(title_time - mod_time)))
    tz_diff = abs(time_diff - round(time_diff/60/60)*60*60)
    if time_diff > args.max_diff and tz_diff >= args.max_tz_diff:
      print '{}: discrepancy of {} ({})'.format(image_name,
        datetime.timedelta(seconds=time_diff), time_diff)
      if not args.no_edit:
        # Correct date modified
        os.utime(image_path, (title_time, title_time))


def get_exif_time(image_path):
  #TODO: Use TimeZoneOffset to correct the timestamp
  tag_name = 'EXIF DateTimeOriginal'
  with open(image_path, 'rb') as image_file:
    tags = exifread.process_file(image_file, details=False, stop_tag=tag_name)
  if tag_name in tags:
    return parse_time_str(tags[tag_name].values)
  else:
    sys.stderr.write('Warning: did not find EXIF tag "{}" in file "{}"'
                     '\n'.format(tag_name, image_path))
    return None


def parse_time_str(time_str):
  # Must look like '2014:10:21 11:09:34' or will return None
  if len(time_str) != 19:
    sys.stderr.write('Warning: Invalid EXIF time string length "'+time_str
                     +'".\n')
    return None
  try:
    dt = datetime.datetime(year=int(time_str[0:4]),
                           month=int(time_str[5:7]),
                           day=int(time_str[8:10]),
                           hour=int(time_str[11:13]),
                           minute=int(time_str[14:16]),
                           second=int(time_str[17:19]))
  except ValueError:
    sys.stderr.write('Warning: Invalid EXIF time string "'+time_str+'".\n')
    return None
  return time.mktime(dt.timetuple())


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  main(sys.argv)
