#! /usr/bin/env python2

# Copyright (c) 2012 Victor Terron. All rights reserved.
# Institute of Astrophysics of Andalusia, IAA-CSIC
#
# This file is part of LEMON.
#
# LEMON is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import ConfigParser
import os.path

CONFIG_FILENAME = ".juicerc"
CONFIG_PATH = os.path.expanduser("~/%s" % CONFIG_FILENAME)

VIEW_SECTION = "view"
VIEW_SEXAGESIMAL = "sexagesimal"
VIEW_DECIMAL = "decimal"
PLOT_AIRMASSES = "airmasses"
PLOT_JULIAN = "julian_dates"
PLOT_MIN_SNR = "snr_threshold"

DEFAULT_VIEW_SEXAGESIMAL = True
DEFAULT_VIEW_DECIMAL = False
DEFAULT_PLOT_AIRMASSES = True
DEFAULT_PLOT_JULIAN = False
DEFAULT_PLOT_MIN_SNR = 100

# The color codes can use any of the following formats supported by matplotlib:
# abbreviations ('g'), full names ('green'), hexadecimal strings ('#008000') or
# a string encoding float on the 0-1 range ('0.75') for gray shades.

COLOR_SECTION = "colors"
DEFAULT_COLORS = dict(
    U="violet",
    B="blue",
    V="green",
    R="#ff4246",  # light red
    I="#e81818",  # dark red
    Z="cyan",
    Y="brown",
    J="yellow",
    H="pink",
    KS="orange",
    K="orange",
    L="0.75",  # light gray
    M="0.50",
)  # dark gray

# The options for how light curves are dumped to plain-text files
CURVEDUMP_SECTION = "curve-export"
DEFAULT_CURVEDUMP_OPTS = dict(
    dump_date_text=1,
    dump_date_julian=1,
    dump_date_seconds=1,
    dump_magnitude=1,
    dump_snr=1,
    dump_max_merr=1,
    dump_min_merr=1,
    dump_instrumental_magnitude=1,
    dump_instrumental_snr=1,
    decimal_places=8,
)


class Configuration(ConfigParser.SafeConfigParser):
    """Just a quite simple wrapper to automatically have the configuration
    file loaded at instantiation and written to disk with the update method"""

    DEFAULT_CONFIG = "\n".join(
        [
            "[%s]" % VIEW_SECTION,
            "%s = %d" % (VIEW_SEXAGESIMAL, DEFAULT_VIEW_SEXAGESIMAL),
            "%s = %d" % (VIEW_DECIMAL, DEFAULT_VIEW_DECIMAL),
            "%s = %d" % (PLOT_AIRMASSES, DEFAULT_PLOT_AIRMASSES),
            "%s = %d" % (PLOT_JULIAN, DEFAULT_PLOT_JULIAN),
            "%s = %d" % (PLOT_MIN_SNR, DEFAULT_PLOT_MIN_SNR),
            "",
            "[%s]" % COLOR_SECTION,
        ]
        + ["%s = %s" % (k, v) for k, v in DEFAULT_COLORS.iteritems()]
        + ["", "[%s]" % CURVEDUMP_SECTION]
        + ["%s = %s" % (k, v) for k, v in DEFAULT_CURVEDUMP_OPTS.iteritems()]
    )

    def __init__(self, path, update=True):
        """Parse a configuration file, creating and populating it with
        the default options in case 'path' does not exist"""

        ConfigParser.SafeConfigParser.__init__(self)

        if not os.path.exists(path):
            with open(path, "wt") as fd:
                fd.write(self.DEFAULT_CONFIG)

        self.read([path])
        self.path = path

    def color(self, letter):
        """ Return the color code to be used for a photometric filter """
        return self.get(COLOR_SECTION, letter.upper())

    def update(self):
        """ Write to disk the configuration file """
        with open(self.path, "wt") as fd:
            self.write(fd)

    # SafeConfigParser is an old-style class (does not support properties)
    def get_minimum_snr(self):
        """ Return the PLOT_MIN_SNR option in the VIEW_SECTION section """
        return self.getint(VIEW_SECTION, PLOT_MIN_SNR)

    def set_minimum_snr(self, snr):
        """ Set the value of the PLOT_MIN_SNR option in the VIEW_SECTION """
        self.set(VIEW_SECTION, PLOT_MIN_SNR, str(int(snr)))

    def dumpint(self, option):
        """ Coerce 'option' in the curves export section to an integer """
        return self.getint(CURVEDUMP_SECTION, option)

    def dumpset(self, option, value):
        """ Set 'option' to 'value' in the curves export section """
        self.set(CURVEDUMP_SECTION, option, str(value))
