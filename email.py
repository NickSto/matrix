#!/usr/bin/env python
from __future__ import division
import os
import sys
import socket
import getpass
import argparse
import subprocess
import ConfigParser
import distutils.spawn
# Munge sys.path to prevent the "import email.mime.text" from trying to import this script.
local_dir = sys.path.pop(0)
sys.path.append(local_dir)
import email.mime.text

CONFIG_FILENAME = 'email.cfg'
OPT_DEFAULTS = {}
USAGE = "%(prog)s [options] [to [subject [body [from]]]]"
DESCRIPTION = """User-friendly wrapper around sendmail."""
EPILOG = 'Add a file named "'+CONFIG_FILENAME+"""" to the script directory to set default values for
any of the fields. Format is a standard config file, with values in the [fields] section."""


def main(argv):

  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION, epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('to', metavar='To', nargs='?',
    help='Destination email address.')
  parser.add_argument('subject', metavar='Subject', nargs='?',
    help='Subject line.')
  parser.add_argument('body', metavar='Body', nargs='?',
    help='Email body.')
  parser.add_argument('from', metavar='From', nargs='?',
    help='Origin email address (default is your username on this machine and its hostname).')
  parser.add_argument('-t', '--to', dest='to_opt', metavar='recipient@email.com',
    help='Alias for the positional argument.')
  parser.add_argument('-s', '--subject', dest='subject_opt', metavar='Subject',
    help='Alias for the positional argument.')
  parser.add_argument('-b', '--body', dest='body_opt', metavar='Body\ text',
    help='Alias for the positional argument.')
  parser.add_argument('-f', '--from', dest='from_opt', metavar='sender@email.com',
    help='Alias for the positional argument.')
  parser.add_argument('-n', '--simulate', action='store_true',
    help='Do not actually send the email. Instead, print the formatted email text that will be '
         'passed to sendmail.')
  parser.add_argument('-c', '--config',
    help='Use this config file instead of the default ("'+CONFIG_FILENAME+'" in the script '
         'directory).')

  args = parser.parse_args(argv[1:])

  if args.config:
    config_path = args.config
  else:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(script_dir, CONFIG_FILENAME)
  fields = read_config(config_path)

  # Read fields in from arguments.
  # Order of precedence:
  # First, use named options, then positional arguments, then the config file, then the defaults.
  ## To
  if args.to_opt is not None:
    fields['to'] = args.to_opt
  elif args.to is not None:
    fields['to'] = args.to
  elif 'to' not in fields:
    fail('Error: Must specify a destination address ("to").')
  ## From
  if args.from_opt is not None:
    fields['from'] = args.from_opt
  elif getattr(args, 'from') is not None:
    fields['from'] = getattr(args, 'from')
  elif 'from' not in fields:
    fields['from'] = getpass.getuser()+'@'+socket.getfqdn()
  ## Subject
  if args.subject_opt is not None:
    fields['subject'] = args.subject_opt
  elif args.subject is not None:
    fields['subject'] = args.subject
  else:
    fields['subject'] = fields.get('subject', '')
  ## Body
  if args.body_opt is not None:
    fields['body'] = args.body_opt
  elif args.body is not None:
    fields['body'] = args.body
  else:
    fields['body'] = fields.get('body', '')

  return sendmail(fields, args.simulate)


def read_config(config_path):
  fields = {}
  if not os.path.isfile(config_path):
    return fields
  config = ConfigParser.RawConfigParser()
  config.read(config_path)
  for field in config.options('fields'):
    fields[field] = config.get('fields', field)
  return fields


def sendmail(fields, simulate=False):
  if distutils.spawn.find_executable('sendmail'):
    mail_cmd = 'sendmail'
  elif distutils.spawn.find_executable('/usr/sbin/sendmail'):
    mail_cmd = '/usr/sbin/sendmail'
  else:
    return False
  message = email.mime.text.MIMEText(fields['body'])
  message['From'] = fields['from']
  message['To'] = fields['to']
  message['Subject'] = fields['subject']
  if simulate:
    print message.as_string()
  else:
    process = subprocess.Popen([mail_cmd, '-oi', '-t'], stdin=subprocess.PIPE)
    process.communicate(input=message.as_string())
  return 0


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
