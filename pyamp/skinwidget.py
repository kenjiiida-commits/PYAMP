"""スキン画像で描く画面部品の「土台」。

Winamp の画面は 275×116 ピクセルのような小さな座標で設計されています。
ここでは、その小さな座標のまま描いたりクリックを判定したりできるようにし、
実際の表示は scale 倍（2倍など）に拡大します。
"""
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QToolTip, QWidget


@dataclass
class Button:
    """押せるボタン1つ分の情報"""
    rect: QRect
    sprite: Optional[str]                 # ふだんの絵（None なら背景のまま）
    pressed: Optional[str]                # 押している間の絵
    action: Callable
    is_on: Callable = None                # ON/OFF があるボタンなら、今 ON かを返す関数
    sprite_on: str = None
    pressed_on: str = None
    tip: str = ""


@dataclass
class Drag:
    """つまみをドラッグする場所1つ分の情報"""
    rect: QRect
    start: Callable                       # (x, y) を受け取る
    move: Callable
    end: Callable
    tip: str = ""


class SkinWidget(QWidget):
    LOGICAL_W = 275
    LOGICAL_H = 116

    def __init__(self, app):
        super().__init__()
        self.app = app                    # メインウィンドウ（スキン・倍率・状態を持っている）
        self.buttons: list[Button] = []
        self.drags: list[Drag] = []
        self._pressed: Optional[Button] = None
        self._drag: Optional[Drag] = None
        self.setAcceptDrops(False)
        self.update_size()

    # --- 大きさ ----------------------------------------------------------
    @property
    def s(self):
        return self.app.scale

    def logical_size(self):
        return self.LOGICAL_W, self.LOGICAL_H

    def update_size(self):
        w, h = self.logical_size()
        self.setFixedSize(w * self.s, h * self.s)

    def update_logical(self, x, y, w, h):
        """小さな座標の範囲だけ描き直す"""
        self.update(QRect(x * self.s, y * self.s, w * self.s, h * self.s))

    def _pos(self, e):
        return int(e.position().x() // self.s), int(e.position().y() // self.s)

    # --- 描画 ------------------------------------------------------------
    def paintEvent(self, e):
        p = QPainter(self)
        p.scale(self.s, self.s)
        self.paint(p, self.app.skin)

    def paint(self, p, skin):
        pass

    def draw_buttons(self, p, skin):
        for b in self.buttons:
            on = b.is_on() if b.is_on else False
            down = b is self._pressed and b.rect.contains(*self._last)
            if on:
                name = b.pressed_on if down else b.sprite_on
            else:
                name = b.pressed if down else b.sprite
            if name:
                skin.draw(p, name, b.rect.x(), b.rect.y())

    @property
    def active(self):
        return self.window().isActiveWindow()

    # --- マウス ----------------------------------------------------------
    _last = (-1, -1)

    def movable_at(self, x, y):
        """ここをつかんだらウィンドウを動かせるか（各画面で決める）"""
        return True

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        x, y = self._pos(e)
        self._last = (x, y)
        for b in self.buttons:
            if b.rect.contains(x, y):
                self._pressed = b
                self.update()
                return
        for d in self.drags:
            if d.rect.contains(x, y):
                self._drag = d
                d.start(x, y)
                return
        if self.click(x, y):
            return
        if self.movable_at(x, y):
            self.window().windowHandle().startSystemMove()

    def click(self, x, y):
        """ボタン以外の場所をクリックしたとき。処理したら True を返す"""
        return False

    def mouseMoveEvent(self, e):
        x, y = self._pos(e)
        self._last = (x, y)
        if self._drag:
            self._drag.move(x, y)
        elif self._pressed:
            self.update()

    def mouseReleaseEvent(self, e):
        x, y = self._pos(e)
        if self._drag:
            d, self._drag = self._drag, None
            d.end(x, y)
        elif self._pressed:
            b, self._pressed = self._pressed, None
            self.update()
            if b.rect.contains(x, y):
                b.action()

    def event(self, e):
        if e.type() == e.Type.ToolTip:
            x, y = int(e.pos().x() // self.s), int(e.pos().y() // self.s)
            for item in self.buttons + self.drags:
                if item.rect.contains(x, y) and item.tip:
                    QToolTip.showText(e.globalPos(), item.tip, self)
                    return True
            QToolTip.hideText()
            return True
        return super().event(e)

    def contextMenuEvent(self, e):
        self.app.show_main_menu(e.globalPos())
