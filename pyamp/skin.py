"""スキンの読み込みと、スキン画像を使った描画の手伝い。

- 内蔵スキン（default_skin.py がコードで描いたもの）
- Winamp のスキンファイル（.wsz）  ※中身は BMP 画像の入った zip
- 展開済みのスキンフォルダ
のどれでも同じように扱えます。足りない画像は内蔵スキンのもので補います。
"""
import re
import zipfile
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap

from sprites import CHAR_H, CHAR_W, FONT_LOOKUP, SKIN_FILES, SPRITES

_default_cache = None


_default_pix_cache = None


def _default_pixmaps(images):
    global _default_pix_cache
    if _default_pix_cache is None:
        _default_pix_cache = {k: QPixmap.fromImage(v) for k, v in images.items()}
    return _default_pix_cache


def _default():
    global _default_cache
    if _default_cache is None:
        from default_skin import build_default
        _default_cache = build_default()
    return _default_cache


class Skin:
    def __init__(self, path=None):
        d = _default()
        self.path = str(path) if path else None
        self.name = "PYAMP 標準"
        self.nums_ex = False      # 新しい形式の数字画像（マイナス記号つき）か
        images = dict(d["images"])
        self.viscolors = [QColor(c) for c in d["viscolors"]]
        self.pl = dict(d["pledit"])
        if path:
            self.name = Path(path).stem
            loaded = self._load(Path(path))
            if "volume" in loaded and "balance" not in loaded:
                loaded["balance"] = loaded["volume"]  # Winamp と同じ代用
            images.update(loaded)
        self.pix = {k: QPixmap.fromImage(v) for k, v in images.items()}
        self.images = images
        # スキンに足りない部品があったとき用に、内蔵スキンの絵も持っておく
        self._default_images = d["images"]
        self._default_pix = _default_pixmaps(d["images"])
        self._text_bg, self._text_fg = self._text_colors(images["text"])

    # ------------------------------------------------------------------
    # 読み込み
    # ------------------------------------------------------------------
    def _load(self, path):
        files = {}  # 小文字のファイル名 → 中身(bytes)
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    files[f.name.lower()] = f.read_bytes()
        else:
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    if not info.is_dir():
                        files[Path(info.filename).name.lower()] = z.read(info)

        images = {}
        for name in SKIN_FILES:
            data = files.get(f"{name}.bmp")
            if name == "numbers" and "nums_ex.bmp" in files:
                data = files["nums_ex.bmp"]       # Winamp と同じく、新しい形式を優先
                self.nums_ex = True
            if data is None:
                continue
            img = QImage.fromData(data)
            if not img.isNull():
                images[name] = img.convertToFormat(QImage.Format_ARGB32)

        if "viscolor.txt" in files:
            colors = []
            for line in files["viscolor.txt"].decode("latin-1").splitlines():
                nums = re.findall(r"\d+", line.split("//")[0])
                if len(nums) >= 3:
                    colors.append(QColor(*[min(255, int(n)) for n in nums[:3]]))
            if len(colors) >= 24:
                self.viscolors = colors[:24]

        if "pledit.txt" in files:
            for line in files["pledit.txt"].decode("latin-1").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    key, value = key.strip().lower(), value.strip()
                    if key in ("normal", "current", "normalbg", "selectedbg"):
                        if not value.startswith("#"):
                            value = "#" + value
                        if QColor(value).isValid():
                            self.pl[key] = value
                    elif key == "font" and value:
                        self.pl["font"] = value
        return images

    @staticmethod
    def _text_colors(img):
        """文字画像の「背景色」と「文字色」を調べる（日本語など絵がない文字の代わりに使う）"""
        counts = Counter()
        for y in range(0, min(img.height(), 18)):
            for x in range(0, min(img.width(), 155)):
                counts[img.pixel(x, y)] += 1
        common = [QColor.fromRgb(c) for c, _ in counts.most_common(8)]
        bg = common[0] if common else QColor("black")
        fg = QColor("#00ff00")
        best = -1
        for c in common[1:]:
            diff = abs(c.red() - bg.red()) + abs(c.green() - bg.green()) + abs(c.blue() - bg.blue())
            if diff > best:
                best, fg = diff, c
        return bg, fg

    # ------------------------------------------------------------------
    # 描画の手伝い
    # ------------------------------------------------------------------
    def _source(self, file, sx, sy, w, h):
        """絵を取り出す元の画像。スキンの画像が小さくてその部品が入っていなければ、内蔵スキンから取る"""
        img = self.images[file]
        if sx + w <= img.width() and sy + h <= img.height():
            return self.pix[file]
        return self._default_pix[file]

    def draw(self, p: QPainter, name: str, x: int, y: int):
        """部品 name を (x, y) に描く"""
        file, sx, sy, w, h = SPRITES[name]
        p.drawPixmap(x, y, self._source(file, sx, sy, w, h), sx, sy, w, h)

    def draw_part(self, p, file, sx, sy, w, h, x, y):
        p.drawPixmap(x, y, self._source(file, sx, sy, w, h), sx, sy, w, h)

    def tile(self, p, name, x, y, w, h):
        """部品を並べて (x, y, w, h) を埋める（プレイリストの枠用）"""
        file, sx, sy, sw, sh = SPRITES[name]
        pix = self._source(file, sx, sy, sw, sh)
        p.save()
        p.setClipRect(QRect(x, y, w, h), Qt.IntersectClip)
        yy = y
        while yy < y + h:
            xx = x
            while xx < x + w:
                p.drawPixmap(xx, yy, pix, sx, sy, sw, sh)
                xx += sw
            yy += sh
        p.restore()

    def pixel_color(self, name, dx, dy):
        file, sx, sy, w, h = SPRITES[name]
        img = self.images[file]
        if sx + w > img.width() or sy + h > img.height():
            img = self._default_images[file]
        return QColor.fromRgb(img.pixel(sx + dx, sy + dy))

    def can_bitmap(self, text: str) -> bool:
        return all(ch.lower() in FONT_LOOKUP for ch in text)

    def text_width(self, text: str) -> int:
        return len(text) * CHAR_W

    def draw_text(self, p: QPainter, text: str, x: int, y: int):
        """Winamp の小さな文字（text.bmp）で文字列を描く。
        絵がない文字（日本語など）を含む場合は、普通のフォントで同じ色で描く。"""
        if self.can_bitmap(text):
            for i, ch in enumerate(text):
                row, col = FONT_LOOKUP[ch.lower()]
                if ch == " ":
                    p.fillRect(x + i * CHAR_W, y, CHAR_W, CHAR_H, self._text_bg)
                else:
                    p.drawPixmap(x + i * CHAR_W, y, self.pix["text"],
                                 col * CHAR_W, row * CHAR_H, CHAR_W, CHAR_H)
            return CHAR_W * len(text)
        font = self.fallback_font()
        p.save()
        p.setFont(font)
        p.setPen(self._text_fg)
        p.drawText(QRectF(x, y - 3, 2000, CHAR_H + 6), Qt.AlignLeft | Qt.AlignVCenter, text)
        p.restore()
        return self.fallback_width(text)

    def fallback_font(self):
        f = QFont("Noto Sans CJK JP")
        f.setPixelSize(8)
        return f

    def fallback_width(self, text):
        from PySide6.QtGui import QFontMetricsF
        return int(QFontMetricsF(self.fallback_font()).horizontalAdvance(text)) + 1

    def measure(self, text):
        return self.text_width(text) if self.can_bitmap(text) else self.fallback_width(text)

    @property
    def text_bg(self):
        return self._text_bg
