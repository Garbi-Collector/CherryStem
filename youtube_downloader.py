import subprocess
import os
import threading
import tempfile
import re


def es_url_youtube(texto):
    """Detecta si el texto es una URL de YouTube válida."""
    patron = re.compile(
        r"(https?://)?(www\.)?"
        r"(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)"
        r"[\w\-]{11}"
    )
    return bool(patron.search(texto.strip()))


def descargar_audio_youtube(url, progress_callback=None, done_callback=None):
    """
    Descarga el audio de un video de YouTube como MP3.
    Llama a done_callback(ruta_archivo, error).
    Requiere: yt-dlp instalado (pip install yt-dlp)
    """

    def run():
        tmp_dir = None
        try:
            if progress_callback:
                progress_callback("Verificando yt-dlp...")

            # Verificar que yt-dlp esté instalado
            try:
                subprocess.run(
                    ["yt-dlp", "--version"],
                    capture_output=True, check=True
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                if done_callback:
                    done_callback(None, "yt-dlp no está instalado. Ejecutá: pip install yt-dlp")
                return

            tmp_dir = tempfile.mkdtemp()
            output_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")

            if progress_callback:
                progress_callback("Obteniendo información del video...")

            # Obtener título primero
            result = subprocess.run(
                ["yt-dlp", "--get-title", url],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            titulo = result.stdout.strip() if result.returncode == 0 else "audio_youtube"

            if progress_callback:
                progress_callback(f"Descargando: {titulo}")

            # Descargar y convertir a MP3
            comando = [
                "yt-dlp",
                "-x",                          # Extraer solo audio
                "--audio-format", "mp3",
                "--audio-quality", "0",        # Mejor calidad
                "--no-playlist",               # Solo el video, no la playlist
                "-o", output_template,
                "--newline",                   # Una línea por progreso
                url
            ]

            process = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    if line and progress_callback:
                        # Mostrar solo líneas útiles
                        if any(k in line for k in ["[download]", "[ExtractAudio]", "Destination", "ETA", "%"]):
                            progress_callback(line)

            process.wait()

            if process.returncode != 0:
                if done_callback:
                    done_callback(None, "Error al descargar el video. Verificá la URL.")
                return

            # Buscar el MP3 generado
            mp3_file = None
            for f in os.listdir(tmp_dir):
                if f.endswith(".mp3"):
                    mp3_file = os.path.join(tmp_dir, f)
                    break

            if not mp3_file:
                if done_callback:
                    done_callback(None, "No se encontró el archivo de audio descargado.")
                return

            if progress_callback:
                progress_callback(f"✓ Descarga completada: {os.path.basename(mp3_file)}")

            if done_callback:
                done_callback(mp3_file, None)

        except Exception as e:
            if done_callback:
                done_callback(None, str(e))
        # Nota: NO limpiamos tmp_dir acá porque separator.py necesita el archivo.
        # El llamador es responsable de limpiar tmp_dir después de procesar.

    thread = threading.Thread(target=run, daemon=True)
    thread.start()