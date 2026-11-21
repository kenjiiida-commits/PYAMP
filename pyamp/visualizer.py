"""ビジュアライザー：曲に合わせて動く不思議な模様（MilkDrop 風・オリジナル）。

仕組み（MilkDrop と同じ考え方）：
  1. 前の画面を「少し回して・少し拡大して・少しゆがめて・少し暗くして」写し直す
  2. その上に、音に合わせて形が変わる図形（輪・波・渦・星）を描き足す
  3. これを毎秒60回くり返すと、溶けて流れるような残像の模様になる
描くのは全部 GPU（OpenGL のシェーダー）なので、全画面でも軽く動きます。

キー操作：
  Space / →：次の模様　←：前の模様　L：今の模様で固定（ロック）
  F / Enter / ダブルクリック：全画面の切り替え　Esc：全画面をやめる／閉じる　H：操作の説明
"""
import math
import random
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QSurfaceFormat, QVector3D, QVector4D
from PySide6.QtOpenGL import (QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat,
                              QOpenGLShader, QOpenGLShaderProgram, QOpenGLVertexArrayObject)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QLabel

# OpenGL の定数（数字で書く決まり）
GL_TEXTURE_2D = 0x0DE1
GL_TEXTURE0 = 0x84C0
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_MAG_FILTER = 0x2800
GL_TEXTURE_WRAP_S = 0x2802
GL_TEXTURE_WRAP_T = 0x2803
GL_LINEAR = 0x2601
GL_MIRRORED_REPEAT = 0x8370
GL_TRIANGLES = 0x0004
GL_COLOR_BUFFER_BIT = 0x4000
GL_FRAMEBUFFER = 0x8D40
GL_RGBA16F = 0x881A
GL_BLEND = 0x0BE2
GL_DEPTH_TEST = 0x0B71

# --- シェーダー（GPU で動く小さなプログラム）-------------------------------
VERTEX = """
#version 330 core
out vec2 uv;
void main() {
    // 画面全体を覆う大きな三角形を1つ作る
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

# 1) 前の画面をゆがめて写し、図形を描き足す
WARP = """
#version 330 core
in vec2 uv;
out vec4 fragColor;
uniform sampler2D prev;
uniform float time, aspect, bass, mid, treb, beat, beatAge;
uniform float zoom, rot, warp, decay, hueBase, hueSpeed, drift;
uniform vec4 shapeW;          // 輪・波・渦・星 の強さ
uniform vec4 spec[16];        // 64本の周波数の強さ（0〜1）

float specAt(float x) {
    float f = clamp(x, 0.0, 1.0) * 63.0;
    int a = int(f);
    int b = min(a + 1, 63);
    float va = spec[a / 4][a % 4];
    float vb = spec[b / 4][b % 4];
    return mix(va, vb, fract(f));
}
vec3 hsv(float h, float s, float v) {
    vec3 k = clamp(abs(mod(h * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
    return v * mix(vec3(1.0), k, s);
}
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void main() {
    vec2 p = uv - 0.5;
    p.x *= aspect;
    // 動きの中心がゆっくりさまよう
    vec2 center = drift * 0.12 * vec2(sin(time * 0.31), cos(time * 0.23));
    vec2 d = p - center;
    float r = length(d);

    // --- 1. 前の画面を回転・拡大・ゆがませて写す ---
    float ang = rot * (1.0 + 1.5 * bass);
    mat2 R = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
    vec2 q = R * d / (zoom + 0.03 * bass) + center;
    q += warp * 0.012 * vec2(sin(d.y * 7.0 + time * 1.3) + sin(r * 11.0 - time),
                             cos(d.x * 6.0 - time * 1.1) + cos(r * 9.0 + time * 0.7));
    q.x /= aspect;
    vec3 c = texture(prev, q + 0.5).rgb * decay - 0.002;

    // --- 2. 音に合わせた図形を描き足す ---
    float a = atan(d.y, d.x);
    float t = a / 6.28318 + 0.5;
    float hue = hueBase + time * hueSpeed;
    vec3 col = hsv(hue + t * 0.35, 0.85, 1.0);
    vec3 col2 = hsv(hue + 0.5, 0.7, 1.0);

    // 輪：周波数で形が変わる円
    float s = specAt(abs(fract(t * 2.0) - 0.5) * 2.0);
    float ringR = 0.16 + 0.22 * s + 0.06 * bass;
    c += shapeW.x * col * smoothstep(0.010, 0.0, abs(r - ringR)) * (0.5 + 1.2 * s);

    // 波：左右に流れる波形（上下対称）
    float x = uv.x;
    float wave = 0.5 + (0.08 + 0.25 * specAt(abs(x - 0.5) * 2.0)) * sin(x * 18.0 + time * 3.0) * (0.4 + mid);
    c += shapeW.y * hsv(hue + x * 0.5, 0.8, 1.0) * smoothstep(0.008, 0.0, abs(uv.y - wave)) * 0.9;

    // 渦：回転する腕
    float arms = sin(a * 3.0 + r * 22.0 - time * 3.5);
    c += shapeW.z * col2 * smoothstep(0.93, 1.0, arms) * smoothstep(0.55, 0.05, r) * (0.25 + 1.3 * treb);

    // 星：拍に合わせてきらめく点
    vec2 cell = floor(uv * vec2(48.0 * aspect, 48.0));
    float h = hash(cell + floor(time * 4.0));
    vec2 f = fract(uv * vec2(48.0 * aspect, 48.0)) - 0.5;
    c += shapeW.w * hsv(h + hue, 0.4, 1.0) * step(0.985 - 0.04 * beat, h) * smoothstep(0.35, 0.0, length(f)) * (0.4 + beat);

    // 拍の瞬間に広がる輪
    float burst = smoothstep(0.02, 0.0, abs(r - beatAge * 0.9)) * exp(-beatAge * 3.0);
    c += burst * col2 * 0.8;

    fragColor = vec4(clamp(c, 0.0, 4.0), 1.0);
}
"""

# 2) できた絵を画面に出す（鏡・万華鏡の効果もここで）
DISPLAY = """
#version 330 core
in vec2 uv;
out vec4 fragColor;
uniform sampler2D img;
uniform vec3 mirrorW;   // そのまま・左右の鏡・万華鏡 の割合
void main() {
    vec2 m = vec2(uv.x < 0.5 ? uv.x : 1.0 - uv.x, uv.y);
    vec2 k = vec2(0.5) + abs(uv - vec2(0.5));
    vec3 col = mirrorW.x * texture(img, uv).rgb
             + mirrorW.y * texture(img, m).rgb
             + mirrorW.z * texture(img, k).rgb;
    col = vec3(1.0) - exp(-col * 1.6);          // まぶしすぎないように
    fragColor = vec4(col, 1.0);
}
"""

# --- 模様の種類（プリセット）-----------------------------------------------
#   zoom>1 で吸い込まれる / <1 で広がる、rot は回転、warp はゆがみ、decay は残像の長さ
#   shape: (輪, 波, 渦, 星)  mirror: (そのまま, 左右の鏡, 万華鏡)
PRESETS = [
    dict(name="星雲の渦", zoom=1.015, rot=0.006, warp=0.5, decay=0.975, hueSpeed=0.03, drift=1.0,
         shape=(1.0, 0.0, 0.0, 0.6), mirror=(1, 0, 0)),
    dict(name="万華鏡", zoom=1.008, rot=-0.010, warp=0.3, decay=0.965, hueSpeed=0.05, drift=0.5,
         shape=(0.8, 0.0, 1.0, 0.0), mirror=(0, 0, 1)),
    dict(name="海のうねり", zoom=0.995, rot=0.0, warp=1.0, decay=0.970, hueSpeed=0.02, drift=0.3,
         shape=(0.0, 1.0, 0.0, 0.0), mirror=(0, 1, 0)),
    dict(name="光のトンネル", zoom=1.045, rot=0.004, warp=0.1, decay=0.955, hueSpeed=0.04, drift=0.6,
         shape=(1.0, 0.0, 0.3, 0.0), mirror=(1, 0, 0)),
    dict(name="オーロラ", zoom=1.004, rot=0.002, warp=0.8, decay=0.985, hueSpeed=0.015, drift=0.2,
         shape=(0.0, 0.8, 0.0, 0.5), mirror=(0, 1, 0)),
    dict(name="花火", zoom=0.988, rot=0.0, warp=0.2, decay=0.950, hueSpeed=0.08, drift=0.0,
         shape=(0.6, 0.0, 0.0, 1.0), mirror=(0, 0, 1)),
    dict(name="螺旋の夢", zoom=1.020, rot=0.016, warp=0.4, decay=0.970, hueSpeed=0.03, drift=0.8,
         shape=(0.0, 0.0, 1.0, 0.2), mirror=(1, 0, 0)),
    dict(name="鏡の迷宮", zoom=1.010, rot=-0.006, warp=0.6, decay=0.975, hueSpeed=0.04, drift=0.4,
         shape=(0.7, 0.6, 0.0, 0.0), mirror=(0, 0, 1)),
]

AUTO_SWITCH_SEC = 18      # この秒数ごとに模様が変わる
BLEND_SEC = 2.5           # 次の模様へなめらかに移る時間
NUM_KEYS = ("zoom", "rot", "warp", "decay", "hueSpeed", "drift")


def _mix(a, b, t):
    return a + (b - a) * t


class VisualizerWindow(QOpenGLWidget):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        self.setFormat(fmt)
        self.setWindowTitle("PYAMP ビジュアライザー")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(720, 450)
        self.setFocusPolicy(Qt.StrongFocus)

        # 音の情報
        self.spec = [0.0] * 64
        self._ranges = []
        self.bass = self.mid = self.treb = 0.0
        self._bass_avg = 0.0
        self.beat = 0.0
        self._last_beat = 0.0

        # 模様の切り替え
        self.locked = False
        self._index = random.randrange(len(PRESETS))
        self._from = dict(PRESETS[self._index])
        self._to = dict(PRESETS[self._index])
        self._blend_start = -BLEND_SEC
        self._switched_at = time.monotonic()
        self._hue = random.random()
        self._t0 = time.monotonic()
        self._last_frame = self._t0

        self._fbo = [None, None]
        self._ready = False

        self.label = QLabel(self)
        self.label.setStyleSheet("color: rgba(255,255,255,210); background: rgba(0,0,0,90);"
                                 "padding: 4px 8px; font-size: 14px; border-radius: 4px;")
        self.label.move(10, 10)
        self._label_until = 0.0
        self._show_name()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    # ------------------------------------------------------------------
    # 音のデータを受け取る（PYAMP のスペクトラム解析から）
    # ------------------------------------------------------------------
    def feed(self, mags):
        if not mags:
            return
        n = len(mags)
        if len(self._ranges) != 64 or self._ranges[-1][1] > n:
            band_hz = 22050 / n
            edges = [40 * (16000 / 40) ** (i / 64) for i in range(65)]
            self._ranges = []
            for lo, hi in zip(edges, edges[1:]):
                a = min(int(lo / band_hz), n - 1)
                self._ranges.append((a, min(max(a + 1, int(math.ceil(hi / band_hz))), n)))
        for i, (a, b) in enumerate(self._ranges):
            level = max(0.0, min(1.0, (max(mags[a:b]) + 70) / 60))
            self.spec[i] = max(level, self.spec[i] * 0.8)
        self.bass = sum(self.spec[0:9]) / 9
        self.mid = sum(self.spec[9:36]) / 27
        self.treb = sum(self.spec[36:64]) / 28
        # 拍（ドン！という瞬間）を見つける：低音が平均よりぐっと大きくなったとき
        now = time.monotonic()
        self._bass_avg = self._bass_avg * 0.95 + self.bass * 0.05
        if self.bass > self._bass_avg * 1.3 + 0.04 and now - self._last_beat > 0.3:
            self._last_beat = now
            self.beat = 1.0
            # 拍に合わせて模様を切り替える（ある程度時間がたっていれば）
            if not self.locked and now - self._switched_at > AUTO_SWITCH_SEC * 0.6 and random.random() < 0.15:
                self.next_preset()

    # ------------------------------------------------------------------
    # 模様の切り替え
    # ------------------------------------------------------------------
    def _current_params(self):
        t = (time.monotonic() - self._blend_start) / BLEND_SEC
        t = max(0.0, min(1.0, t))
        t = t * t * (3 - 2 * t)        # なめらかに
        p = {k: _mix(self._from[k], self._to[k], t) for k in NUM_KEYS}
        p["shape"] = tuple(_mix(a, b, t) for a, b in zip(self._from["shape"], self._to["shape"]))
        p["mirror"] = tuple(_mix(a, b, t) for a, b in zip(self._from["mirror"], self._to["mirror"]))
        return p

    def _go(self, index):
        self._from = dict(self._current_params())
        self._index = index % len(PRESETS)
        self._to = dict(PRESETS[self._index])
        self._blend_start = time.monotonic()
        self._switched_at = self._blend_start
        self._hue += random.uniform(0.2, 0.6)
        self._show_name()

    def next_preset(self):
        self._go(self._index + random.randint(1, len(PRESETS) - 1) if not self.locked else self._index + 1)

    def prev_preset(self):
        self._go(self._index - 1)

    def _show_name(self, text=None, sec=3.0):
        lock = "（ロック中）" if self.locked else ""
        self.label.setText(text or f"{PRESETS[self._index]['name']}{lock}")
        self.label.adjustSize()
        self.label.show()
        self._label_until = time.monotonic() + sec

    # ------------------------------------------------------------------
    # 毎フレームの処理
    # ------------------------------------------------------------------
    def _tick(self):
        now = time.monotonic()
        dt = now - self._last_frame
        self._last_frame = now
        # 音が来ないとき（停止中など）は少しずつ静かにしていく
        k = 0.92 ** (dt * 60)
        self.spec = [v * k for v in self.spec]
        self.bass *= k
        self.mid *= k
        self.treb *= k
        self.beat *= 0.88 ** (dt * 60)
        if not self.locked and now - self._switched_at > AUTO_SWITCH_SEC:
            self.next_preset()
        if self.label.isVisible() and now > self._label_until:
            self.label.hide()
        self.update()

    # ------------------------------------------------------------------
    # OpenGL
    # ------------------------------------------------------------------
    def initializeGL(self):
        self.gl = self.context().functions()
        self.vao = QOpenGLVertexArrayObject(self)
        self.vao.create()
        self.warp_prog = self._program(WARP)
        self.disp_prog = self._program(DISPLAY)
        self._ready = self.warp_prog is not None and self.disp_prog is not None

    def _program(self, fragment):
        prog = QOpenGLShaderProgram(self)
        ok = prog.addShaderFromSourceCode(QOpenGLShader.Vertex, VERTEX)
        ok = ok and prog.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment)
        ok = ok and prog.link()
        if not ok:
            print("シェーダーのエラー:", prog.log())
            return None
        return prog

    def _make_fbos(self, w, h):
        fmt = QOpenGLFramebufferObjectFormat()
        fmt.setInternalTextureFormat(GL_RGBA16F)
        gl = self.gl
        self._fbo = []
        for _ in range(2):
            fbo = QOpenGLFramebufferObject(w, h, fmt)
            gl.glBindTexture(GL_TEXTURE_2D, fbo.texture())
            gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_MIRRORED_REPEAT)
            gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_MIRRORED_REPEAT)
            fbo.bind()
            gl.glViewport(0, 0, w, h)
            gl.glClearColor(0, 0, 0, 1)
            gl.glClear(GL_COLOR_BUFFER_BIT)
            fbo.release()
            self._fbo.append(fbo)

    def _internal_size(self):
        dpr = self.devicePixelRatioF()
        w, h = max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr))
        scale = min(1.0, 1280 / w)          # 大きすぎる画面では内部を少し小さく描いて軽くする
        return max(16, int(w * scale)), max(16, int(h * scale))

    def paintGL(self):
        if not self._ready:
            return
        gl = self.gl
        size = self._internal_size()
        if self._fbo[0] is None or (self._fbo[0].width(), self._fbo[0].height()) != size:
            self._make_fbos(*size)
        w, h = size
        p = self._current_params()
        now = time.monotonic() - self._t0
        gl.glDisable(GL_DEPTH_TEST)
        gl.glDisable(GL_BLEND)
        self.vao.bind()

        # 1) 前の画面 → ゆがめて新しい画面へ
        src, dst = self._fbo
        dst.bind()
        gl.glViewport(0, 0, w, h)
        prog = self.warp_prog
        prog.bind()
        gl.glActiveTexture(GL_TEXTURE0)
        gl.glBindTexture(GL_TEXTURE_2D, src.texture())
        prog.setUniformValue1i("prev", 0)
        for name, value in [("time", now), ("aspect", w / h), ("bass", self.bass), ("mid", self.mid),
                            ("treb", self.treb), ("beat", self.beat),
                            ("beatAge", time.monotonic() - self._last_beat if self._last_beat else 99.0),
                            ("zoom", p["zoom"]), ("rot", p["rot"]), ("warp", p["warp"]),
                            ("decay", p["decay"]), ("hueBase", self._hue), ("hueSpeed", p["hueSpeed"]),
                            ("drift", p["drift"])]:
            prog.setUniformValue1f(name, float(value))
        prog.setUniformValue("shapeW", QVector4D(*p["shape"]))
        for i in range(16):
            prog.setUniformValue(f"spec[{i}]", QVector4D(*self.spec[i * 4:i * 4 + 4]))
        gl.glDrawArrays(GL_TRIANGLES, 0, 3)
        dst.release()

        # 2) 画面に出す
        gl.glBindFramebuffer(GL_FRAMEBUFFER, self.defaultFramebufferObject())
        dpr = self.devicePixelRatioF()
        gl.glViewport(0, 0, int(self.width() * dpr), int(self.height() * dpr))
        prog = self.disp_prog
        prog.bind()
        gl.glBindTexture(GL_TEXTURE_2D, dst.texture())
        prog.setUniformValue1i("img", 0)
        prog.setUniformValue("mirrorW", QVector3D(*p["mirror"]))
        gl.glDrawArrays(GL_TRIANGLES, 0, 3)
        self.vao.release()

        self._fbo = [dst, src]       # 次のフレームでは今の絵が「前の画面」になる

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.unsetCursor()
        else:
            self.showFullScreen()
            self.setCursor(Qt.BlankCursor)

    def mouseDoubleClickEvent(self, e):
        self.toggle_fullscreen()

    def keyPressEvent(self, e):
        key = e.key()
        if key in (Qt.Key_Space, Qt.Key_Right):
            self.next_preset()
        elif key == Qt.Key_Left:
            self.prev_preset()
        elif key == Qt.Key_L:
            self.locked = not self.locked
            self._show_name()
        elif key in (Qt.Key_F, Qt.Key_Return, Qt.Key_Enter):
            self.toggle_fullscreen()
        elif key == Qt.Key_H:
            self._show_name("Space/→：次の模様　←：前の模様　L：ロック\n"
                            "F・ダブルクリック：全画面　Esc：戻る/閉じる", sec=6.0)
        elif key == Qt.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()
            else:
                self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self._timer.stop()
        self.closed.emit()
        super().closeEvent(e)
