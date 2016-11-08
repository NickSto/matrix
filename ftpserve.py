#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import argparse
import pyftpdlib.authorizers
import pyftpdlib.handlers
import pyftpdlib.servers

ARG_DEFAULTS = {'port':23189, 'dir':'.'}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Quickly set up an FTP server to allow read and/or writing to a given directory."""


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('-u', '--user',
    help='The username to use when logging into the server. If omitted, anonymous users will be '
         'permitted instead.')
  parser.add_argument('-p', '--password',
    help='The password you\'ll need to use when logging into the server. WARNING: This is not a '
         'secure script at all. The password will be printed to the screen, sent in the clear, and '
         'shown to your mother.')
  parser.add_argument('-P', '--port', type=int,
    help='The port to listen on. Default: %(default)s')
  parser.add_argument('-d', '--dir',
    help='The root directory to serve/receive files from/to. Default: The current directory.')
  parser.add_argument('-i', '--any-ip', action='store_true',
    help='Allow connections from any IP address instead of just localhost.')
  parser.add_argument('-w', '--allow-write', action='store_true',
    help='Allow write permissions to the directory as well as read permissions.')

  args = parser.parse_args(argv[1:])

  if (args.user and not args.password) or (args.password and not args.user):
    fail('Error: Must provide both a username *and* password.')
  if args.allow_write and not (args.user and args.password):
    fail('Error: Cannot allow write permissions from anonymous users.')

  perm_str = 'read'
  permissions = 'elr'
  if args.allow_write:
    perm_str += ' and write'
    permissions += 'adfmwM'

  listen_ip = '127.0.0.1'
  listen_str = 'localhost'
  if args.any_ip:
    listen_ip = '0.0.0.0'
    listen_str = 'any IP'

  authorizer = pyftpdlib.authorizers.DummyAuthorizer()
  if args.user and args.password:
    user_str = 'user {} with password "{}"'.format(args.user, args.password)
    authorizer.add_user(args.user, args.password, args.dir, perm=permissions)
  else:
    user_str = 'anonymous users'
    authorizer.add_anonymous(args.dir)
  handler = pyftpdlib.handlers.FTPHandler
  handler.authorizer = authorizer
  server = pyftpdlib.servers.FTPServer((listen_ip, args.port), handler)

  print('Starting server listening on port {} for {} from {}, allowing {} access to {}/ ...'
        .format(args.port, user_str, listen_str, perm_str, os.path.abspath(args.dir)))

  # Run the server.
  server.serve_forever()


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
