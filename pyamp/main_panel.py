"""メイン画面（Winamp の 275×116 の部分）"""
import math

from PySide6.QtCore import QRect, QTimer

from skinwidget import Button, Drag, SkinWidget
from sprites import MAIN_POS as P


def time_digits(ms):
    s = max(0, ms) // 1000
    m = min(99, s // 60)
    return f"{m:02d}{s % 60:02d}"


def mmss(ms):
    s = int(max(0, ms) // 1000)
    return f"{s // 60}:{s % 60:02d}"


class Visualizer:
    """スペクトラムのバー19本の高さを計算する係（Winamp と同じ 3px 幅 × 19本）"""
    BARS = 19
    HEIGHT = 16

    def __init__(self):
        self.levels = [0.0] * self.BARS
        self.peaks = [0.0] * self.BARS
        self.hold = [0] * self.BARS
        self._ranges = []

    def _make_ranges(self, n, rate=44100):
        band_hz = rate / 2 / n
        lo_hz, hi_hz = 50, 16000
        edges = [lo_hz * (hi_hz / lo_hz) ** (i / self.BARS) for i in range(self.BARS + 1)]
        self._ranges = []
        for lo, hi in zip(edges, edges[1:]):
            a = min(int(lo / band_hz), n - 1)
            b = min(max(a + 1, int(math.ceil(hi / band_hz))), n)
            self._ranges.append((a, b))

    def feed(self, mags):
        if not mags:
            return
        if len(self._ranges) != self.BARS or self._ranges[-1][1] > len(mags):
            self._make_ranges(len(mags))
        for i, (a, b) in enumerate(self._ranges):
            level = max(0.0, min(1.0, (max(mags[a:b]) + 70) / 60)) * self.HEIGHT
            self.levels[i] = max(self.levels[i], level)
            if level >= self.peaks[i]:
                self.peaks[i] = level
                self.hold[i] = 10

    def step(self):
        """少しずつ下に落とす。動きがあれば True"""
        moved = False
        for i in range(self.BARS):
            if self.levels[i] > 0:
                self.levels[i] = max(0.0, self.levels[i] - 0.9)
                moved = True
            if self.hold[i]:
                self.hold[i] -= 1
            elif self.peaks[i] > 0:
                self.peaks[i] = max(0.0, self.peaks[i] - 0.35)
                moved = True
        return moved


class MainPanel(SkinWidget):
    def __init__(self, app):
        super().__init__(app)
        self.vis = Visualizer()
        self.vis_on = True
        self.marquee_offset = 0
        self.message = None          # ドラッグ中などに一時的に出す文字
        self._seek_x = None          # シークバーをドラッグ中のつまみ位置
        self._vol_drag = self._bal_drag = False
        self._blink = True

        a = app
        btn = Button
        self.buttons = [
            btn(QRect(*P["OPTIONS"], 9, 9), None, "OPTIONS_P", self._options, tip="メニュー"),
            btn(QRect(*P["MINIMIZE"], 9, 9), None, "MINIMIZE_P", lambda: a.showMinimized(), tip="最小化"),
            btn(QRect(*P["SHADE"], 9, 9), None, "SHADE_P", a.toggle_compact, tip="EQ・プレイリストをまとめて隠す/出す"),
            btn(QRect(*P["CLOSE"], 9, 9), None, "CLOSE_P", a.close, tip="閉じる"),
            btn(QRect(*P["PREV"], 23, 18), "PREV", "PREV_P", a.prev_track, tip="前の曲 (Z)"),
            btn(QRect(*P["PLAY"], 23, 18), "PLAY", "PLAY_P", a.play, tip="再生 (X)"),
            btn(QRect(*P["PAUSE"], 23, 18), "PAUSE", "PAUSE_P", a.pause, tip="一時停止 (C)"),
            btn(QRect(*P["STOP"], 23, 18), "STOP", "STOP_P", a.stop, tip="停止 (V)"),
            btn(QRect(*P["NEXT"], 22, 18), "NEXT", "NEXT_P", a.next_track, tip="次の曲 (B)"),
            btn(QRect(*P["EJECT"], 22, 16), "EJECT", "EJECT_P", a.open_files, tip="ファイルを開く (L)"),
            btn(QRect(*P["SHUFFLE"], 47, 15), "SHUFFLE", "SHUFFLE_P", a.toggle_shuffle,
                lambda: a.shuffle, "SHUFFLE_ON", "SHUFFLE_ON_P", "シャッフル (S)"),
            btn(QRect(*P["REPEAT"], 28, 15), "REPEAT", "REPEAT_P", a.toggle_repeat,
                lambda: a.repeat, "REPEAT_ON", "REPEAT_ON_P", "リピート (R)"),
            btn(QRect(*P["EQ_BTN"], 23, 12), "EQ_BTN", "EQ_BTN_P", lambda: a.toggle_eq(),
                lambda: a.show_eq, "EQ_BTN_ON", "EQ_BTN_ON_P", "イコライザー (Alt+G)"),
            btn(QRect(*P["PL_BTN"], 23, 12), "PL_BTN", "PL_BTN_P", lambda: a.toggle_pl(),
                lambda: a.show_pl, "PL_BTN_ON", "PL_BTN_ON_P", "プレイリスト (Alt+E)"),
        ]
        vx, vy, vw, vh = P["VOLUME"]
        bx, by, bw, bh = P["BALANCE"]
        px, py, pw, ph = P["POS"]
        self.drags = [
            Drag(QRect(vx, vy, vw, vh), self._vol_start, self._vol_move, self._vol_end, "音量 (↑↓)"),
            Drag(QRect(bx, by, bw, bh), self._bal_start, self._bal_move, self._bal_end, "左右のバランス"),
            Drag(QRect(px, py, pw, ph), self._seek_start, self._seek_move, self._seek_end, "再生位置 (←→)"),
        ]

        self._anim = QTimer(self)        # スペクトラムと曲名スクロールのアニメーション
        self._anim.timeout.connect(self._tick)
        self._anim.start(30)
        self._tick_count = 0

    # ------------------------------------------------------------------
    # 描画
    # ------------------------------------------------------------------
    def paint(self, p, skin):
        a = self.app
        state = a.player.state()
        skin.draw(p, "MAIN_BG", 0, 0)
        skin.draw(p, "TITLE_ACTIVE" if self.active else "TITLE", 0, 0)

        # 再生状態のマーク
        ind = {"playing": "IND_PLAY", "paused": "IND_PAUSE", "stopped": "IND_STOP"}[state]
        skin.draw(p, ind, *P["IND"])
        if state == "playing":
            skin.draw(p, "IND_WORKING", *P["WORK"])

        # 時間（一時停止中は点滅）
        if state != "stopped" and (state == "playing" or self._blink):
            ms = a.position
            if a.show_remaining and a.duration > 0:
                ms = a.duration - a.position
                if skin.nums_ex:      # 新しい形式：数字画像の12番目がマイナス記号
                    skin.draw_part(p, "numbers", 99, 0, 9, 13, 38, P["DIGIT_Y"])
                else:
                    skin.draw(p, "MINUS", *P["MINUS"])
            for x, d in zip(P["DIGITS"], time_digits(ms)):
                skin.draw_part(p, "numbers", int(d) * 9, 0, 9, 13, x, P["DIGIT_Y"])

        self._paint_vis(p, skin)
        self._paint_marquee(p, skin)

        # kbps / kHz / モノラル・ステレオ
        if state != "stopped":
            if a.kbps:
                skin.draw_text(p, f"{min(a.kbps, 999):>3}", P["KBPS"][0], P["KBPS"][1])
            if a.khz:
                skin.draw_text(p, f"{min(a.khz, 99):>2}", P["KHZ"][0], P["KHZ"][1])
        ch = a.channels if state != "stopped" else 0
        skin.draw(p, "MONO_ON" if ch == 1 else "MONO", *P["MONO"])
        skin.draw(p, "STEREO_ON" if ch >= 2 else "STEREO", *P["STEREO"])

        # 音量・バランス
        vx, vy, _, _ = P["VOLUME"]
        frame = max(0, round(a.volume / 100 * 28) - 1)
        skin.draw_part(p, "volume", 0, frame * 15, 68, 13, vx, vy)
        skin.draw(p, "VOL_THUMB_P" if self._vol_drag else "VOL_THUMB", vx + round(a.volume / 100 * 54), vy + 1)
        bx, by, _, _ = P["BALANCE"]
        frame = min(27, math.floor(abs(a.balance) / 100 * 27))
        skin.draw_part(p, "balance", 9, frame * 15, 38, 13, bx, by)
        skin.draw(p, "BAL_THUMB_P" if self._bal_drag else "BAL_THUMB",
                  bx + round((a.balance + 100) / 200 * 24), by + 1)

        # シークバー
        px, py, _, _ = P["POS"]
        skin.draw(p, "POS_BG", px, py)
        if state != "stopped" and a.duration > 0:
            if self._seek_x is not None:
                tx = self._seek_x
            else:
                tx = round(a.position / a.duration * 219)
            skin.draw(p, "POS_THUMB_P" if self._seek_x is not None else "POS_THUMB", px + tx, py)

        self.draw_buttons(p, skin)

    def _paint_vis(self, p, skin):
        x0, y0, w, h = P["VIS"]
        c = skin.viscolors
        p.fillRect(x0, y0, w, h, c[0])
        for y in range(1, h, 2):
            for x in range(0, w, 2):
                p.fillRect(x0 + x, y0 + y, 1, 1, c[1])
        if not self.vis_on:
            return
        for i in range(Visualizer.BARS):
            bx = x0 + i * 4
            hgt = int(self.vis.levels[i])
            for y in range(h - hgt, h):
                p.fillRect(bx, y0 + y, 3, 1, c[2 + y])
            pk = int(self.vis.peaks[i])
            if pk > 0:
                p.fillRect(bx, y0 + h - pk, 3, 1, c[23])

    def marquee_string(self):
        if self.message:
            return self.message
        return self.app.marquee_text

    def _paint_marquee(self, p, skin):
        x, y, w, h = P["MARQUEE"]
        text = self.marquee_string()
        p.save()
        p.setClipRect(QRect(x, y - 3, w, h + 6))
        width = skin.measure(text)
        if self.message or width <= w:
            skin.draw_text(p, text, x, y)
        else:
            loop_text = text + "  ***  "
            loop = skin.measure(loop_text)
            off = self.marquee_offset % loop
            xx = x - off
            while xx < x + w:
                skin.draw_text(p, loop_text, xx, y)
                xx += loop
        p.restore()

    # ------------------------------------------------------------------
    # アニメーション
    # ------------------------------------------------------------------
    def _tick(self):
        self._tick_count += 1
        if self.vis.step() or self.app.player.state() == "playing":
            self.update_logical(*P["VIS"])
        if self._tick_count % 2 == 0:
            self.marquee_offset += 1
            x, y, w, h = P["MARQUEE"]
            self.update_logical(x, y - 3, w, h + 6)
        if self._tick_count % 17 == 0:
            self._blink = not self._blink
            if self.app.player.state() == "paused":
                self.update_logical(36, 26, 64, 13)

    def feed_spectrum(self, mags):
        if self.vis_on:
            self.vis.feed(mags)

    # ------------------------------------------------------------------
    # クリック・ドラッグ
    # ------------------------------------------------------------------
    def _options(self):
        self.app.show_main_menu(self.mapToGlobal(self.rect().topLeft()) + self._offset(6, 12))

    def _offset(self, x, y):
        from PySide6.QtCore import QPoint
        return QPoint(x * self.s, y * self.s)

    def click(self, x, y):
        if QRect(36, 26, 64, 13).contains(x, y):
            self.app.show_remaining = not self.app.show_remaining
            self.update()
            return True
        if QRect(*P["VIS"]).contains(x, y):
            self.vis_on = not self.vis_on
            self.vis.levels = [0.0] * Visualizer.BARS
            self.vis.peaks = [0.0] * Visualizer.BARS
            self.update()
            return True
        return False

    def mouseDoubleClickEvent(self, e):
        x, y = self._pos(e)
        if y < 14:
            self.app.cycle_scale()
        elif QRect(*P["VIS"]).contains(x, y):
            self.app.open_visualizer()          # スペクトラムをダブルクリック → ビジュアライザー

    # 音量
    def _vol_start(self, x, y):
        self._vol_drag = True
        self._vol_move(x, y)

    def _vol_move(self, x, y):
        v = round(max(0, min(54, x - P["VOLUME"][0] - 7)) / 54 * 100)
        self.app.set_volume(v)
        self.message = f"volume: {v}%"
        self.update()

    def _vol_end(self, x, y):
        self._vol_drag = False
        self.message = None
        self.update()

    # バランス
    def _bal_start(self, x, y):
        self._bal_drag = True
        self._bal_move(x, y)

    def _bal_move(self, x, y):
        b = round(max(0, min(24, x - P["BALANCE"][0] - 7)) / 24 * 200 - 100)
        if abs(b) < 25:
            b = 0                     # 真ん中付近は中央に吸い付く（Winamp と同じ）
        self.app.set_balance(b)
        self.message = "balance: center" if b == 0 else \
            f"balance: {abs(b)}% {'right' if b > 0 else 'left'}"
        self.update()

    def _bal_end(self, x, y):
        self._bal_drag = False
        self.message = None
        self.update()

    # シーク
    def _seek_start(self, x, y):
        if self.app.player.state() == "stopped" or self.app.duration <= 0:
            return
        self._seek_move(x, y)

    def _seek_move(self, x, y):
        if self.app.player.state() == "stopped" or self.app.duration <= 0:
            return
        self._seek_x = max(0, min(219, x - P["POS"][0] - 14))
        pct = self._seek_x / 219
        self.message = f"seek to: {mmss(self.app.duration * pct)}/{mmss(self.app.duration)} ({round(pct * 100)}%)"
        self.update()

    def _seek_end(self, x, y):
        if self._seek_x is not None:
            self.app.player.seek(int(self.app.duration * self._seek_x / 219))
        self._seek_x = None
        self.message = None
        self.update()
