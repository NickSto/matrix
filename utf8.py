#!/usr/bin/env python3
import re
import sys
import errno
import logging
import argparse
import unittest
import unicodedata
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Convert UTF-8 encoded bytes into Unicode characters, or vice versa."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('inputs', nargs='*',
    help='Your characters or bytes. Omit to read from stdin. Warning: It will read the entire '
         'input into memory.')
  parser.add_argument('-i', '--input-type', choices=('bytes', 'chars',), default='bytes',
    help='Whether the input is UTF-8 encoded bytes, or Unicode characters.')
  parser.add_argument('-o', '--output-type', choices=('bytes', 'chars'), default='chars',
    help='What to convert your input into.')
  parser.add_argument('-I', '--input-format', choices=('hex', 'int', 'str'), default='hex',
    help='The format of the input. "str" means to interpret the input argument as the literal '
         'Unicode characters. For "hex", you can include characters outside [0-9A-F]. They will '
         'be removed. If you are giving "chars" in hex (code points), separate them with spaces or '
         'commas.')
  parser.add_argument('-O', '--output-format', choices=('hex', 'int', 'str', 'desc'), default='desc')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARN)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  parser.add_argument('-t', '--test', action='store_true',
    help='Run tests.')
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  if args.test:
    sys.argv = sys.argv[:1]
    unittest.main()
    return

  # Process format arguments.
  input_format = args.input_format
  if args.output_type == 'bytes' and args.output_format == 'desc':
    # The default output for bytes should be hex.
    output_format = 'hex'
  elif args.output_type == 'bytes' and args.output_format == 'str':
    fail('"str" is an invalid output format for type "bytes".')
  else:
    output_format = args.output_format

  input_strs = get_input(args.inputs, input_format)

  code_points = input_to_code_points(input_strs, args.input_type, input_format)

  for line in code_points_to_output(code_points, args.output_type, output_format):
    print(line)


def input_to_code_points(input_strs, input_type, input_format):
  """Parse input into code points."""
  if input_type == 'bytes':
    bin_input = ''
    for input_str in input_strs:
      if input_format == 'hex':
        hex_input = clean_up_hex(input_str)
        bin_input += hex_to_binary(hex_input)
      elif input_format == 'int':
        integer = int(input_str)
        bin_input += pad_binary(bin(integer)[2:])
    input_bytes = binary_to_bytes(bin_input)
    for char_bytes in chunk_byte_sequence(input_bytes):
      yield char_bytes_to_code_point(char_bytes)
  elif input_type == 'chars':
    if input_format == 'str':
      for char in input_strs:
        yield ord(char)
    else:
      for input_str in input_strs:
        if input_format == 'hex':
          hex_input = clean_up_hex(input_str)
          yield int(hex_input, 16)
        elif input_format == 'int':
          yield int(input_str)


def code_points_to_output(code_points, output_type, output_format):
  """Format code points into the output format.
  Yields a series of lines ready to be printed."""
  if output_type == 'chars':
    if output_format == 'desc':
      for code_point in code_points:
        yield format_code_point_output(code_point)
    elif output_format == 'str':
      output_str = ''
      for code_point in code_points:
        output_str += chr(code_point)
      yield output_str
    else:
      output_strs = []
      for code_point in code_points:
        if output_format == 'hex':
          code_point_hex = hex(code_point)[2:].upper()
          code_point_hex = pad_hex(code_point_hex)
          output_strs.append(code_point_hex)
        elif output_format == 'int':
          output_strs.append(str(code_point))
      yield ' '.join(output_strs)
  elif output_type == 'bytes':
    for code_point in code_points:
      #TODO: Do this encoding manually.
      char = chr(code_point)
      char_bytes = bytes(char, 'utf8')
      output_strs = []
      for byte in char_bytes:
        if output_format == 'hex':
          byte_hex = hex(byte)[2:].upper()
          output_strs.append(byte_hex)
        elif output_format == 'int':
          output_strs.append(str(byte))
      yield ' '.join(output_strs)


def get_input(input_args, format):
  if input_args:
    input_chunks = input_args
  else:
    input_chunks = sys.stdin
  for input_chunk in input_chunks:
    if format == 'str':
      for char in input_chunk:
        yield char
    else:
      for input_str in comma_or_space_split(input_chunk):
        yield input_str


def comma_or_space_split(in_str):
  if ',' in in_str:
    return in_str.split(',')
  else:
    return in_str.split()


def clean_up_hex(hex_input):
  upper_input = hex_input.upper()
  return re.sub(r'[^0-9A-F]+', '', upper_input)


def hex_to_binary(hex_input):
  int_input = int(hex_input, 16)
  bin_input = bin(int_input)[2:]
  return pad_binary(bin_input)


def pad_binary(binary):
  bin_len = len(binary)
  num_bytes = ((bin_len-1) // 8) + 1
  num_bits = num_bytes*8
  pad_bits = num_bits-bin_len
  binary = '0'*pad_bits + binary
  return binary


def binary_to_bytes(binary):
  for start in range(0, len(binary), 8):
    stop = start+8
    yield binary[start:stop]


def chunk_byte_sequence(input_bytes):
  bytes_togo = 0
  char_bytes = []
  for byte in input_bytes:
    char_bytes.append(byte)
    if byte.startswith('0'):
      if bytes_togo > 0:
        logging.warn('Invalid byte sequence (not enough continuation bytes): "{}"'
                     .format(' '.join(char_bytes)))
      yield char_bytes
      char_bytes = []
    elif byte.startswith('11'):
      if bytes_togo > 0:
        logging.warn('Invalid byte sequence (not enough continuation bytes): "{}"'
                     .format(' '.join(char_bytes)))
        char_bytes = []
        bytes_togo = 0
      match = re.search(r'^(1+)0', byte)
      assert match, byte
      leading_bits = match.group(1)
      bytes_togo = leading_bits.count('1') - 1
    elif byte.startswith('10'):
      if bytes_togo == 0:
        logging.warn('Invalid byte sequence (misplaced continuation byte): "{}"'.format(byte))
        char_bytes = []
      else:
        bytes_togo -= 1
        if bytes_togo == 0:
          if len(char_bytes) > 4:
            logging.warn('Invalid byte sequence (more than 4 bytes): "{}"'
                         .format(' '.join(char_bytes)))
          yield char_bytes
          char_bytes = []
  if len(char_bytes) > 0:
    logging.warn('Invalid byte sequence (not enough continuation bytes): "{}"'
                 .format(' '.join(char_bytes)))


def char_bytes_to_code_point(char_bytes):
  """Turn a byte sequence for a single character into the int for the code point it encodes."""
  code_point_bits = None
  for byte in char_bytes:
    if code_point_bits is None:
      if byte.startswith('0'):
        # ASCII (single-byte) character.
        code_point_bits = byte
        break
      elif byte.startswith('11'):
        # Leading byte of a multibyte sequence.
        code_point_bits = re.sub(r'^1+0', '', byte)
      else:
        logging.warn('Invalid byte sequence: "{}" (error on byte {})'
                     .format(' '.join(char_bytes), byte))
        raise ValueError
    else:
      # Continuation byte of a multibyte sequence.
      assert byte.startswith('10'), byte
      code_point_bits += byte[2:]
  return int(code_point_bits, 2)


def format_code_point_output(code_point_int):
  code_point_hex = hex(code_point_int)[2:].upper()
  code_point_hex = pad_hex(code_point_hex)
  character = chr(code_point_int)
  hex_col = 'U+{}:'.format(code_point_hex)
  return '{:9s} {} ({})'.format(hex_col, character, unicodedata.name(character))


def pad_hex(hex_input, pad_to=None):
  """Pad a hexadecimal string with leading zeros.
  If no pad_to is given, pad to the standard Unicode 4 or 6 digit length."""
  hex_len = len(hex_input)
  if pad_to is None:
    if hex_len <= 4:
      pad_to = 4
    else:
      pad_to = 6
  pad_chars = pad_to - hex_len
  return '0'*pad_chars + hex_input


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


####################   TESTS   ####################

UNICODE_STR = 'Iñtërnâtiônàlizætiøn☃💩'
UNICODE_CODE_POINTS = [73, 241, 116, 235, 114, 110, 226, 116, 105, 244, 110, 224, 108, 105, 122,
                       230, 116, 105, 248, 110, 9731, 128169]
UNICODE_CHAR_INTS = ['73', '241', '116', '235', '114', '110', '226', '116', '105', '244', '110',
                     '224', '108', '105', '122', '230', '116', '105', '248', '110', '9731', '128169']
UNICODE_CHAR_HEX = ['49', 'F1', '74', 'EB', '72', '6E', 'E2', '74', '69', 'F4', '6E', 'E0', '6C',
                    '69', '7A', 'E6', '74', '69', 'F8', '6E', '2603', '1F4A9']
UNICODE_CHAR_PADDED_HEX = ['0049', '00F1', '0074', '00EB', '0072', '006E', '00E2', '0074', '0069',
                           '00F4', '006E', '00E0', '006C', '0069', '007A', '00E6', '0074', '0069',
                           '00F8', '006E', '2603', '01F4A9']
UNICODE_CHAR_DESC = [
  'U+0049:   I (LATIN CAPITAL LETTER I)',
  'U+00F1:   ñ (LATIN SMALL LETTER N WITH TILDE)',
  'U+0074:   t (LATIN SMALL LETTER T)',
  'U+00EB:   ë (LATIN SMALL LETTER E WITH DIAERESIS)',
  'U+0072:   r (LATIN SMALL LETTER R)',
  'U+006E:   n (LATIN SMALL LETTER N)',
  'U+00E2:   â (LATIN SMALL LETTER A WITH CIRCUMFLEX)',
  'U+0074:   t (LATIN SMALL LETTER T)',
  'U+0069:   i (LATIN SMALL LETTER I)',
  'U+00F4:   ô (LATIN SMALL LETTER O WITH CIRCUMFLEX)',
  'U+006E:   n (LATIN SMALL LETTER N)',
  'U+00E0:   à (LATIN SMALL LETTER A WITH GRAVE)',
  'U+006C:   l (LATIN SMALL LETTER L)',
  'U+0069:   i (LATIN SMALL LETTER I)',
  'U+007A:   z (LATIN SMALL LETTER Z)',
  'U+00E6:   æ (LATIN SMALL LETTER AE)',
  'U+0074:   t (LATIN SMALL LETTER T)',
  'U+0069:   i (LATIN SMALL LETTER I)',
  'U+00F8:   ø (LATIN SMALL LETTER O WITH STROKE)',
  'U+006E:   n (LATIN SMALL LETTER N)',
  'U+2603:   ☃ (SNOWMAN)',
  'U+01F4A9: 💩 (PILE OF POO)'
]
UTF8_HEX = [
  ['49'],
  ['C3', 'B1'],
  ['74'],
  ['C3', 'AB'],
  ['72'],
  ['6E'],
  ['C3', 'A2'],
  ['74'],
  ['69'],
  ['C3', 'B4'],
  ['6E'],
  ['C3', 'A0'],
  ['6C'],
  ['69'],
  ['7A'],
  ['C3', 'A6'],
  ['74'],
  ['69'],
  ['C3', 'B8'],
  ['6E'],
  ['E2', '98', '83'],
  ['F0', '9F', '92', 'A9']
]
UTF8_INTS = [
  ['73'],
  ['195', '177'],
  ['116'],
  ['195', '171'],
  ['114'],
  ['110'],
  ['195', '162'],
  ['116'],
  ['105'],
  ['195', '180'],
  ['110'],
  ['195', '160'],
  ['108'],
  ['105'],
  ['122'],
  ['195', '166'],
  ['116'],
  ['105'],
  ['195', '184'],
  ['110'],
  ['226', '152', '131'],
  ['240', '159', '146', '169']
 ]


def join_list_of_lists(lol):
  out = []
  for l in lol:
    out.extend(l)
  return out


class UnicodeInputTest(unittest.TestCase):

  @classmethod
  def make_test(cls, type, format, input):
    def test(self):
      code_points = list(input_to_code_points(input, type, format))
      self.assertEqual(code_points, UNICODE_CODE_POINTS)
    return test

  test_data = (
    {'type':'chars', 'format':'hex', 'input':UNICODE_CHAR_PADDED_HEX},
    {'type':'chars', 'format':'hex', 'input':UNICODE_CHAR_HEX},
    {'type':'chars', 'format':'int', 'input':UNICODE_CHAR_INTS},
    {'type':'chars', 'format':'str', 'input':UNICODE_STR},
    {'type':'bytes', 'format':'hex', 'input':join_list_of_lists(UTF8_HEX)},
    {'type':'bytes', 'format':'int', 'input':join_list_of_lists(UTF8_INTS)},
  )

for data in UnicodeInputTest.test_data:
  test_function = UnicodeInputTest.make_test(data['type'], data['format'], data['input'])
  setattr(UnicodeInputTest, 'test_parse_{type}_{format}'.format(**data), test_function)


class UnicodeOutputTest(unittest.TestCase):

  @classmethod
  def make_test(cls, type, format, expected_output):
    def test(self):
      output_lines = list(code_points_to_output(UNICODE_CODE_POINTS, type, format))
      self.assertEqual(output_lines, expected_output)
    return test

  test_data = (
    {'type':'chars', 'format':'str', 'output':[UNICODE_STR]},
    {'type':'chars', 'format':'hex', 'output':[' '.join(UNICODE_CHAR_PADDED_HEX)]},
    {'type':'chars', 'format':'int', 'output':[' '.join(UNICODE_CHAR_INTS)]},
    {'type':'chars', 'format':'desc', 'output':UNICODE_CHAR_DESC},
    {'type':'bytes', 'format':'hex', 'output':[' '.join(bytes) for bytes in UTF8_HEX]},
    {'type':'bytes', 'format':'int', 'output':[' '.join(bytes) for bytes in UTF8_INTS]},
  )

for data in UnicodeOutputTest.test_data:
  test_function = UnicodeOutputTest.make_test(data['type'], data['format'], data['output'])
  setattr(UnicodeOutputTest, 'test_format_{type}_{format}'.format(**data), test_function)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
