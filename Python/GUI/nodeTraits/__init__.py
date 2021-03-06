""" nodeTraits.py

    There could be categories of traits eg. relating to cameras, bones, media
    assets.  This might be a way to allow Camera CnC messages to be sifted and
    given special treatment.

    There will be Implementations of the following types of trait:
        0D:
            boolean
            enum
            int
            float
            String
            timecode
        1D:
            bitfield
            vec3i
            vec3f
            colour
            stringlist
        nD:
            matrix

    And this should be mirrored in GUI.widgets to provide interfaces to control
    the trait.  For any new Type, Implement at least TRAIT_STYLE_EDIT.
"""

# Type Registry
TRAIT_TYPE_NONE  = "TRAIT_NONE"
TRAIT_TYPE_INT   = "TRAIT_INT"
TRAIT_TYPE_FLOAT = "TRAIT_FLOAT"

# Interface Styles
TRAIT_STYLE_EDIT = 0
TRAIT_STYLE_KNOB = 1
TRAIT_STYLE_DIAL = 2


class AbstractNodeTrait( object ):
    """
        Object describing controllable trait of some parameter or attribute.
        It holds GUI presentable data like a human readable name, description,
        min and max values, and a "Castor" to get fom str to the correct type.

        'mode' flags are a combination of Read, Write, Advanced, eXclude
            Eg. "rwa" read, write, advanced; "rx" read only, not displayed
    """

    TYPE_INFO = TRAIT_TYPE_NONE

    def __init__(self, name, default, min, max,
                 value=None, units=None, units_short=None,
                 human_name=None, desc=None, mode=None, style=None ):

        # ToDo: Needs an 'unbounded' condition.
        # required
        self.name = name
        self.default = default
        self.min = min
        self.max = max

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

    # Virtuals ?????????? Not sure about these
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


TRAIT_STYLE_EDIT = 0
TRAIT_STYLE_KNOB = 1
TRAIT_STYLE_DIAL = 2

TRAIT_LUT = {
    TRAIT_TYPE_INT   : TraitInt,
    TRAIT_TYPE_FLOAT : TraitFloat,
}

def factory( type_info ):
    return TRAIT_LUT[ type_info ]