# 
# Copyright (C) 2016~2021 The Gimli Project
# This file is part of Gimli <https://github.com/bit-meddler/Gimli>.
#
# Gimli is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Gimli is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gimli.  If not, see <http://www.gnu.org/licenses/>.
#

""" nodeTraits.py

    There could be categories of traits eg. relating to cameras, bones, media
    assets.  This might be a way to allow Camera CnC messages to be sifted and
    given special treatment.

    There will be Implementations of the following types of trait:
        0D:
            x boolean
            x enum/list
            x int
            x float
            x String
              timecode
        1D:
              bitfield
              vec3i ?
              vec3f
              colour
              enum/list - multi select
        nD:
              matrix

    And this should be mirrored in GUI.widgets to provide interfaces to control
    the trait.  For any new Type, Implement at least TRAIT_STYLE_EDIT.
"""

# Type Registry
TRAIT_TYPE_NONE  = "TRAIT_NONE"
TRAIT_TYPE_INT   = "TRAIT_INT"
TRAIT_TYPE_FLOAT = "TRAIT_FLOAT"
TRAIT_TYPE_LIST  = "TRAIT_LIST"
TRAIT_TYPE_BOOL  = "TRAIT_BOOL"
TRAIT_TYPE_STR   = "TRAIT_STR"

# Interface Styles
TRAIT_STYLE_EDIT = 0
TRAIT_STYLE_KNOB = 1
TRAIT_STYLE_DIAL = 2

# Trait Categories
TRAIT_KIND_NORMAL = 0 # A normal trait, that needs to be recorded
TRAIT_KIND_SENDER = 1 # Additionally a Sender emits CnC Messages to the Arbiter


class AbstractNodeTrait( object ):
    """
        Object describing controllable trait of some parameter or attribute.
        It holds GUI presentable data like a human readable name, description,
        min and max values, and a "Castor" to get fom str to the correct type.

        'mode' flags are a combination of Read, Write, Advanced, eXclude
            Eg. "rwa" read, write, advanced; "rx" read only, not displayed
    """

    TYPE_INFO = TRAIT_TYPE_NONE

    def __init__(self, name, default, min, max, kind=TRAIT_KIND_NORMAL,
                 value=None, units=None, units_short=None,
                 human_name=None, desc=None, mode=None, style=None ):

        # ToDo: Needs an 'unbounded' condition.
        # required
        self.name = name
        self.default = default
        self.min = min
        self.max = max
        self.kind = kind

        # interface sugar
        self.value = value or default
        self.units = units or ""
        self.units_short = units_short or ""
        self.human_name = human_name or name
        self.desc = desc or ""
        self.mode = mode or "rw"
        self.style = style or TRAIT_STYLE_EDIT

    def isValid( self, candidate ):
        """ Basic Validation, override for special cases """
        return ( (candidate <= self.max) and (candidate >= self.min) )

    def isAdvanced( self ):
        return bool( "a" in self.mode )

    def isShowable( self ):
        return bool( "x" in self.mode )

    # Virtuals ?????????? Not sure about these, might be used in JSON parsing...
    def cast( self ):
        pass

    def toString( self, native_val ):
        pass

    def fromString( self, str_val ):
        pass


class TraitInt( AbstractNodeTrait ):
    TYPE_INFO = TRAIT_TYPE_INT

    def fromString( self, str_val ):
        return int( str_val )

    def toString( self, native_val ):
        return str( native_val )


class TraitFloat( AbstractNodeTrait ):
    TYPE_INFO = TRAIT_TYPE_FLOAT

    def fromString( self, str_val ):
        return float( str_val )

    def toString( self, native_val ):
        return str( native_val )


class TraitList( AbstractNodeTrait ):
    TYPE_INFO = TRAIT_TYPE_LIST

    def __init__(self, name, default, options, kind=TRAIT_KIND_NORMAL,
                 value=None, units=None, units_short=None,
                 human_name=None, desc=None, mode=None, style=None ):

        super( TraitList, self ).__init__( name, default, None, None, kind,
                                           value, units, units_short,
                                           human_name, desc, mode, style )
        self.options = options

    def isValid( self, candidate ):
        return bool( candidate in self.options )


class TraitBool( AbstractNodeTrait ):
    TYPE_INFO = TRAIT_TYPE_BOOL

    def __init__(self, name, default, kind=TRAIT_KIND_NORMAL,
                 value=None, units=None, units_short=None,
                 human_name=None, desc=None, mode=None, style=None ):

        super( TraitBool, self ).__init__( name, default, None, None, kind,
                                           value, units, units_short,
                                           human_name, desc, mode, style )

    def isValid( self, candidate ):
        return bool( candidate in self.options )


class TraitStr( AbstractNodeTrait ):
    TYPE_INFO = TRAIT_TYPE_STR

    def __init__(self, name, default, kind=TRAIT_KIND_NORMAL,
                 value=None, units=None, units_short=None,
                 human_name=None, desc=None, mode=None, style=None ):

        super( TraitStr, self ).__init__( name, default, None, None, kind,
                                          value, units, units_short,
                                          human_name, desc, mode, style )

    def isValid( self, candidate ):
        # Pluggable validation?
        return True


TRAIT_LUT = {
    TRAIT_TYPE_INT   : TraitInt,
    TRAIT_TYPE_FLOAT : TraitFloat,
    TRAIT_TYPE_LIST  : TraitList,
    TRAIT_TYPE_BOOL  : TraitBool,
    TRAIT_TYPE_STR   : TraitStr,
}

def factory( type_info ):
    return TRAIT_LUT[ type_info ]

