#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pt2025.py - PeakTech 2025 multimeter reader, print to STDOUT.

The digital multimeter PeakTech 2025 does have a RS232 USB interface.
There is a MS Windows software DMM - Digital Multimeter Software, but only for Windows.
The communication protocol is plain text and documented, see
https://www.peaktech.de/productdetail/kategorie/software/produkt/dmm-tool-basic.1034.html

Usage:
  pt2025.py [options] <COM-port-or-URL>
  pt2025.py --list
  pt2025.py -h | --help
  pt2025.py --version

Arguments:
  COM-port        COM port device, e.g., /dev/ttyUSB3, or URL.
                  (https://pythonhosted.org/pyserial/url_handlers.html#urls)
Options:
  -h --help       Show this screen.
  -j --json       JSON output.
  -l --list       List available ports.
  --version       Show version.
"""
##
## LICENSE:
##
## Copyright (C) 2020 Alexander Streicher
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
import os
import sys
import logging
from time import sleep
from codecs import open
from docopt import docopt
from json import dumps
import serial   ## https://pythonhosted.org/pyserial/pyserial.html#installation
import serial.tools.list_ports

__version__ = "1.0"
__date__ = "2020-01-25"
__updated__ = "2020-01-25"
__author__ = "Ixtalo"
__license__ = "AGPL-3.0+"
__email__ = "ixtalo@gmail.com"
__status__ = "Production"

DEBUG = 0
TESTRUN = 0
PROFILE = 0
__script_dir = os.path.dirname(os.path.realpath(__file__))

## check for Python3
if sys.version_info < (3, 0):
    sys.stderr.write("Minimum required version is Python 3.x!\n")
    sys.exit(1)


def show_ports():
    for port in serial.tools.list_ports.comports(include_links=True):
        print(port)


def decode(line):
    result = {}

    if len(line) != 14:
        logging.warning('Invalid byte stream input (wrong length %d)', len(line))
        return result

    try:
        sign = chr(line[0])
        digits = line[1:5].decode()
        decpos = int(chr(line[6]))  ## decimal position
        status_byte_1 = line[7]
        status_byte_2 = line[8]
        status_byte_3 = line[9]
        status_byte_4 = line[10]
        bar_graph = line[11]
    except IndexError as ex:
        logging.warning('Invalid line (%s)', ex)
        return result

    status = []
    if status_byte_1 & (2 ** 0): status.append('BPN')
    if status_byte_1 & (2 ** 1): status.append('HOLD')
    if status_byte_1 & (2 ** 2): status.append('REL')
    if status_byte_1 & (2 ** 3): status.append('AC')
    if status_byte_1 & (2 ** 4): status.append('DC')
    if status_byte_1 & (2 ** 5): status.append('AUTO')

    if status_byte_2 & (2 ** 2): status.append('BATT')
    if status_byte_2 & (2 ** 3): status.append('APO')
    if status_byte_2 & (2 ** 4): status.append('MIN')
    if status_byte_2 & (2 ** 5): status.append('MAX')
    if status_byte_3 & (2 ** 1): status.append('%')
    if status_byte_3 & (2 ** 2): status.append('Diode')
    if status_byte_3 & (2 ** 3): status.append('Continuity')

    unit = ''
    if status_byte_3 & (2 ** 4): unit = 'M'
    if status_byte_3 & (2 ** 5): unit = 'k'
    if status_byte_3 & (2 ** 6): unit = 'm'
    if status_byte_3 & (2 ** 7): unit = 'µ'

    mode = None
    if status_byte_4 & (2 ** 0): mode = '°F'
    if status_byte_4 & (2 ** 1): mode = '°C'
    if status_byte_4 & (2 ** 2): mode = 'F'
    if status_byte_4 & (2 ** 3): mode = 'Hz'
    if status_byte_4 & (2 ** 4): mode = 'hFE'
    if status_byte_4 & (2 ** 5): mode = 'Ω'
    if status_byte_4 & (2 ** 6): mode = 'A'
    if status_byte_4 & (2 ** 7): mode = 'V'

    if mode == 'F':
        if status_byte_2 & (2 ** 1): unit = 'n'

    if digits == '?0:?':
        value = 'NA'
    else:
        if decpos > 0:
            ## insert the decimal point at the specified position
            digits_a = list(digits)
            digits_a.insert(min(decpos, 3), '.')
        else:
            ## no decimal point
            digits_a = digits
        value = float(''.join(digits_a))

    logging.debug((sign, value, unit, mode, status))

    result = {
        'sign': sign,
        'value': value,
        'unit': unit,
        'mode': mode,
        'status': status
    }

    return result


def main():
    arguments = docopt(__doc__, version="pt2025 %s (%s)" % (__version__, __updated__))
    #print(arguments)

    port = arguments['<COM-port-or-URL>']
    list_ports = arguments['--list']
    as_json = arguments['--json']

    ## setup logging
    logging.basicConfig(
        level=logging.INFO if not DEBUG else logging.DEBUG,
        handlers=(logging.StreamHandler(sys.stderr),)
    )

    if list_ports:
        show_ports()
        return 0

    with serial.serial_for_url(port, baudrate=2400, timeout=1) as ser:
        while True:
            line = ser.readline()
            data = decode(line)
            data['status'] = ','.join(data['status'])
            if as_json:
                print(dumps(data))
            else:
                print(';'.join([str(v) for v in data.values()]))

    return 0


if __name__ == "__main__":
    if DEBUG:
        #sys.argv.append("-v")
        #sys.argv.append("--debug")
        # sys.argv.append("-h")
        pass
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = __file__ + '.profile.bin'
        cProfile.run('main()', profile_filename)
        with open("%s.txt" % profile_filename, "wb") as statsfp:
            p = pstats.Stats(profile_filename, stream=statsfp)
            stats = p.strip_dirs().sort_stats('cumulative')
            stats.print_stats()
        sys.exit(0)
    sys.exit(main())
