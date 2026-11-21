"""タグの文字化けを直す。

古い日本の MP3 には、タグを Shift_JIS（Windows の日本語）で書いたものが多くあります。
ところが MP3 の決まりでは「西欧文字（Latin-1）」として読むことになっているため、
そのまま読むと「ÆÆ」のような文字化けになります。
文字化けした文字列を元のバイト列に戻して、Shift_JIS や UTF-8 として読み直します。
"""
import re

# ひらがな・カタカナ・漢字・全角記号が含まれていれば「日本語として読めた」とみなす
_JAPANESE = re.compile(r"[　-ヿ一-鿿＀-￯]")


def fix_mojibake(text: str) -> str:
    if not text:
        return text
    # Latin-1 の範囲の文字だけで、しかも 0x80 以上の文字がある → 文字化けの可能性
    if any(ord(c) > 0xFF for c in text) or not any(ord(c) >= 0x80 for c in text):
        return text
    raw = text.encode("latin-1")
    for encoding in ("utf-8", "cp932", "euc_jp"):
        try:
            fixed = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if encoding == "utf-8" or _JAPANESE.search(fixed):
            return fixed
    return text
