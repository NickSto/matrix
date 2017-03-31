#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import errno
import struct
import socket
import base64
import logging
import argparse
import datetime

ARG_DEFAULTS = {'log':sys.stderr, 'volume':logging.ERROR}
DESCRIPTION = """"""


def make_argparser():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('data',
    help='Input data.')
  parser.add_argument('-e', '--encode', action='store_true')
  parser.add_argument('-c', '--cookie', action='store_true',
    help='The data is a mod_uid cookie. In addition to encoding or decoding it, also print its '
         'meaning.')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'),
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)

  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  if args.cookie:
    if args.encode:
      cookie = encode_cookie(args.data)
      print(cookie)
    else:
      net_ints = cookie_to_ints(args.data)
      uid = ints_to_uid(net_to_host_ints(net_ints))
      print(uid)
      data = decode_ints(net_ints)
      print(format_data(data))


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def decode_cookie(cookie):
  net_ints = cookie_to_ints(cookie)
  host_ints = net_to_host_ints(net_ints)
  return ints_to_uid(host_ints)


def cookie_to_ints(cookie):
  """Decode an Nginx userid cookie into a uid string.
  Taken from: https://stackoverflow.com/questions/18579127/parsing-nginxs-http-userid-module-cookie-in-python/19037624#19037624
  This algorithm is for version 2 of http://wiki.nginx.org/HttpUseridModule.
  This nginx module follows the apache mod_uid module algorithm, which is
  documented here: http://www.lexa.ru/programs/mod-uid-eng.html.
  """
  # get the raw binary value
  binary_cookie = base64.b64decode(cookie)
  # unpack into 4 parts, each a network byte orderd 32 bit unsigned int
  unsigned_ints = struct.unpack('!4I', binary_cookie)
  # Note: these ints are now in network byte order, and the original code had a conversion to host
  # byte order. But I found that gave incorrect values when translated to their actual meanings.
  return unsigned_ints


def net_to_host_ints(net_ints):
  # convert from network (big-endian) to host byte (probably little-endian) order
  host_byte_order_ints = [socket.ntohl(i) for i in net_ints]
  return host_byte_order_ints


def ints_to_uid(ints):
  # convert to upper case hex value
  uid = ''.join(['{0:08X}'.format(i) for i in ints])
  return uid


def decode_ints(ints):
  # The IP address, as a single integer.
  service_num_int = ints[0]
  ip = int_to_ip(service_num_int)
  # The actual unix timestamp, no manipulation required (surprise!).
  timestamp = ints[1]
  # Lower 16 bits is the actual pid. Not sure what the upper 16 bits is, but it looks similar to a
  # pid and it does change when the server process restarts.
  pid_int = ints[2]
  pid = pid_int & 0b1111111111111111
  pid_upper = pid_int >> 16
  # Upper 24 bits is the actual sequence number, starting at 0x030303. Increments with every cookie
  # issued by the process. The lower 8 bits is the cookie version number (should be 2).
  sequence_num_int = ints[3]
  sequence_num = (sequence_num_int >> 8) - 0x030303
  version = sequence_num_int & 0b11111111
  if version != 2:
    logging.warn('Cookie version is {}, not 2 as expected.'.format(version))
  return {'ip':ip, 'timestamp':timestamp, 'pid_upper':pid_upper, 'pid':pid, 'counter':sequence_num,
          'version':version}


def format_data(data):
  lines = []
  lines.append('IP address:\t\t'+data['ip'])
  human_time = datetime.datetime.fromtimestamp(data['timestamp'])
  lines.append('timestamp:\t\t{} ({})'.format(human_time, data['timestamp']))
  lines.append('16 bits above pid:\t{}'.format(data['pid_upper']))
  lines.append('pid:\t\t\t{}'.format(data['pid']))
  lines.append('sequence #:\t\t{}'.format(data['counter']))
  lines.append('version:\t\t{}'.format(data['version']))
  return '\n'.join(lines)


def int_to_ip(integer):
  ip_bytes = []
  for shift in range(0, 32, 8):
    ip_bytes.append((integer >> shift) & 0b11111111)
  ip_strs = map(str, reversed(ip_bytes))
  return '.'.join(ip_strs)


def encode_cookie(uid):
  """Encode a uid into an Nginx userid cookie.
  Reversed from decode_cookie() above."""
  unsigned_ints = []
  if len(uid) != 32:
    return None
  for i in range(0, 32, 8):
    host_byte_str = uid[i:i+8]
    try:
      host_byte_int = int(host_byte_str, 16)
    except ValueError:
      return None
    net_byte_int = socket.htonl(host_byte_int)
    unsigned_ints.append(net_byte_int)
  binary_cookie = struct.pack('!4I', *unsigned_ints)
  cookie_bytes = base64.b64encode(binary_cookie)
  return str(cookie_bytes, 'utf8')


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
