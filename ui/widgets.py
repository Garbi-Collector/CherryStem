import tkinter as tk
import math
import random
from .theme import ACCENT, BORDER, BORDER2, CARD, TEXT3, hex_to_rgb


class Seekbar(tk.Canvas):
    """Horizontal scrub bar with draggable handle."""

    def __init__(self, parent, color=ACCENT, on_seek=None, height=20, **kwargs):
        super().__init__(parent, highlightthickness=0, height=height,
                         cursor="hand2", **kwargs)
        self.color = color
        self.on_seek = on_seek
        self._progress = 0.0
        self._dragging = False
        self._hover = False
        self.bind("<Configure>",      lambda e: self._draw())
        self.bind("<ButtonPress-1>",  self._on_press)
        self.bind("<B1-Motion>",      self._on_drag)
        self.bind("<ButtonRelease-1>",self._on_release)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def set_progress(self, v):
        self._progress = max(0.0, min(1.0, v))
        if not self._dragging:
            self._draw()

    def _set_hover(self, v):
        self._hover = v
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        cy = h // 2
        th = 4 if self._hover else 3
        self.create_line(0, cy, w, cy, fill=BORDER2, width=th, capstyle=tk.ROUND)
        fill_x = int(w * self._progress)
        if fill_x > 0:
            self.create_line(0, cy, fill_x, cy, fill=self.color,
                             width=th, capstyle=tk.ROUND)
        r = 7 if self._hover else 5
        self.create_oval(fill_x - r, cy - r, fill_x + r, cy + r,
                         fill=self.color, outline="")

    def _to_progress(self, x):
        w = self.winfo_width()
        return max(0.0, min(1.0, x / w)) if w > 0 else 0.0

    def _on_press(self, e):
        self._dragging = True
        self._progress = self._to_progress(e.x)
        self._draw()

    def _on_drag(self, e):
        if self._dragging:
            self._progress = self._to_progress(e.x)
            self._draw()

    def _on_release(self, e):
        self._dragging = False
        self._progress = self._to_progress(e.x)
        self._draw()
        if self.on_seek:
            self.on_seek(self._progress)


class WaveformCanvas(tk.Canvas):
    """Animated waveform that shows playback progress."""

    def __init__(self, parent, color, height=40, **kwargs):
        super().__init__(parent, bg=CARD, highlightthickness=0,
                         height=height, **kwargs)
        self.color = color
        self.height_px = height
        self._bars: list[float] = []
        self._anim_id = None
        self._playing = False
        self._offset = 0.0
        self._progress = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set_waveform(self, bars=None):
        self._bars = bars or [random.uniform(0.06, 1.0) for _ in range(90)]
        self._draw()

    def set_progress(self, v):
        self._progress = max(0.0, min(1.0, v))
        if not self._playing:
            self._draw()

    def start_animation(self):
        self._playing = True
        self._animate()

    def stop_animation(self):
        self._playing = False
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.height_px
        if not self._bars or w < 10:
            self.create_line(0, h // 2, w, h // 2, fill=BORDER, width=1)
            return
        bar_w = max(2.0, w / len(self._bars))
        cx = h / 2
        fill_x = int(w * self._progress)
        for i, amp in enumerate(self._bars):
            x = i * bar_w + bar_w / 2
            half = amp * cx * 0.82
            if self._playing:
                half = max(0.05 * cx,
                           half + 0.12 * math.sin(i * 0.35 + self._offset) * cx)
            color = self.color if x <= fill_x else TEXT3
            self.create_line(x, cx - half, x, cx + half,
                             fill=color, width=max(1, bar_w - 1.5),
                             capstyle=tk.ROUND)

    def _animate(self):
        if not self._playing:
            return
        self._offset += 0.07
        self._draw()
        self._anim_id = self.after(40, self._animate)