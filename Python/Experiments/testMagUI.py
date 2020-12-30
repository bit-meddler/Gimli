from PySide2 import QtGui, QtWidgets, QtCore
import sys

class TimeSlider( QtWidgets.QAbstractSlider ):

    FONT_SIZE = 12
    
    GRATICS = (
        # resolution, (Mjr Tick frequency, Minor Tick Frequency)
        # single frame resolution
        (    1, (  1,  0)),
        # Tiny resolution
        (   50, ( 10,  1)),
        # Hundreds of frames
        (  100, ( 25,  5)),
        (  200, ( 50, 10)),
        (  400, ( 75, 20)),
        # thousands of frames
        ( 1000, (200, 50)),
        # 1e5s
        
    )
        
    def __init__(self):
        super( TimeSlider, self ).__init__()
        self.setOrientation( QtCore.Qt.Horizontal )

        self._font = QtGui.QFont( "Decorative", 8 )
        self._font.setPixelSize( self.FONT_SIZE )

        self._dragging = False # dragging the Playhead
        self.lastValue = -1
        
        font_metrics = QtGui.QFontMetrics( self._font )
        self._font_h = font_metrics.height()

        self._pref_height = self._font_h * 3
        self.setMinimumWidth( 70 )
        self.setMinimumHeight( self._pref_height )

        self._playhead_width = 10
        self._px_per_frame = 10.0
        self._grat_cadence = ( 1, 0 )
        
        self._grat_mjr_height = int( self._font_h * 1.25 )
        self._grat_mnr_height = int( self._font_h * 0.90 )
        self._grat_mjr_width = 2
        self._grat_mnr_width = 1
        
        self._playhead = QtCore.QRect( 0, 0, self._playhead_width, self._pref_height )

        
    def paintEvent( self, painter_event ):
        mn, mx = self.minimum(), self.maximum()
        w, h   = self.width(), self.height()
        val    = self.value()
        ph_pos = int( val * self._px_per_frame )
        mx_pos = int( mx * self._px_per_frame )

        palette = self.palette()
        
        painter = QtGui.QPainter()

        painter.begin( self )
        # clear
        painter.setFont( self._font )
        painter.setPen( palette.color( palette.Active, palette.Window ) )
        painter.setBrush( palette.color( palette.Active, palette.Window ) )
        painter.drawRect( self.rect() )

        # Playhead
        painter.setPen( palette.color( palette.Active, palette.Highlight ) )
        painter.setBrush( palette.color( palette.Active, palette.Highlight ) )
        self._playhead.moveLeft( ph_pos )
        painter.drawRect( self._playhead )

        # graticules
        mjr, mnr = self._grat_cadence
        painter.setPen( palette.color( palette.Active, palette.Mid ) ) # Graticule Ticks & Text
        text_area = QtCore.QRect(0, 0, mjr*int( self._px_per_frame ), self._grat_mjr_height )

        # draw first tick exactly on minimum
        tx_flags = QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
        painter.drawLine( 0, h, 0, h-self._grat_mjr_height )
        painter.drawText( text_area, tx_flags, str( mn ) )

        # Draw the Graticules
        tx_flags = QtCore.Qt.AlignTop | QtCore.Qt.AlignCenter

        anchor_mjr = ((mn // mjr) + 1) * mjr
        
        if( mnr > 0 ):
            # work back to "Zero"
            next_mnr = anchor_mjr - mnr
            while( next_mnr > mn ):
                delta = int( next_mnr * self._px_per_frame )
                painter.drawLine( delta, h, delta, h-self._grat_mnr_height )
                next_mnr -= mnr
        
        # work forwards from the anchor
        next_mjr = anchor_mjr
        thw = int( text_area.width() / 2 )
        text_area.translate( -thw, 0 )
        while( next_mjr < mx ):
            delta = int( next_mjr * self._px_per_frame )
            text_area.moveLeft( delta - thw )
            painter.drawLine( delta, h, delta, h-self._grat_mjr_height )
            painter.drawText( text_area, tx_flags, str( next_mjr ) )
            next_mnr = next_mjr - mnr
            next_mjr += mjr
            # do the minors up to next_mjr or mx
            while( next_mnr < next_mjr ):
                delta = int( next_mnr * self._px_per_frame )
                painter.drawLine( delta, h, delta, h-self._grat_mnr_height )
                next_mnr += mnr
            
        # draw last tick exactly on maximum
        tx_flags = QtCore.Qt.AlignTop | QtCore.Qt.AlignRight
        if( mx_pos >= w ):
            mx_pos = w -1
        text_area.moveTopRight( QtCore.QPoint( mx_pos, 0 ) )
        painter.drawLine( mx_pos, h, mx_pos, h-self._grat_mjr_height )
        painter.drawText( text_area, tx_flags, str( mx ) )

        # Finally draw the Playhead Decoration
        val_txt = str( val )
        font_metrics = QtGui.QFontMetrics( self._font )
        val_w = font_metrics.width( val_txt )
        text_area.moveBottomLeft( QtCore.QPoint( ph_pos, h - 1 ) )
        text_area.setWidth( val_w + 1 )
        
        painter.setPen( palette.color( palette.Active, palette.Highlight ) )
        painter.setBrush( palette.color( palette.Active, palette.Highlight ) )

        if( ph_pos + val_w > mx_pos ):
            # write on LHS
            tx_flags = QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight
            text_area.moveRight( ph_pos - 1 )
            painter.setPen( palette.color( palette.Active, palette.Text ) )
        else:
            tx_flags = QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft
            painter.drawRect( text_area )
            painter.setPen( palette.color( palette.Active, palette.HighlightedText ) )
            
        painter.drawText( text_area, tx_flags, val_txt )

        painter.setPen( palette.color( palette.Active, palette.Link ) )
        painter.drawLine( ph_pos, 0, ph_pos, h )
        # Done
        painter.end()

        
    def resizeEvent( self, sz_event ):
        self.updateMetrics()
        super( TimeSlider, self ).resizeEvent( sz_event )
        
    def updateMetrics( self ):
        # calculate scale of visible range and playhead size
        w, h = self.width(), self.height()
        mn, mx = self.minimum(), self.maximum()
        span = mx - mn
        self._px_per_frame = float(w) / span
        self._playhead_width = int( self._px_per_frame )
        if( self._px_per_frame < 2.0 ):
            # Todo: will need to force play head width to be visible
            self._playhead_width = 2
        
        # Compute Graticule scale
        for res, cadence in self.GRATICS:
            if( res >= span ):
                # this is best scale
                self._grat_cadence = cadence
                break

        self._playhead = QtCore.QRect( 0, 0, self._playhead_width, h )
        self.update()
        
    def mousePressEvent( self, event ):
        if( event.button() == QtCore.Qt.LeftButton ):
            self.sliderPressed.emit()
            self._last_value = self.value()
            new_val = self._valueFromX( event.pos().x() )
            if( new_val != self._last_value ):
                # update value
                self.setValue( new_val )
            self._dragging = True
        
        super( TimeSlider, self ).mousePressEvent( event )
 
    def mouseReleaseEvent( self, event ):
        if( event.button() == QtCore.Qt.LeftButton ):
            self.sliderReleased.emit()
            self._dragging = False
            
        super( TimeSlider, self ).mouseReleaseEvent( event )

    def mouseMoveEvent( self, event ):
        if( self._dragging ):
            self._last_value = self.value()
            new_val = self._valueFromX( event.pos().x() )
            if( self._last_value != new_val ):
                self.sliderMoved.emit( new_val )
                self.setValue( new_val )
                
        super( TimeSlider, self ).mouseMoveEvent( event )
        
    def _valueFromX( self, x_pos ):
        os = int( x_pos / self._px_per_frame )
        return os + self.minimum()


class MagSlider( QtWidgets.QAbstractSlider ):

    def __init__(self, parent ):
        super( MagSlider, self ).__init__( parent )
        self.setOrientation( QtCore.Qt.Horizontal )

        self._font = QtGui.QFont( "Decorative", 8 )
        self._font.setPixelSize( TimeSlider.FONT_SIZE )
        
        font_metrics = QtGui.QFontMetrics( self._font )
        self._font_h = font_metrics.height()

        self._pref_height = self._font_h * 1.5
        self.setMinimumWidth( 70 )
        self.setMinimumHeight( self._pref_height )
        
    def paintEvent( self, painter_event ):
        palette = self.palette()        
        painter = QtGui.QPainter()
        painter.begin( self )
        
        painter.end()
        
    def resizeEvent( self, sz_event ):
        self.updateMetrics()
        super( MagSlider, self ).resizeEvent( sz_event )
        
    def updateMetrics( self ):
        # calculate scale of visible range and playhead size
        w, h = self.width(), self.height()
        self.update()
        
    def mousePressEvent( self, event ):       
        super( MagSlider, self ).mousePressEvent( event )
 
    def mouseReleaseEvent( self, event ):
        super( MagSlider, self ).mouseReleaseEvent( event )

    def mouseMoveEvent( self, event ):
        super( MagSlider, self ).mouseMoveEvent( event )

        
class MagTimeSlider( QtWidgets.QWidget ):
    def __init__( self, parent ):
        super( MagTimeSlider, self ).__init__( parent )

        vbox = QtWidgets.QVBoxLayout( self )
        vbox.setContentsMargins( 0, 0, 0, 0)
        vbox.setSpacing( 0 )

        self.sld = TimeSlider()
        self.sld.setMaximum( 150 )
        self.sld.setMinimum( 12 )
        
        self.sld.valueChanged.connect( lambda x: print(x) )
        vbox.addWidget( self.sld )

        self.mag = MagSlider( self )
        vbox.addWidget( self.mag )

        vbox.addStretch()


class Window( QtWidgets.QMainWindow ):
    
    def __init__(self):
        super( Window, self ).__init__()
        self.setWindowTitle("Testing ScrollBars")

        mag_slider = MagTimeSlider( self )
        
        self.setCentralWidget( mag_slider )
        self.resize( 700, 120 )

if( __name__ == "__main__" ):
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
