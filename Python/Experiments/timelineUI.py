#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt, QPoint, QLine, QRect, QRectF, Signal
from PySide2.QtGui import QPainter, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
from PySide2.QtWidgets import QWidget, QFrame, QScrollArea, QVBoxLayout
import sys
import os
import math
from numpy import load

__textColor__ = Qt.darkGray
__backgroudColor__ = QColor(60, 63, 65)
__alternateBase__ = QColor(43, 43, 43)
__font__ = QFont('Decorative', 8)
__pointer__ = QColor(100, 100, 100)
__fontScale__ = 7


class QDarkPalette(QtGui.QPalette):
    """ Dark palette for a Qt application, meant to be used with the Fusion theme.
        from Gist: https://gist.github.com/lschmierer/443b8e21ad93e2a2d7eb
    """
    WHITE = QtGui.QColor(255, 255, 255)
    BLACK = QtGui.QColor(0, 0, 0)
    RED = QtGui.QColor(255, 0, 0)
    PRIMARY = QtGui.QColor(53, 53, 53)
    SECONDARY = QtGui.QColor(35, 35, 35)
    TERTIARY = QtGui.QColor(87, 140, 178)

    def __init__(self, *args):
        super(QDarkPalette, self).__init__(*args)

        self.setColor(QtGui.QPalette.Window, self.PRIMARY)
        self.setColor(QtGui.QPalette.WindowText, self.WHITE)
        self.setColor(QtGui.QPalette.Base, self.SECONDARY)
        self.setColor(QtGui.QPalette.AlternateBase, self.PRIMARY)
        self.setColor(QtGui.QPalette.ToolTipBase, self.WHITE)
        self.setColor(QtGui.QPalette.ToolTipText, self.WHITE)
        self.setColor(QtGui.QPalette.Text, self.WHITE)
        self.setColor(QtGui.QPalette.Button, self.PRIMARY)
        self.setColor(QtGui.QPalette.ButtonText, self.WHITE)
        self.setColor(QtGui.QPalette.BrightText, self.RED)
        self.setColor(QtGui.QPalette.Link, self.TERTIARY)
        self.setColor(QtGui.QPalette.Highlight, self.TERTIARY)
        self.setColor(QtGui.QPalette.HighlightedText, self.BLACK)

    @staticmethod
    def css_rgb(colour, a=False):
        """Get a CSS rgb or rgba string from a QtGui.QColor."""
        return ("rgba({}, {}, {}, {})" if a else "rgb({}, {}, {})").format(*colour.getRgb())

    @staticmethod
    def set_stylesheet(_app):
        _app.setStyleSheet(
            "QToolTip {{"
            "color: {white};"
            "background-color: {primary};"
            "border: 1px solid {white};"
            "}}"
            "QToolButton:checked {{"
            "background-color: {tertiary};"
            "border: 1px solid;"
            "border-radius: 2px;"
            "}}".format(white=QDarkPalette.css_rgb(QDarkPalette.WHITE),
                        primary=QDarkPalette.css_rgb(QDarkPalette.PRIMARY),
                        secondary=QDarkPalette.css_rgb(QDarkPalette.SECONDARY),
                        tertiary=QDarkPalette.css_rgb(QDarkPalette.TERTIARY))
        )

    def apply2Qapp(self, _app):
        _app.setStyle("Fusion")
        _app.setPalette(self)
        self.set_stylesheet(_app)

class VideoSample:

    def __init__(self, duration, color=Qt.darkYellow, picture=None, audio=None):
        self.duration = duration
        self.color = color  # Floating color
        self.defColor = color  # DefaultColor
        if picture is not None:
            self.picture = picture.scaledToHeight(45)
        else:
            self.picture = None
        self.startPos = 0  # Inicial position
        self.endPos = self.duration  # End position


class QTimeLine(QWidget):

    positionChanged = Signal(int)
    selectionChanged = Signal(VideoSample)
    timelineChanged = Signal()

    def __init__(self, parent=None):
        super(QTimeLine, self).__init__(parent=parent)

        # Set variables
        self._start = 0
        self._end = 30
        self.backgroundColor = __backgroudColor__
        self.textColor = __textColor__
        self.font = __font__
        self.pos = None
        self.pointerPos = 0
        self.selectedFrameNr = self._start
        self.currentFrame = self._start
        self.pointerNext = self.get_frame_position(0)
        self.pointerTimePos = None
        self.selectedSample = None
        self.clicking = False  # Check if mouse left button is being pressed
        self.is_in = False  # check if user is in the widget
        self.videoSamples = []  # List of videos samples

        self.setMouseTracking(True)  # Mouse events
        self.setAutoFillBackground(True)  # background

        self.setBackgroundRole(QPalette.Base)
        self.timelineChanged.connect(self.refreshPointer)
        self.initUI()

    def initUI(self):

        self.setMinimumWidth(70)
        self.setWindowTitle("Timeline")

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        font = qp.font()
        font.setPixelSize(__fontScale__)
        qp.setFont(font)
        self.updatePointer()
        if self.pointerPos is not None:
            poly = QPolygon([QPoint(self.pointerPos, 0),
                      QPoint(self.pointerPos, 40),
                      QPoint(self.pointerNext, 40),
                      QPoint(self.pointerNext, 0)])
            qp.setPen(__pointer__)
            qp.setBrush(QBrush(__pointer__))
            qp.drawPolygon(poly)

        qp.setPen(self.textColor)
        #qp.setFont(self.font)
        qp.setRenderHint(QPainter.Antialiasing)

        # Draw time
        scale = self.getScale()

        self.ticks()
        width = round(self.width() / (self._increment ))
        w = 0
        point = 0
        value = self.start() / float(self._tick)
        first = self.start()
        missing = 0
        if value != int(value):
            first = self._tick * math.ceil(value)
            missing = self._tick * math.ceil(value) - self.start()
            w = missing * self.frameWidth()
            point = missing * self.frameWidth()
        i = 0
        while w < self.width():
            w = self.get_frame_position(w)
            nr = (i * self._tick) + first
            qp.drawText(w, 0, self.linesWidth() * 2, 50, Qt.AlignLeft, str(nr))
            w += width
            i += 1
        # Draw down line
        qp.setPen(QPen(Qt.darkCyan, 5, Qt.SolidLine))
        qp.drawLine(0, 40, self.width(), 40)

        # Draw dash lines

        qp.setPen(QPen(self.textColor))
        qp.drawLine(0, 40, self.width(), 40)

        while point < self.width():
            point = self.get_frame_position(point)
            qp.drawLine(point, 40, point, 20)
            point += width


        # Clear clip path
        path = QPainterPath()
        path.addRect(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
        qp.setClipPath(path)
        qp.setPen(Qt.white)
        w = self.pointerPos
        textWidth = self.textWidth(self.currentFrame)
        if self.pointerPos + textWidth > self.width():
            w = self.width() - textWidth
        qp.drawText(w, 20, self.linesWidth()* 2, 50, Qt.AlignLeft, str(self.currentFrame))

        qp.end()

    # Mouse movement
    def mouseMoveEvent(self, e):
        self.pos = e.pos()

        # if mouse is being pressed, update pointer
        if self.clicking:
            x = self.pos.x()
            self.updateSelection(x)
            self.positionChanged.emit(self.pointerPos)
            self.pointerTimePos = self.pointerPos*self.getScale()

        self.update()

    # Mouse pressed
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            x = e.pos().x()
            self.updateSelection(x)
            self.positionChanged.emit(self.pointerPos)
            self.pointerTimePos = self.pointerPos * self.getScale()

            self.update()
            self.clicking = True  # Set clicking check to true

    # Mouse release
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicking = False  # Set clicking check to false

    # Enter
    def enterEvent(self, e):
        self.is_in = True

    # Leave
    def leaveEvent(self, e):
        self.is_in = False
        self.update()

    def isEven(self, val):
        if val/2 == int(val/2):

            return True
        else:
            return False
    # check selection
    def updateSelection(self, x):
        if x < 0:
            x = 0
        if round(x) >= self.width():
            x = self.width() - self.frameWidth()
        self.setSelectedFrame(x)


    def selectedFrame(self):
        return self.selectedFrameNr + self.start()


    def updatePointer(self):
        self.pointerPos = (self.selectedFrameNr) * self.width() / self.duration()
        self.pointerNext = self.pointerPos + self.frameWidth()


    def setSelectedFrame(self, x):
        self.selectedFrameNr = int(self.duration() * x / self.width())
        self.currentFrame = self.selectedFrameNr + self.start()

    def setPointerPositions(self):
        self.pointerPos = round(self.selectedFrameNr * self.width() / self.duration())
        self.pointerNext = self.pointerPos + self.frameWidth()

    def get_frame_position(self, x):
        pos = round(self.duration() * x / self.width())
        return pos * self.width() / self.duration()

    def refreshPointer(self):
        self.selectedFrameNr = self.currentFrame - self.start()

    def frameWidth(self):
        return self.width() / self.duration()

    def get_time_string(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return str(int(seconds / self.getFPS()))
        return "%02d:%02d:%02d" % (h, m, s)

    def getFPS(self):
        return 30

    # Get scale from length
    def getScale(self):
        return float(self.duration())/float(self.width())

    # Get selected sample
    def getSelectedSample(self):
        return self.selectedSample


    def defaultFont(self):
        if not hasattr(self, "_defaultFont"):
            qp = QPainter()
            self._defaultFont = qp.font()
            self._defaultFont.setPixelSize(__fontScale__)
        return self._defaultFont

    def linesWidth(self):
        self._linesWidth = int(self.textWidth(self.duration()) * 1.5)
        return self._linesWidth

    def textWidth(self, text):
        self.defaultFont()
        return QtGui.QFontMetrics(self.defaultFont()).boundingRect(str(text)).width()

    def ticks(self):
        totalWidth = self.duration() * self.linesWidth()
        ticks = [1, 2, 4, 5]
        i = 0
        decimal = 1
        tick = 1
        while totalWidth > self.width():
            if i > 3:
                decimal = decimal * 10
                i = 0
            tick = ticks[i] * decimal
            totalWidth = self.duration() / tick * self.linesWidth()

            i += 1
        self._increment = round(self.duration() / tick)
        self._tick = tick
        return

    # Set background color
    def setBackgroundColor(self, color):
        self.backgroundColor = color

    # Set text color
    def setTextColor(self, color):
        self.textColor = color

    # Set Font
    def setTextFont(self, font):
        self.font = font


    def duration(self):
        return self.end() - self.start() + 1

    def start(self):
        return self._start

    def setStart(self, val):

        if val > self.end():
            self.setEnd(val + 1)
        self._start = val
        self.timelineChanged.emit()
        self.update()

    def end(self):
        return self._end

    def setEnd(self, val):
        if val == self.end():
            return
        if val < self.start():
            self.setStart(val-1)
        self._end = val
        self.timelineChanged.emit()
        self.update()


class QTimeLineEditor(QWidget):

    def __init__(self, parent=None):
        self._app = parent
        super(QTimeLineEditor, self).__init__()

        dark_fusion = QDarkPalette()
        dark_fusion.apply2Qapp(self._app)


        self.timeline = QTimeLine()
        layout = QtWidgets.QHBoxLayout(self)
        vLayout = QtWidgets.QVBoxLayout(self)

        self.startSB = QtWidgets.QSpinBox(self)
        self.endSB = QtWidgets.QSpinBox(self)
        self.startSB.setValue(self.timeline.start())
        self.endSB.setValue(self.timeline.end())
        self.setLayout(layout)
        layout.addWidget(self.timeline)
        layout.addLayout(vLayout)
        self.startSB.setMaximumWidth(50)
        self.endSB.setMaximumWidth(50)
        self.startSB.setMaximum(999999999)
        self.endSB.setMaximum(999999999)
        self.startSB.setMinimum(-999999999)
        self.endSB.setMinimum(-999999999)
        self.startSB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.endSB.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        vLayout.addWidget(self.startSB)
        vLayout.addWidget(self.endSB)


        vLayout.addStretch()

        self.startSB.editingFinished.connect(self.setStart)
        self.endSB.editingFinished.connect(self.setEnd)
        self.setGeometry(150, 150, 800, 100)

    def setStart(self):
        val = self.startSB.value()
        start = self.timeline.start()
        end = self.timeline.end()
        if val == start:
            return

        if val > end:
            self.endSB.setValue(val + 1)
        self.timeline.setStart(val)

    def setEnd(self):
        val = self.endSB.value()
        start = self.timeline.start()
        end = self.timeline.end()

        if val == end:
            return

        if val < start:
            self.startSB.setValue(val-1)
        self.timeline.setEnd(val)

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication()
    qtimeline = QTimeLineEditor(app)
    qtimeline.show()  # Creates an 360/60 = 6 minutes long timeline
    sys.exit(app.exec_())

    #