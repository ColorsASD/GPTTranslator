from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QEasingCurve, QPointF, Property, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QCheckBox, QFrame, QSizePolicy, QWidget


SURFACE = QColor("#252525")
BORDER = QColor("#383838")
TEXT = QColor("#ececec")
SECONDARY = QColor("#b0b0b0")

# OpenAI jel: Simple Icons 11.15.0, CC0; a marka az OpenAI tulajdona.
# https://cdn.jsdelivr.net/npm/simple-icons@11.15.0/icons/openai.svg
OPENAI_LOGO_SVG = b'<svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>OpenAI</title><path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z"/></svg>'


def _path(points: list[tuple[float, float]], close: bool = False) -> QPainterPath:
    result = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        result.lineTo(QPointF(*point))
    if close:
        result.closeSubpath()
    return result


def _draw_icon(painter: QPainter, name: str, rect: QRectF, color: QColor) -> None:
    """Egységes, felbontástól független, 24 egységes vonalikonok."""
    painter.save()
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 24.0, rect.height() / 24.0)
    pen = QPen(color, 1.65, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "home":
        painter.drawPath(_path([(3, 10), (12, 2.8), (21, 10)]))
        painter.drawPath(_path([(5, 8.6), (5, 21), (9.2, 21), (9.2, 14), (14.8, 14), (14.8, 21), (19, 21), (19, 8.6)]))
    elif name == "gamepad":
        shape = QPainterPath(QPointF(7.1, 5.2))
        shape.cubicTo(9.2, 5.2, 9.5, 6.4, 12, 6.4)
        shape.cubicTo(14.5, 6.4, 14.8, 5.2, 16.9, 5.2)
        shape.cubicTo(19.1, 5.2, 20.2, 8.2, 21.5, 14.7)
        shape.cubicTo(22.7, 20.3, 19.1, 20.2, 16.7, 16.4)
        shape.lineTo(7.3, 16.4)
        shape.cubicTo(4.9, 20.2, 1.3, 20.3, 2.5, 14.7)
        shape.cubicTo(3.8, 8.2, 4.9, 5.2, 7.1, 5.2)
        painter.drawPath(shape)
        painter.drawLine(QPointF(6.1, 10.7), QPointF(10.1, 10.7))
        painter.drawLine(QPointF(8.1, 8.7), QPointF(8.1, 12.7))
        painter.setBrush(color)
        for x, y in ((16, 9.4), (18, 11.5)):
            painter.drawEllipse(QPointF(x, y), .7, .7)
    elif name == "history":
        painter.drawArc(QRectF(3.2, 3.2, 17.6, 17.6), 37 * 16, 284 * 16)
        painter.drawPath(_path([(2.5, 4.3), (2.5, 9), (7.2, 9)]))
        painter.drawPath(_path([(12, 7), (12, 12), (15.4, 14.2)]))
    elif name == "compass":
        painter.drawEllipse(QRectF(2.4, 2.4, 19.2, 19.2))
        painter.drawPath(_path([(15.6, 8.4), (13.2, 13.2), (8.4, 15.6), (10.8, 10.8)], True))
    elif name == "profile":
        painter.drawEllipse(QRectF(2.4, 2.4, 19.2, 19.2))
        painter.drawEllipse(QRectF(8.1, 5.6, 7.8, 7.8))
        profile = QPainterPath(QPointF(5.7, 18.6))
        profile.cubicTo(6.3, 12.8, 17.7, 12.8, 18.3, 18.6)
        painter.drawPath(profile)
    elif name == "grid":
        for x in (3, 13):
            for y in (3, 13):
                painter.drawRoundedRect(QRectF(x, y, 7.5, 7.5), 1.2, 1.2)
    elif name == "settings":
        gear = QPainterPath()
        for step in range(48):
            angle = (step * math.pi / 24) - math.pi / 2
            tooth = step % 6
            radius = 10 if tooth in (1, 2, 3) else 7.65
            point = QPointF(12 + math.cos(angle) * radius, 12 + math.sin(angle) * radius)
            if step == 0:
                gear.moveTo(point)
            else:
                gear.lineTo(point)
        gear.closeSubpath()
        painter.drawPath(gear)
        painter.drawEllipse(QRectF(8, 8, 8, 8))
    elif name == "keyboard":
        painter.drawRoundedRect(QRectF(2, 4.4, 20, 15.2), 2.5, 2.5)
        painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for y in (8.1, 11.8):
            for x in (6.1, 10.1, 14.1, 18.1):
                painter.drawPoint(QPointF(x, y))
        painter.drawLine(QPointF(7, 15.5), QPointF(17, 15.5))
    elif name == "monitor":
        painter.drawRoundedRect(QRectF(2, 3, 20, 14), 2, 2)
        painter.drawLine(QPointF(12, 17), QPointF(12, 21))
        painter.drawLine(QPointF(7, 21), QPointF(17, 21))
    elif name == "activity":
        painter.drawPath(_path([(1.5, 12), (6.5, 12), (9.4, 3), (14, 21), (17.3, 10), (20, 12), (22.5, 12)]))
    elif name == "send":
        painter.drawPath(_path([(2.5, 10.4), (21.3, 2.7), (14, 21.2), (10.7, 13.3), (2.5, 10.4)], True))
        painter.drawLine(QPointF(10.7, 13.3), QPointF(21.3, 2.7))
    elif name == "close":
        painter.drawLine(QPointF(5, 5), QPointF(19, 19))
        painter.drawLine(QPointF(19, 5), QPointF(5, 19))
    elif name == "download":
        painter.drawPath(_path([(4, 15), (4, 21), (20, 21), (20, 15)]))
        painter.drawPath(_path([(7.5, 10.5), (12, 15), (16.5, 10.5)]))
        painter.drawLine(QPointF(12, 3), QPointF(12, 15))
    elif name == "reset":
        painter.drawArc(QRectF(3.5, 3.5, 17, 17), -48 * 16, 288 * 16)
        painter.drawPath(_path([(2.6, 3.5), (2.6, 9), (8.1, 9)]))
    elif name == "plus":
        painter.drawLine(QPointF(12, 3), QPointF(12, 21))
        painter.drawLine(QPointF(3, 12), QPointF(21, 12))
    elif name == "microphone":
        painter.drawRoundedRect(QRectF(8.5, 2.2, 7, 12.8), 3.5, 3.5)
        capture = QPainterPath(QPointF(5, 11))
        capture.cubicTo(5, 21, 19, 21, 19, 11)
        painter.drawPath(capture)
        painter.drawLine(QPointF(12, 18.5), QPointF(12, 22))
        painter.drawLine(QPointF(8.5, 22), QPointF(15.5, 22))
    elif name == "arrow_up":
        painter.drawPath(_path([(4.3, 10.1), (12, 2.8), (19.7, 10.1)]))
        painter.drawLine(QPointF(12, 3), QPointF(12, 21))
    elif name == "chevron_right":
        painter.drawPath(_path([(9, 5), (16, 12), (9, 19)]))
    elif name == "chevron_down":
        painter.drawPath(_path([(5.5, 9), (12, 15.5), (18.5, 9)]))
    elif name == "link":
        left = QPainterPath(QPointF(10.1, 8.5))
        left.lineTo(7.8, 8.5)
        left.cubicTo(1.4, 8.5, 1.4, 18.5, 7.8, 18.5)
        left.lineTo(10.2, 18.5)
        left.cubicTo(12.4, 18.5, 13.3, 17.1, 14, 15.3)
        painter.drawPath(left)
        right = QPainterPath(QPointF(13.9, 15.5))
        right.lineTo(16.2, 15.5)
        right.cubicTo(22.6, 15.5, 22.6, 5.5, 16.2, 5.5)
        right.lineTo(13.8, 5.5)
        right.cubicTo(11.6, 5.5, 10.7, 6.9, 10, 8.7)
        painter.drawPath(right)
        painter.drawLine(QPointF(8.8, 12), QPointF(15.2, 12))
    elif name == "document":
        painter.drawPath(_path([(5, 2.5), (14, 2.5), (20, 8.5), (20, 21.5), (5, 21.5)], True))
        painter.drawPath(_path([(14, 2.5), (14, 8.5), (20, 8.5)]))
        painter.drawLine(QPointF(8.5, 13), QPointF(16.5, 13))
        painter.drawLine(QPointF(8.5, 17), QPointF(16.5, 17))
    elif name == "bulb":
        bulb = QPainterPath(QPointF(8.3, 17))
        bulb.cubicTo(8.3, 12.8, 5.1, 13, 5.1, 8.7)
        bulb.cubicTo(5.1, -.2, 18.9, -.2, 18.9, 8.7)
        bulb.cubicTo(18.9, 13, 15.7, 12.8, 15.7, 17)
        bulb.closeSubpath()
        painter.drawPath(bulb)
        painter.drawLine(QPointF(8.7, 20), QPointF(15.3, 20))
        painter.drawLine(QPointF(10.2, 22), QPointF(13.8, 22))
    elif name == "language":
        painter.drawLine(QPointF(2, 5), QPointF(14, 5))
        painter.drawLine(QPointF(8, 2), QPointF(8, 5))
        curve = QPainterPath(QPointF(11.6, 5))
        curve.cubicTo(10.6, 10, 6.8, 14.5, 3, 16)
        painter.drawPath(curve)
        curve = QPainterPath(QPointF(4.8, 8))
        curve.cubicTo(6.6, 11.8, 8.8, 14, 11.5, 15.7)
        painter.drawPath(curve)
        painter.drawPath(_path([(12, 21), (17, 8), (22, 21)]))
        painter.drawLine(QPointF(14, 16), QPointF(20, 16))
    elif name == "check":
        painter.drawEllipse(QRectF(2.4, 2.4, 19.2, 19.2))
        painter.drawPath(_path([(6.8, 12.3), (10.3, 15.6), (17.2, 8.7)]))
    elif name == "chatgpt":
        data = OPENAI_LOGO_SVG.replace(b"<path ", ('<path fill="' + color.name() + '" ').encode())
        QSvgRenderer(data).render(painter, QRectF(0, 0, 24, 24))
    else:
        painter.drawRoundedRect(QRectF(3, 3, 18, 18), 4, 4)
    painter.restore()


@lru_cache(maxsize=256)
def icon(name: str, size: int = 24, color: str = "#ececec") -> QIcon:
    """Átlátszó, élsimított ikon a sötét, semleges szürke felülethez."""
    logical_size = max(1, int(size))
    result = QIcon()
    for ratio in (1, 2):
        pixmap = QPixmap(logical_size * ratio, logical_size * ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        _draw_icon(painter, name, QRectF(0, 0, pixmap.width(), pixmap.height()), QColor(color))
        painter.end()
        pixmap.setDevicePixelRatio(ratio)
        result.addPixmap(pixmap)
    return result


class IconBadge(QWidget):
    def __init__(self, name: str, size: int = 56, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.setObjectName("iconBadge")
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor("#323232"))
        gradient.setColorAt(1, QColor("#242424"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#363636"), 1))
        radius = min(self.width(), self.height()) * .33
        painter.drawRoundedRect(rect, radius, radius)
        inset = self.width() * .26
        _draw_icon(painter, self.name, QRectF(self.rect()).adjusted(inset, inset, -inset, -inset), TEXT)


class ContentEdge(QWidget):
    """Élsimított sarok és szegély a téglalapban rajzoló webnézet felett."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline = QPainterPath()
        outline.addRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 20, 20)
        outside = QPainterPath()
        outside.setFillRule(Qt.FillRule.OddEvenFill)
        outside.addRect(QRectF(self.rect()))
        outside.addPath(outline)
        painter.fillPath(outside, QColor("#141414"))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#323232"), 1))
        painter.drawPath(outline)


class AmbientPanel(QFrame):
    def __init__(self, parent: QWidget | None = None, controller: bool = True) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setObjectName("ambientPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 20, 20)
        painter.setClipPath(clip)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor("#222222"))
        gradient.setColorAt(.47, QColor("#171717"))
        gradient.setColorAt(1, QColor("#1c1c1c"))
        painter.fillPath(clip, gradient)
        width, height = rect.width(), rect.height()

        # A referencián látható visszafogott, aszimmetrikus hullámok.
        top_wave = QPainterPath(QPointF(-1, -.5))
        top_wave.lineTo(width * .29, -.5)
        top_wave.cubicTo(width * .27, height * .29, width * .13, height * .2, -.5, height * .5)
        top_wave.closeSubpath()
        wave_gradient = QLinearGradient(0, 0, width * .32, height * .35)
        wave_gradient.setColorAt(0, QColor(100, 100, 100, 42))
        wave_gradient.setColorAt(1, QColor(55, 55, 55, 8))
        painter.fillPath(top_wave, wave_gradient)
        painter.setPen(QPen(QColor(136, 136, 136, 17), 1))
        painter.drawPath(top_wave)

        diagonal = QPainterPath(QPointF(width * .14, 0))
        diagonal.lineTo(width * .3, 0)
        diagonal.cubicTo(width * .19, height * .24, width * .12, height * .24, 0, height * .57)
        diagonal.lineTo(0, height * .38)
        diagonal.closeSubpath()
        painter.fillPath(diagonal, QColor(110, 110, 110, 5))

        bottom_wave = QPainterPath(QPointF(-1, height * .72))
        bottom_wave.cubicTo(width * .09, height * .69, width * .13, height * .97, width * .35, height + 1)
        bottom_wave.lineTo(-1, height + 1)
        bottom_wave.closeSubpath()
        bottom_gradient = QLinearGradient(0, height * .7, width * .27, height)
        bottom_gradient.setColorAt(0, QColor(121, 121, 121, 21))
        bottom_gradient.setColorAt(1, QColor(64, 64, 64, 5))
        painter.fillPath(bottom_wave, bottom_gradient)
        painter.drawPath(bottom_wave)

        right_wave = QPainterPath(QPointF(width * .74, height + 1))
        right_wave.cubicTo(width * .88, height * .73, width * .97, height * .98, width + 1, height * .65)
        right_wave.lineTo(width + 1, height + 1)
        right_wave.closeSubpath()
        painter.fillPath(right_wave, QColor(111, 111, 111, 14))
        painter.drawPath(right_wave)

        if self.controller:
            self._draw_controller(painter, width, height)
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 20, 20)

    @staticmethod
    def _draw_controller(painter: QPainter, width: float, height: float) -> None:
        painter.save()
        controller_size = min(width * .37, height * .75)
        painter.translate(width * .84, height * .51)
        painter.rotate(18)
        painter.scale(controller_size / 240, controller_size / 240)
        body = QPainterPath(QPointF(-81, -68))
        body.cubicTo(-103, -70, -111, -42, -127, 24)
        body.cubicTo(-155, 118, -122, 127, -75, 66)
        body.cubicTo(-51, 37, -28, 47, 0, 47)
        body.cubicTo(28, 47, 51, 37, 75, 66)
        body.cubicTo(122, 127, 155, 118, 127, 24)
        body.cubicTo(111, -42, 103, -70, 81, -68)
        body.lineTo(36, -65)
        body.cubicTo(12, -62, 27, -42, 0, -42)
        body.cubicTo(-27, -42, -12, -62, -36, -65)
        body.closeSubpath()
        shade = QLinearGradient(-95, -60, 75, 100)
        shade.setColorAt(0, QColor(138, 138, 138, 27))
        shade.setColorAt(.6, QColor(68, 68, 68, 6))
        shade.setColorAt(1, QColor(70, 70, 70, 2))
        painter.setBrush(shade)
        painter.setPen(QPen(QColor(145, 145, 145, 24), 1))
        painter.drawPath(body)
        painter.setPen(QPen(QColor(120, 120, 120, 18), 1))
        painter.setBrush(QColor(112, 112, 112, 15))
        cross = QPainterPath()
        cross.addRoundedRect(QRectF(-82, -13, 19, 61), 6, 6)
        cross.addRoundedRect(QRectF(-103, 8, 61, 19), 6, 6)
        painter.drawPath(cross.simplified())
        for x, y in ((75, -3), (55, 18), (95, 18), (75, 39)):
            painter.drawEllipse(QRectF(x - 10, y - 10, 20, 20))
        painter.restore()


class ToggleSwitch(QCheckBox):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._position = 0.0
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.setObjectName("toggleSwitch")
        self.setFixedSize(56, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(56, 30)

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        if not self.isVisible():
            self.position = 1.0 if checked else 0.0
            return
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def _get_position(self) -> float:
        return self._position

    def _set_position(self, value: float) -> None:
        self._position = value
        self.update()

    position = Property(float, _get_position, _set_position)

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isChecked() and self._animation.state() != QPropertyAnimation.State.Running:
            self._position = 1.0
        elif not self.isChecked() and self._animation.state() != QPropertyAnimation.State.Running:
            self._position = 0.0
        rect = QRectF(1, 2, 54, 26)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#898989") if self.isChecked() else QColor("#484848"))
        if not self.isEnabled():
            painter.setOpacity(.45)
        painter.drawRoundedRect(rect, 13, 13)
        painter.setBrush(QColor(0, 0, 0, 25))
        knob_x = 4 + 26 * self._position
        painter.drawEllipse(QRectF(knob_x, 5, 22, 22))
        painter.setBrush(QColor("#f1f1f1"))
        painter.drawEllipse(QRectF(knob_x, 4, 22, 22))
        if self.hasFocus():
            painter.setOpacity(1)
            painter.setPen(QPen(QColor("#a0a0a0"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(.5, .5, 55, 29), 14, 14)
