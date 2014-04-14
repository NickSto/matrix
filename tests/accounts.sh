#!/usr/bin/env bash
dirname=$(dirname $0)

# functional tests
echo -e "\taccounts.py ::: accounts.txt.in:"
$dirname/../accounts.py -q $dirname/accounts.txt.in | diff -s - $dirname/accounts.txt.stdout

echo -e "\taccounts.py ::: accounts.txt.in:"
$dirname/../accounts.py -O $dirname/accounts.txt.in | diff -s - $dirname/accounts.txt.stderr