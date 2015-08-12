#!/usr/bin/env python
from __future__ import division
import sys
import socket
import getpass
import argparse
import subprocess
import distutils.spawn
# Munge sys.path to prevent the "import email.mime.text" from trying to import this script.
local_dir = sys.path.pop(0)
sys.path.append(local_dir)
import email.mime.text

OPT_DEFAULTS = {}
USAGE = "%(prog)s [options] [to [subject [body [from]]]]"
DESCRIPTION = """User-friendly wrapper around sendmail."""


def main(argv):

  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('to', metavar='To', nargs='?',
    help='Destination email address.')
  parser.add_argument('subject', metavar='Subject', nargs='?',
    help='Subject line.')
  parser.add_argument('body', metavar='Body', nargs='?',
    help='Email body.')
  parser.add_argument('from', metavar='From', nargs='?',
    help='Origin email address (default is your username on this machine and its hostname).')
  parser.add_argument('-n', '--simulate', action='store_true',
    help='Do not actually send the email. Instead, print the formatted email text that will be '
         'passed to sendmail.')
  parser.add_argument('-t', '--to',
    help='Alias for the positional argument.')
  parser.add_argument('-s', '--subject',
    help='Alias for the positional argument.')
  parser.add_argument('-b', '--body',
    help='Alias for the positional argument.')
  parser.add_argument('-f', '--from',
    help='Alias for the positional argument.')

  args = parser.parse_args(argv[1:])

  if args.to is None:
    fail('Error: Must specify a destination address ("to").')
  else:
    to = args.to
  if getattr(args, 'from') is None:
    from_ = getpass.getuser()+'@'+socket.getfqdn()
  else:
    from_ = getattr(args, 'from')
  subject = args.subject or ''
  body = args.body or ''

  return sendmail(from_, to, subject, body, args.simulate)


def sendmail(from_, to, subject, body, simulate=False):
  if distutils.spawn.find_executable('sendmail'):
    mail_cmd = 'sendmail'
  elif distutils.spawn.find_executable('/usr/sbin/sendmail'):
    mail_cmd = '/usr/sbin/sendmail'
  else:
    return False
  message = email.mime.text.MIMEText(body)
  message['From'] = from_
  message['To'] = to
  message['Subject'] = subject
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
