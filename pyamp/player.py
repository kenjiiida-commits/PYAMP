"""再生エンジン：GStreamer を使って音を鳴らす部分。

画面（PySide6）とは「シグナル」でやりとりします。
  画面 → エンジン : play() / pause() / seek() などのメソッドを呼ぶ
  エンジン → 画面 : position_changed などのシグナルを出す

音の流れ（パイプライン）:
  ファイル → デコード → [プリアンプ → イコライザー → スペクトラム解析] → スピーカー
                          ↑ この部分を自分で組み立てて playbin に差し込んでいます
"""
import re
from collections import deque

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402

Gst.init(None)

from sprites import EQ_FREQS  # noqa: E402  Winamp と同じ 60Hz〜16kHz
from textfix import fix_mojibake  # noqa: E402

# スペクトラムのメッセージから数値の並びを取り出すための正規表現
_MAG_RE = re.compile(r"magnitude=\(float\)\{([^}]*)\}")


class Player(QObject):
    position_changed = Signal(int, int)  # 再生位置(ミリ秒), 曲の長さ(ミリ秒)
    state_changed = Signal(str)          # "playing" / "paused" / "stopped"
    spectrum_changed = Signal(list)      # 各周波数帯の強さ(dB, -80〜0)
    title_changed = Signal(str)          # 曲のタグから読んだ「アーティスト - 曲名」
    finished = Signal()                  # 曲の最後まで再生した
    error = Signal(str)
    info_changed = Signal(int, int, int)  # ビットレート(kbps), サンプリング周波数(kHz), チャンネル数

    SPECTRUM_BANDS = 256   # 解析する周波数帯の数（画面側で約20本にまとめます）
    THRESHOLD_DB = -80     # これより小さい音は無音扱い

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "stopped"
        self._spectrum_queue = deque()

        self._playbin = Gst.ElementFactory.make("playbin", "player")
        if self._playbin is None:
            raise RuntimeError("GStreamer の playbin が見つかりません。")
        # 音声だけを扱う（MP3のジャケット画像などを映像として開かないように）
        self._playbin.set_property("flags", 0x2 | 0x10)  # AUDIO | SOFT_VOLUME
        # 音の出口：Ubuntu 標準（PipeWire の PulseAudio 互換）を優先して使う
        sink = Gst.ElementFactory.make("pulsesink", "sink")
        if sink is not None:
            sink.set_property("client-name", "PYAMP")
            self._playbin.set_property("audio-sink", sink)

        # --- 自作の音声フィルター部分を組み立てる ---
        conv_in = Gst.ElementFactory.make("audioconvert", None)
        self._preamp = Gst.ElementFactory.make("volume", "preamp")
        self._eq = Gst.ElementFactory.make("equalizer-nbands", "eq")
        self._spectrum = Gst.ElementFactory.make("spectrum", "spectrum")
        self._panorama = Gst.ElementFactory.make("audiopanorama", "balance")
        conv_out = Gst.ElementFactory.make("audioconvert", None)
        for name, el in [("イコライザー", self._eq), ("スペクトラム", self._spectrum),
                         ("バランス", self._panorama)]:
            if el is None:
                raise RuntimeError(
                    f"{name}の部品がありません。gstreamer1.0-plugins-good を入れてください。")

        self._spectrum.set_property("bands", self.SPECTRUM_BANDS)
        self._spectrum.set_property("threshold", self.THRESHOLD_DB)
        self._spectrum.set_property("interval", 30 * Gst.MSECOND)
        self._spectrum.set_property("post-messages", True)

        # イコライザーを Winamp と同じ10個の周波数にする
        self._eq.set_property("num-bands", len(EQ_FREQS))
        self._bands = []
        for i, hz in enumerate(EQ_FREQS):
            band = self._eq.get_child_by_index(i)
            band.set_property("freq", float(hz))
            band.set_property("bandwidth", hz * 0.7)
            band.set_property("gain", 0.0)
            self._bands.append(band)

        fbin = Gst.Bin.new("audio_filter")
        chain = [conv_in, self._preamp, self._eq, self._spectrum, self._panorama, conv_out]
        for el in chain:
            fbin.add(el)
        for a, b in zip(chain, chain[1:]):
            a.link(b)
        fbin.add_pad(Gst.GhostPad.new("sink", conv_in.get_static_pad("sink")))
        fbin.add_pad(Gst.GhostPad.new("src", conv_out.get_static_pad("src")))
        self._playbin.set_property("audio-filter", fbin)

        self._bus = self._playbin.get_bus()

        # GStreamer からのお知らせを定期的に確認するタイマー
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(20)

        self._eq_gains = [0.0] * len(EQ_FREQS)
        self._eq_enabled = True
        self._kbps = self._khz = self._channels = 0

    # ------------------------------------------------------------------
    # 画面から呼ぶ操作
    # ------------------------------------------------------------------
    def load(self, path: str):
        """ファイルを開いてすぐ再生する"""
        self._playbin.set_state(Gst.State.NULL)
        self._spectrum_queue.clear()
        self._kbps = self._khz = self._channels = 0
        self._playbin.set_property("uri", Gst.filename_to_uri(path))
        self._playbin.set_state(Gst.State.PLAYING)
        self._set_state("playing")

    def play(self):
        self._playbin.set_state(Gst.State.PLAYING)
        self._set_state("playing")

    def pause(self):
        if self._state == "playing":
            self._playbin.set_state(Gst.State.PAUSED)
            self._set_state("paused")

    def stop(self):
        self._playbin.set_state(Gst.State.NULL)
        self._spectrum_queue.clear()
        self._set_state("stopped")
        self.position_changed.emit(0, 0)
        self.spectrum_changed.emit([])

    def seek(self, ms: int):
        if self._state == "stopped":
            return
        self._playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            max(0, ms) * Gst.MSECOND,
        )
        self._spectrum_queue.clear()

    def position(self) -> int:
        ok, pos = self._playbin.query_position(Gst.Format.TIME)
        return pos // Gst.MSECOND if ok else 0

    def state(self) -> str:
        return self._state

    def set_volume(self, percent: int):
        """音量 0〜100"""
        v = max(0, min(100, percent)) / 100
        self._playbin.set_property("volume", v ** 2)  # 耳の感じ方に合わせて2乗

    def set_preamp(self, db: float):
        self._preamp.set_property("volume", 10 ** (db / 20))

    def set_balance(self, percent: int):
        """左右のバランス -100(左)〜0(中央)〜100(右)"""
        self._panorama.set_property("panorama", max(-100, min(100, percent)) / 100)

    def set_eq_band(self, index: int, db: float):
        self._eq_gains[index] = db
        if self._eq_enabled:
            self._bands[index].set_property("gain", float(db))

    def set_eq_enabled(self, enabled: bool):
        self._eq_enabled = enabled
        for band, g in zip(self._bands, self._eq_gains):
            band.set_property("gain", float(g) if enabled else 0.0)

    def shutdown(self):
        self._timer.stop()
        self._playbin.set_state(Gst.State.NULL)

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------
    def _set_state(self, state: str):
        if state != self._state:
            self._state = state
            self.state_changed.emit(state)

    def _poll(self):
        while True:
            msg = self._bus.pop()
            if msg is None:
                break
            self._handle_message(msg)

        if self._state != "stopped":
            ok1, pos = self._playbin.query_position(Gst.Format.TIME)
            ok2, dur = self._playbin.query_duration(Gst.Format.TIME)
            self.position_changed.emit(
                pos // Gst.MSECOND if ok1 else 0,
                dur // Gst.MSECOND if ok2 else 0,
            )
        self._emit_due_spectrum()

    def _handle_message(self, msg):
        t = msg.type
        if t == Gst.MessageType.EOS:
            self._playbin.set_state(Gst.State.NULL)
            self._set_state("stopped")
            self.finished.emit()
        elif t == Gst.MessageType.ERROR:
            err, _debug = msg.parse_error()
            self._playbin.set_state(Gst.State.NULL)
            self._set_state("stopped")
            self.error.emit(err.message)
        elif t == Gst.MessageType.TAG:
            taglist = msg.parse_tag()
            for key in ("bitrate", "nominal-bitrate"):
                ok_b, bitrate = taglist.get_uint(key)
                if ok_b and bitrate:
                    self._kbps = round(bitrate / 1000)
                    self._emit_info()
                    break
            ok_t, title = taglist.get_string("title")
            ok_a, artist = taglist.get_string("artist")
            title, artist = fix_mojibake(title or ""), fix_mojibake(artist or "")
            if ok_t and title:
                self.title_changed.emit(f"{artist} - {title}" if ok_a and artist else title)
        elif t == Gst.MessageType.STATE_CHANGED and msg.src == self._playbin:
            _old, new, _pending = msg.parse_state_changed()
            if new == Gst.State.PLAYING and not self._channels:
                self._read_audio_format()
        elif t == Gst.MessageType.ELEMENT:
            s = msg.get_structure()
            if s is not None and s.get_name() == "spectrum":
                self._queue_spectrum(s)

    def _read_audio_format(self):
        """サンプリング周波数とモノラル/ステレオを調べる"""
        pad = self._playbin.emit("get-audio-pad", 0)
        caps = pad.get_current_caps() if pad else None
        if caps and caps.get_size():
            st = caps.get_structure(0)
            ok_r, rate = st.get_int("rate")
            ok_c, ch = st.get_int("channels")
            if ok_r:
                self._khz = round(rate / 1000)
            if ok_c:
                self._channels = ch
            self._emit_info()

    def _emit_info(self):
        self.info_changed.emit(self._kbps, self._khz, self._channels)

    def _queue_spectrum(self, s):
        """解析結果は実際に音が出るより少し早く届くので、その音が鳴る時刻まで待たせる。
        時刻は「曲の中の位置（stream-time）」で比べる。
        （音の出口の時計は曲が変わるとリセットされることがあり、それで比べると止まってしまうため）"""
        m = _MAG_RE.search(s.to_string())
        if not m:
            return
        values = [float(x) for x in m.group(1).split(",")]
        ok, stream_time = s.get_uint64("stream-time")
        if not ok:
            stream_time = s.get_value("running-time")
        end = stream_time + s.get_value("duration")
        self._spectrum_queue.append((end, values))
        while len(self._spectrum_queue) > 50:
            self._spectrum_queue.popleft()

    def _emit_due_spectrum(self):
        if not self._spectrum_queue or self._state != "playing":
            return
        ok, now = self._playbin.query_position(Gst.Format.TIME)
        latest = None
        while self._spectrum_queue:
            end = self._spectrum_queue[0][0]
            # 位置が分からない・大きくずれている（2秒以上先）ときは待たずに出す（止まったままにしない）
            if not ok or end <= now or end - now > 2 * Gst.SECOND:
                latest = self._spectrum_queue.popleft()[1]
            else:
                break
        if latest is not None:
            self.spectrum_changed.emit(latest)
