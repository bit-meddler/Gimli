from . import TYPE_CAMERA_MC_PI
from .camera import Camera


class MoCapPi( Camera ):
    TYPE_INFO = TYPE_CAMERA_MC_PI
    DEFAULT_NAME = "Camera"

    def __init__( self, name, parent=None ):
        super( MoCapPi, self ).__init__( name, parent )