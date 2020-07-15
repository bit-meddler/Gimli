"""
MoCap Camera / control unit communications
"""
class CameraTraits( object ):
    """ Object describing controllable traits of a camera. It holds GUI presentable data
        like a human readable name, description etc, and implementation specific data
        like how to set the value (which will be very camera dependant)
    """
    def __init__(self, name, default, min, max, dtype, value=None, units=None, human_name=None, desc=None ):
        # required
        self.name = name
        self.default = default
        self.min = min
        self.max = max
        self.dtype = dtype

        # interface sugar
        self.value = default if value is None else value
        self.units = "" if units is None else units
        self.human_name = name if human_name is None else human_name
        self.desc = "" if desc is None else desc

    def isValid( self, candidate ):
        """ Basic Validation, override for special cases """
        return ( (candidate <= self.max) and (candidate >= self.min) )