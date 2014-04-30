#!/usr/bin/env python
from __future__ import division
from matplotlib import pyplot

DEFAULTS = {'figsize':(8,6), 'dpi':80, 'width':640, 'height':480}
OPT_DEFAULTS = {'x_label':'Value', 'y_label':'Frequency',
  'color':'cornflowerblue'}


def add_arguments(parser):
  """Add global matplotlib plotting arguments to the argparse parser."""
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('-T', '--title',
    help='Plot title. Default: "%(default)s".')
  parser.add_argument('-X', '--x-label',
    help='Label for the X axis. Default: "%(default)s".')
  parser.add_argument('-Y', '--y-label',
    help='Label for the Y axis. Default: "%(default)s".')
  parser.add_argument('-W', '--width', type=int,
    help='Width of the output image, in pixels. Default: {width}px.'.format(
      **DEFAULTS))
  parser.add_argument('-H', '--height', type=int,
    help='Height of the output image, in pixels. Default: {height}px.'.format(
      **DEFAULTS))
  parser.add_argument('-D', '--dpi', type=int,
    help='DPI of the image. If a height or width is given, a larger DPI will '
      'effectively just scale up the plot features, and a smaller DPI will '
      'scale them down. Default: {dpi}dpi.'.format(**DEFAULTS))
  parser.add_argument('-C', '--color',
    help='Color for the plot data elements. Can use any CSS color. Default: '
      '"%(default)s".')
  return parser


def scale(defaults=DEFAULTS, **args):
  """Calculate the correct dpi and figsize to scale the image as the user
  requested.
  Required keyword arguments: 'dpi', 'width', 'height'
  """
  # assumptions
  assert 'dpi' in args and 'width' in args and 'height' in args, (
    'Necessary command-line arguments are missing.'
  )
  default_ratio = defaults['figsize'][0] / defaults['figsize'][1]
  pixel_ratio = defaults['width'] / defaults['height']
  assert default_ratio == pixel_ratio, 'Default aspect ratios do not match.'
  # If only a width or height is given, infer the other dimension, assuming the
  # default aspect ratio.
  if args['width'] and not args['height']:
    args['height'] = args['width'] / default_ratio
  elif args['height'] and not args['width']:
    args['width'] = args['height'] * default_ratio
  # Did the user specify a dpi?
  if args['dpi']:
    # If user gave a dpi, use it.
    # If user gives no width or height, a custom dpi will resize the plot.
    dpi = args['dpi']
    if args['width'] and args['height']:
      # If they did give a width/height, a custom dpi will scale the elements
      # in the plot.
      figsize = (args['width']/dpi, args['height']/dpi)
    else:
      figsize = defaults['figsize']
  elif args['width'] and args['height']:
    # If user gives a width or height and no dpi, scale both dpi and figsize.
    ratio = args['width'] / args['height']
    if ratio > default_ratio:
      scale = args['height'] / defaults['height']
      figsize = (
        defaults['figsize'][0] * (ratio/default_ratio),
        defaults['figsize'][1]
      )
    else:
      scale = args['width'] / defaults['width']
      figsize = (
        defaults['figsize'][0],
        defaults['figsize'][1] / (ratio/default_ratio)
      )
    dpi = scale * defaults['dpi']
  else:
    dpi = defaults['dpi']
    figsize = defaults['figsize']
  return (dpi, figsize)


def preplot(**args):
  """Set up the initial pyplot figure parameters, return a pyplot object.
  Run this, get pyplot from it, and create your plot with it. E.g.:
    pyplot = matplotliblib.preplot(**vars(args))
    pyplot.hist(data)
  Required keyword arguments: 'dpi', 'width', 'height'
  """
  (dpi, figsize) = scale(**args)
  pyplot.figure(dpi=dpi, figsize=figsize)
  return pyplot


def plot(pyplot, **args):
  """Add options to a plot, and either display it or save it.
  Create your plot, then give the pyplot object to this function, e.g.:
    pyplot.hist(data)
    matplotliblib.plot(pyplot, **vars(args))
  Required keyword arguments:
  'x_label', 'y_label', 'title', 'x_range', 'out_file'
  """
  required_opts = ['x_label', 'y_label', 'title', 'x_range', 'out_file']
  assert all([opt in args for opt in required_opts]), (
    'Necessary command-line arguments are missing.'
  )
  pyplot.xlabel(args['x_label'])
  pyplot.ylabel(args['y_label'])
  if args['x_range']:
    pyplot.xlim(*args['x_range'])
  if args['title']:
    pyplot.title(args['title'])
  if args['out_file']:
    pyplot.savefig(args['out_file'])
  else:
    pyplot.show()