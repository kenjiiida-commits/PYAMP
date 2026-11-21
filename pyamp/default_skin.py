"""内蔵スキン「PYAMP 標準」：Winamp のスキン形式と同じ並びの画像を、コードで描いて作ります。
（絵はすべてオリジナルです。色を変えたいときは下の「色」の部分を書き換えてください）
"""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPolygon

from sprites import CHAR_H, CHAR_W, EQ_FREQS, FONT_LOOKUP

# ---- 色 ---------------------------------------------------------------
BASE_TOP = QColor("#3b404e")
BASE_BOTTOM = QColor("#252830")
LIGHT = QColor("#626a7c")
DARK = QColor("#121419")
FACE = QColor("#4a5163")      # ボタンの面
FACE_DOWN = QColor("#323745")
ICON = QColor("#e4e8f0")
ICON_DOWN = QColor("#a9b0bf")
GOLD = QColor("#e3b95e")
LABEL = QColor("#9aa2b4")
LCD_BG = QColor("#000000")
LCD = QColor("#3cf08e")
LCD_DIM = QColor("#0c2617")
THUMB = QColor("#8c95aa")
PANEL = QColor("#1b1e25")

# ---- 4×5 ドットの小さな文字 --------------------------------------------
GLYPHS = {
    "a": [".##.", "#..#", "####", "#..#", "#..#"], "b": ["###.", "#..#", "###.", "#..#", "###."],
    "c": [".###", "#...", "#...", "#...", ".###"], "d": ["###.", "#..#", "#..#", "#..#", "###."],
    "e": ["####", "#...", "###.", "#...", "####"], "f": ["####", "#...", "###.", "#...", "#..."],
    "g": [".###", "#...", "#.##", "#..#", ".###"], "h": ["#..#", "#..#", "####", "#..#", "#..#"],
    "i": ["###.", ".#..", ".#..", ".#..", "###."], "j": ["..##", "...#", "...#", "#..#", ".##."],
    "k": ["#..#", "#.#.", "##..", "#.#.", "#..#"], "l": ["#...", "#...", "#...", "#...", "####"],
    "m": ["#..#", "####", "####", "#..#", "#..#"], "n": ["#..#", "##.#", "#.##", "#..#", "#..#"],
    "o": [".##.", "#..#", "#..#", "#..#", ".##."], "p": ["###.", "#..#", "###.", "#...", "#..."],
    "q": [".##.", "#..#", "#..#", "#.#.", ".#.#"], "r": ["###.", "#..#", "###.", "#.#.", "#..#"],
    "s": [".###", "#...", ".##.", "...#", "###."], "t": ["###.", ".#..", ".#..", ".#..", ".#.."],
    "u": ["#..#", "#..#", "#..#", "#..#", ".##."], "v": ["#..#", "#..#", "#..#", ".##.", ".##."],
    "w": ["#..#", "#..#", "####", "####", "#..#"], "x": ["#..#", "#..#", ".##.", "#..#", "#..#"],
    "y": ["#.#.", "#.#.", ".#..", ".#..", ".#.."], "z": ["####", "..#.", ".#..", "#...", "####"],
    "0": [".##.", "#.##", "##.#", "#..#", ".##."], "1": [".#..", "##..", ".#..", ".#..", "###."],
    "2": ["###.", "...#", ".##.", "#...", "####"], "3": ["###.", "...#", ".##.", "...#", "###."],
    "4": ["#..#", "#..#", "####", "...#", "...#"], "5": ["####", "#...", "###.", "...#", "###."],
    "6": [".##.", "#...", "###.", "#..#", ".##."], "7": ["####", "...#", "..#.", ".#..", ".#.."],
    "8": [".##.", "#..#", ".##.", "#..#", ".##."], "9": [".##.", "#..#", ".###", "...#", ".##."],
    ".": ["....", "....", "....", "....", ".#.."], ":": ["....", ".#..", "....", ".#..", "...."],
    "(": ["..#.", ".#..", ".#..", ".#..", "..#."], ")": [".#..", "..#.", "..#.", "..#.", ".#.."],
    "-": ["....", "....", "###.", "....", "...."], "'": [".#..", ".#..", "....", "....", "...."],
    "!": [".#..", ".#..", ".#..", "....", ".#.."], "_": ["....", "....", "....", "....", "####"],
    "+": ["....", ".#..", "###.", ".#..", "...."], "\\": ["#...", "#...", ".#..", "..#.", "..#."],
    "/": ["..#.", "..#.", ".#..", "#...", "#..."], "[": [".##.", ".#..", ".#..", ".#..", ".##."],
    "]": [".##.", "..#.", "..#.", "..#.", ".##."], "^": [".#..", "#.#.", "....", "....", "...."],
    "&": [".#..", "#.#.", ".#..", "#.#.", ".#.#"], "%": ["#..#", "..#.", ".#..", "#...", "#..#"],
    ",": ["....", "....", "....", ".#..", "#..."], "=": ["....", "###.", "....", "###.", "...."],
    "$": [".###", "##..", ".##.", "..##", "###."], "#": [".#.#", "####", ".#.#", "####", ".#.#"],
    '"': ["#.#.", "#.#.", "....", "....", "...."], "@": [".##.", "#.##", "#.##", "#...", ".##."],
    "…": ["....", "....", "....", "....", "#.#."], "?": ["###.", "...#", ".##.", "....", ".#.."],
    "*": ["....", "#.#.", ".#..", "#.#.", "...."], "å": [".#..", ".##.", "#..#", "####", "#..#"],
    "ö": ["#..#", ".##.", "#..#", "#..#", ".##."], "ä": ["#..#", ".##.", "#..#", "####", "#..#"],
}


# ---- 描画の小道具 ------------------------------------------------------
def _img(w, h, color=QColor(0, 0, 0)):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(color)
    return img


def base_color(y, height=116):
    """背景のグラデーション色（y 座標で決まる）。細い横じまで金属っぽく。"""
    t = max(0.0, min(1.0, y / height))
    c = QColor(int(BASE_TOP.red() + (BASE_BOTTOM.red() - BASE_TOP.red()) * t),
               int(BASE_TOP.green() + (BASE_BOTTOM.green() - BASE_TOP.green()) * t),
               int(BASE_TOP.blue() + (BASE_BOTTOM.blue() - BASE_TOP.blue()) * t))
    return c.darker(108) if y % 2 else c


def texture(p, x, y, w, h, global_y=None, height=116):
    gy = y if global_y is None else global_y
    for i in range(h):
        p.fillRect(x, y + i, w, 1, base_color(gy + i, height))


def bevel(p, x, y, w, h, face=FACE, raised=True):
    p.fillRect(x, y, w, h, face)
    hi, lo = (LIGHT, DARK) if raised else (DARK, LIGHT)
    p.fillRect(x, y, w, 1, hi)
    p.fillRect(x, y, 1, h, hi)
    p.fillRect(x, y + h - 1, w, 1, lo)
    p.fillRect(x + w - 1, y, 1, h, lo)


def sunken(p, x, y, w, h, face=LCD_BG):
    bevel(p, x, y, w, h, face, raised=False)


def glyph_text(p, text, x, y, color):
    for i, ch in enumerate(text.lower()):
        rows = GLYPHS.get(ch)
        if not rows:
            continue
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "#":
                    p.fillRect(x + i * CHAR_W + rx, y + ry, 1, 1, color)


def centered_text(p, text, cx, y, color):
    glyph_text(p, text, cx - (len(text) * CHAR_W - 1) // 2, y, color)


def poly(p, color, *pts):
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPolygon(QPolygon([QPoint(*pt) for pt in pts]))


def grooves(p, x, y, w, rows=(4, 7, 10)):
    for ry in rows:
        p.fillRect(x, y + ry, w, 1, DARK)
        p.fillRect(x, y + ry + 1, w, 1, LIGHT)


def title_bar(p, x, y, w, text, active, h=14):
    top, bottom = (QColor("#566079"), QColor("#2b303b")) if active else (QColor("#3d414b"), QColor("#2a2d33"))
    for i in range(h):
        t = i / (h - 1)
        p.fillRect(x, y + i, w, 1, QColor(int(top.red() + (bottom.red() - top.red()) * t),
                                          int(top.green() + (bottom.green() - top.green()) * t),
                                          int(top.blue() + (bottom.blue() - top.blue()) * t)))
    tw = len(text) * CHAR_W
    cx = x + w // 2
    rows = (3, 6, 9) if h == 14 else (5, 8, 11)
    grooves(p, x + 18, y, cx - tw // 2 - 6 - (x + 18), rows)
    grooves(p, cx + tw // 2 + 6, y, x + w - 40 - (cx + tw // 2 + 6), rows)
    centered_text(p, text, cx, y + (h - 5) // 2, GOLD if active else LABEL)


def small_button(p, x, y, kind, pressed):
    bevel(p, x, y, 9, 9, FACE_DOWN if pressed else FACE, raised=not pressed)
    c = ICON_DOWN if pressed else ICON
    o = 1 if pressed else 0
    if kind == "close":
        for i in range(5):
            p.fillRect(x + 2 + i + o, y + 2 + i + o, 1, 1, c)
            p.fillRect(x + 6 - i + o, y + 2 + i + o, 1, 1, c)
    elif kind == "min":
        p.fillRect(x + 2 + o, y + 6 + o, 5, 1, c)
    elif kind == "shade":
        p.fillRect(x + 2 + o, y + 2 + o, 5, 1, c)
        p.fillRect(x + 2 + o, y + 6 + o, 5, 1, c)
    elif kind == "options":
        for i in range(3):
            p.fillRect(x + 2 + o, y + 2 + i * 2 + o, 5, 1, c)


def led(p, x, y, on):
    p.fillRect(x, y, 3, 3, LCD if on else LCD_DIM)


# ---- 各画像 ------------------------------------------------------------
def make_main():
    img = _img(275, 116)
    p = QPainter(img)
    texture(p, 0, 0, 275, 116)
    p.fillRect(0, 0, 275, 1, LIGHT)
    p.fillRect(0, 0, 1, 116, LIGHT)
    p.fillRect(0, 115, 275, 1, DARK)
    p.fillRect(274, 0, 1, 116, DARK)
    sunken(p, 9, 21, 96, 43)                  # 時間とスペクトラムの黒い窓
    sunken(p, 108, 23, 159, 13)               # 曲名の窓
    sunken(p, 108, 40, 21, 10)                # kbps
    glyph_text(p, "kbps", 131, 43, LABEL)
    sunken(p, 153, 40, 16, 10)                # khz
    glyph_text(p, "khz", 171, 43, LABEL)
    p.fillRect(8, 85, 259, 1, DARK)
    p.fillRect(8, 86, 259, 1, LIGHT)
    glyph_text(p, "pyamp", 243, 96, GOLD)
    p.end()
    return img


def make_titlebar():
    img = _img(344, 87, QColor(0, 0, 0, 0))
    p = QPainter(img)
    title_bar(p, 27, 0, 275, "pyamp", True)
    title_bar(p, 27, 15, 275, "pyamp", False)
    for y in (0, 15):                      # タイトルバーに描き込んでおくボタン
        for kind, x in [("options", 6), ("min", 244), ("shade", 254), ("close", 264)]:
            small_button(p, 27 + x, y + 3, kind, False)
    for kind, x, y in [("options", 0, 0), ("min", 9, 0), ("close", 18, 0)]:
        small_button(p, x, y, kind, False)
        small_button(p, x, y + 9, kind, True)
    small_button(p, 0, 18, "shade", False)
    small_button(p, 9, 18, "shade", True)
    p.end()
    return img


def _transport_icon(p, kind, x, y, c):
    if kind == "prev":
        p.fillRect(x + 5, y + 5, 2, 8, c)
        poly(p, c, (x + 7, y + 9), (x + 11, y + 5), (x + 11, y + 13))
        poly(p, c, (x + 11, y + 9), (x + 15, y + 5), (x + 15, y + 13))
    elif kind == "play":
        poly(p, c, (x + 8, y + 4), (x + 8, y + 13), (x + 15, y + 8))
    elif kind == "pause":
        p.fillRect(x + 8, y + 5, 2, 8, c)
        p.fillRect(x + 13, y + 5, 2, 8, c)
    elif kind == "stop":
        p.fillRect(x + 7, y + 5, 8, 8, c)
    elif kind == "next":
        poly(p, c, (x + 10, y + 9), (x + 6, y + 5), (x + 6, y + 13))
        poly(p, c, (x + 14, y + 9), (x + 10, y + 5), (x + 10, y + 13))
        p.fillRect(x + 15, y + 5, 2, 8, c)
    elif kind == "eject":
        poly(p, c, (x + 11, y + 3), (x + 6, y + 8), (x + 16, y + 8))
        p.fillRect(x + 6, y + 10, 11, 2, c)


def make_cbuttons():
    img = _img(136, 36)
    p = QPainter(img)
    for kind, x, w, h in [("prev", 0, 23, 18), ("play", 23, 23, 18), ("pause", 46, 23, 18),
                          ("stop", 69, 23, 18), ("next", 92, 22, 18), ("eject", 114, 22, 16)]:
        bevel(p, x, 0, w, h, FACE, True)
        _transport_icon(p, kind, x, 0, ICON)
        bevel(p, x, h, w, h, FACE_DOWN, False)
        _transport_icon(p, kind, x + 1, h + 1, ICON_DOWN)
    p.end()
    return img


SEGMENTS = {  # 7セグメント： (x, y, 幅, 高さ)
    "a": (2, 0, 5, 2), "b": (7, 1, 2, 5), "c": (7, 7, 2, 5), "d": (2, 11, 5, 2),
    "e": (0, 7, 2, 5), "f": (0, 1, 2, 5), "g": (2, 6, 5, 1),
}
DIGIT_SEGS = ["abcdef", "bc", "abged", "abgcd", "fgbc", "afgcd", "afgedc", "abc", "abcdefg", "abcdfg"]


def make_numbers():
    img = _img(108, 13, LCD_BG)
    p = QPainter(img)
    for i in range(11):
        for s in "abcdefg":           # うっすら見える「消えているセグメント」
            x, y, w, h = SEGMENTS[s]
            p.fillRect(i * 9 + x, y, w, h, LCD_DIM)
        if i < 10:
            for s in DIGIT_SEGS[i]:
                x, y, w, h = SEGMENTS[s]
                p.fillRect(i * 9 + x, y, w, h, LCD)
    p.end()
    return img


def make_playpaus():
    img = _img(42, 9, LCD_BG)
    p = QPainter(img)
    poly(p, LCD, (2, 1), (2, 7), (6, 4))
    p.fillRect(11, 1, 2, 7, LCD)
    p.fillRect(14, 1, 2, 7, LCD)
    p.fillRect(20, 2, 5, 5, LCD)
    p.fillRect(37, 3, 1, 3, QColor("#5a1010"))
    p.fillRect(40, 3, 1, 3, LCD)
    p.end()
    return img


def make_monoster():
    img = _img(58, 24, LCD_BG)
    p = QPainter(img)
    glyph_text(p, "stereo", 0, 3, LCD)
    glyph_text(p, "stereo", 0, 15, LCD_DIM)
    glyph_text(p, "mono", 33, 3, LCD)
    glyph_text(p, "mono", 33, 15, LCD_DIM)
    p.end()
    return img


def make_posbar():
    img = _img(307, 10)
    p = QPainter(img)
    texture(p, 0, 0, 248, 10, global_y=72)
    sunken(p, 0, 3, 248, 4, QColor("#0d0f13"))
    bevel(p, 248, 0, 29, 10, THUMB, True)
    bevel(p, 278, 0, 29, 10, GOLD, True)
    for x in (258, 262, 266, 288, 292, 296):
        p.fillRect(x, 3, 1, 4, DARK)
    p.end()
    return img


def _slider_frames(p, x0, width, global_y, centered):
    for i in range(28):
        y = i * 15
        texture(p, x0, y, width, 13, global_y=global_y)
        sunken(p, x0, y + 4, width, 5, QColor("#0d0f13"))
        color = QColor.fromHsv(int(120 - 120 * i / 27), 210, 235)
        inner = width - 2
        if centered:
            half = int(inner / 2 * i / 27)
            p.fillRect(x0 + 1 + inner // 2 - half, y + 5, half * 2, 3, color)
        else:
            p.fillRect(x0 + 1, y + 5, int(inner * (i + 1) / 28), 3, color)


def make_volume():
    img = _img(68, 433)
    p = QPainter(img)
    _slider_frames(p, 0, 68, 57, centered=False)
    bevel(p, 15, 422, 14, 11, THUMB, True)
    bevel(p, 0, 422, 14, 11, GOLD, True)
    p.end()
    return img


def make_balance():
    img = _img(47, 433)
    p = QPainter(img)
    _slider_frames(p, 9, 38, 57, centered=True)
    bevel(p, 15, 422, 14, 11, THUMB, True)
    bevel(p, 0, 422, 14, 11, GOLD, True)
    p.end()
    return img


def _toggle(p, x, y, w, h, label, on, pressed, icon=None):
    bevel(p, x, y, w, h, FACE_DOWN if pressed else FACE, raised=not pressed)
    o = 1 if pressed else 0
    led(p, x + 3 + o, y + (h - 3) // 2 + o, on)
    color = LCD if on else LABEL
    if icon == "repeat":
        cx, cy = x + 9 + o, y + 4 + o
        p.fillRect(cx, cy, 12, 1, color)
        p.fillRect(cx, cy + 6, 12, 1, color)
        p.fillRect(cx, cy, 1, 7, color)
        p.fillRect(cx + 11, cy, 1, 7, color)
        poly(p, color, (cx + 6, cy - 2), (cx + 9, cy), (cx + 6, cy + 2))
    else:
        glyph_text(p, label, x + 8 + o, y + (h - 5) // 2 + o, color)


def make_shufrep():
    img = _img(92, 85)
    p = QPainter(img)
    for row, (on, pressed) in enumerate([(False, False), (False, True), (True, False), (True, True)]):
        _toggle(p, 0, row * 15, 28, 15, "", on, pressed, icon="repeat")
        _toggle(p, 28, row * 15, 47, 15, "shuffle", on, pressed)
    for x, label in [(0, "eq"), (23, "pl")]:
        _toggle(p, x, 61, 23, 12, label, False, False)
        _toggle(p, x, 73, 23, 12, label, True, False)
        _toggle(p, x + 46, 61, 23, 12, label, False, True)
        _toggle(p, x + 46, 73, 23, 12, label, True, True)
    p.end()
    return img


def make_text():
    img = _img(155, 18, LCD_BG)
    p = QPainter(img)
    for ch, (row, col) in FONT_LOOKUP.items():
        if ch in GLYPHS and (ch.isalnum() or not ch.isalpha()):
            glyph_text(p, ch, col * CHAR_W, row * CHAR_H, LCD)
    p.end()
    return img


def make_eqmain():
    img = _img(275, 315)
    p = QPainter(img)
    # 背景
    texture(p, 0, 0, 275, 116)
    p.fillRect(0, 0, 275, 1, LIGHT)
    p.fillRect(0, 0, 1, 116, LIGHT)
    p.fillRect(0, 115, 275, 1, DARK)
    p.fillRect(274, 0, 1, 116, DARK)
    sunken(p, 85, 16, 115, 21)
    sunken(p, 14, 34, 250, 70, PANEL)
    glyph_text(p, "+12db", 44, 37, LABEL)
    glyph_text(p, "+0db", 46, 65, LABEL)
    glyph_text(p, "-12db", 44, 96, LABEL)
    centered_text(p, "preamp", 28, 107, LABEL)
    for i, hz in enumerate(EQ_FREQS):
        label = f"{hz // 1000}k" if hz >= 1000 else str(hz)
        centered_text(p, label, 78 + 18 * i + 7, 107, LABEL)
    # タイトルバー・閉じるボタン
    title_bar(p, 0, 134, 275, "equalizer", True)
    title_bar(p, 0, 149, 275, "equalizer", False)
    small_button(p, 264, 137, "close", False)
    small_button(p, 264, 152, "close", False)
    small_button(p, 0, 116, "close", False)
    small_button(p, 0, 125, "close", True)
    # ON / AUTO
    for x, on, pressed in [(10, False, False), (69, True, False), (128, False, True), (187, True, True)]:
        _toggle(p, x, 119, 26, 12, "on", on, pressed)
    for x, on, pressed in [(36, False, False), (95, True, False), (154, False, True), (213, True, True)]:
        _toggle(p, x, 119, 32, 12, "auto", on, pressed)
    # つまみ
    bevel(p, 0, 164, 11, 11, THUMB, True)
    bevel(p, 0, 176, 11, 11, GOLD, True)
    for y in (168, 170, 180, 182):
        p.fillRect(2, y, 7, 1, DARK)
    # スライダーの溝（28段階）
    for i in range(28):
        x = 13 + (i % 14) * 15
        y = 164 + (i // 14) * 65
        p.fillRect(x, y, 14, 63, PANEL)
        p.fillRect(x + 5, y, 4, 63, QColor("#0b0c10"))
        level = int(61 * i / 27)
        color = QColor.fromHsv(int(120 - 120 * i / 27), 200, 230)
        p.fillRect(x + 6, y + 62 - level, 2, level + 1, color)
    # プリセットボタン
    for y, pressed in [(164, False), (176, True)]:
        bevel(p, 224, y, 44, 12, FACE_DOWN if pressed else FACE, raised=not pressed)
        glyph_text(p, "presets", 229 + pressed, y + 4 + pressed, ICON_DOWN if pressed else ICON)
    # グラフ
    p.fillRect(0, 294, 113, 19, LCD_BG)
    for x in range(0, 113, 2):
        p.fillRect(x, 294 + 9, 1, 1, QColor("#1d3a28"))
    for y in range(19):
        d = abs(y - 9) / 9
        p.fillRect(115, 294 + y, 1, 1, QColor.fromHsv(int(120 - 120 * d), 220, 240))
    p.fillRect(0, 314, 113, 1, QColor("#5a6070"))
    p.end()
    return img


def make_pledit():
    img = _img(280, 186)
    p = QPainter(img)
    face = QColor("#30343e")
    for y0, active in [(0, True), (21, False)]:
        top = QColor("#4b546a") if active else QColor("#363a44")
        for i in range(20):
            p.fillRect(0, y0 + i, 178, 1, top.darker(100 + i * 3))
        rows = (6, 9, 12)
        grooves(p, 4, y0, 21, rows)                     # 左上の角
        p.fillRect(0, y0, 1, 20, LIGHT)
        grooves(p, 26, y0, 24, rows)                    # タイトル
        grooves(p, 102, y0, 24, rows)
        centered_text(p, "playlist", 76, y0 + 7, GOLD if active else LABEL)
        grooves(p, 127, y0, 25, rows)                   # 横に並べる部分
        grooves(p, 153, y0, 12, rows)                   # 右上の角
        small_button(p, 153 + 14, y0 + 3, "close", False)
        p.fillRect(177, y0, 1, 20, DARK)
        p.fillRect(0, y0 + 19, 178, 1, DARK)
    small_button(p, 52, 42, "close", True)
    # 左右の縁
    p.fillRect(0, 42, 12, 29, face)
    p.fillRect(0, 42, 1, 29, LIGHT)
    p.fillRect(11, 42, 1, 29, DARK)
    p.fillRect(31, 42, 20, 29, face)
    p.fillRect(31, 42, 1, 29, LIGHT)
    p.fillRect(36, 42, 8, 29, QColor("#0d0f13"))
    p.fillRect(50, 42, 1, 29, DARK)
    bevel(p, 52, 53, 8, 18, THUMB, True)
    bevel(p, 61, 53, 8, 18, GOLD, True)
    # 下の部分
    for x, w in [(179, 25), (0, 125), (126, 150)]:
        y = 0 if x == 179 else 72
        p.fillRect(x, y, w, 38, face)
        p.fillRect(x, y, w, 1, LIGHT)
        p.fillRect(x, y + 37, w, 1, DARK)
    p.fillRect(0, 72, 1, 38, LIGHT)
    p.fillRect(275, 72, 1, 38, DARK)
    for i, label in enumerate(["add", "rem", "sel", "misc"]):
        x = 14 + 29 * i
        bevel(p, x, 80, 22, 18, FACE, True)
        centered_text(p, label, x + 11, 87, ICON)
    bevel(p, 126 + 106, 80, 22, 18, FACE, True)
    centered_text(p, "list", 126 + 117, 87, ICON)
    sunken(p, 126 + 6, 72 + 9, 64, 10)
    for i, kind in enumerate(["prev", "play", "pause", "stop", "next", "eject"]):
        bx = 126 + 3 + i * 10
        bevel(p, bx, 72 + 22, 10, 10, FACE, True)
        _mini_icon(p, kind, bx, 72 + 22)
    sunken(p, 126 + 64, 72 + 22, 28, 10)
    for i in range(3):                                  # 大きさを変えるつまみ
        for j in range(i + 1):
            p.fillRect(126 + 146 - i * 3 + j * 3 - 3, 72 + 34 - (i - j) * 3 - 3, 2, 2, LIGHT)
    p.end()
    return img


def _mini_icon(p, kind, x, y):
    c = ICON
    if kind in ("play",):
        poly(p, c, (x + 3, y + 2), (x + 3, y + 7), (x + 6, y + 4))
    elif kind == "pause":
        p.fillRect(x + 3, y + 3, 1, 4, c)
        p.fillRect(x + 6, y + 3, 1, 4, c)
    elif kind == "stop":
        p.fillRect(x + 3, y + 3, 4, 4, c)
    elif kind == "prev":
        p.fillRect(x + 2, y + 3, 1, 4, c)
        poly(p, c, (x + 3, y + 5), (x + 7, y + 2), (x + 7, y + 7))
    elif kind == "next":
        poly(p, c, (x + 6, y + 5), (x + 2, y + 2), (x + 2, y + 7))
        p.fillRect(x + 7, y + 3, 1, 4, c)
    elif kind == "eject":
        poly(p, c, (x + 5, y + 2), (x + 2, y + 5), (x + 8, y + 5))
        p.fillRect(x + 2, y + 6, 7, 1, c)


def viscolors():
    cols = ["#000000", "#20242c"]
    for i in range(16):                     # 2 が一番上（赤）、17 が一番下（緑）
        t = i / 15
        cols.append(QColor.fromHsv(int(0 + 130 * t), 230, 255 - int(40 * t)).name())
    cols += ["#ffffff", "#c8f0d8", "#90e0b0", "#58c888", "#30a060", "#d8d8e0"]
    return cols


def build_default():
    return {
        "images": {
            "main": make_main(), "titlebar": make_titlebar(), "cbuttons": make_cbuttons(),
            "numbers": make_numbers(), "playpaus": make_playpaus(), "monoster": make_monoster(),
            "posbar": make_posbar(), "volume": make_volume(), "balance": make_balance(),
            "shufrep": make_shufrep(), "text": make_text(), "eqmain": make_eqmain(),
            "pledit": make_pledit(),
        },
        "viscolors": viscolors(),
        "pledit": {"normal": "#3cf08e", "current": "#ffffff", "normalbg": "#000000",
                   "selectedbg": "#1e3d73", "font": "DejaVu Sans"},
    }
