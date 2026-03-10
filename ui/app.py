import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import time
import zipfile
import pygame

from separator import separar_audio
from .theme import (ACCENT, ACCENT_D, BG, BG3, BORDER, BORDER2, CARD,
                    FONT_LABEL, FONT_MONO, FONT_SMALL, SUCCESS, TEXT, TEXT2,
                    TEXT3, STEM_COLORS, STEM_ICONS, STEM_LABELS)
from .stem_track import StemTrack
from .bottom_player import BottomPlayer


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
        self.root.minsize(720, 680)
        self.root.geometry("820x820")

        self.input_file     = None
        self.stems          = {}
        self.is_playing     = False
        self._tracks        = {}
        self._duration_ms   = 0
        self._pos_ms        = 0
        self._play_start    = 0
        self._ticker_id     = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=22, pady=14)

        self._build_file_card(body)
        self._build_sep_row(body)
        self._build_log_card(body)
        self._build_tracks(body)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        self.player = BottomPlayer(
            self.root,
            on_play_pause=self._toggle_play,
            on_stop=self._stop_all,
            on_seek=self._on_seek,
            on_download_zip=self._download_zip,
        )
        self.player.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_header(self):
        h = tk.Frame(self.root, bg=BG)
        h.pack(fill=tk.X, padx=24, pady=(18, 10))
        left = tk.Frame(h, bg=BG)
        left.pack(side=tk.LEFT)
        tk.Label(left, text="🍒", font=("Segoe UI Emoji", 22), bg=BG).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(left, text="CHERRY", font=("Segoe UI", 20, "bold"), bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Label(left, text="STEM",   font=("Segoe UI", 20, "bold"), bg=BG, fg=TEXT).pack(side=tk.LEFT, padx=(3, 0))
        tk.Label(h, text="AI Audio Separator", font=("Segoe UI", 9), bg=BG, fg=TEXT3).pack(side=tk.RIGHT, pady=6)

    def _build_file_card(self, parent):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.X, pady=(0, 10))
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill=tk.X, padx=16, pady=12)

        tk.Label(inner, text="AUDIO FILE", font=FONT_LABEL, bg=CARD, fg=TEXT3).pack(anchor="w")
        row = tk.Frame(inner, bg=CARD)
        row.pack(fill=tk.X, pady=(5, 0))

        self.entry_path = tk.Entry(
            row, font=("Segoe UI", 9), bg=BG3, fg=TEXT,
            insertbackground=TEXT, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, readonlybackground=BG3, state="readonly",
        )
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 8))

        b = tk.Label(row, text="Browse", font=("Segoe UI", 9, "bold"),
                     bg=BG3, fg=TEXT2, cursor="hand2", padx=14, pady=7,
                     relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER)
        b.bind("<Button-1>", lambda e: self._pick_file())
        b.bind("<Enter>",    lambda e: b.config(bg=BORDER2, fg=TEXT))
        b.bind("<Leave>",    lambda e: b.config(bg=BG3,     fg=TEXT2))
        b.pack(side=tk.LEFT)

        tk.Label(inner, text="MP3 · WAV · FLAC · M4A · OGG",
                 font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(4, 0))

    def _build_sep_row(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill=tk.X, pady=(0, 10))

        self.btn_sep = tk.Label(
            row, text="  ✦  SEPARATE TRACKS  ",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg=TEXT, cursor="hand2", padx=20, pady=11, relief=tk.FLAT,
        )
        self.btn_sep.bind("<Button-1>", lambda e: self._start_separation())
        self.btn_sep.bind("<Enter>",    lambda e: self.btn_sep.config(bg=ACCENT_D))
        self.btn_sep.bind("<Leave>",    lambda e: self.btn_sep.config(bg=ACCENT))
        self.btn_sep.pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar()
        self.progressbar  = ttk.Progressbar(parent, variable=self.progress_var,
                                             maximum=100, mode="indeterminate")

    def _build_log_card(self, parent):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.X, pady=(0, 10))
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill=tk.X, padx=14, pady=8)
        tk.Label(inner, text="LOG", font=FONT_LABEL, bg=CARD, fg=TEXT3).pack(anchor="w")
        self.log_text = tk.Text(inner, bg=BG, fg=TEXT2, font=FONT_MONO,
                                height=3, relief=tk.FLAT, state=tk.DISABLED,
                                wrap=tk.WORD, highlightthickness=0)
        self.log_text.pack(fill=tk.X, pady=(4, 0))

    def _build_tracks(self, parent):
        tk.Label(parent, text="STEMS", font=FONT_LABEL,
                 bg=BG, fg=TEXT3).pack(anchor="w", pady=(2, 6))
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill=tk.X)
        for stem in ["vocals", "drums", "bass", "other"]:
            t = StemTrack(frame, stem_name=stem, color=STEM_COLORS[stem],
                          icon=STEM_ICONS[stem], label=STEM_LABELS[stem],
                          on_solo=self._on_solo)
            t.pack(fill=tk.X, pady=(0, 5))
            self._tracks[stem] = t

    # ── Log helpers ────────────────────────────────────────────────────────
    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ── File ───────────────────────────────────────────────────────────────
    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio", "*.mp3 *.wav *.flac *.m4a *.ogg *.aac"), ("All", "*.*")],
        )
        if not path:
            return
        self.input_file = path
        self.entry_path.config(state="normal")
        self.entry_path.delete(0, tk.END)
        self.entry_path.insert(0, path)
        self.entry_path.config(state="readonly")
        self._log(f"Loaded: {os.path.basename(path)}")
        for t in self._tracks.values():
            t.reset()
        self.stems = {}
        self.player.set_track_name(os.path.basename(path))
        self.player.reset()

    # ── Separation ─────────────────────────────────────────────────────────
    def _start_separation(self):
        if not self.input_file or not os.path.exists(self.input_file):
            messagebox.showwarning("No file", "Please select an audio file first.")
            return
        self._stop_all()
        self._clear_log()
        self._log("Starting separation (htdemucs)…")
        self._log("First run may take several minutes.")
        self.btn_sep.config(fg=TEXT3)
        self.progressbar.pack(fill=tk.X, pady=(0, 8))
        self.progressbar.start(15)
        out_dir = os.path.join(os.path.dirname(self.input_file), "cherrystem_output")
        separar_audio(
            self.input_file, out_dir, model="htdemucs",
            progress_callback=lambda msg: self.root.after(0, self._log, msg),
            done_callback=lambda s, e: self.root.after(0, self._on_done, s, e),
        )

    def _on_done(self, stems, error):
        self.progressbar.stop()
        self.progressbar.pack_forget()
        self.btn_sep.config(fg=TEXT)
        if error:
            self._log(f"❌ {error}")
            messagebox.showerror("Error", f"Separation failed:\n\n{error}\n\npip install demucs")
            return
        if not stems:
            self._log("❌ No output tracks found.")
            return
        self.stems = stems
        self._log("✅ Separation complete.")
        for name, path in stems.items():
            self._log(f"  ✓ {name}: {os.path.basename(path)}")
            if name in self._tracks:
                self._tracks[name].set_file(path)
        self._estimate_duration()

    def _estimate_duration(self):
        for path in self.stems.values():
            if os.path.exists(path):
                try:
                    self._duration_ms = int(pygame.mixer.Sound(path).get_length() * 1000)
                    self.player.set_progress(0, self._duration_ms)
                    return
                except Exception:
                    pass

    # ── Playback ───────────────────────────────────────────────────────────
    def _toggle_play(self):
        self._pause_all() if self.is_playing else self._play_all()

    def _play_all(self):
        if not self.stems:
            messagebox.showinfo("No tracks", "Separate audio first.")
            return
        self._stop_all()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
        except Exception as e:
            self._log(f"Audio error: {e}")
            return
        self.is_playing = True
        self._play_start = time.time() * 1000
        for name, track in self._tracks.items():
            if name in self.stems:
                track.play()
        self.player.set_playing(True)
        self._start_ticker()

    def _pause_all(self):
        try:
            pygame.mixer.pause()
        except Exception:
            pass
        self.is_playing = False
        for t in self._tracks.values():
            t.waveform.stop_animation()
        self.player.set_playing(False)
        self._stop_ticker()

    def _stop_all(self):
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        for t in self._tracks.values():
            t.stop()
            t.set_waveform_progress(0)
        self.is_playing = False
        self._pos_ms = 0
        self.player.set_playing(False)
        self.player.set_progress(0, self._duration_ms)
        self._stop_ticker()

    def _on_seek(self, v):
        if self._duration_ms <= 0:
            return
        self._pos_ms = v * self._duration_ms
        for t in self._tracks.values():
            t.set_waveform_progress(v)
        if self.is_playing:
            # Recalcular play_start para que el ticker no se desincronice
            self._play_start = time.time() * 1000 - self._pos_ms
            # Reiniciar cada stem desde el offset
            for name, track in self._tracks.items():
                if name in self.stems:
                    track.play_from(self._pos_ms)

    def _start_ticker(self):
        self._stop_ticker()
        self._tick()

    def _stop_ticker(self):
        if self._ticker_id:
            self.root.after_cancel(self._ticker_id)
            self._ticker_id = None

    def _tick(self):
        if not self.is_playing:
            return
        elapsed = time.time() * 1000 - self._play_start
        pos = min(elapsed, self._duration_ms) if self._duration_ms > 0 else elapsed
        self._pos_ms = pos
        self.player.set_progress(pos, self._duration_ms)
        prog = pos / self._duration_ms if self._duration_ms > 0 else 0
        for t in self._tracks.values():
            t.set_waveform_progress(prog)
        if self._duration_ms > 0 and pos >= self._duration_ms:
            self._stop_all()
            return
        self._ticker_id = self.root.after(250, self._tick)

    def _on_solo(self, soloed_name, is_on):
        if is_on:
            for name, t in self._tracks.items():
                if name != soloed_name:
                    t.set_muted_external(True)
        elif not any(t._soloed for t in self._tracks.values()):
            for t in self._tracks.values():
                t.set_muted_external(False)

    # ── ZIP ────────────────────────────────────────────────────────────────
    def _download_zip(self):
        if not self.stems:
            messagebox.showinfo("No tracks", "Separate audio first.")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")],
            initialfile="cherrystem_stems.zip",
        )
        if not dest:
            return
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, path in self.stems.items():
                if os.path.exists(path):
                    zf.write(path, arcname=f"{name}.wav")
        self._log(f"✅ ZIP saved: {dest}")
        messagebox.showinfo("Exported", f"Stems saved to:\n{dest}")

    # ── Close ──────────────────────────────────────────────────────────────
    def _on_close(self):
        self._stop_all()
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()