"""PYAMP — Winamp 風の音楽プレイヤー

起動方法:  python3 main.py  [音楽ファイルやフォルダ ...]
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PYAMP")
    app.setDesktopFileName("pyamp")
    app.setStyle("Fusion")  # どの環境でも同じ見た目にする
    app.setWindowIcon(QIcon.fromTheme("pyamp"))

    win = MainWindow()
    # コマンドラインでファイルを渡されたら、それを一覧にしてすぐ再生
    files = sys.argv[1:]
    if files:
        win.playlist.clear()
        if win.playlist.add_paths(files):
            win.play_row(0)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
