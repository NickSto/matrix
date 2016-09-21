#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import os
import sys
import time
import logging
import argparse
from lib import simplewrap
from lib import ipwraplib
from lib import console

UPTIME_PATH = '/proc/uptime'
ARG_DEFAULTS = {'status_path':'/proc/net/dev', 'watch_interfaces':'', 'ignore_interfaces':'lo',
                'last_file':os.path.expanduser('~/.local/share/nbsdata/bwlast.tsv'),
                'log':sys.stderr, 'log_level':logging.ERROR}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Print bandwidth usage in the current observation window. Uses {status_path} by
default to monitor the bandwidth use of each interface. It will parse that pseudo-file, log the
current numbers to {last_file} if requested, and print the change since the start of the observation
period. By default, it will only print information on the currently active interface (the default
route). If --no-default is given, it will print a line for every interface.
Each line consists of 7 tab-delimited columns:
1. Current Unix timestamp
2. Seconds since the start of the observation period
3. Interface name
4. Gateway MAC address
5. Wifi SSID
6. Bytes received in this period
7. Bytes sent in this period
8. Received rate in this period (bytes/sec)
9. Sent rate in this period (bytes/sec).""".format(**ARG_DEFAULTS)


def main(argv):

  # Set up a wrapper to wrap text around the current terminal width. I want to be able to include
  # line breaks in my help text, which requires argparse.RawDescriptionHelpFormatter, but that
  # results in fixed-width text that's really messy, unless I auto-resize it myself with simplewrap.
  wrapper = simplewrap.Wrapper()
  wrapped_description = wrapper.wrap(DESCRIPTION)

  # A bug in argparse is that it gets the current terminal width from $COLUMNS, which is usually not
  # set. Manually set it so it wraps the text at the actual terminal width.
  os.environ['COLUMNS'] = str(console.termwidth())
  parser = argparse.ArgumentParser(description=wrapped_description,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('-s', '--status-path',
    help='The path to the pseudo-file containing the current bandwidth usage. Default: '
         '"%(default)s"')
  parser.add_argument('-l', '--last-file',
    help='The path to the log file containing the bandwidth usage at the start of this '
         'observation period. The start of the period is assumed to be the date modified of '
         'this file. If this file does not exist, the script will assume the record started '
         'at the last reboot, and that the totals were 0 then. Default: "%(default)s"')
  parser.add_argument('-u', '--update', action='store_true',
    help='Update the last_file. This will serve as the start of a new observation period.')
  parser.add_argument('-D', '--no-default', action='store_true',
    help='Watch all interfaces, not just the one designated as the default route.')
  parser.add_argument('-i', '--watch-interfaces',
    help='If --no-default is given, this specifies which interfaces to exclusively watch '
         '(comma-delimited). If given, the script will only output info on these interfaces, '
         'ignoring all others. Default: "%(default)s"')
  parser.add_argument('-I', '--ignore-interfaces',
    help='If --no-default is given, this specifies interfaces to ignore (comma-delimited). '
         'Default: "%(default)s"')
  parser.add_argument('-L', '--log', type=argparse.FileType('w'),
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='log_level', action='store_const', const=logging.CRITICAL,
    help='Print messages only on critical errors.')
  parser.add_argument('--debug', dest='log_level', action='store_const', const=logging.DEBUG)

  args = parser.parse_args(argv[1:])

  tone_down_logger()
  logging.basicConfig(stream=args.log, level=args.log_level, format='%(message)s')

  # Read in and parse watch/ignored interfaces.
  ifaces_watch = []
  if args.watch_interfaces:
    ifaces_watch = args.watch_interfaces.split(',')
  ifaces_ignore = []
  if args.ignore_interfaces:
    ifaces_ignore = args.ignore_interfaces.split(',')

  now = time.time()
  last_reboot = now - get_uptime(UPTIME_PATH)
  try:
    last = read_last(args.last_file)
    last_time = os.path.getmtime(args.last_file)
    # If the last modified is before the last restart, we can't use the last_file.
    if last_time < last_reboot:
      last = {}
      last_time = last_reboot
  except IOError:
    # If last status file doesn't exist, give an empty data structure (will be interpreted as
    # zeroes), and assume it began at the last reboot.
    last = {}
    last_time = last_reboot
  elapsed = now - last_time

  wifi_info = ipwraplib.get_wifi_info()
  default_interface, default_ip = ipwraplib.get_default_route()
  wifi = {'interface':wifi_info[0], 'ssid':wifi_info[1], 'mac':wifi_info[2]}

  line_num = 0
  if args.update:
    last_file = open(args.last_file, 'w')
  with open(args.status_path) as status_file:
    for line in status_file:
      line_num += 1
      # Note: Sometimes the output has been observed to have no space between the colon and the
      # first field: https://stackoverflow.com/questions/1052589/how-can-i-parse-the-output-of-proc-net-dev-into-keyvalue-pairs-per-interface-u
      fields = line.split(':')
      if len(fields) != 2:
        continue
      interface = fields[0].strip()
      if args.no_default:
        if interface in ifaces_ignore:
          logging.info('line {}: ignoring interface {}.'.format(line_num, interface))
          continue
        if ifaces_watch and interface not in ifaces_watch:
          logging.info('line {}: not watching interface {}.'.format(line_num, interface))
          continue
      elif interface != default_interface:
        continue
      fields = fields[1].split()
      if len(fields) != 16:
        logging.warn('line {}: only {} fields.'.format(line_num, len(fields)))
        continue
      try:
        received = int(fields[0])
        sent = int(fields[8])
      except ValueError:
        logging.warn('line {}: invalid int(s): "{}" and/or "{}".'
                     .format(line_num, fields[0], fields[8]))
        continue
      try:
        last_received, last_sent = last[interface]
      except KeyError:
        last_received, last_sent = (0, 0)
      if received < last_received:
        logging.error('Last recv > current recv: {} > {}'.format(last_received, received))
        continue
      if sent < last_sent:
        logging.error('Last recv > current recv: {} > {}'.format(last_received, received))
        continue
      if received == 0:
        logging.error('recv is 0.')
        continue
      if sent == 0:
        logging.error('sent is 0.')
        continue
      received_since = received - last_received
      sent_since = sent - last_sent
      received_rate = received_since/elapsed
      sent_rate = sent_since/elapsed
      # If this is the wifi interface, we can add more info about it.
      #TODO: Get the MAC address of non-wifi gateways too.
      if interface == wifi['interface']:
        ssid = wifi['ssid']
        mac = wifi['mac']
      else:
        ssid = '.'
        mac = '.'
      print(int(round(now)), int(round(elapsed)), interface, mac, ssid, received_since, sent_since,
            int(round(received_rate)), int(round(sent_rate)), sep='\t')
      logging.debug('{}:\t{} recv\t{} sent'.format(interface, received, sent))
      if args.update:
        last_file.write('{}\t{}\t{}\n'.format(interface, received, sent))
  if args.update:
    last_file.close()


def read_last(last_path):
  """Parse last status file, return data.
  Last status file has 3 columns: interface, received bytes, sent bytes.
  Returned data structure is a dict mapping interface names to tuples.
  The tuples contain 2 ints: received bytes and sent bytes.
  Parsing errors are ignored."""
  data = {}
  with open(last_path) as last_file:
    for line in last_file:
      fields = line.strip('\r\n').split('\t')
      try:
        interface, received, sent = fields
      except ValueError:
        continue
      try:
        data[interface] = (int(received), int(sent))
      except ValueError:
        continue
  return data


def get_uptime(uptime_path):
  """Get system uptime, in seconds, from /proc/uptime (or whatever path is provided)."""
  with open(uptime_path) as uptime_file:
    uptime_fields = uptime_file.read().split()
    try:
      return float(uptime_fields[0])
    except (ValueError, IndexError):
      pass


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


if __name__ == '__main__':
  sys.exit(main(sys.argv))
