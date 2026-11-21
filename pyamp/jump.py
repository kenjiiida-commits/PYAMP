"""曲にジャンプ（Winamp の J キー）：曲名を入力すると、プレイリストから絞り込んですぐ再生できる。

探し方：
- スペースで区切った言葉が「全部」入っている曲を表示（例：「ビートルズ let」）
- ひらがな/カタカナ、全角/半角、大文字/小文字の違いは区別しない
- 曲名だけでなく、ファイルの場所（フォルダ名）でも探せる
"""
import unicodedata
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QVBoxLayout)


def normalize(text: str) -> str:
    """比べやすい形にそろえる：全角→半角、大文字→小文字、カタカナ→ひらがな"""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


class JumpDialog(QDialog):
    def __init__(self, parent, entries, current_row, skin):
        """entries: [(行番号, 表示名, ファイルの場所), ...]"""
        super().__init__(parent)
        self.setWindowTitle("曲にジャンプ")
        self.resize(460, 420)
        self.chosen = -1
        # 探すための文字を先に作っておく（曲が多くても速いように）
        self._entries = [(row, title, normalize(f"{title} {Path(path).parent.name} {Path(path).name}"))
                         for row, title, path in entries]
        self._current_row = current_row

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("曲名やフォルダ名の一部を入力（スペースで区切ると AND 検索）")
        self.edit.textChanged.connect(self._filter)
        self.edit.installEventFilter(self)

        self.list = QListWidget()
        self.list.itemActivated.connect(lambda _: self._accept())
        self.count_label = QLabel()

        lay = QVBoxLayout(self)
        lay.addWidget(self.edit)
        lay.addWidget(self.list, 1)
        lay.addWidget(self.count_label)

        pl = skin.pl
        self.setStyleSheet(f"""
            QDialog {{ background: #2a2d35; }}
            QLabel {{ color: #b0b6c4; }}
            QLineEdit {{ background: {pl['normalbg']}; color: {pl['normal']};
                         border: 1px solid #555; padding: 4px; font-size: 14px; }}
            QListWidget {{ background: {pl['normalbg']}; color: {pl['normal']};
                           border: 1px solid #555; font-size: 13px; outline: none; }}
            QListWidget::item:selected {{ background: {pl['selectedbg']}; color: {pl['current']}; }}
        """)
        self._filter("")
        self.edit.setFocus()

    def _filter(self, text):
        words = normalize(text).split()
        self.list.clear()
        for row, title, key in self._entries:
            if all(w in key for w in words):
                item = QListWidgetItem(f"{row + 1}. {title}")
                item.setData(Qt.UserRole, row)
                self.list.addItem(item)
        self.count_label.setText(f"{self.list.count()} / {len(self._entries)} 曲　"
                                 "（↑↓で選んで Enter で再生、Esc で閉じる）")
        if self.list.count():
            # 何も入力していないときは、今の曲を選んでおく
            pick = 0
            if not words:
                for i in range(self.list.count()):
                    if self.list.item(i).data(Qt.UserRole) == self._current_row:
                        pick = i
                        break
            self.list.setCurrentRow(pick)
            self.list.scrollToItem(self.list.currentItem(), QListWidget.PositionAtCenter)

    def eventFilter(self, obj, e):
        """入力欄にいたまま ↑↓・PageUp/PageDown で一覧を動かせるようにする"""
        if obj is self.edit and e.type() == e.Type.KeyPress:
            key = e.key()
            if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
                self.list.keyPressEvent(e)
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._accept()
                return True
        return super().eventFilter(obj, e)

    def _accept(self):
        item = self.list.currentItem()
        if item:
            self.chosen = item.data(Qt.UserRole)
            self.accept()
