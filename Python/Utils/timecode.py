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

""" Simple Timecode for simCam and simSync """


class SimpleTimecode( object ):
    """
    Simple SMPTE Timecode object.  Internally a count of Quanta since Midnight.  This is a Strict SMPTE timecode, so
    we're unaware of timecodes greater than 30 fps.  When dealing with Video Signals of 50i, 59.97p or MoCap Data which
    could be an arbitrary frame count per second (usually 100, 119.88, 120, or 150) we use the multiplier and divisor
    properties.  A 60fps video is configured as r=30, m=2, d=1; 29.97fps is r=30, m=1, d=1.001.
    """

    # Divisors
    WHOLE = 1.0
    FRACTIONAL = 1.001

    def __init__( self, rate, multi=None, divisor=None ):
        """

        Args:
            rate: (int) SMPTE Timecoe Rate (24, 25, or 30)
            multi: (int) Multiplier, to get 60 or 120 fps for example
            divisor: (float) 1.0 or 1.001 to consider fractional frame rates (23.976, 29,97)
        """
        self._qsm = 0
        self.rate = rate or 25
        self.multi = multi or 1
        self.divisor = divisor or SimpleTimecode.WHOLE

    def inc( self, amt=1 ):
        """
        Increment timecode by one quanta, or given amount.
        Args:
            amt: (int) Amount to increment by (default 1 Quanta)
        """
        self._qsm +=amt

    def toInts( self, frm_cnt=False ):
        """
        Get current timecode as list of ints.
        Args:
            frm_cnt: (bool) return a frame count, rather than frames, and subframes
        Returns:
            timecode: (tuple) Timecode as list of ints
        """
        frames, subs = divmod( self._qsm, self.multi )
        secs, frames = divmod( frames, self.rate )
        mins, secs   = divmod( secs, 60 )
        hours, mins  = divmod( mins, 60 )

        if( frm_cnt ):
            frames = (frames * self.multi) + subs
            subs = 0

        return ( hours, mins, secs, frames, subs )

    def toString( self, frm_cnt=False ):
        """
        Get current timecode as a string
        Args:
            frm_cnt: (bool) return a frame count, rather than frames and subframes
        Returns:
            timecode: (str) The timecode
        """
        if( frm_cnt ):
            return "{:02}:{:02}:{:02}:{:02}".format( *self.toInts(True) )
        else:
            return "{:02}:{:02}:{:02}:{:02}.({})".format( *self.toInts() )

    def toBCDlist( self ):
        """
        Get the timecode as a list of ints, striuct SMPTE (no subs, no frames>30)
        Returns:
            timecode: (tuple) The SMPTE Timecode
        """
        return self.toInts()[:-1]

    def setQSM( self, quanta ):
        """
        Set as offset from midnight
        Args:
            quanta: (int) Quanta since midnight
        """
        self._qsm = quanta

    def setHMSF( self, hours, mins, secs, frames, subs=None, frm_cnt=False ):
        """
        Set from integers.
        Args:
            hours: (int)
            mins: (int)
            secs: (int)
            frames: (int)
            subs: (int)
            frm_cnt: (bool) Ignore subs, and interpret frames as a frame count
        """
        sub = subs or 0

        if( frm_cnt ):
            frame, sub = divmod( frames, self.multi )
        else:
            frame = frames

        t_secs = secs + (mins * 60) + (hours * 3600)
        t_frms = (t_secs * self.rate) + frame
        quanta = (t_frms * self.multi) + sub

        self._qsm = quanta

    def setString( self, tc_string, frm_cnt=False ):
        """
        Set from a Timecode string, agnostic to DF/NDF - BUT THIS IS NOT RESPECTED IN THE REPRESENTATION!
        Args:
            tc_string: (str) A String like "13:25:33;22", "13:25:33:22.1", or "13:25:33:44" if frm_cnt is set
        """
        toks = tc_string.replace(";",":").replace(".",":").split(":")

        for i in range( len( toks ) ):
            try:
                toks[i] = int( toks[i] )
            except:
                toks[i] = 0

        while( len( toks ) < 4 ):
            toks.append( 0 )

        if( frm_cnt ): # force back to SMPTE
            toks[3], toks[4] = divmod( toks[3], self.multi )

        self.setHMSF( *toks, frm_cnt=frm_cnt )
