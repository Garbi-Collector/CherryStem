import tkinter as tk
from .widgets import Seekbar
from .theme import ACCENT, BG2, BG3, BORDER, BORDER2, FONT_TIME, TEXT, TEXT2, TEXT3


class BottomPlayer(tk.Frame):
    """Fixed transport bar: play/pause, stop, seekbar, time, export."""

    def __init__(self, parent, on_play_pause=None, on_stop=None,
                 on_seek=None, on_download_zip=None, **kwargs):
        super().__init__(parent, bg=BG2,
                         highlightthickness=1, highlightbackground=BORDER2,
                         **kwargs)
        self.on_play_pause   = on_play_pause
        self.on_stop         = on_stop
        self.on_seek         = on_seek
        self.on_download_zip = on_download_zip
        self._playing = False
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────
    def _build(self):
        pad = tk.Frame(self, bg=BG2)
        pad.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Info row
        info = tk.Frame(pad, bg=BG2)
        info.pack(fill=tk.X, pady=(0, 6))
        self.lbl_track = tk.Label(info, text="No track loaded",
                                  font=("Segoe UI", 9), bg=BG2, fg=TEXT2)
        self.lbl_track.pack(side=tk.LEFT)
        self.lbl_time = tk.Label(info, text="0:00 / 0:00",
                                 font=FONT_TIME, bg=BG2, fg=TEXT3)
        self.lbl_time.pack(side=tk.RIGHT)

        # Seekbar
        self.seekbar = Seekbar(pad, color=ACCENT, on_seek=self._handle_seek,
                               height=18, bg=BG2)
        self.seekbar.pack(fill=tk.X, pady=(0, 8))

        # Controls
        ctrl = tk.Frame(pad, bg=BG2)
        ctrl.pack(fill=tk.X)

        left = tk.Frame(ctrl, bg=BG2)
        left.pack(side=tk.LEFT)
        self.btn_pp   = self._circle_btn(left, "▶", self._pp_click,   ACCENT, 36)
        self.btn_pp.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_stop = self._circle_btn(left, "■", self._stop_click, TEXT3,  30)
        self.btn_stop.pack(side=tk.LEFT)

        right = tk.Frame(ctrl, bg=BG2)
        right.pack(side=tk.RIGHT)
        self._text_btn(right, "↓ Export ZIP", self._zip_click).pack()

    def _circle_btn(self, parent, symbol, cmd, fg, size):
        c = tk.Canvas(parent, width=size, height=size, bg=BG2,
                      highlightthickness=0, cursor="hand2")

        def draw(hover=False):
            c.delete("all")
            c.create_oval(2, 2, size - 2, size - 2,
                          fill=BORDER2 if hover else BORDER, outline="")
            label = "⏸" if (symbol == "▶" and self._playing) else symbol
            font  = ("Segoe UI Emoji", size // 3) if label == "⏸" \
                    else ("Segoe UI", size // 3)
            c.create_text(size // 2, size // 2, text=label, font=font, fill=fg)

        draw()
        c.bind("<Button-1>", lambda e: cmd())
        c.bind("<Enter>",    lambda e: draw(True))
        c.bind("<Leave>",    lambda e: draw(False))
        c._redraw = draw
        return c

    def _text_btn(self, parent, text, cmd):
        lbl = tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"),
                       bg=BG3, fg=TEXT2, cursor="hand2",
                       padx=10, pady=5, relief=tk.FLAT,
                       highlightthickness=1, highlightbackground=BORDER)
        lbl.bind("<Button-1>", lambda e: cmd())
        lbl.bind("<Enter>",    lambda e: lbl.config(bg=BORDER2, fg=TEXT))
        lbl.bind("<Leave>",    lambda e: lbl.config(bg=BG3,     fg=TEXT2))
        return lbl

    # ── Callbacks ──────────────────────────────────────────────────────────
    def _pp_click(self):
        if self.on_play_pause:
            self.on_play_pause()

    def _stop_click(self):
        if self.on_stop:
            self.on_stop()

    def _zip_click(self):
        if self.on_download_zip:
            self.on_download_zip()

    def _handle_seek(self, v):
        if self.on_seek:
            self.on_seek(v)

    # ── Public API ─────────────────────────────────────────────────────────
    def set_playing(self, v):
        self._playing = v
        self.btn_pp._redraw()

    def set_track_name(self, name):
        self.lbl_track.config(text=name)

    def set_progress(self, pos_ms, dur_ms):
        if dur_ms > 0:
            self.seekbar.set_progress(pos_ms / dur_ms)

        def fmt(ms):
            s = int(ms / 1000)
            return f"{s // 60}:{s % 60:02d}"

        self.lbl_time.config(text=f"{fmt(pos_ms)} / {fmt(dur_ms)}")

    def reset(self):
        self._playing = False
        self.btn_pp._redraw()
        self.seekbar.set_progress(0)
        self.lbl_time.config(text="0:00 / 0:00")
        self.lbl_track.config(text="No track loaded")