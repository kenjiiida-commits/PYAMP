"""メインウィンドウ：メイン画面・EQ・プレイリストを縦に並べ、
再生エンジン・キー操作・メニュー・スキン・設定の保存をまとめる。"""
import json
import shutil
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox, QVBoxLayout, QWidget

from equalizer import EqualizerPanel
from jump import JumpDialog
from main_panel import MainPanel
from player import Player
from playlist import PlaylistPanel
from skin import Skin
from trackinfo import TrackInfoScanner

CONFIG_DIR = Path.home() / ".config" / "pyamp"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
PLAYLIST_FILE = CONFIG_DIR / "playlist.m3u8"
SKIN_DIR = CONFIG_DIR / "skins"
TRACKINFO_FILE = CONFIG_DIR / "trackinfo.json"
APP_NAME = "PYAMP"


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # --- 状態（画面はここを見て描く）---
        self.scale = 2
        self.skin = Skin()
        self.volume = 80
        self.balance = 0
        self.shuffle = False
        self.repeat = True
        self.show_eq = False
        self.show_pl = True
        self.show_remaining = False
        self.eq_on = True
        self.eq_auto = False
        self.eq_gains = [0] * 10
        self.preamp = 0
        self.auto_presets = {}          # AUTO 用：曲ごとの EQ
        self.position = 0
        self.duration = 0
        self.kbps = self.khz = self.channels = 0
        self.marquee_text = ""
        self._compact_saved = None

        self.player = Player(self)
        self.scanner = TrackInfoScanner(TRACKINFO_FILE, self)
        self.main = MainPanel(self)
        self.eq = EqualizerPanel(self)
        self.playlist = PlaylistPanel(self)
        self.playlist.play_requested.connect(self.play_row)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        for w in (self.main, self.eq, self.playlist):
            lay.addWidget(w)

        p = self.player
        p.position_changed.connect(self._on_position)
        p.state_changed.connect(lambda s: self.refresh())
        p.spectrum_changed.connect(self.main.feed_spectrum)
        p.title_changed.connect(self._on_title)
        p.info_changed.connect(self._on_info)
        p.finished.connect(self._on_finished)
        p.error.connect(self._on_error)

        self.vis_window = None
        self._make_shortcuts()
        self._load_settings()

    # ==================================================================
    # 画面の更新・大きさ
    # ==================================================================
    def refresh(self):
        for w in (self.main, self.eq, self.playlist):
            w.update()

    def fit_window(self):
        self.eq.setVisible(self.show_eq)
        self.playlist.setVisible(self.show_pl)
        h = self.main.height()
        if self.show_eq:
            h += self.eq.height()
        if self.show_pl:
            h += self.playlist.height()
        self.setFixedSize(self.main.width(), h)
        self.refresh()

    def set_scale(self, scale):
        self.scale = scale
        for w in (self.main, self.eq, self.playlist):
            w.update_size()
        self.playlist.apply_skin(self.skin)
        self.fit_window()

    def cycle_scale(self):
        self.set_scale({1: 2, 2: 3, 3: 1}[self.scale])

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange:
            self.refresh()        # タイトルバーの色（選択中/非選択）を切り替える
        super().changeEvent(e)

    # ==================================================================
    # スキン
    # ==================================================================
    def apply_skin(self, path=None):
        try:
            self.skin = Skin(path)
        except Exception as ex:  # 壊れたスキンでも落ちないように
            QMessageBox.warning(self, "スキン", f"スキンを読み込めませんでした:\n{ex}")
            self.skin = Skin()
        self.playlist.apply_skin(self.skin)
        self.refresh()

    def installed_skins(self):
        SKIN_DIR.mkdir(parents=True, exist_ok=True)
        items = [p for p in SKIN_DIR.iterdir()
                 if p.is_dir() or p.suffix.lower() in (".wsz", ".zip")]
        return sorted(items, key=lambda p: p.name.lower())

    def add_skin_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Winamp スキンを追加", str(Path.home() / "Downloads"),
                                           "Winamp スキン (*.wsz *.zip)")
        if f:
            SKIN_DIR.mkdir(parents=True, exist_ok=True)
            dest = SKIN_DIR / Path(f).name
            if Path(f).resolve() != dest.resolve():
                shutil.copy(f, dest)
            self.apply_skin(dest)

    # ==================================================================
    # メニュー
    # ==================================================================
    def show_main_menu(self, pos):
        m = QMenu(self)
        m.addAction("ファイルを開く… (L)", self.open_files)
        m.addAction("フォルダを追加… (Shift+L)", self.playlist.open_folder_dialog)
        m.addAction("曲にジャンプ… (J)", self.jump_to_file)
        m.addAction("ビジュアライザー (Ctrl+Shift+K)", self.open_visualizer)
        m.addSeparator()

        sm = m.addMenu("スキン")
        group = QActionGroup(sm)
        current = self.skin.path

        def add_skin_action(label, path):
            act = QAction(label, sm, checkable=True, checked=(current == (str(path) if path else None)))
            act.triggered.connect(lambda _=False, p=path: self.apply_skin(p))
            group.addAction(act)
            sm.addAction(act)

        add_skin_action("PYAMP 標準", None)
        for p in self.installed_skins():
            add_skin_action(p.stem, p)
        sm.addSeparator()
        sm.addAction("スキンファイル (.wsz) を追加…", self.add_skin_file)
        sm.addAction("スキンフォルダを開く", lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(SKIN_DIR))))
        sm.addAction("スキンを探す（Winamp Skin Museum）", lambda: QDesktopServices.openUrl(
            QUrl("https://skins.webamp.org/")))

        zm = m.addMenu("表示サイズ")
        zg = QActionGroup(zm)
        for s in (1, 2, 3):
            act = QAction(f"{s}倍", zm, checkable=True, checked=(self.scale == s))
            act.triggered.connect(lambda _=False, s=s: self.set_scale(s))
            zg.addAction(act)
            zm.addAction(act)

        m.addSeparator()
        for label, checked, fn in [("イコライザー (Alt+G)", self.show_eq, self.toggle_eq),
                                   ("プレイリスト (Alt+E)", self.show_pl, self.toggle_pl),
                                   ("残り時間で表示", self.show_remaining, self._toggle_remaining)]:
            act = QAction(label, m, checkable=True, checked=checked)
            act.triggered.connect(lambda _=False, fn=fn: fn())
            m.addAction(act)
        m.addAction("キー操作の一覧", self._show_keys)
        m.addSeparator()
        m.addAction("終了 (Ctrl+Q)", self.close)
        m.exec(pos)

    def _show_keys(self):
        QMessageBox.information(self, "キー操作", (
            "Z：前の曲　X：再生　C：一時停止　V：停止　B：次の曲\n"
            "L：ファイルを開く　Shift+L：フォルダを追加\n"
            "S：シャッフル　R：リピート\n"
            "←/→：5秒戻る/進む　↑/↓：音量\n"
            "Alt+G：イコライザー　Alt+E：プレイリスト\n"
            "J：曲名で探してジャンプ\n"
            "Ctrl+Shift+K：ビジュアライザー（曲に合わせて動く模様）\n"
            "Delete：選んだ曲を一覧から外す\n\n"
            "時間表示をクリック：残り時間表示に切り替え\n"
            "スペクトラムをクリック：表示の ON/OFF\n"
            "タイトルバーをダブルクリック：表示サイズの切り替え\n"
            "プレイリスト右下をドラッグ：高さを変える\n"
            "右クリック：メニュー（スキン変更など）"))

    # ==================================================================
    # キー操作
    # ==================================================================
    def _make_shortcuts(self):
        keys = {
            "Z": self.prev_track, "X": self.play, "C": self.pause, "V": self.stop, "B": self.next_track,
            "L": self.open_files, "Shift+L": self.playlist.open_folder_dialog,
            "S": self.toggle_shuffle, "R": self.toggle_repeat,
            "Alt+G": self.toggle_eq, "Alt+E": self.toggle_pl,
            "J": self.jump_to_file,
            "Ctrl+Shift+K": self.open_visualizer,
            "Left": lambda: self.player.seek(self.player.position() - 5000),
            "Right": lambda: self.player.seek(self.player.position() + 5000),
            "Ctrl+Q": self.close,
        }
        for key, slot in keys.items():
            QShortcut(QKeySequence(key), self).activated.connect(slot)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Up:
            self.set_volume(self.volume + 5)
        elif e.key() == Qt.Key_Down:
            self.set_volume(self.volume - 5)
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.play()
        else:
            super().keyPressEvent(e)

    # ==================================================================
    # 再生操作
    # ==================================================================
    def play_row(self, row):
        path = self.playlist.path_at(row)
        if not path:
            return
        self.playlist.set_current(row)
        self._set_marquee(row)
        self.kbps = self.khz = self.channels = 0
        self.player.load(path)
        if self.eq_auto and path in self.auto_presets:
            gains, pre = self.auto_presets[path]
            self.set_eq_gains(gains, remember=False)
            self.set_preamp(pre, remember=False)

    def _set_marquee(self, row):
        self.marquee_text = f"{row + 1}. {self.playlist.title_at(row)}"
        if self.duration > 0 and self.player.state() != "stopped":
            s = self.duration // 1000
            self.marquee_text += f" ({s // 60}:{s % 60:02d})"
        self.main.update()

    def play(self):
        state = self.player.state()
        if state == "paused":
            self.player.play()
        elif state == "playing":
            self.player.seek(0)
        else:
            row = self.playlist.selected_row()
            if row < 0:
                row = max(0, self.playlist.current_row())
            self.play_row(row)

    def pause(self):
        if self.player.state() == "playing":
            self.player.pause()
        elif self.player.state() == "paused":
            self.player.play()

    def stop(self):
        self.player.stop()

    def next_track(self):
        row = self.playlist.next_row(self.shuffle, True)
        if row >= 0:
            self.play_row(row)

    def prev_track(self):
        row = self.playlist.prev_row(self.shuffle)
        if row >= 0:
            self.play_row(row)

    def open_files(self):
        before = self.playlist.count()
        if self.playlist.open_files_dialog() and self.player.state() == "stopped":
            self.play_row(before)

    def jump_to_file(self):
        """J キー：曲名で探して、選んだ曲をすぐ再生する"""
        pl = self.playlist
        if pl.count() == 0:
            return
        entries = [(i, pl.title_at(i), pl.path_at(i)) for i in range(pl.count())]
        dlg = JumpDialog(self, entries, pl.current_row(), self.skin)
        if dlg.exec() and dlg.chosen >= 0:
            pl.view.clearSelection()
            pl.view.item(dlg.chosen).setSelected(True)
            self.play_row(dlg.chosen)

    def open_visualizer(self):
        """曲に合わせて動く模様の画面を開く（もう開いていれば前に出す）"""
        if self.vis_window is None:
            from visualizer import VisualizerWindow   # 使うときだけ読み込む
            self.vis_window = VisualizerWindow()
            self.player.spectrum_changed.connect(self.vis_window.feed)
            self.vis_window.closed.connect(self._visualizer_closed)
        self.vis_window.show()
        self.vis_window.raise_()
        self.vis_window.activateWindow()

    def _visualizer_closed(self):
        try:
            self.player.spectrum_changed.disconnect(self.vis_window.feed)
        except (RuntimeError, TypeError):
            pass
        self.vis_window = None

    def set_volume(self, v):
        self.volume = max(0, min(100, v))
        self.player.set_volume(self.volume)
        self.main.update()

    def set_balance(self, b):
        self.balance = max(-100, min(100, b))
        self.player.set_balance(self.balance)
        self.main.update()

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.main.update()

    def toggle_repeat(self):
        self.repeat = not self.repeat
        self.main.update()

    def _toggle_remaining(self):
        self.show_remaining = not self.show_remaining
        self.main.update()

    def toggle_eq(self, show=None):
        self.show_eq = (not self.show_eq) if show is None else show
        self.fit_window()

    def toggle_pl(self, show=None):
        self.show_pl = (not self.show_pl) if show is None else show
        self.fit_window()

    def toggle_compact(self):
        """EQ とプレイリストをまとめて隠す／元に戻す"""
        if self._compact_saved is None:
            self._compact_saved = (self.show_eq, self.show_pl)
            self.show_eq = self.show_pl = False
        else:
            self.show_eq, self.show_pl = self._compact_saved
            self._compact_saved = None
        self.fit_window()

    # --- イコライザー ---
    def toggle_eq_on(self):
        self.eq_on = not self.eq_on
        self.player.set_eq_enabled(self.eq_on)
        self.eq.update()

    def toggle_eq_auto(self):
        self.eq_auto = not self.eq_auto
        self.eq.update()

    def set_eq_band(self, i, db, remember=True):
        self.eq_gains[i] = db
        self.player.set_eq_band(i, db)
        self.eq.update()
        if remember:
            self._remember_auto()

    def set_eq_gains(self, gains, remember=True):
        for i, g in enumerate(gains):
            self.set_eq_band(i, g, remember=False)
        if remember:
            self._remember_auto()

    def set_all_eq(self, db):
        self.set_eq_gains([db] * 10)

    def set_preamp(self, db, remember=True):
        self.preamp = db
        self.player.set_preamp(db)
        self.eq.update()
        if remember:
            self._remember_auto()

    def _remember_auto(self):
        if self.eq_auto:
            path = self.playlist.path_at(self.playlist.current_row())
            if path:
                self.auto_presets[path] = (list(self.eq_gains), self.preamp)

    # ==================================================================
    # エンジンからのお知らせ
    # ==================================================================
    def _on_position(self, pos, dur):
        first = dur > 0 and self.duration != dur
        self.position, self.duration = pos, dur
        if first:
            self._set_marquee(self.playlist.current_row())
            self.playlist.set_duration(self.playlist.current_row(), dur)
        self.main.update_logical(24, 26, 80, 14)    # 時間
        self.main.update_logical(16, 72, 248, 10)   # シークバー
        if self.show_pl:
            w, h = self.playlist.logical_size()
            self.playlist.update_logical(w - 150, h - 38, 150, 38)   # 合計時間と再生位置の両方

    def _on_title(self, title):
        row = self.playlist.current_row()
        if row >= 0:
            self.playlist.set_title(row, title)
            self._set_marquee(row)

    def _on_info(self, kbps, khz, channels):
        self.kbps, self.khz, self.channels = kbps, khz, channels
        self.main.update()

    def _on_finished(self):
        row = self.playlist.next_row(self.shuffle, self.repeat)
        if row >= 0:
            self.play_row(row)
        else:
            self.position = 0
            self.refresh()

    def _on_error(self, message):
        name = self.playlist.title_at(self.playlist.current_row())
        self.marquee_text = f"再生できません: {name} ({message})"
        self.main.update()
        QTimer.singleShot(1500, self._on_finished)

    # ==================================================================
    # ドラッグ＆ドロップ（メイン画面・EQに落とすと、一覧を入れ替えてすぐ再生）
    # ==================================================================
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        skins = [p for p in paths if p.lower().endswith(".wsz")]
        if skins:                                # スキンを落としたら、スキンとして追加
            SKIN_DIR.mkdir(parents=True, exist_ok=True)
            dest = SKIN_DIR / Path(skins[0]).name
            if Path(skins[0]).resolve() != dest.resolve():
                shutil.copy(skins[0], dest)
            self.apply_skin(dest)
            return
        self.player.stop()
        self.playlist.clear()
        if self.playlist.add_paths(paths):
            self.play_row(0)

    # ==================================================================
    # 設定の保存と読み込み
    # ==================================================================
    def _load_settings(self):
        s = {}
        try:
            s = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        self.scale = s.get("scale", 2)
        skin_path = s.get("skin")
        if skin_path and Path(skin_path).exists():
            self.apply_skin(skin_path)
        else:
            self.apply_skin(None)
        self.set_volume(s.get("volume", 80))
        self.set_balance(s.get("balance", 0))
        self.shuffle = s.get("shuffle", False)
        self.repeat = s.get("repeat", True)
        self.show_remaining = s.get("remaining", False)
        gains = s.get("eq", [0] * 10)
        self.set_eq_gains(gains if len(gains) == 10 else [0] * 10, remember=False)
        self.set_preamp(s.get("preamp", 0), remember=False)
        self.eq_on = s.get("eq_on", True)
        self.player.set_eq_enabled(self.eq_on)
        self.eq_auto = s.get("eq_auto", False)
        self.auto_presets = {k: tuple(v) for k, v in s.get("auto_presets", {}).items()}
        self.show_eq = s.get("show_eq", False)
        self.show_pl = s.get("show_pl", True)
        self.playlist.rows = s.get("playlist_rows", 4)
        if PLAYLIST_FILE.exists():
            self.playlist.add_paths([str(PLAYLIST_FILE)])
            row = s.get("current", -1)
            if 0 <= row < self.playlist.count():
                self.playlist.set_current(row)
                self._set_marquee(row)
        if not self.marquee_text:
            self.marquee_text = "PYAMP - drop music here or press L"
        self.set_scale(self.scale)

    def _save_settings(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        s = {
            "scale": self.scale, "skin": self.skin.path,
            "volume": self.volume, "balance": self.balance,
            "shuffle": self.shuffle, "repeat": self.repeat, "remaining": self.show_remaining,
            "eq": self.eq_gains, "preamp": self.preamp, "eq_on": self.eq_on,
            "eq_auto": self.eq_auto, "auto_presets": self.auto_presets,
            "show_eq": self.show_eq, "show_pl": self.show_pl,
            "playlist_rows": self.playlist.rows,
            "current": self.playlist.current_row(),
        }
        SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        self.playlist.save_m3u(PLAYLIST_FILE)
        self.scanner.save()

    def closeEvent(self, e):
        if self.vis_window is not None:
            self.vis_window.close()
        try:
            self._save_settings()
        finally:
            self.player.shutdown()
        super().closeEvent(e)
