# 
# Copyright (C) 2016~2022 The Gimli Project
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

from . import TYPE_CAMERA_MC_PI
from .camera import Camera


class MoCapPi( Camera ):
    TYPE_INFO = TYPE_CAMERA_MC_PI
    DEFAULT_NAME = "Camera"

    def __init__( self, name, parent=None ):
        super( MoCapPi, self ).__init__( name, parent )

