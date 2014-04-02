#!/usr/bin/env python
import sys
import fileinput

seen = set()
for line in fileinput.input():
  if line not in seen:
    sys.stdout.write(line)
  seen.add(line)