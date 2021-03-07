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
TRAIT_TYPE_LIST  = "TRAIT_LIST"

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


TRAIT_LUT = {
    TRAIT_TYPE_INT   : TraitInt,
    TRAIT_TYPE_FLOAT : TraitFloat,
    TRAIT_TYPE_LIST  : TraitList,
}

def factory( type_info ):
    return TRAIT_LUT[ type_info ]