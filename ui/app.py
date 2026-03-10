import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import time
import zipfile
import pygame
from separator import separar_audio
from youtube_downloader import es_url_youtube, descargar_audio_youtube
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
        self.input_file      = None
        self.stems           = {}
        self.is_playing      = False
        self._tracks         = {}
        self._duration_ms    = 0
        self._pos_ms         = 0
        self._play_start     = 0
        self._ticker_id      = None
        self._sep_process    = None   # referencia al subprocess de demucs
        self._yt_tmp_dir     = None   # carpeta temporal de descarga de YouTube
        self._separating     = False  # flag para saber si hay proceso activo
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

        # Encabezado con label y hint de YouTube
        header_row = tk.Frame(inner, bg=CARD)
        header_row.pack(fill=tk.X)
        tk.Label(header_row, text="AUDIO FILE OR YOUTUBE URL",
                 font=FONT_LABEL, bg=CARD, fg=TEXT3).pack(side=tk.LEFT, anchor="w")
        tk.Label(header_row, text="▶ youtube.com/watch?v=...  ·  youtu.be/...",
                 font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(side=tk.RIGHT, anchor="e")

        row = tk.Frame(inner, bg=CARD)
        row.pack(fill=tk.X, pady=(5, 0))

        # Entry ahora es editable para pegar URLs
        self.entry_path = tk.Entry(
            row, font=("Segoe UI", 9), bg=BG3, fg=TEXT,
            insertbackground=TEXT, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 8))
        # Placeholder
        self._entry_placeholder = "Paste a YouTube URL or browse a file…"
        self._set_placeholder()
        self.entry_path.bind("<FocusIn>",  self._on_entry_focus_in)
        self.entry_path.bind("<FocusOut>", self._on_entry_focus_out)
        self.entry_path.bind("<Return>",   lambda e: self._load_from_entry())

        b = tk.Label(row, text="Browse", font=("Segoe UI", 9, "bold"),
                     bg=BG3, fg=TEXT2, cursor="hand2", padx=14, pady=7,
                     relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER)
        b.bind("<Button-1>", lambda e: self._pick_file())
        b.bind("<Enter>",    lambda e: b.config(bg=BORDER2, fg=TEXT))
        b.bind("<Leave>",    lambda e: b.config(bg=BG3,     fg=TEXT2))
        b.pack(side=tk.LEFT)

        tk.Label(inner, text="MP3 · WAV · FLAC · M4A · OGG  ·  or paste a YouTube link and press Enter",
                 font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(4, 0))

    def _set_placeholder(self):
        self.entry_path.delete(0, tk.END)
        self.entry_path.insert(0, self._entry_placeholder)
        self.entry_path.config(fg=TEXT3)
        self._placeholder_active = True

    def _on_entry_focus_in(self, event):
        if getattr(self, "_placeholder_active", False):
            self.entry_path.delete(0, tk.END)
            self.entry_path.config(fg=TEXT)
            self._placeholder_active = False

    def _on_entry_focus_out(self, event):
        if not self.entry_path.get().strip():
            self._set_placeholder()

    def _load_from_entry(self):
        """Llamado al presionar Enter en el campo: carga la URL si es YouTube."""
        val = self.entry_path.get().strip()
        if not val or val == self._entry_placeholder:
            return
        if es_url_youtube(val):
            self._log(f"🔗 YouTube URL detectada: {val}")
            self.input_file = val          # guardamos la URL como "archivo"
            self.player.set_track_name(val)
            for t in self._tracks.values():
                t.reset()
            self.stems = {}
            self.player.reset()
        else:
            self._log("⚠️  No es una URL de YouTube válida. Usá Browse para archivos locales.")

    def _build_sep_row(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill=tk.X, pady=(0, 10))

        self.btn_sep = tk.Label(
            row, text="  ✦  SEPARATE TRACKS  ",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg=TEXT, cursor="hand2", padx=20, pady=11, relief=tk.FLAT,
        )
        self.btn_sep.bind("<Button-1>", lambda e: self._start_separation())
        self.btn_sep.bind("<Enter>",    lambda e: self.btn_sep.config(bg=ACCENT_D) if not self._separating else None)
        self.btn_sep.bind("<Leave>",    lambda e: self.btn_sep.config(bg=ACCENT)   if not self._separating else None)
        self.btn_sep.pack(side=tk.LEFT)

        # Botón cancelar — solo visible durante la separación
        self.btn_cancel = tk.Label(
            row, text="  ✕  CANCEL  ",
            font=("Segoe UI", 11, "bold"),
            bg=BG3, fg=TEXT2, cursor="hand2", padx=16, pady=11, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=BORDER,
        )
        self.btn_cancel.bind("<Button-1>", lambda e: self._cancel_separation())
        self.btn_cancel.bind("<Enter>",    lambda e: self.btn_cancel.config(bg=BORDER2, fg=TEXT))
        self.btn_cancel.bind("<Leave>",    lambda e: self.btn_cancel.config(bg=BG3,     fg=TEXT2))
        # Empieza oculto
        self.btn_cancel.pack_forget()

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
        self.entry_path.config(fg=TEXT)
        self._placeholder_active = False
        self.entry_path.delete(0, tk.END)
        self.entry_path.insert(0, path)
        self._log(f"Loaded: {os.path.basename(path)}")
        for t in self._tracks.values():
            t.reset()
        self.stems = {}
        self.player.set_track_name(os.path.basename(path))
        self.player.reset()

    # ── Separation ─────────────────────────────────────────────────────────
    def _set_separating(self, active: bool):
        """Actualiza el estado visual de los botones según si hay proceso activo."""
        self._separating = active
        if active:
            self.btn_sep.config(fg=TEXT3, cursor="")
            self.btn_cancel.pack(side=tk.LEFT, padx=(8, 0))
            self.progressbar.pack(fill=tk.X, pady=(0, 8))
            self.progressbar.start(15)
        else:
            self.btn_sep.config(fg=TEXT, cursor="hand2")
            self.btn_cancel.pack_forget()
            self.progressbar.stop()
            self.progressbar.pack_forget()

    def _cancel_separation(self):
        """Cancela el proceso activo (descarga o separación)."""
        if not self._separating:
            return
        self._log("⏹ Cancelando proceso...")
        # Matar subprocess de demucs si está corriendo
        if self._sep_process and self._sep_process.poll() is None:
            try:
                self._sep_process.terminate()
            except Exception:
                pass
        # Limpiar tmp dir de YouTube si existe
        self._cleanup_yt_tmp()
        self._set_separating(False)
        self._log("✕ Proceso cancelado.")

    def _cleanup_yt_tmp(self):
        if self._yt_tmp_dir and os.path.exists(self._yt_tmp_dir):
            import shutil
            try:
                shutil.rmtree(self._yt_tmp_dir)
            except Exception:
                pass
        self._yt_tmp_dir = None

    def _start_separation(self):
        if self._separating:
            return  # ya hay un proceso en curso

        val = self.entry_path.get().strip()
        is_placeholder = getattr(self, "_placeholder_active", False) or val == self._entry_placeholder

        # Decidir fuente: URL de YouTube o archivo local
        if not is_placeholder and es_url_youtube(val):
            self.input_file = val

        if not self.input_file:
            messagebox.showwarning("No source", "Please select a file or paste a YouTube URL first.")
            return

        self._stop_all()
        self._clear_log()
        self._set_separating(True)

        # ── Flujo YouTube ──────────────────────────────────────────────────
        if es_url_youtube(str(self.input_file)):
            self._log(f"🔗 YouTube URL detectada. Descargando audio…")

            def on_descarga(ruta_mp3, error):
                if not self._separating:   # fue cancelado
                    return
                if error:
                    self.root.after(0, self._on_done, None, f"Error en descarga: {error}")
                    return
                self._yt_tmp_dir = os.path.dirname(ruta_mp3)
                self.root.after(0, self._log, "🎵 Descarga completa. Iniciando separación…")
                self._run_separation(ruta_mp3)

            descargar_audio_youtube(
                url=self.input_file,
                progress_callback=lambda msg: self.root.after(0, self._log, msg),
                done_callback=on_descarga,
            )

        # ── Flujo archivo local ────────────────────────────────────────────
        else:
            if not os.path.exists(self.input_file):
                self._on_done(None, "El archivo no existe.")
                return
            self._log("Starting separation (htdemucs)…")
            self._log("First run may take several minutes.")
            self._run_separation(self.input_file)

    def _run_separation(self, audio_file):
        """Lanza separar_audio pasando la referencia al proceso para poder cancelarlo."""
        out_dir = os.path.join(
            os.path.dirname(audio_file) if os.path.isabs(audio_file) else os.getcwd(),
            "cherrystem_output"
        )

        # Monkey-patch temporal: interceptamos el proceso para guardarlo
        _original_popen = subprocess.Popen

        app_ref = self

        class _TrackingPopen(_original_popen):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                app_ref._sep_process = self

        subprocess.Popen = _TrackingPopen

        try:
            separar_audio(
                audio_file, out_dir, model="htdemucs",
                progress_callback=lambda msg: self.root.after(0, self._log, msg),
                done_callback=lambda s, e: self.root.after(0, self._on_done, s, e),
            )
        finally:
            subprocess.Popen = _original_popen

    def _on_done(self, stems, error):
        self._set_separating(False)
        self._cleanup_yt_tmp()
        self._sep_process = None

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
            self._play_start = time.time() * 1000 - self._pos_ms
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
        self._cancel_separation()
        self._stop_all()
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()