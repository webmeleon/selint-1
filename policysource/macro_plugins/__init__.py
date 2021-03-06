#
#    Written by Filippo Bonazzi
#    Copyright (C) 2016 Aalto University
#
#    This file is part of the policysource library.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 2.1 of
#    the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.
#
u"""Plugin module implementing file-specific macro parsing functions"""

# Necessary for Python 2/3 compatibility
from __future__ import absolute_import
from future.utils import itervalues

import os
from os import path
import sys
import keyword
import inspect
import logging
import policysource.macro


__all__ = []
__plugins__ = {}
for plugin_file in os.listdir(os.path.dirname(__file__)):
    if plugin_file.endswith(u".py"):
        module = os.path.splitext(plugin_file)[0]
        if not module.startswith(u'_') and not keyword.iskeyword(module):
            try:
                __import__(__name__ + u'.' + module)
            except:
                e = sys.exc_info()
                print(e)
            else:
                __all__.append(module)
                __plugins__[module] = locals()[module]
__all__.sort()


class M4MacroParser(object):

    u"""Class providing a m4 file parser.

    The class handles a list of specific macro files through a plugin
    architecture defined in the macro_plugin module."""

    def __init__(self, tmpdir=None, extra_defs=None):
        u"""Initialize plugin architecture.

        Find all plugins offered by macro_plugins, check that they implement
        the required methods and add them to the plugin dictionary.

        The parser will need a working directory. If the user does not supply a
        valid one, the parser will create a temporary directory, which will be
        destroyed with the object.
        If the user supplies a valid one, it will be up to the user to manage
        its lifecycle."""
        # Setup logger
        self.log = logging.getLogger(self.__class__.__name__)
        # Setup plugins
        self.plugins = {}
        for mod in __all__:
            plugin = __plugins__[mod]
            if (inspect.isfunction(plugin.expects)
                    and inspect.isfunction(plugin.parse)):
                self.plugins[mod] = plugin
                self.log.debug(u"Found plugin \"%s\"", mod)
            else:
                self.log.debug(u"Invalid plugin \"%s\"", mod)
        # Setup temporary directory passthrough
        self._tmpdir = tmpdir
        self._tmpdir_managed = False
        # Setup macro expander variable
        self.macro_expander = None
        self.extra_defs = extra_defs

    @property
    def tmpdir(self):
        u"""Get the temporary directory used by the parser."""
        return self._tmpdir

    @property
    def tmpdir_managed(self):
        u"""Check if the temporary directory is managed by the parser."""
        return self._tmpdir_managed

    def __get_parser__(self, single_file):
        u"""Find the appropriate parser for the given file."""
        for plg in itervalues(self.plugins):
            if plg.expects(single_file):
                return plg
        return None

    def __parse_file__(self, single_file, parser):
        u"""Parse a single file"""
        f_macros = None
        try:
            # Parse the file using the appropriate parser
            f_macros = parser.parse(single_file, self.macro_expander)
        except ValueError as e:
            # This really should not happen, since we have already
            # checked that the plugin accepts the file.
            # Log and skip
            self.log.warning(u"%s", e)
            self.log.warning(u"Could not parse \"%s\"", single_file)
        else:
            # File parsed successfully
            self.log.info(u"Parsed macros from \"%s\"", single_file)
        return f_macros

    def expects(self):
        u"""Returns a list of files that the parser can handle."""
        return self.plugins.keys()

    def parse(self, files):
        u"""Parses a list of files and returns a dictionary of macros."""
        # Setup the M4MacroExpander
        try:
            self.macro_expander = policysource.macro.M4MacroExpander(
                files, self.tmpdir, self.extra_defs)
        except policysource.macro.M4MacroExpanderError as e:
            self.log.error(u"%s", e.message)
            macros = None
        else:
            # Parse each file, using the macro expander
            macros = {}
            for single_file in files:
                # Find the appropriate parser
                parser = self.__get_parser__(single_file)
                if parser:
                    # We have a parser for this file
                    self.log.debug(u"Parsing macros from \"%s\" with plugin "
                                   u"\"%s\"", single_file, parser.__name__)
                    # Parse this file and obtain a dictionary of macros
                    f_macros = self.__parse_file__(single_file, parser)
                    if f_macros:
                        # Update the global macro dictionary
                        macros.update(f_macros)
                else:
                    # We don't have a parser for this file
                    self.log.debug(u"No parser for \"%s\"", single_file)
        return macros
