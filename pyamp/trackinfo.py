"""曲の長さとタグ（アーティスト・曲名）を裏で調べる係。

- 画面が固まらないよう、別のスレッドで1曲ずつ調べる
- 調べた結果はファイル（~/.config/pyamp/trackinfo.json）に保存して、次回からはすぐ使う
  （ファイルの更新日時と大きさが変わっていたら調べ直す）
"""
import json
import queue
import threading
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GstPbutils  # noqa: E402

from PySide6.QtCore import QObject, Signal  # noqa: E402

from textfix import fix_mojibake  # noqa: E402


def _stamp(path):
    try:
        st = Path(path).stat()
        return [int(st.st_mtime), st.st_size]
    except OSError:
        return None


class TrackInfoScanner(QObject):
    found = Signal(str, int, str)   # ファイル, 長さ(ミリ秒, 不明なら -1), 表示名(タグがなければ "")

    def __init__(self, cache_file: Path, parent=None):
        super().__init__(parent)
        self._cache_file = cache_file
        self._cache = {}
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._queued = set()
        try:
            self._cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._cache = {}
        self._thread = threading.Thread(target=self._work, daemon=True)
        self._thread.start()

    def cached(self, path):
        """保存済みで、ファイルが変わっていなければ (長さ, 表示名) を返す"""
        with self._lock:
            entry = self._cache.get(path)
        if entry and entry.get("stamp") == _stamp(path):
            return entry["ms"], fix_mojibake(entry.get("title", ""))
        return None

    def request(self, paths):
        """調べてほしい曲を順番待ちに入れる（保存済みのものはすぐ結果を返す）"""
        for path in paths:
            hit = self.cached(path)
            if hit is not None:
                self.found.emit(path, hit[0], hit[1])
            elif path not in self._queued:
                self._queued.add(path)
                self._queue.put(path)

    def save(self):
        with self._lock:
            data = dict(self._cache)
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    # --- ここから下は別スレッドで動く ---------------------------------------
    def _work(self):
        discoverer = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        while True:
            path = self._queue.get()
            ms, title = -1, ""
            try:
                info = discoverer.discover_uri(Gst.filename_to_uri(path))
                dur = info.get_duration()
                if dur and dur > 0:
                    ms = dur // Gst.MSECOND
                for stream in info.get_audio_streams():
                    tags = stream.get_tags()
                    if tags:
                        ok_t, t = tags.get_string("title")
                        ok_a, a = tags.get_string("artist")
                        t, a = fix_mojibake(t or ""), fix_mojibake(a or "")
                        if ok_t and t.strip():
                            title = f"{a.strip()} - {t.strip()}" if ok_a and a.strip() else t.strip()
                        break
            except Exception:  # 壊れたファイルなど：長さ不明のまま
                pass
            with self._lock:
                self._cache[path] = {"stamp": _stamp(path), "ms": ms, "title": title}
            self._queued.discard(path)
            self.found.emit(path, ms, title)
