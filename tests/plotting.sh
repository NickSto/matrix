#!/usr/bin/env bash
dirname=$(dirname $0)

# functional tests
echo -e "\thistoplot.py ::: histoplot.txt.in:"
$dirname/../histoplot.py -H 240 -D 60 $dirname/histoplot.txt.in -o $dirname/histoplot-tmp.png
if [[ $(crc32 $dirname/histoplot-tmp.png) == $(crc32 $dirname/histoplot-H240-D60.png.out) ]]; then
  echo "Output is identical to histoplot-H240-D60.png.out"
else
  echo "Output does not match histoplot-H240-D60.png.out" >&2
fi

rm $dirname/histoplot-tmp.png
