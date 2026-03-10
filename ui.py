import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import zipfile
import shutil
import pygame
import time

from separator import separar_audio

# ─── Colores y fuentes ────────────────────────────────────────────────────────
BG         = "#0d0d0f"
BG2        = "#141416"
BG3        = "#1c1c20"
CARD       = "#1e1e24"
BORDER     = "#2a2a32"
ACCENT     = "#e8365d"
ACCENT2    = "#ff6b6b"
MUTED      = "#ff3366"
TEXT       = "#f0f0f5"
TEXT2      = "#9090a8"
TEXT3      = "#5a5a72"
SUCCESS    = "#2ecc71"
WARNING    = "#f39c12"

STEM_COLORS = {
    "vocals": "#e8365d",
    "drums":  "#f59e0b",
    "bass":   "#3b82f6",
    "other":  "#8b5cf6",
}

STEM_ICONS = {
    "vocals": "🎤",
    "drums":  "🥁",
    "bass":   "🎸",
    "other":  "🎹",
}

STEM_LABELS = {
    "vocals": "VOCALS",
    "drums":  "DRUMS",
    "bass":   "BASS",
    "other":  "OTHER",
}

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_SUB    = ("Segoe UI", 11)
FONT_LABEL  = ("Segoe UI", 9, "bold")
FONT_SMALL  = ("Segoe UI", 8)
FONT_BTN    = ("Segoe UI", 10, "bold")
FONT_MONO   = ("Consolas", 8)


class WaveformCanvas(tk.Canvas):
    """Canvas que dibuja una forma de onda animada o estática."""

    def __init__(self, parent, color, height=48, **kwargs):
        super().__init__(parent, bg=CARD, highlightthickness=0, height=height, **kwargs)
        self.color = color
        self.height_px = height
        self._bars = []
        self._anim_id = None
        self._playing = False
        self._offset = 0
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self._draw_idle()

    def set_waveform(self, amplitudes=None):
        import random
        if amplitudes is None:
            amplitudes = [random.uniform(0.15, 1.0) for _ in range(80)]
        self._bars = amplitudes
        self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.height_px
        if not self._bars or w < 10:
            # Línea central placeholder
            self.create_line(0, h//2, w, h//2, fill=BORDER, width=1)
            return
        n = len(self._bars)
        bar_w = max(2, w / n)
        cx = h / 2
        for i, amp in enumerate(self._bars):
            x = i * bar_w + bar_w / 2
            half = amp * cx * 0.85
            alpha_hex = "88"
            clr = self.color + alpha_hex if len(self.color) == 7 else self.color
            self.create_line(x, cx - half, x, cx + half,
                             fill=self.color, width=max(1, bar_w - 1),
                             capstyle=tk.ROUND)

    def start_animation(self):
        self._playing = True
        self._animate()

    def stop_animation(self):
        self._playing = False
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self._draw_idle()

    def _animate(self):
        if not self._playing:
            return
        import math
        self.delete("all")
        w = self.winfo_width()
        h = self.height_px
        cx = h / 2
        n = len(self._bars) if self._bars else 60
        bar_w = max(2, w / n)
        bars = self._bars if self._bars else [0.5] * n
        self._offset += 0.08
        for i, amp in enumerate(bars):
            wave = 0.15 * math.sin(i * 0.3 + self._offset)
            a = max(0.05, min(1.0, amp + wave))
            x = i * bar_w + bar_w / 2
            half = a * cx * 0.85
            self.create_line(x, cx - half, x, cx + half,
                             fill=self.color, width=max(1, bar_w - 1),
                             capstyle=tk.ROUND)
        self._anim_id = self.after(40, self._animate)


class StemTrack(tk.Frame):
    """Tarjeta de una pista individual con controles."""

    def __init__(self, parent, stem_name, color, icon, label, on_solo=None, **kwargs):
        super().__init__(parent, bg=CARD, **kwargs)
        self.stem_name = stem_name
        self.color = color
        self.icon = icon
        self.label_text = label
        self.on_solo = on_solo
        self.filepath = None
        self._muted = False
        self._soloed = False
        self._channel = None
        self._sound = None
        self._playing = False
        self._pos_ms = 0
        self._start_time = 0

        self._build()

    def _build(self):
        # Borde de color
        accent_bar = tk.Frame(self, bg=self.color, width=4)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        # Contenido principal
        body = tk.Frame(self, bg=CARD)
        body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 8), pady=8)

        # Fila superior: icono, nombre, estado, controles
        top = tk.Frame(body, bg=CARD)
        top.pack(fill=tk.X)

        tk.Label(top, text=self.icon, font=("Segoe UI Emoji", 16),
                 bg=CARD, fg=self.color).pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(top, text=self.label_text, font=FONT_LABEL,
                 bg=CARD, fg=TEXT).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(top, text="", font=FONT_SMALL,
                                   bg=CARD, fg=TEXT3)
        self.status_lbl.pack(side=tk.LEFT, padx=6)

        # Botones a la derecha
        btn_frame = tk.Frame(top, bg=CARD)
        btn_frame.pack(side=tk.RIGHT)

        self.btn_mute = self._make_btn(btn_frame, "M", self._toggle_mute, TEXT3)
        self.btn_mute.pack(side=tk.LEFT, padx=2)

        self.btn_solo = self._make_btn(btn_frame, "S", self._toggle_solo, TEXT3)
        self.btn_solo.pack(side=tk.LEFT, padx=2)

        self.btn_dl = self._make_btn(btn_frame, "⬇", self._download, TEXT3)
        self.btn_dl.pack(side=tk.LEFT, padx=2)

        # Waveform
        wf_frame = tk.Frame(body, bg=BORDER, pady=1)
        wf_frame.pack(fill=tk.X, pady=(6, 0))

        self.waveform = WaveformCanvas(wf_frame, self.color, height=44)
        self.waveform.pack(fill=tk.X)

    def _make_btn(self, parent, text, cmd, fg):
        btn = tk.Label(parent, text=text, font=FONT_LABEL,
                       bg=BG3, fg=fg, cursor="hand2",
                       width=3, pady=2, relief=tk.FLAT)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.config(bg=BORDER))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG3))
        return btn

    def set_file(self, path):
        self.filepath = path
        self.status_lbl.config(text="✓ listo", fg=SUCCESS)
        import random
        bars = [random.uniform(0.1, 1.0) for _ in range(80)]
        self.waveform.set_waveform(bars)

    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self.btn_mute.config(fg=ACCENT, bg=BG3)
            if self._channel and self._channel.get_busy():
                self._channel.set_volume(0)
        else:
            self.btn_mute.config(fg=TEXT3, bg=BG3)
            if self._channel and self._channel.get_busy():
                self._channel.set_volume(1)

    def _toggle_solo(self):
        self._soloed = not self._soloed
        col = self.color if self._soloed else TEXT3
        self.btn_solo.config(fg=col, bg=BG3)
        if self.on_solo:
            self.on_solo(self.stem_name, self._soloed)

    def _download(self):
        if not self.filepath or not os.path.exists(self.filepath):
            messagebox.showwarning("Sin archivo", "Primero separa el audio.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav"), ("Todos", "*.*")],
            initialfile=f"{self.stem_name}.wav"
        )
        if dest:
            shutil.copy2(self.filepath, dest)
            messagebox.showinfo("Descargado", f"Guardado en:\n{dest}")

    def play(self):
        if not self.filepath or not os.path.exists(self.filepath):
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._sound = pygame.mixer.Sound(self.filepath)
            self._channel = self._sound.play()
            if self._muted and self._channel:
                self._channel.set_volume(0)
            self._playing = True
            self.waveform.start_animation()
        except Exception as e:
            print(f"Error reproduciendo {self.stem_name}: {e}")

    def stop(self):
        if self._sound:
            self._sound.stop()
        self._playing = False
        self.waveform.stop_animation()

    def set_muted_external(self, muted):
        self._muted = muted
        col = ACCENT if muted else TEXT3
        self.btn_mute.config(fg=col)
        if self._channel:
            self._channel.set_volume(0 if muted else 1)

    def reset(self):
        self.filepath = None
        self._muted = False
        self._soloed = False
        self.btn_mute.config(fg=TEXT3)
        self.btn_solo.config(fg=TEXT3)
        self.status_lbl.config(text="", fg=TEXT3)
        self.waveform.stop_animation()
        self.waveform.delete("all")


class CherryStemApp:

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        try:
            pygame.mixer.init()
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.title("CherryStem")
        self.root.configure(bg=BG)
        self.root.minsize(740, 700)
        self.root.geometry("800x780")

        # Estado
        self.input_file = None
        self.stems = {}
        self.is_playing = False
        self._tracks = {}

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG, pady=20)
        header.pack(fill=tk.X, padx=28)

        left_h = tk.Frame(header, bg=BG)
        left_h.pack(side=tk.LEFT)

        cherry = tk.Label(left_h, text="🍒", font=("Segoe UI Emoji", 26), bg=BG)
        cherry.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(left_h, text="CHERRY", font=("Segoe UI", 22, "bold"),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Label(left_h, text="STEM", font=("Segoe UI", 22, "bold"),
                 bg=BG, fg=TEXT).pack(side=tk.LEFT, padx=(2, 0))

        tk.Label(header, text="AI Audio Separator", font=FONT_SUB,
                 bg=BG, fg=TEXT3).pack(side=tk.RIGHT, pady=6)

        # Separador
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # Scroll body
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # ── Sección de carga ──────────────────────────────────────────────────
        load_card = tk.Frame(body, bg=CARD, pady=18, padx=20)
        load_card.pack(fill=tk.X, pady=(0, 12))
        self._rounded_border(load_card)

        tk.Label(load_card, text="ARCHIVO DE AUDIO", font=FONT_LABEL,
                 bg=CARD, fg=TEXT3).pack(anchor="w")

        row = tk.Frame(load_card, bg=CARD)
        row.pack(fill=tk.X, pady=(6, 0))

        self.entry_path = tk.Entry(row, font=FONT_SUB, bg=BG3, fg=TEXT,
                                   insertbackground=TEXT, relief=tk.FLAT,
                                   highlightthickness=1,
                                   highlightbackground=BORDER,
                                   highlightcolor=ACCENT,
                                   readonlybackground=BG3, state="readonly")
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True,
                             ipady=7, padx=(0, 8))

        self._btn(row, "  ELEGIR ARCHIVO  ", self._pick_file,
                  bg=BG3, fg=TEXT).pack(side=tk.LEFT)

        # Formatos
        tk.Label(load_card, text="MP3 · WAV · FLAC · M4A · OGG",
                 font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(4, 0))

        # ── Botón separar ─────────────────────────────────────────────────────
        sep_frame = tk.Frame(body, bg=BG)
        sep_frame.pack(fill=tk.X, pady=(0, 12))

        self.btn_sep = self._btn(sep_frame, "  🔬  SEPARAR PISTAS  ",
                                 self._start_separation,
                                 bg=ACCENT, fg=TEXT,
                                 font=("Segoe UI", 12, "bold"),
                                 pady=11, padx=24)
        self.btn_sep.pack(side=tk.LEFT)

        self.btn_play = self._btn(sep_frame, "  ▶  REPRODUCIR TODO  ",
                                  self._play_all,
                                  bg=BG3, fg=TEXT,
                                  font=("Segoe UI", 11, "bold"),
                                  pady=11, padx=18)
        self.btn_play.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_stop = self._btn(sep_frame, "  ■  STOP  ",
                                  self._stop_all,
                                  bg=BG3, fg=TEXT3,
                                  font=("Segoe UI", 11, "bold"),
                                  pady=11, padx=18)
        self.btn_stop.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_zip = self._btn(sep_frame, "  ⬇  DESCARGAR ZIP  ",
                                 self._download_zip,
                                 bg=BG3, fg=TEXT3,
                                 font=("Segoe UI", 11, "bold"),
                                 pady=11, padx=18)
        self.btn_zip.pack(side=tk.RIGHT)

        # ── Log / progreso ────────────────────────────────────────────────────
        log_card = tk.Frame(body, bg=CARD, padx=16, pady=10)
        log_card.pack(fill=tk.X, pady=(0, 12))

        log_header = tk.Frame(log_card, bg=CARD)
        log_header.pack(fill=tk.X)
        tk.Label(log_header, text="LOG", font=FONT_LABEL,
                 bg=CARD, fg=TEXT3).pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(log_card, variable=self.progress_var,
                                           maximum=100, mode="indeterminate",
                                           length=200)

        self.log_text = tk.Text(log_card, bg=BG, fg=TEXT2, font=FONT_MONO,
                                height=4, relief=tk.FLAT, state=tk.DISABLED,
                                wrap=tk.WORD, highlightthickness=0)
        self.log_text.pack(fill=tk.X, pady=(4, 0))

        # ── Pistas ────────────────────────────────────────────────────────────
        tk.Label(body, text="PISTAS", font=FONT_LABEL,
                 bg=BG, fg=TEXT3).pack(anchor="w", pady=(4, 6))

        tracks_frame = tk.Frame(body, bg=BG)
        tracks_frame.pack(fill=tk.X)

        for stem in ["vocals", "drums", "bass", "other"]:
            track = StemTrack(
                tracks_frame,
                stem_name=stem,
                color=STEM_COLORS[stem],
                icon=STEM_ICONS[stem],
                label=STEM_LABELS[stem],
                on_solo=self._on_solo,
            )
            track.pack(fill=tk.X, pady=(0, 6))
            self._tracks[stem] = track

    # ── Helpers UI ────────────────────────────────────────────────────────────

    def _btn(self, parent, text, cmd, bg=BG3, fg=TEXT,
             font=FONT_BTN, pady=7, padx=12):
        btn = tk.Label(parent, text=text, font=font,
                       bg=bg, fg=fg, cursor="hand2",
                       pady=pady, padx=padx, relief=tk.FLAT)
        btn.bind("<Button-1>", lambda e: cmd())
        _bg = bg
        _dark = self._darken(bg)
        btn.bind("<Enter>", lambda e: btn.config(bg=_dark))
        btn.bind("<Leave>", lambda e: btn.config(bg=_bg))
        return btn

    def _darken(self, hex_color):
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r = max(0, r - 25)
            g = max(0, g - 25)
            b = max(0, b - 25)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def _rounded_border(self, widget):
        widget.config(highlightthickness=1,
                      highlightbackground=BORDER,
                      highlightcolor=ACCENT)

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar audio",
            filetypes=[
                ("Audio", "*.mp3 *.wav *.flac *.m4a *.ogg *.aac"),
                ("Todos", "*.*")
            ]
        )
        if path:
            self.input_file = path
            self.entry_path.config(state="normal")
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, path)
            self.entry_path.config(state="readonly")
            self._log(f"Archivo cargado: {os.path.basename(path)}")
            for t in self._tracks.values():
                t.reset()
            self.stems = {}

    def _start_separation(self):
        if not self.input_file or not os.path.exists(self.input_file):
            messagebox.showwarning("Sin archivo", "Primero selecciona un archivo de audio.")
            return

        self._stop_all()
        self._clear_log()
        self._log("Iniciando separación con demucs (htdemucs)...")
        self._log("Esto puede tardar varios minutos la primera vez.")

        self.btn_sep.config(fg=TEXT3)
        self.progressbar.pack(fill=tk.X, pady=(4, 0))
        self.progressbar.start(15)

        out_dir = os.path.join(os.path.dirname(self.input_file), "cherrystem_output")

        separar_audio(
            self.input_file,
            out_dir,
            model="htdemucs",
            progress_callback=lambda msg: self.root.after(0, self._log, msg),
            done_callback=lambda stems, err: self.root.after(0, self._on_done, stems, err)
        )

    def _on_done(self, stems, error):
        self.progressbar.stop()
        self.progressbar.pack_forget()
        self.btn_sep.config(fg=TEXT)

        if error:
            self._log(f"❌ Error: {error}")
            messagebox.showerror("Error", f"La separación falló:\n\n{error}\n\nAsegúrate de tener demucs instalado:\npip install demucs")
            return

        if not stems:
            self._log("❌ No se encontraron pistas de salida.")
            return

        self.stems = stems
        self._log("✅ Separación completada.")

        for stem_name, path in stems.items():
            self._log(f"  ✓ {stem_name}: {os.path.basename(path)}")
            if stem_name in self._tracks:
                self._tracks[stem_name].set_file(path)

        self.btn_zip.config(fg=TEXT)

    def _play_all(self):
        if not self.stems:
            messagebox.showinfo("Sin pistas", "Primero separa el audio.")
            return

        self._stop_all()

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            # pygame.mixer solo mezcla N canales; usamos 4
            pygame.mixer.set_num_channels(8)
        except Exception as e:
            self._log(f"Error de audio: {e}")
            return

        self._log("▶ Reproduciendo todas las pistas...")
        self.is_playing = True

        for stem_name, track in self._tracks.items():
            if stem_name in self.stems:
                track.play()

        self.btn_play.config(fg=ACCENT)

    def _stop_all(self):
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        for track in self._tracks.values():
            track.stop()
        self.is_playing = False
        self.btn_play.config(fg=TEXT)

    def _on_solo(self, soloed_name, is_on):
        """Mutea todas las pistas excepto la soloada."""
        if is_on:
            for name, track in self._tracks.items():
                if name != soloed_name:
                    track.set_muted_external(True)
        else:
            # Quitar mute solo si ninguna otra está en solo
            any_solo = any(t._soloed for t in self._tracks.values())
            if not any_solo:
                for track in self._tracks.values():
                    track.set_muted_external(False)

    def _download_zip(self):
        if not self.stems:
            messagebox.showinfo("Sin pistas", "Primero separa el audio.")
            return

        dest = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")],
            initialfile="cherrystem_stems.zip"
        )
        if not dest:
            return

        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for stem_name, path in self.stems.items():
                if os.path.exists(path):
                    zf.write(path, arcname=f"{stem_name}.wav")

        self._log(f"✅ ZIP guardado en: {dest}")
        messagebox.showinfo("Descargado", f"Todas las pistas guardadas en:\n{dest}")

    # ── Loop ──────────────────────────────────────────────────────────────────

    def _on_close(self):
        self._stop_all()
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()