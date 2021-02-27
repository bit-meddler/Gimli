from . import TYPE_VIEW
from .camera import Camera


class View( Camera ):
    TYPE_INFO = TYPE_VIEW
    DEFAULT_NAME = "View"

    def __init__( self, name, parent=None ):
        super( View, self ).__init__( name, parent )