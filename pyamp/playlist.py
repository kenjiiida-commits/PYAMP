"""プレイリスト画面：スキンの枠の中に曲の一覧を表示する。
ドラッグ＆ドロップでの追加・並べ替え、m3u の保存/読込、ADD/REM/SEL/MISC/LIST メニュー。
"""
import os
import random
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QListWidget, QListWidgetItem,
                               QMenu, QStyle, QStyledItemDelegate)

from skinwidget import Button, Drag, SkinWidget

AUDIO_EXTS = {".mp3", ".ogg", ".oga", ".opus", ".flac", ".wav", ".m4a", ".aac", ".wma"}

PATH_ROLE = Qt.UserRole          # ファイルの場所
TITLE_ROLE = Qt.UserRole + 1     # 表示する名前
CURRENT_ROLE = Qt.UserRole + 2   # 今再生中の曲なら True
DUR_ROLE = Qt.UserRole + 3       # 曲の長さ（ミリ秒）。まだ分からなければ None、調べても不明なら -1

TOP_H, BOTTOM_H, ROW_STEP = 20, 38, 29


def expand_paths(paths):
    """フォルダが混じっていたら中の音楽ファイルを全部（サブフォルダも）探して並べる"""
    result = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS]
            result.extend(sorted(files, key=lambda f: str(f).lower()))
        elif p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            result.append(p)
        elif p.is_file() and p.suffix.lower() in {".m3u", ".m3u8"}:
            result.extend(read_m3u(p))
    return [str(f) for f in result]


def read_m3u(path):
    base = Path(path).parent
    files = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = Path(line)
        if not f.is_absolute():
            f = base / f
        if f.is_file():
            files.append(f)
    return files


class PlaylistView(QListWidget):
    """外からのファイルのドロップと、中での並べ替えの両方に対応した一覧"""

    files_dropped = Signal(list, int)  # ファイル一覧, 挿入する行(-1なら末尾)
    delete_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setFrameShape(QListWidget.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setUniformItemSizes(True)
        self.setTextElideMode(Qt.ElideRight)

    def _is_external(self, e):
        return e.mimeData().hasUrls() and e.source() is not self

    def dragEnterEvent(self, e):
        if self._is_external(e):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self._is_external(e):
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if self._is_external(e):
            paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
            row = self.indexAt(e.position().toPoint()).row()
            self.files_dropped.emit(paths, row)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.delete_pressed.emit()
        else:
            super().keyPressEvent(e)


class TrackDelegate(QStyledItemDelegate):
    """一覧の1行を描く係：左に「番号. 曲名」、右端に曲の長さ（Winamp と同じ並び）"""

    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel

    def paint(self, p, option, index):
        pl = self.panel.app.skin.pl
        s = self.panel.s
        r = option.rect
        if option.state & QStyle.State_Selected:
            p.fillRect(r, QColor(pl["selectedbg"]))
        color = QColor(pl["current"] if index.data(CURRENT_ROLE) else pl["normal"])
        p.save()
        p.setFont(option.font)
        p.setPen(color)
        fm = option.fontMetrics
        pad = 2 * s
        ms = index.data(DUR_ROLE)
        dur_text = fmt_time(ms) if ms is not None and ms >= 0 else ""
        dur_w = fm.horizontalAdvance(dur_text) + pad * 2 if dur_text else pad
        title = fm.elidedText(index.data(Qt.DisplayRole) or "", Qt.ElideRight, r.width() - pad - dur_w)
        p.drawText(r.adjusted(pad, 0, -dur_w, 0), Qt.AlignVCenter | Qt.AlignLeft, title)
        if dur_text:
            p.drawText(r.adjusted(0, 0, -pad, 0), Qt.AlignVCenter | Qt.AlignRight, dur_text)
        p.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(13 * self.panel.s)
        return size


def fmt_time(ms):
    """ミリ秒を 3:45 や 1:02:03 の形にする"""
    sec = int(max(0, ms) // 1000)
    h, m, x = sec // 3600, sec // 60 % 60, sec % 60
    return f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}"


def short_time(ms, level=0):
    """短い時間表示。level 0: 1:02:03　1: 1h02m　2: 1h（1時間未満はいつも 3:45）"""
    sec = int(max(0, ms) // 1000)
    h, m = sec // 3600, sec // 60 % 60
    if h == 0 or level == 0:
        return fmt_time(ms)
    return f"{h}h{m:02d}m" if level == 1 else f"{h}h"


class PlaylistPanel(SkinWidget):
    play_requested = Signal(int)  # この行の曲を再生して
    rows = 4                          # 枠の「段」の数（1段 = 29ピクセル）

    def __init__(self, app):
        super().__init__(app)
        self._history = []                  # シャッフル時の「前の曲」用
        self._scroll_drag = False

        self.view = PlaylistView(self)
        self.view.files_dropped.connect(lambda paths, row: self.add_paths(paths, row))
        self.view.delete_pressed.connect(self.remove_selected)
        self.view.itemActivated.connect(lambda item: self.play_requested.emit(self.view.row(item)))
        self.view.model().rowsMoved.connect(self._renumber)
        self.view.verticalScrollBar().valueChanged.connect(lambda _: self.update())
        self.view.verticalScrollBar().rangeChanged.connect(lambda *_: self.update())
        self.view.setItemDelegate(TrackDelegate(self))
        self.view.itemSelectionChanged.connect(self.update)

        # 曲の長さ・タグを調べた結果は、少しまとめてから一覧に反映する（たくさんあっても軽いように）
        self._results = {}
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.timeout.connect(self._apply_results)
        app.scanner.found.connect(self._on_found)
        self._layout_children()

    # --- 大きさ -----------------------------------------------------------
    def logical_size(self):
        return 275, TOP_H + BOTTOM_H + ROW_STEP * self.rows

    def set_rows(self, rows):
        rows = max(2, min(30, rows))
        if rows != self.rows:
            self.rows = rows
            self.update_size()
            self._layout_children()
            self.app.fit_window()

    def update_size(self):
        super().update_size()
        if hasattr(self, "view"):
            self._layout_children()

    def _list_rect(self):
        w, h = self.logical_size()
        return QRect(12, TOP_H, w - 32, h - TOP_H - BOTTOM_H)

    def _layout_children(self):
        r = self._list_rect()
        s = self.s
        self.view.setGeometry(r.x() * s, r.y() * s, r.width() * s, r.height() * s)
        self._make_hits()

    def apply_skin(self, skin):
        pl = skin.pl
        s = self.s
        font = QFont(pl.get("font", "DejaVu Sans"))
        font.setPixelSize(max(9, round(9 * s)))
        self.view.setFont(font)
        self.view.setStyleSheet(f"""
            QListWidget {{ background: {pl['normalbg']}; color: {pl['normal']}; outline: none; }}
            QListWidget::item {{ height: {13 * s}px; padding: 0px {2 * s}px; border: none; }}
            QListWidget::item:selected {{ background: {pl['selectedbg']}; color: {pl['normal']}; }}
        """)
        self._current_color = QColor(pl["current"])
        self.set_current(self.current_row())
        self.update()

    # --- 押せる場所 -------------------------------------------------------
    def _make_hits(self):
        w, h = self.logical_size()
        by = h - 30
        a = self.app
        self.buttons = [
            Button(QRect(w - 11, 3, 9, 9), None, "PL_CLOSE_P", lambda: a.toggle_pl(False), tip="閉じる"),
            Button(QRect(14, by, 22, 18), None, None, lambda: self._menu_add(14), tip="追加"),
            Button(QRect(43, by, 22, 18), None, None, lambda: self._menu_rem(43), tip="削除"),
            Button(QRect(72, by, 22, 18), None, None, lambda: self._menu_sel(72), tip="選択"),
            Button(QRect(101, by, 22, 18), None, None, lambda: self._menu_misc(101), tip="並べ替えなど"),
            Button(QRect(w - 44, by, 22, 18), None, None, lambda: self._menu_list(w - 44), tip="保存・読込"),
        ]
        bx = w - 150 + 3
        for i, (fn, tip) in enumerate([(a.prev_track, "前の曲"), (a.play, "再生"), (a.pause, "一時停止"),
                                       (a.stop, "停止"), (a.next_track, "次の曲"), (a.open_files, "開く")]):
            self.buttons.append(Button(QRect(bx + i * 10, h - BOTTOM_H + 22, 10, 10), None, None, fn, tip=tip))
        lr = self._list_rect()
        self.drags = [
            Drag(QRect(w - 15, lr.y(), 8, lr.height()), self._scroll_start, self._scroll_move,
                 self._scroll_end),
            Drag(QRect(w - 20, h - 20, 20, 20), lambda x, y: None, self._resize_move,
                 lambda x, y: None, "ドラッグで高さを変える"),
        ]

    def movable_at(self, x, y):
        return True

    # --- 描画 -------------------------------------------------------------
    def paint(self, p, skin):
        w, h = self.logical_size()
        act = "_ACTIVE" if self.active else ""
        title_x = (w - 100) // 2
        skin.tile(p, "PL_TOP" + act, 25, 0, w - 50, TOP_H)
        skin.draw(p, "PL_TL" + act, 0, 0)
        skin.draw(p, "PL_TITLE" + act, title_x, 0)
        skin.draw(p, "PL_TR" + act, w - 25, 0)
        mid_h = h - TOP_H - BOTTOM_H
        skin.tile(p, "PL_LEFT", 0, TOP_H, 12, mid_h)
        skin.tile(p, "PL_RIGHT", w - 20, TOP_H, 20, mid_h)
        skin.tile(p, "PL_BOTTOM", 125, h - BOTTOM_H, max(0, w - 275), BOTTOM_H)
        skin.draw(p, "PL_BL", 0, h - BOTTOM_H)
        skin.draw(p, "PL_BR", w - 150, h - BOTTOM_H)
        # スクロールのつまみ
        sb = self.view.verticalScrollBar()
        travel = mid_h - 18
        frac = sb.value() / sb.maximum() if sb.maximum() > 0 else 0
        skin.draw(p, "PL_SCROLL_P" if self._scroll_drag else "PL_SCROLL",
                  w - 15, TOP_H + round(frac * travel))
        # 右下の時間表示（Winamp と同じ：「選んだ曲の合計/全部の合計」と、今の再生位置）
        skin.draw_text(p, self.total_times(), w - 150 + 7, h - BOTTOM_H + 12)
        a = self.app
        if a.player.state() != "stopped":
            skin.draw_text(p, _mmss(a.position)[:5], w - 150 + 66, h - BOTTOM_H + 24)
        self.draw_buttons(p, skin)

    def total_times(self):
        """右下の窓に出す「選んだ曲の合計/全部の合計」の文字。
        窓の幅は12文字分なので、入りきらないときは 1h05m → 517h のように短くする。
        長さが分からない曲があれば末尾に + を付ける"""
        def total(items):
            ms, unknown = 0, False
            for it in items:
                d = it.data(DUR_ROLE)
                if d is None or d < 0:
                    unknown = True
                else:
                    ms += d
            return ms, ("+" if unknown else "")
        all_items = [self.view.item(i) for i in range(self.view.count())]
        (sel_ms, sel_plus), (all_ms, all_plus) = total(self.view.selectedItems()), total(all_items)
        for level in range(3):
            text = f"{short_time(sel_ms, level)}{sel_plus}/{short_time(all_ms, level)}{all_plus}"
            if len(text) <= 12:
                return text
        return text[:12]

    # --- 曲の長さ・タグの反映 ---------------------------------------------
    def _on_found(self, path, ms, title):
        self._results[path] = (ms, title)
        if not self._apply_timer.isActive():
            self._apply_timer.start(150)

    def _apply_results(self):
        results, self._results = self._results, {}
        changed = False
        for i in range(self.view.count()):
            item = self.view.item(i)
            hit = results.get(item.data(PATH_ROLE))
            if hit is None:
                continue
            ms, title = hit
            if item.data(DUR_ROLE) is None or ms > 0:
                item.setData(DUR_ROLE, ms)
            # 曲名がまだファイル名のままなら、タグの「アーティスト - 曲名」にする
            if title and item.data(TITLE_ROLE) == Path(item.data(PATH_ROLE)).stem:
                item.setData(TITLE_ROLE, title)
                changed = True
        if changed:
            self._renumber()
        self.update()

    def set_duration(self, row, ms):
        """再生中に分かった正確な長さで上書きする"""
        item = self.view.item(row)
        if item and ms > 0 and item.data(DUR_ROLE) != ms:
            item.setData(DUR_ROLE, ms)
            self.update()

    # --- スクロール・大きさ変更 -------------------------------------------
    def _scroll_start(self, x, y):
        self._scroll_drag = True
        self._scroll_move(x, y)

    def _scroll_move(self, x, y):
        lr = self._list_rect()
        frac = max(0.0, min(1.0, (y - lr.y() - 9) / max(1, lr.height() - 18)))
        sb = self.view.verticalScrollBar()
        sb.setValue(round(frac * sb.maximum()))

    def _scroll_end(self, x, y):
        self._scroll_drag = False
        self.update()

    def _resize_move(self, x, y):
        self.set_rows(round((y - TOP_H - BOTTOM_H + 10) / ROW_STEP))

    # --- メニュー ---------------------------------------------------------
    def _popup(self, x, actions):
        menu = QMenu(self)
        for item in actions:
            if item is None:
                menu.addSeparator()
            else:
                menu.addAction(*item)
        h = self.logical_size()[1]
        menu.exec(self.mapToGlobal(QPoint(x * self.s, (h - 30) * self.s)))

    def _menu_add(self, x):
        self._popup(x, [("ファイルを追加… (L)", self.open_files_dialog),
                        ("フォルダを追加… (Shift+L)", self.open_folder_dialog)])

    def _menu_rem(self, x):
        self._popup(x, [("選んだ曲を外す (Delete)", self.remove_selected),
                        ("選んだ曲以外を外す", self.crop),
                        ("見つからないファイルを外す", self.remove_missing),
                        None, ("すべて外す", self.clear)])

    def _menu_sel(self, x):
        self._popup(x, [("曲にジャンプ… (J)", self.app.jump_to_file),
                        None,
                        ("すべて選択", self.view.selectAll),
                        ("選択を解除", self.view.clearSelection),
                        ("選択を反転", self.invert_selection)])

    def _menu_misc(self, x):
        self._popup(x, [("曲名で並べ替え", lambda: self.sort_by(lambda i: i.data(TITLE_ROLE).lower())),
                        ("ファイルの場所で並べ替え", lambda: self.sort_by(lambda i: i.data(PATH_ROLE).lower())),
                        ("順番を逆にする", self.reverse),
                        ("順番をランダムに混ぜる", self.randomize)])

    def _menu_list(self, x):
        self._popup(x, [("プレイリストを開く…", self.load_dialog),
                        ("プレイリストを保存…", self.save_dialog)])

    # --- 追加・削除 ---------------------------------------------------------
    def add_paths(self, paths, row=-1):
        files = expand_paths(paths)
        if row < 0:
            row = self.view.count()
        for i, f in enumerate(files):
            item = QListWidgetItem()
            item.setData(PATH_ROLE, f)
            item.setData(TITLE_ROLE, Path(f).stem)
            item.setData(DUR_ROLE, None)
            self.view.insertItem(row + i, item)
        self._renumber()
        self.app.scanner.request(files)
        return len(files)

    def remove_selected(self):
        for item in self.view.selectedItems():
            self.view.takeItem(self.view.row(item))
        self._renumber()

    def crop(self):
        selected = set(id(i) for i in self.view.selectedItems())
        for i in reversed(range(self.view.count())):
            if id(self.view.item(i)) not in selected:
                self.view.takeItem(i)
        self._renumber()

    def remove_missing(self):
        for i in reversed(range(self.view.count())):
            if not Path(self.view.item(i).data(PATH_ROLE)).exists():
                self.view.takeItem(i)
        self._renumber()

    def clear(self):
        self.view.clear()
        self._history.clear()
        self._renumber()

    def invert_selection(self):
        for i in range(self.view.count()):
            item = self.view.item(i)
            item.setSelected(not item.isSelected())

    def _take_all(self):
        return [self.view.takeItem(0) for _ in range(self.view.count())]

    def sort_by(self, key):
        items = sorted(self._take_all(), key=key)
        for it in items:
            self.view.addItem(it)
        self._renumber()

    def reverse(self):
        for it in reversed(self._take_all()):
            self.view.addItem(it)
        self._renumber()

    def randomize(self):
        items = self._take_all()
        random.shuffle(items)
        for it in items:
            self.view.addItem(it)
        self._renumber()

    def paths(self):
        return [self.view.item(i).data(PATH_ROLE) for i in range(self.view.count())]

    def count(self):
        return self.view.count()

    # --- 再生中の曲の管理 --------------------------------------------------
    _current_color = None

    def current_row(self):
        for i in range(self.view.count()):
            if self.view.item(i).data(CURRENT_ROLE):
                return i
        return -1

    def set_current(self, row):
        old = self.current_row()
        if old >= 0 and old != row:
            self._history.append(old)
            self._history = self._history[-200:]
        for i in range(self.view.count()):
            item = self.view.item(i)
            is_cur = i == row
            item.setData(CURRENT_ROLE, is_cur)
            if is_cur and self._current_color:
                item.setForeground(self._current_color)
            else:
                item.setData(Qt.ForegroundRole, None)
        if row >= 0:
            self.view.scrollToItem(self.view.item(row))

    def path_at(self, row):
        item = self.view.item(row)
        return item.data(PATH_ROLE) if item else None

    def title_at(self, row):
        item = self.view.item(row)
        return item.data(TITLE_ROLE) if item else ""

    def set_title(self, row, title):
        item = self.view.item(row)
        if item:
            item.setData(TITLE_ROLE, title)
            self._renumber()

    def selected_row(self):
        rows = sorted(self.view.row(i) for i in self.view.selectedItems())
        return rows[0] if rows else -1

    def next_row(self, shuffle, repeat):
        n = self.view.count()
        if n == 0:
            return -1
        cur = self.current_row()
        if shuffle:
            if n == 1:
                return 0 if repeat or cur != 0 else -1
            return random.choice([i for i in range(n) if i != cur])
        if cur + 1 < n:
            return cur + 1
        return 0 if repeat else -1

    def prev_row(self, shuffle):
        n = self.view.count()
        if n == 0:
            return -1
        if shuffle and self._history:
            r = self._history.pop()
            if r < n:
                return r
        return max(0, self.current_row() - 1)

    def _renumber(self, *args):
        for i in range(self.view.count()):
            item = self.view.item(i)
            item.setText(f"{i + 1}. {item.data(TITLE_ROLE)}")
        self.update()

    # --- ダイアログ --------------------------------------------------------
    def open_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "曲を追加", os.path.expanduser("~/Music"),
            "音楽ファイル (*.mp3 *.ogg *.opus *.flac *.wav *.m4a *.aac *.m3u *.m3u8);;すべて (*)")
        if files:
            self.add_paths(files)
        return len(files)

    def open_folder_dialog(self):
        d = QFileDialog.getExistingDirectory(self, "フォルダを追加", os.path.expanduser("~/Music"))
        if d:
            self.add_paths([d])

    def load_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, "プレイリストを開く", os.path.expanduser("~/Music"),
                                           "プレイリスト (*.m3u8 *.m3u)")
        if f:
            self.clear()
            self.add_paths([f])

    def save_dialog(self):
        f, _ = QFileDialog.getSaveFileName(
            self, "プレイリストを保存", os.path.expanduser("~/Music/playlist.m3u8"),
            "プレイリスト (*.m3u8 *.m3u)")
        if f:
            self.save_m3u(f)

    def save_m3u(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("#EXTM3U\n" + "\n".join(self.paths()) + "\n", encoding="utf-8")


def _mmss(ms):
    s = max(0, ms) // 1000
    return f"{s // 60}:{s % 60:02d}"
