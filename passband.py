#! /usr/bin/env python2
# encoding:UTF-8

# Copyright (c) 2012 Victor Terron. All rights reserved.
# Institute of Astrophysics of Andalusia, IAA-CSIC
#
# This file is part of LEMON.
#
# LEMON is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


""" The class Passband encapsulates a photometric filter. The supported systems
are Johnson, Cousins, Gunn, SDSS, 2MASS, Strömgren and H-alpha, but photometric
letters, designating a particular section of the electromagnetic spectrum, may
also be given without a system (for example, 'V'). The main advantage that this
class offers is that it makes it possible to recognize as equal filters written
differently but that are indeed the same (e.g., 'Gunn r' and 'rGunn'). Also,
filters can be sorted according to their position in the spectrum — otherwise,
if the names of the filters were simply sorted lexicographically, 'Johnson I',
for example, would go before 'Johnson V', even although the right order is the
other way around (as V has a shorter wavelength than I).

In addition to the built-in photometric systems, user-defined (custom) filters
are supported via the CONFIG_PATH configuration file, defined as options in the
CUSTOM_SECTION section. Please refer to the documentation of the Passband class
for further information.

"""

import ConfigParser
import itertools
import os.path
import random
import re
import string

# LEMON module
from setup import CONFIG_PATH

JOHNSON = 'Johnson'
COUSINS = 'Cousins'
HARRIS = 'Harris'
GUNN = 'Gunn'
SDSS = 'SDSS'
TWOMASS = '2MASS'
STROMGREN = 'Strömgren'
HALPHA = 'Halpha'
UNKNOWN = 'Unknown'
CUSTOM = 'Custom'

CUSTOM_SECTION = 'custom_filters'

def load_custom_filters(path = CONFIG_PATH):
    """ Load the name and description of the user custom photometric filters.

    Parse a ConfigParser configuration file, CONFIG_PATH by default, and return
    a generator that yields two-element tuples, (option, value), for each of
    the options in the section CUSTOM_SECTION. Each option is expected to be
    the name of a custom photometric filter (e.g., 'NO'), and the associated
    value the description that str(Passband) must show (e.g., 'Blank filter').
    The case of the options is preserved. In case the file does not exist or
    CUSTOM_SECTION is not present or empty, nothing is returned.

    """

    parser = ConfigParser.SafeConfigParser()
    parser.optionxform = str
    if os.path.exists(path):
        parser.read([path])
    # (name, description) pairs for each filter
    if parser.has_section(CUSTOM_SECTION):
        for item in parser.items(CUSTOM_SECTION):
            yield item

# The case-insensitive regular expression that the name of a filter must match
# in order to consider that it belongs to each photometric system. For example,
# 'rGunn' can be identified as a filter of the Gunn photometric system because
# re.search(REGEXPS[GUNN], 'rGunn', re.IGNORECASE) produces a match.

REGEXPS = {JOHNSON : 'Johnson|John',
           HARRIS : 'Harris|Har',
           COUSINS : 'Cousins?|Cous?',
           GUNN : 'Gunn|Gun',
           SDSS : "SDSS|'|prime|Sloan",
           TWOMASS : '2MASS|2M',
           STROMGREN : 'Strömgren|Stromgren|Stroemgren|Stro',
           HALPHA : 'H(a(lpha)?)?\d{4}'}

# Map each custom filter to its description. For example:
# {'REROS': 'R (EROS-2 survey)', 'NO': 'Blank Filter'}
CUSTOM_FILTERS = dict(load_custom_filters())

class NonRecognizedPassband(ValueError):
    """ Raised when the photometric filter cannot be identified """

    ERROR_NOTE = ("If this is a legitimate filter name, and you think LEMON "
                  "should be able to recognize it, please let us know at "
                  "[http://github.com/vterron/lemon/issues]. In the meantime, "
                  "you can define your own filters in the {} file, as options "
                  "of the [{}] section. For an example, see "
                  "[https://github.com/vterron/lemon/issues/14#issuecomment-"
                  "43504285").format(CONFIG_PATH, CUSTOM_SECTION)

    def __init__(self, name, path = None, keyword = None):
        """ Instantiation method for the NonRecognizedPassband class.

        The 'name' argument is the name of the filter whose photometric system
        could not be identified. If applicable, the path to the FITS image and
        keyword from which the filter was read may be given in the 'path' and
        'keyword' keyword arguments, respectively, so that they are also
        included in the error message.

        """

        self.name = name
        self.path = path
        self.keyword = keyword

    def __str__(self):
        """ Return the error message of the NonRecognizedPassband exception.

        If the the FITS image and keyword the unrecognized photometric filter
        was read from have been given, they are also included in the message.
        Also, users are requested to open a ticket on the GitHub issue tracker
        if they come across a filter incorrectly considered unrecognizable.

        """

        msg = "cannot identify the photometric system of filter '%s'"

        details = []
        if self.path:
            details.append("FITS image = '%s'" % self.path)
        if self.keyword:
            details.append("keyword = '%s'" % self.keyword)
        if details:
            msg += " (%s). " % ', '.join(details)
        else:
            msg += ". "

        return msg  % self.name + self.ERROR_NOTE


class InvalidPassbandLetter(NonRecognizedPassband):
    """ Raised if the letter of the filter does not belong to the system.

    For example, this exception should be raised if we come across something
    like 'Johnson Z', as Z is not a filter of the Johnson photometric system
    (UBVRIJHKLMN).

    """

    def __init__(self, name, system):
        self.name = name
        self.system = system

    def __str__(self):
        msg = "'%s' is not a letter of the %s photometric system. "
        return msg % (self.name, self.system) + self.ERROR_NOTE


class Passband(object):
    """ Encapsulates a passband (or filter) of the photometric system.

    The photometric systems currently supported are:

    - Johnson (1965): UBVRI(JHKLMN)
    - Harris (USNO) : UBVRI
    - Cousins (1976): RI
    - Strömgren and Crawford (1956): uvbyHbeta
    - Thuan and Gunn (1976): uvgr
    - Sloan DSS (1996): ugriz
    - 2MASS: J H Ks
    - H-alpha

    The information of these filters has been taken from the useful Asiago
    Database on Photometric Systems (http://ulisse.pd.astro.it/Astro/ADPS/).
    The Passband class also supports filters whose system is not known, such
    as 'V' — we do not know whether it belongs to the Johnson, Strömgren or
    Gunn system, but we can still work with it.

    In addition to the above, user-defined (custom) photometric filters are
    supported via the CONFIG_PATH configuration file. They may be defined as
    options in the CUSTOM_SECTION section. For example:

    [custom_filters]
    BEROS = B (EROS-2 survey)
    REROS = R (EROS-2 survey)
    NO = Blank Filter

    This defines three custom filters: 'BEROS', 'REROS' and 'NO' (the filter
    names that can be found in the headers of your FITS files). The associated
    values are their descriptions, used by both repr() and str() to return a
    user-friendly string representation. A filter name is custom if it compares
    equal (case-insensitively) to one of these definitions. Regular expressions
    are not allowed. In fact, all non-alphanumerics are backslashed, so regexp
    metacharacters in it are ignored

    """

    SYSTEM_LETTERS = {JOHNSON : tuple('UBVRIJHKLMN'),
                      COUSINS : tuple('VRI'),
		      HARRIS : tuple('UBVRI'),
                      GUNN : tuple('UVGR'),
                      SDSS : tuple('UGRIZ'),
                      TWOMASS : ('J', 'H', 'KS'),
                      STROMGREN : ('U', 'V', 'B', 'Y', 'NARROW', 'N', 'WIDE', 'W')}

    ALL_SYSTEMS = set(SYSTEM_LETTERS.keys() + [HALPHA, CUSTOM])
    ALL_LETTERS = set(itertools.chain(*SYSTEM_LETTERS.itervalues()))

    # The order of the photometric letters, regardless of the system
    LETTERS_ORDER = ['U', 'B', 'NARROW', 'WIDE', 'V', 'G', 'R', 'I',
                     'Z', 'Y', 'J', 'H', 'KS', 'K', 'L', 'M', 'N']

    @staticmethod
    def _identify_system(name):
        """ Return the photometric system to which a filter belongs.

        Loop over the regular expressions stored as values of the REGEXP
        module-level dictionary, returning the key of the first to which 'name'
        matches. For example, Passband._identify_system('rGunn') returns GUNN
        because re.search(REGEXPS[GUNN], 'rGunn', re.IGNORECASE) produces a
        match. Returns UNKNOWN if none of the regexps matches 'name'.

        """

        for system, regexp in REGEXPS.iteritems():
            if re.search(regexp, name, re.IGNORECASE):
                return system
        else:
            return UNKNOWN

    @classmethod
    def _parse_halpha_filter(cls, name):
        """ Extract the wavelength from the name of a H-alpha filter.

        Extract the wavelength from a H-alpha photometric filter name following
        the pattern 'Hxxxx(/yy)?', where xxxx is the filter wavelength and yy,
        optionally, its bandwidth. 'H' may also be 'Ha' or 'Halpha'; matching
        is case insensitive. The wavelength *must* be a four-digit number.
        Returns None if there is no match.

        """

        regexp = ".*H(a(lpha)?)?(?P<wavelength>\d{4})(?P<bandwidth>/\d{2})?.*"
        match = re.match(regexp, name, re.IGNORECASE)
        if match is not None:
            return match.group('wavelength')

    @classmethod
    def _parse_name(cls, name, system):
        """ Extract the letter from the name of a photometric filter.

        Parse the name of a Johnson, Cousins, Gunn, SDSS, 2MASS or Strömgren
        filter (that is, all the photometric systems except for H-alpha and
        user-defined filters) and extract the letter. Whitespaces and any other
        separators, such as dashes and underscores, *must* have been removed
        from the name of the filter, as the regular expressions that match the
        photometric systems do not take them into account.

        The system of the filter must be specified in the 'system' argument,
        and match one of the module-level variables that define the different
        systems (such as JOHNSON or COUSINS).

        The NonRecognizedPassband exception is raised if the photometric letter
        cannot be determined, and InvalidPassbandLetter if, although correctly
        extracted, the letter does not belong to the photometric system (e.g.,
        Johnson Z does not exist).

        """

        if system == HALPHA:
            msg = "Passband._parse_name() does not support H-alpha filter " \
                  "names. Use Passband._parse_halpha_filter() instead"
            raise ValueError(msg)

        def fix_stromgren_letter(name):
            """ A couple of cosmetic fixes needed by the Strömgren filters.

            Two of the filters of the Strömgren photometric system are 'HB
            narrow' and 'HB wide'. The 'HB' part is entirely optional and can
            be written in several different ways (such as 'H B' or 'H Beta').
            Remove it from the name of the filter, and in case what is left is
            'N' or 'W' (short for 'NARROW' and 'WIDE', respectively), replace
            them with the longer version. Returns the result in uppercase.

            """

            name = re.sub("H[\-\s]*B(ETA)?", '', name.upper())
            if name == 'N':
                return 'NARROW'
            elif name == 'W':
                return 'WIDE'
            return name

        # Remove from the name of the filter, which is converted to uppercase,
        # the leftmost non-overlapping occurrences of the regular expression of
        # the photometric system. This means that e.g., 'vJohnson' returns 'V'.
        # We cannot use flags = re.IGNORECASE for Python 2.6 compatibility.
        letter = re.sub(REGEXPS[system].upper(), '', name.upper()).upper()

        # Strömgren subtleties
        if system == STROMGREN:
            letter = fix_stromgren_letter(letter)

        # There should only be one letter
        if len(letter.split()) != 1:
            raise NonRecognizedPassband(name)

        # Make sure that the letter belongs to the photometric system. If not,
        # InvalidPassbandLetter is raised if it belongs to a different system
        # (for example, "Gunn N") or at least is a valid letter ("Johnson A").
        # Otherwise, raise NonRecognizedPassband.

        elif letter not in cls.SYSTEM_LETTERS[system]:
            all_letters = set(itertools.chain(cls.ALL_LETTERS,
                                              string.ascii_uppercase))
            if letter in all_letters:
                raise InvalidPassbandLetter(letter, system)
            else:
                raise NonRecognizedPassband(name)
        else:
            return letter

    def __init__custom(self, filter_name):
        """ Instantiate a custom photometric filter.

        This method is called at the beginning of __init__() in order to check
        whether 'filter_name' corresponds to a custom photometric filter, those
        defined in the CONFIG_PATH ConfigParser configuration file, section
        CUSTOM_SECTION. If that is the case, this method sets the value of the
        'letter' and 'system' attributes and returns True (which indicates to
        __init__() that the object was been successfully initialized and there
        is nothing else that must be done). Otherwise, False is returned.

        Note that, while 'system' is (not surprisingly) set to CUSTOM, 'letter'
        is assigned the value of the description of the filter. This is, well,
        undeniably confusing, but there is reason to our madness: it allows us
        to consistently use the same attributes for all the Passband objects,
        regardless of what type of photometric filter they are.

        A photometric filter is considered custom if 'filter_name' matches the
        name *or* the description of one of the custom filters defined in the
        configuration file. Regular expressions are not allowed (in fact, all
        non-alphanumerics are backslashed, so regexp metacharacters in it are
        ignored). The two strings must be equal, although the comparison is
        case-insensitive.

        The reason why filter names are allowed to match the description is so
        that eval(repr(Passband)) works. For example, if the configuration file
        defines 'NO' as a custom filter, with the associated description 'Blank
        Filter', repr(Passband('No')) returns 'Passband('Blank Filter') and
        str() 'Blank Filter'. Since we may want to create a Passband object
        from that string representation, with eval(), we need to match it too.

        """

        for name, description in CUSTOM_FILTERS.iteritems():
            regexp = '|'.join(re.escape(x) for x in [name, description])
            if re.match(regexp, filter_name, re.IGNORECASE):
                self.letter = description
                self.system = CUSTOM
                return True
        else:
            return False

    def __init__(self, filter_name):
        """ Instantiation method for the Passband class.

        Receive the name of the photometric filter and automatically extract
        the system and letter (or wavelength, if it is H-alpha). The regular
        expressions that identify them are quite flexible and should allow for
        most, if not all, of the ways in which the name of a filter may be
        written, assuming sane astronomers, under normal circumstances.

        If that is not your case, you may define your own photometric filters
        in the CONFIG_PATH configuration file, listing them as options of the
        CUSTOM_SECTION section. For example, a line such as 'NO = Blank Filter'
        defines the 'NO' (case-insentitive) filter, with 'Blank Filter' as it
        associated description. The former should be the filter name that you
        expect to come across in your FITS images, while the description is
        what both repr() and str() use to return a string representation.

        The NonRecognizedPassband exception is raised if the photometric letter
        cannot be determined, and InvalidPassbandLetter if, although correctly
        extracted, the letter does not belong to the photometric system (e.g.,
        Johnson Z does not exist).

        """

        # User-defined (custom) photometric filters are a particular case and
        # have their own initializer, __init__custom(). It returns True if the
        # filter name was identified as belonging to a custom filter and the
        # object therefore initialized, so we can exit from __init__().
        if self.__init__custom(filter_name):
            return

        # E.g., from "_Johnson_(V)_" to "JohnsonV"
        name = re.sub('[\s\-_\(\)]', '', filter_name)

        system = self._identify_system(name)

        if system == UNKNOWN:
            letter = name.strip().upper()
            if letter not in self.ALL_LETTERS:
                raise NonRecognizedPassband(filter_name)

        elif system == HALPHA:
            letter = self._parse_halpha_filter(name)
            if letter is None:
                raise NonRecognizedPassband(filter_name)

        else:
            letter = self._parse_name(name, system)

        self.system = system
        self.letter = letter

    @classmethod
    def all(cls):
        """ Return (almost) all of the filters this class encapsulates.

        Return a list with a Passband object for each photometric system and
        the corresponding letters contained in Passband.SYSTEM_LETTERS. That
        is, for each supported photometric system (Johnson, Cousins, Gunn,
        etc), a Passband object is created for each of the letters defined by
        it (e.g., in the case of Johnson, UBVRIJHKLMN). Although user-defined
        filters do not have letters, they are also included. H-alpha filters
        are not, however, as they do not choose a letter from among a discrete
        set, but instead use their wavelength.

        """

        pfilters = []
        for system, letters in cls.SYSTEM_LETTERS.iteritems():
            for letter in letters:
                # Avoid duplicates: 'N' and 'W' are short for 'narrow' and
                # 'wide', respectively, so they are indeed the same filter.
                if system == STROMGREN and letter in ['N', 'W']:
                    continue
                name = "%s %s" % (system, letter)
                pfilters.append(name)

        # User-defined photometric filters
        for name in CUSTOM_FILTERS.iterkeys():
            pfilters.append(name)

        return [Passband(x) for x in pfilters]

    def __str__(self):
        """ The 'informal' string representation.

        Return a nice string representation of the photometric filter, such as
        'Johnson V', 'Cousins R', 'Gunn r', 'SDSS g'', '2MASS Ks', 'Stromgren
        y', 'H-alpha 6317' and, if the system is not known, simply 'V'. For
        user-defined photometric filters, their description is returned. Note
        that the letter of the Gunn, Strömgren and SDSS filters is written in
        lowercase, and that an apostrophe is affixed to the latter. Strömgren
        is written as 'Stromgren', removing the umlaut, so that the returned
        string object is always ASCII-compatible.

        """

        system = self.system
        letter = self.letter

        if letter == 'KS':
             letter = 'Ks'

        # User-defined filters have their description stored in the 'letter'
        # attribute, which is undeniably confusing. The reason for this is that
        # it allows us to consistently use the same attributes ('system' and
        # 'letter') for all the Passband objects, regardless of what type of
        # photometric filter they are.
        if system in [CUSTOM, UNKNOWN]:
            return letter

        if system in (GUNN, SDSS):
            letter = letter.lower()

        if system == STROMGREN:
            system = "Stromgren"
            if letter in ('NARROW', 'WIDE'):
                letter = "HB " + letter.lower()
            else:
                letter = letter.lower()
        elif system == SDSS:
            letter = "%s'" % letter
        elif system == HALPHA:
            system = 'Ha'

        return "%s %s" % (system, letter)

    def __repr__(self):
        """ The unambiguous string representation """
        return "%s(\"%s\")" % (self.__class__.__name__, self)

    def __cmp__(self, other):
        """ Called by comparison operations if rich comparison is not defined.

        Returns a negative integer is self < other, zero if self == other, and
        a positive integer if self > other. Passband objects are sorted by the
        photometric letter (for example, Johnson B < Johnson V < Johnson I),
        and lexicographically by the name of the system in case the letters
        are the same (e.g., Cousins I < Johnson I < SDSS i').

        There are two exceptions to this rule: first, user-defined (custom)
        filters are always smaller than the rest of photometric filters, and
        compared between them lexicographically, by their description. Second,
        H-alpha filters: they are compared by their wavelength, and are always
        greater than the filters of other photometric systems (for example,
        2MASS Ks < Johnson N < H-alpha 6563 < H-alpha 6607).

        """

        # If both filters are custom, sort them lexicographically, by their
        # description (stored in the 'letter' attribute). Custom filters are
        # smaller than all the other filters.

        self_custom  =  self.system == CUSTOM
        other_custom = other.system == CUSTOM

        if self_custom or other_custom:
            if self_custom and other_custom:
                return cmp(self.letter, other.letter)
            else:
                # Note: int(True) == 1; int(False) == 0
                return int(other_custom) - int(self_custom)

        # If both filters are H-alpha, sort by their wavelength.
        # H-alpha filters are greater than all the other filters

        self_alpha =   self.system == HALPHA
        other_alpha = other.system == HALPHA

        if self_alpha or other_alpha:
            if self_alpha and other_alpha:
                return int(self.letter) - int(other.letter)
            else:
                return int(self_alpha) - int(other_alpha)

        # If the photometric systems are different, sort by letter.
        # If the letters are the same, sort by system (lexicographically)
        self_index  = self.LETTERS_ORDER.index(self.letter)
        other_index = self.LETTERS_ORDER.index(other.letter)

        if self_index != other_index:
            return self_index - other_index
        else:
            return cmp(self.system, other.system)

    def __hash__(self):
        return hash((self.system, self.letter))

    @classmethod
    def random(cls):
        """ Return a random Passband object.

        Choose a random photometric system (Johnson, Cousins, Gunn, SDSS,
        2MASS, Strömgren or H-alpha) and one of the letters that the system
        defines. H-alpha filters do not have a letter, but wavelength: for
        this, a random integer in the range [6000, 7000] is used.

        """
        MIN_WAVELENGTH = 6000
        MAX_WAVELENGTH = 7000

        keys = cls.SYSTEM_LETTERS.keys() + [HALPHA]
        if CUSTOM_FILTERS:
            keys += [CUSTOM]

        system = random.choice(keys)
        if system == CUSTOM:
            name = random.choice(CUSTOM_FILTERS.keys())
            return cls(name)
        elif system == HALPHA:
            wavelength = random.randrange(MIN_WAVELENGTH, MAX_WAVELENGTH)
            return cls("%s %04d" % (system, wavelength))
        else:
            letter = random.choice(cls.SYSTEM_LETTERS[system])
            return cls("%s %s" % (system, letter))

    def different(self):
        """ Return a random Passband object different than this one.

        The returned Passband object does not compare equal to 'self'. This
        means that it has a different photometric system or, in case these are
        equal, its letter (or wavelength, for H-alpha filters) is different.

        """

        while True:
            passband = self.random()
            if passband != self:
                return passband

