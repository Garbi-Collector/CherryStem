import subprocess
import os
import threading
import shutil
import tempfile
import unicodedata
import re


def separar_audio(input_file, output_folder, model="htdemucs", progress_callback=None, done_callback=None):
    def run():
        tmp_dir = None
        try:
            if progress_callback:
                progress_callback("Iniciando separación...")

            os.makedirs(output_folder, exist_ok=True)

            # Copiar a ruta temporal sin tildes ni caracteres especiales
            ext = os.path.splitext(input_file)[1]
            raw_name = os.path.splitext(os.path.basename(input_file))[0]
            safe_name = unicodedata.normalize("NFKD", raw_name)
            safe_name = safe_name.encode("ascii", "ignore").decode("ascii")
            safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", safe_name).strip("_") or "audio_input"

            tmp_dir = tempfile.mkdtemp()
            tmp_file = os.path.join(tmp_dir, safe_name + ext)
            shutil.copy2(input_file, tmp_file)

            if progress_callback:
                progress_callback(f"Archivo preparado como: {safe_name}{ext}")

            # Forzar UTF-8
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            # --mp3 evita usar torchaudio/torchcodec para guardar
            comando = [
                "python", "-m", "demucs.separate",
                "-n", model,
                "-o", output_folder,
                "--mp3",
                tmp_file
            ]

            process = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env
            )

            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                if line and progress_callback:
                    line = line.strip()
                    if line:
                        progress_callback(line)

            process.wait()

            if process.returncode != 0:
                if done_callback:
                    done_callback(None, "Error durante la separación. Revisá el log arriba.")
                return

            # Buscar carpeta generada: output_folder/model/safe_name/
            stems_folder = None
            for root, dirs, files in os.walk(output_folder):
                for d in dirs:
                    if d == safe_name:
                        stems_folder = os.path.join(root, d)
                        break
                if stems_folder:
                    break

            if not stems_folder:
                if done_callback:
                    done_callback(None, "No se encontraron archivos de salida.")
                return

            stems = {}
            for stem_key in ["vocals", "drums", "bass", "other"]:
                for ext_out in [".mp3", ".wav", ".flac"]:
                    path = os.path.join(stems_folder, stem_key + ext_out)
                    if os.path.exists(path):
                        stems[stem_key] = path
                        break

            if done_callback:
                done_callback(stems, None)

        except Exception as e:
            if done_callback:
                done_callback(None, str(e))
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    pass

    thread = threading.Thread(target=run, daemon=True)
    thread.start()