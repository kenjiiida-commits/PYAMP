"""イコライザー画面（Winamp の EQ と同じ 275×116、60Hz〜16kHz の10バンド）"""
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QMenu

from skinwidget import Button, Drag, SkinWidget
from sprites import EQ_POS as P

# プリセット（10バンド分の dB 値。範囲は -12〜+12）
PRESETS = {
    "フラット": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "ロック": [5, 4, 3, 1, -1, -1, 1, 3, 4, 5],
    "ポップ": [-1, 1, 3, 4, 4, 2, 0, -1, -1, -1],
    "クラシック": [0, 0, 0, 0, 0, 0, -3, -3, -3, -5],
    "ジャズ": [3, 2, 1, 2, -1, -1, 0, 1, 2, 3],
    "ダンス": [6, 5, 2, 0, 0, -2, -3, -3, 0, 0],
    "低音強調": [7, 6, 5, 3, 1, 0, 0, 0, 0, 0],
    "高音強調": [0, 0, 0, 0, 0, 1, 3, 5, 6, 7],
    "ボーカル": [-2, -2, -1, 1, 4, 4, 3, 1, 0, -1],
    "ヘッドホン": [3, 5, 3, -1, -2, 0, 2, 4, 6, 7],
    "ライブ": [-3, 0, 2, 3, 3, 3, 2, 1, 1, 1],
    "テクノ": [5, 4, 0, -3, -3, 0, 5, 6, 6, 5],
}

MIN_DB, MAX_DB = -12, 12
SLIDER_H = 63
THUMB_TRAVEL = 51      # つまみが動ける幅（63 - 11 - 1）


def db_to_frame(db):
    return round((db - MIN_DB) / (MAX_DB - MIN_DB) * 27)


def db_to_thumb_y(db):
    return round((MAX_DB - db) / (MAX_DB - MIN_DB) * THUMB_TRAVEL)


def catmull(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


class EqualizerPanel(SkinWidget):
    def __init__(self, app):
        super().__init__(app)
        self._dragging = None   # 今ドラッグしているスライダー（-1 はプリアンプ）
        a = app
        self.buttons = [
            Button(QRect(*P["CLOSE"], 9, 9), None, "EQ_CLOSE_P", lambda: a.toggle_eq(False), tip="閉じる"),
            Button(QRect(*P["ON"], 26, 12), "EQ_ON", "EQ_ON_P", a.toggle_eq_on,
                   lambda: a.eq_on, "EQ_ON_ON", "EQ_ON_ON_P", "イコライザーを ON/OFF"),
            Button(QRect(*P["AUTO"], 32, 12), "EQ_AUTO", "EQ_AUTO_P", a.toggle_eq_auto,
                   lambda: a.eq_auto, "EQ_AUTO_ON", "EQ_AUTO_ON_P",
                   "AUTO：曲ごとにEQを覚えておく"),
            Button(QRect(*P["PRESETS"], 44, 12), "EQ_PRESETS", "EQ_PRESETS_P", self._presets_menu,
                   tip="プリセット"),
        ]
        self.drags = [Drag(QRect(P["PREAMP"][0], P["PREAMP"][1], 14, SLIDER_H),
                           lambda x, y: self._start(-1, y), self._move, self._end, "プリアンプ")]
        for i in range(10):
            x = P["BAND_X0"] + P["BAND_DX"] * i
            self.drags.append(Drag(QRect(x, P["BAND_Y"], 14, SLIDER_H),
                                   lambda x_, y, i=i: self._start(i, y), self._move, self._end))
        for key, db in [("PLUS12", 12), ("ZERO", 0), ("MINUS12", -12)]:
            self.buttons.append(Button(QRect(*P[key]), None, None,
                                       lambda db=db: a.set_all_eq(db),
                                       tip=f"全部を {db:+d}dB にする"))

    def movable_at(self, x, y):
        return True

    # --- 描画 -------------------------------------------------------------
    def paint(self, p, skin):
        a = self.app
        skin.draw(p, "EQ_BG", 0, 0)
        skin.draw(p, "EQ_TITLE_ACTIVE" if self.active else "EQ_TITLE", 0, 0)
        self._paint_graph(p, skin)
        self._paint_slider(p, skin, P["PREAMP"][0], a.preamp, self._dragging == -1)
        for i, db in enumerate(a.eq_gains):
            self._paint_slider(p, skin, P["BAND_X0"] + P["BAND_DX"] * i, db, self._dragging == i)
        self.draw_buttons(p, skin)

    def _paint_slider(self, p, skin, x, db, pressed):
        n = db_to_frame(db)
        skin.draw_part(p, "eqmain", 13 + (n % 14) * 15, 164 + (n // 14) * 65, 14, SLIDER_H,
                       x, P["BAND_Y"])
        skin.draw(p, "EQ_THUMB_P" if pressed else "EQ_THUMB", x + 1, P["BAND_Y"] + db_to_thumb_y(db))

    def _paint_graph(self, p, skin):
        gx, gy = P["GRAPH"]
        skin.draw(p, "EQ_GRAPH_BG", gx, gy)
        a = self.app
        py = round((MAX_DB - a.preamp) / 24 * 18)
        skin.draw(p, "EQ_PREAMP_LINE", gx, gy + py)
        g = [float(v) for v in a.eq_gains]
        pts = [g[0]] + g + [g[-1]]
        prev = None
        for x in range(113):
            t = x / 112 * 9
            i = min(8, int(t))
            v = catmull(pts[i], pts[i + 1], pts[i + 2], pts[i + 3], t - i)
            y = max(0, min(18, round((MAX_DB - v) / 24 * 18)))
            lo, hi = (y, y) if prev is None else (min(prev, y), max(prev, y))
            for yy in range(lo, hi + 1):
                p.fillRect(gx + x, gy + yy, 1, 1, skin.pixel_color("EQ_GRAPH_COLORS", 0, yy))
            prev = y

    # --- 操作 -------------------------------------------------------------
    def _value_at(self, y):
        t = (y - P["BAND_Y"] - 5) / THUMB_TRAVEL
        return max(MIN_DB, min(MAX_DB, round(MAX_DB - t * (MAX_DB - MIN_DB))))

    def _start(self, index, y):
        self._dragging = index
        self._move(0, y)

    def _move(self, x, y):
        if self._dragging is None:
            return
        db = self._value_at(y)
        if self._dragging == -1:
            self.app.set_preamp(db)
        else:
            self.app.set_eq_band(self._dragging, db)

    def _end(self, x, y):
        self._dragging = None
        self.update()

    def _presets_menu(self):
        menu = QMenu(self)
        for name, gains in PRESETS.items():
            menu.addAction(name, lambda g=gains: self.app.set_eq_gains(g))
        menu.addSeparator()
        menu.addAction("すべて 0 に戻す（プリアンプも）", lambda: (self.app.set_eq_gains([0] * 10),
                                                         self.app.set_preamp(0)))
        x, y = P["PRESETS"]
        menu.exec(self.mapToGlobal(QPoint(x * self.s, (y + 12) * self.s)))
