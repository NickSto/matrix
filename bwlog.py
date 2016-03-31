#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import os
import sys
import time
import argparse
import lib.ipwraplib as ipwraplib
import lib.simplewrap as simplewrap

UPTIME_PATH = '/proc/uptime'
ARG_DEFAULTS = {'status_path':'/proc/net/dev', 'watch_interfaces':'', 'ignore_interfaces':'lo',
                'last_file':os.path.expanduser('~/.local/share/nbsdata/bwlast.tsv')}
USAGE = "%(prog)s [options]"
DESCRIPTION = ('Print bandwidth usage in the current observation window. Uses '+
ARG_DEFAULTS['status_path']+' by default to monitor the bandwidth use of each interface. It will '
'parse that pseudo-file, log the current numbers to '+ARG_DEFAULTS['last_file']+' if requested, '
'and print the change since the start of the observation period. By default, it will only print '
'information on the currently active interface (the default route). If --no-default is given, it '
'will print a line for every interface.'+"""
Each line consists of 7 tab-delimited columns:
1. Current Unix timestamp
2. Seconds since the start of the observation period
3. Interface name
4. Gateway MAC address
5. Wifi SSID
6. Bytes received in this period
7. Bytes sent in this period
8. Received rate in this period (bytes/sec)
9. Sent rate in this period (bytes/sec).""")


def main(argv):

  # Set up a wrapper to wrap text around the current terminal width. I want to be able to include
  # line breaks in my help text, which requires argparse.RawTextHelpFormatter, but that results in
  # fixed-width text that's really messy, unless I auto-resize it myself with simplewrap.
  wrapper = simplewrap.Wrapper()
  wrap = wrapper.wrap

  parser = argparse.ArgumentParser(description=wrap(DESCRIPTION),
                                   formatter_class=argparse.RawTextHelpFormatter)
  parser.set_defaults(**ARG_DEFAULTS)

  wrapper.width = wrapper.width - 24
  parser.add_argument('-s', '--status-path',
    help=wrap('The path to the pseudo-file containing the current bandwidth usage. Default: "'+
              ARG_DEFAULTS['status_path']+'"'))
  parser.add_argument('-l', '--last-file',
    help=wrap('The path to the log file containing the bandwidth usage at the start of this '
              'observation period. The start of the period is assumed to be the date modified of '
              'this file. If this file does not exist, the script will assume the record started '
              'at the last reboot, and that the totals were 0 then. Default: "'
              +ARG_DEFAULTS['last_file']+'"'))
  parser.add_argument('-u', '--update', action='store_true',
    help=wrap('Update the last_file. This will serve as the start of a new observation period.'))
  parser.add_argument('-D', '--no-default', action='store_true',
    help=wrap('Watch all interfaces, not just the one designated as the default route.'))
  parser.add_argument('-i', '--watch-interfaces',
    help=wrap('If --no-default is given, this specifies which interfaces to exclusively watch '
              '(comma-delimited). If given, the script will only output info on these interfaces, '
              'ignoring all others. Default: "'+ARG_DEFAULTS['watch_interfaces']+'"'))
  parser.add_argument('-I', '--ignore-interfaces',
    help=wrap('If --no-default is given, this specifies interfaces to ignore (comma-delimited). '
              'Default: "'+ARG_DEFAULTS['ignore_interfaces']+'"'))

  args = parser.parse_args(argv[1:])

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
          sys.stderr.write('line {}: ignoring interface {}.\n'.format(line_num, interface))
          continue
        if ifaces_watch and interface not in ifaces_watch:
          sys.stderr.write('line {}: not watching interface {}.\n'.format(line_num, interface))
          continue
      elif interface != default_interface:
        continue
      fields = fields[1].split()
      if len(fields) != 16:
        sys.stderr.write('line {}: only {} fields.\n'.format(line_num, len(fields)))
        continue
      try:
        received = int(fields[0])
        sent = int(fields[8])
      except ValueError:
        sys.stderr.write('line {}: invalid int(s): "{}" and/or "{}".\n'
                         .format(line_num, fields[0], fields[8]))
        continue
      try:
        last_received, last_sent = last[interface]
      except KeyError:
        last_received, last_sent = (0, 0)
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
      print(int(now), int(elapsed), interface, mac, ssid, received_since, sent_since,
            int(received_rate), int(sent_rate), sep='\t')
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


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
