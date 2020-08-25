""" Simple Timecode for simCam and simSync """


class SimpleTimecode( object ):

    def __init__( self, rate, multi=None, divisor=None ):
        self._qsm = 0
        self.rate = rate or 25
        self.multi = multi or 2
        self.divisor = divisor or 1.0

    def inc( self ):
        self._qsm +=1

    def toInts( self ):
        frames, subs = divmod( self._qsm, self.multi )
        secs, frames = divmod( frames, self.rate )
        mins, secs   = divmod( secs, 60 )
        hours, mins  = divmod( mins, 60 )
        return ( hours, mins, secs, frames, subs )

    def toString( self ):
        return "{}:{}:{}:{}.({})".format( *self.toInts() )

    def toBCDlist( self ):
        return self.toInts()[:-1]

    def setQSM( self, quanta ):
        self._qsm = quanta

    def setHMSF( self, hours, mins, secs, frames, subs=None, frm_cnt=False ):
        sub = subs or 0

        if( frm_cnt ):
            frame, sub = divmod( frames, self.multi )
        else:
            frame = frames

        t_secs = secs + (mins * 60) + (hours * 3600)
        t_frms = (t_secs * self.rate) + frame
        quanta = (t_frms * self.multi) + sub

        self._qsm = quanta

    def setString( self, tc_string ):
        toks = tc_string.split(":")

        for i in range( len( toks ) ):
            try:
                toks[i] = int(toks[i])
            except:
                toks[i] = 0

        while(len(toks)<4):
            toks.append(0)

        self.setHMSF( *toks, frm_cnt=False )
