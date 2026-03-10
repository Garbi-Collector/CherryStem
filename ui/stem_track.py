import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
import pygame
from .widgets import WaveformCanvas
from .theme import (ACCENT, BG3, BORDER, BORDER2, CARD, FONT_SMALL,
                    SUCCESS, TEXT, TEXT3)


class StemTrack(tk.Frame):
    def __init__(self, parent, stem_name, color, icon, label,
                 on_solo=None, **kwargs):
        super().__init__(parent, bg=CARD, relief=tk.FLAT, bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         **kwargs)
        self.stem_name = stem_name
        self._current_sound = None
        self.color = color
        self.on_solo = on_solo
        self.filepath = None
        self._muted = False
        self._soloed = False
        self._channel = None
        self._sound = None
        self._playing = False
        self._build(icon, label)

    # ── Build ──────────────────────────────────────────────────────────────
    def _build(self, icon, label):
        tk.Frame(self, bg=self.color, width=3).pack(side=tk.LEFT, fill=tk.Y)

        body = tk.Frame(self, bg=CARD)
        body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 8), pady=8)

        top = tk.Frame(body, bg=CARD)
        top.pack(fill=tk.X)

        tk.Label(top, text=icon, font=("Segoe UI Emoji", 14),
                 bg=CARD, fg=self.color).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(top, text=label, font=("Segoe UI", 9, "bold"),
                 bg=CARD, fg=TEXT).pack(side=tk.LEFT)
        self.status_lbl = tk.Label(top, text="", font=FONT_SMALL,
                                   bg=CARD, fg=TEXT3)
        self.status_lbl.pack(side=tk.LEFT, padx=6)

        btn_f = tk.Frame(top, bg=CARD)
        btn_f.pack(side=tk.RIGHT)
        self.btn_mute = self._chip(btn_f, "M", self._toggle_mute)
        self.btn_mute.pack(side=tk.LEFT, padx=2)
        self.btn_solo = self._chip(btn_f, "S", self._toggle_solo)
        self.btn_solo.pack(side=tk.LEFT, padx=2)
        self._chip(btn_f, "↓", self._download).pack(side=tk.LEFT, padx=(2, 0))

        self.waveform = WaveformCanvas(body, self.color, height=40)
        self.waveform.pack(fill=tk.X, pady=(5, 0))

    def _chip(self, parent, text, cmd):
        lbl = tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"),
                       bg=BG3, fg=TEXT3, cursor="hand2", width=3, pady=2,
                       relief=tk.FLAT, highlightthickness=1,
                       highlightbackground=BORDER)
        lbl.bind("<Button-1>", lambda e: cmd())
        lbl.bind("<Enter>", lambda e: lbl.config(bg=BORDER2))
        lbl.bind("<Leave>", lambda e: lbl.config(bg=BG3))
        return lbl

    # ── Public API ─────────────────────────────────────────────────────────
    def set_file(self, path):
        self.filepath = path
        self.status_lbl.config(text="✓ cargando…", fg=SUCCESS)
        # Precarga en hilo para no bloquear la UI
        import threading
        threading.Thread(target=self._preload, daemon=True).start()
        self.waveform.set_waveform()

    def _preload(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._sound = pygame.mixer.Sound(self.filepath)
            # Actualizar label en el hilo de tkinter
            self.after(0, lambda: self.status_lbl.config(text="✓", fg=SUCCESS))
        except Exception as e:
            print(f"[{self.stem_name}] preload error: {e}")
            self.after(0, lambda: self.status_lbl.config(text="⚠", fg="#f59e0b"))

    def play(self):
        self.play_from(0)

    def play_from(self, ms):
        """Reproduce el stem desde el offset indicado en milisegundos."""
        if not self._sound:
            return
        try:
            # Detener reproducción anterior
            self._sound.stop()

            import numpy as np
            # Obtener samples del Sound como array numpy
            samples = pygame.sndarray.array(self._sound)
            freq, _, _ = pygame.mixer.get_init()  # (freq, size, channels)

            # Calcular sample de inicio
            start_sample = int((ms / 1000.0) * freq)
            start_sample = max(0, min(start_sample, len(samples) - 1))

            sliced = samples[start_sample:]
            if len(sliced) == 0:
                return

            new_sound = pygame.sndarray.make_sound(sliced)
            self._channel = new_sound.play()
            # Guardamos referencia para poder silenciar/detener
            self._current_sound = new_sound

            if self._muted and self._channel:
                self._channel.set_volume(0)
            self._playing = True
            self.waveform.start_animation()
        except Exception as e:
            print(f"[{self.stem_name}] play_from error: {e}")

    def stop(self):
        for s in [self._sound, getattr(self, '_current_sound', None)]:
            if s:
                try:
                    s.stop()
                except Exception:
                    pass
        self._playing = False
        self.waveform.stop_animation()

    def set_waveform_progress(self, v):
        self.waveform.set_progress(v)

    def set_muted_external(self, muted):
        self._muted = muted
        self.btn_mute.config(fg=ACCENT if muted else TEXT3)
        if self._channel:
            self._channel.set_volume(0 if muted else 1)

    def reset(self):
        self.stop()
        self.filepath = None
        self._sound   = None
        self._channel = None
        self._muted = self._soloed = self._playing = False
        self.btn_mute.config(fg=TEXT3)
        self.btn_solo.config(fg=TEXT3)
        self.status_lbl.config(text="", fg=TEXT3)
        self.waveform.delete("all")

    # ── Internal actions ───────────────────────────────────────────────────
    def _toggle_mute(self):
        self._muted = not self._muted
        self.btn_mute.config(fg=ACCENT if self._muted else TEXT3)
        if self._channel:
            self._channel.set_volume(0 if self._muted else 1)

    def _toggle_solo(self):
        self._soloed = not self._soloed
        self.btn_solo.config(fg=self.color if self._soloed else TEXT3)
        if self.on_solo:
            self.on_solo(self.stem_name, self._soloed)

    def _download(self):
        if not self.filepath or not os.path.exists(self.filepath):
            messagebox.showwarning("No file", "Separate audio first.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav"), ("All", "*.*")],
            initialfile=f"{self.stem_name}.wav",
        )
        if dest:
            shutil.copy2(self.filepath, dest)
            messagebox.showinfo("Saved", f"Saved to:\n{dest}")