"""Winamp 2.x スキン形式の「座標表」。

Winamp のスキンは、何枚かの BMP 画像に部品の絵が並べて描かれています。
ここには「どの画像の、どこからどこまでが、どの部品か」と
「その部品を画面のどこに置くか」をまとめています。
（座標は Winamp 互換プレイヤー Webamp の資料と同じものです）
"""

# 部品の名前: (画像ファイル名, x, y, 幅, 高さ)
SPRITES = {
    # --- main.bmp ---
    "MAIN_BG": ("main", 0, 0, 275, 116),
    # --- titlebar.bmp ---
    "TITLE": ("titlebar", 27, 15, 275, 14),
    "TITLE_ACTIVE": ("titlebar", 27, 0, 275, 14),
    "OPTIONS": ("titlebar", 0, 0, 9, 9), "OPTIONS_P": ("titlebar", 0, 9, 9, 9),
    "MINIMIZE": ("titlebar", 9, 0, 9, 9), "MINIMIZE_P": ("titlebar", 9, 9, 9, 9),
    "SHADE": ("titlebar", 0, 18, 9, 9), "SHADE_P": ("titlebar", 9, 18, 9, 9),
    "CLOSE": ("titlebar", 18, 0, 9, 9), "CLOSE_P": ("titlebar", 18, 9, 9, 9),
    # --- cbuttons.bmp（再生ボタン類）---
    "PREV": ("cbuttons", 0, 0, 23, 18), "PREV_P": ("cbuttons", 0, 18, 23, 18),
    "PLAY": ("cbuttons", 23, 0, 23, 18), "PLAY_P": ("cbuttons", 23, 18, 23, 18),
    "PAUSE": ("cbuttons", 46, 0, 23, 18), "PAUSE_P": ("cbuttons", 46, 18, 23, 18),
    "STOP": ("cbuttons", 69, 0, 23, 18), "STOP_P": ("cbuttons", 69, 18, 23, 18),
    "NEXT": ("cbuttons", 92, 0, 22, 18), "NEXT_P": ("cbuttons", 92, 18, 22, 18),
    "EJECT": ("cbuttons", 114, 0, 22, 16), "EJECT_P": ("cbuttons", 114, 16, 22, 16),
    # --- numbers.bmp（時間の数字）---
    "MINUS": ("numbers", 20, 6, 5, 1), "NO_MINUS": ("numbers", 9, 6, 5, 1),
    # --- playpaus.bmp（再生状態マーク）---
    "IND_PLAY": ("playpaus", 0, 0, 9, 9), "IND_PAUSE": ("playpaus", 9, 0, 9, 9),
    "IND_STOP": ("playpaus", 18, 0, 9, 9),
    "IND_NOT_WORKING": ("playpaus", 36, 0, 3, 9), "IND_WORKING": ("playpaus", 39, 0, 3, 9),
    # --- monoster.bmp ---
    "STEREO": ("monoster", 0, 12, 29, 12), "STEREO_ON": ("monoster", 0, 0, 29, 12),
    "MONO": ("monoster", 29, 12, 27, 12), "MONO_ON": ("monoster", 29, 0, 27, 12),
    # --- posbar.bmp（シークバー）---
    "POS_BG": ("posbar", 0, 0, 248, 10),
    "POS_THUMB": ("posbar", 248, 0, 29, 10), "POS_THUMB_P": ("posbar", 278, 0, 29, 10),
    # --- volume.bmp / balance.bmp ---
    "VOL_THUMB": ("volume", 15, 422, 14, 11), "VOL_THUMB_P": ("volume", 0, 422, 14, 11),
    "BAL_THUMB": ("balance", 15, 422, 14, 11), "BAL_THUMB_P": ("balance", 0, 422, 14, 11),
    # --- shufrep.bmp ---
    "REPEAT": ("shufrep", 0, 0, 28, 15), "REPEAT_P": ("shufrep", 0, 15, 28, 15),
    "REPEAT_ON": ("shufrep", 0, 30, 28, 15), "REPEAT_ON_P": ("shufrep", 0, 45, 28, 15),
    "SHUFFLE": ("shufrep", 28, 0, 47, 15), "SHUFFLE_P": ("shufrep", 28, 15, 47, 15),
    "SHUFFLE_ON": ("shufrep", 28, 30, 47, 15), "SHUFFLE_ON_P": ("shufrep", 28, 45, 47, 15),
    "EQ_BTN": ("shufrep", 0, 61, 23, 12), "EQ_BTN_ON": ("shufrep", 0, 73, 23, 12),
    "EQ_BTN_P": ("shufrep", 46, 61, 23, 12), "EQ_BTN_ON_P": ("shufrep", 46, 73, 23, 12),
    "PL_BTN": ("shufrep", 23, 61, 23, 12), "PL_BTN_ON": ("shufrep", 23, 73, 23, 12),
    "PL_BTN_P": ("shufrep", 69, 61, 23, 12), "PL_BTN_ON_P": ("shufrep", 69, 73, 23, 12),
    # --- eqmain.bmp ---
    "EQ_BG": ("eqmain", 0, 0, 275, 116),
    "EQ_TITLE": ("eqmain", 0, 149, 275, 14), "EQ_TITLE_ACTIVE": ("eqmain", 0, 134, 275, 14),
    "EQ_THUMB": ("eqmain", 0, 164, 11, 11), "EQ_THUMB_P": ("eqmain", 0, 176, 11, 11),
    "EQ_CLOSE": ("eqmain", 0, 116, 9, 9), "EQ_CLOSE_P": ("eqmain", 0, 125, 9, 9),
    "EQ_ON": ("eqmain", 10, 119, 26, 12), "EQ_ON_P": ("eqmain", 128, 119, 26, 12),
    "EQ_ON_ON": ("eqmain", 69, 119, 26, 12), "EQ_ON_ON_P": ("eqmain", 187, 119, 26, 12),
    "EQ_AUTO": ("eqmain", 36, 119, 32, 12), "EQ_AUTO_P": ("eqmain", 154, 119, 32, 12),
    "EQ_AUTO_ON": ("eqmain", 95, 119, 32, 12), "EQ_AUTO_ON_P": ("eqmain", 213, 119, 32, 12),
    "EQ_PRESETS": ("eqmain", 224, 164, 44, 12), "EQ_PRESETS_P": ("eqmain", 224, 176, 44, 12),
    "EQ_GRAPH_BG": ("eqmain", 0, 294, 113, 19),
    "EQ_GRAPH_COLORS": ("eqmain", 115, 294, 1, 19),
    "EQ_PREAMP_LINE": ("eqmain", 0, 314, 113, 1),
    # --- pledit.bmp（プレイリストの枠）---
    "PL_TL": ("pledit", 0, 21, 25, 20), "PL_TL_ACTIVE": ("pledit", 0, 0, 25, 20),
    "PL_TITLE": ("pledit", 26, 21, 100, 20), "PL_TITLE_ACTIVE": ("pledit", 26, 0, 100, 20),
    "PL_TOP": ("pledit", 127, 21, 25, 20), "PL_TOP_ACTIVE": ("pledit", 127, 0, 25, 20),
    "PL_TR": ("pledit", 153, 21, 25, 20), "PL_TR_ACTIVE": ("pledit", 153, 0, 25, 20),
    "PL_LEFT": ("pledit", 0, 42, 12, 29), "PL_RIGHT": ("pledit", 31, 42, 20, 29),
    "PL_BOTTOM": ("pledit", 179, 0, 25, 38),
    "PL_BL": ("pledit", 0, 72, 125, 38), "PL_BR": ("pledit", 126, 72, 150, 38),
    "PL_SCROLL": ("pledit", 52, 53, 8, 18), "PL_SCROLL_P": ("pledit", 61, 53, 8, 18),
    "PL_CLOSE_P": ("pledit", 52, 42, 9, 9),
}

# メイン画面での置き場所 (x, y)
MAIN_POS = {
    "TITLE": (0, 0), "OPTIONS": (6, 3), "MINIMIZE": (244, 3), "SHADE": (254, 3), "CLOSE": (264, 3),
    "IND": (26, 28), "WORK": (24, 28),
    "MINUS": (38, 32), "DIGITS": (48, 60, 78, 90), "DIGIT_Y": 26,
    "VIS": (24, 43, 76, 16),          # x, y, 幅, 高さ
    "MARQUEE": (111, 27, 154, 6),
    "KBPS": (111, 43, 15), "KHZ": (156, 43, 10),
    "MONO": (212, 41), "STEREO": (239, 41),
    "VOLUME": (107, 57, 68, 13), "BALANCE": (177, 57, 38, 13),
    "EQ_BTN": (219, 58), "PL_BTN": (242, 58),
    "POS": (16, 72, 248, 10),
    "PREV": (16, 88), "PLAY": (39, 88), "PAUSE": (62, 88), "STOP": (85, 88), "NEXT": (108, 88),
    "EJECT": (136, 89), "SHUFFLE": (164, 89), "REPEAT": (210, 89),
}

# イコライザー画面での置き場所
EQ_POS = {
    "CLOSE": (264, 3), "ON": (14, 18), "AUTO": (40, 18), "PRESETS": (217, 18),
    "GRAPH": (86, 17), "PREAMP": (21, 38), "BAND_X0": 78, "BAND_DX": 18, "BAND_Y": 38,
    "PLUS12": (45, 36, 22, 8), "ZERO": (45, 64, 22, 8), "MINUS12": (45, 95, 22, 8),
}

# 文字の絵（text.bmp）は 5×6 ピクセルのマスが並んでいる。文字 → (行, 列)
CHAR_W, CHAR_H = 5, 6
FONT_LOOKUP = {c: (0, i) for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
FONT_LOOKUP.update({'"': (0, 26), "@": (0, 27), " ": (0, 30)})
FONT_LOOKUP.update({c: (1, i) for i, c in enumerate("0123456789")})
FONT_LOOKUP.update({"…": (1, 10), ".": (1, 11), ":": (1, 12), "(": (1, 13), ")": (1, 14),
                    "-": (1, 15), "'": (1, 16), "!": (1, 17), "_": (1, 18), "+": (1, 19),
                    "\\": (1, 20), "/": (1, 21), "[": (1, 22), "]": (1, 23), "^": (1, 24),
                    "&": (1, 25), "%": (1, 26), ",": (1, 27), "=": (1, 28), "$": (1, 29),
                    "#": (1, 30), "å": (2, 0), "ö": (2, 1), "ä": (2, 2), "?": (2, 3),
                    "*": (2, 4), "<": (1, 22), ">": (1, 23), "{": (1, 22), "}": (1, 23),
                    ";": (1, 12), "~": (1, 15), "`": (1, 16), "|": (1, 17)})

# スキンを構成する画像ファイル
SKIN_FILES = ["main", "titlebar", "cbuttons", "numbers", "playpaus", "monoster", "posbar",
              "volume", "balance", "shufrep", "text", "eqmain", "pledit"]

# Winamp と同じイコライザーの周波数（Hz）
EQ_FREQS = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]
