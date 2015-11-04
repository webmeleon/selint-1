#
#    Written by Filippo Bonazzi
#    Copyright (C) 2015 Aalto University
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Plugin to parse the global_macros file"""

from policysource.macro import M4Macro as M4Macro, M4MacroError as M4MacroError
import os
import re
import logging

MACRO_FILE = "global_macros"
LOG = logging.getLogger(__name__)


def expects(f):
    """Return True/False depending on whether the plugin can handle the file"""
    if f and os.path.basename(f) == MACRO_FILE:
        return True
    else:
        return False


def parse(f, tempdir, m4_freeze_file):
    """Parse the file and return a dictionary of macros.

    Raise ValueError if unable to handle the file."""
    # Check that we can handle the file we're served
    if not f or not expects(f):
        raise ValueError("{} can't handle {}.".format(MACRO_FILE, f))
    macros = {}
    # Parse the global_macros file
    macrodef = re.compile(r'^define\(\`([^\']+)\',\s+`([^\']+)\'')
    with open(f) as global_macros_file:
        for lineno, line in enumerate(global_macros_file):
            # If the line contains a macro, parse it
            n = macrodef.search(line)
            if n is not None:
                # Construct the new macro object
                name = n.group(1)
                expansion = n.group(2)
                try:
                    new_macro = M4Macro(name, expansion, f)
                except M4MacroError as e:
                    # Log the failure and skip
                    # Find the macro line and report it to the user
                    LOG.warning("%s", e.msg)
                    LOG.warning("Macro \"%s\" is at %s:%s", name, f, lineno)
                else:
                    # Add the new macro to the dictionary
                    macros[name] = new_macro
    return macros