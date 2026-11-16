#!/usr/bin/env python3
# ============================================================
# Plugin: Videobehandlare och Bildkomprimerare
# ============================================================
# FIL:       plugins/video_processor.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/video_processor.py)
# Syfte:     Komprimera video och bilder vid export
# PLUGIN_NAME: "Videobehandlare"
# PRIORITY:  25
# VERSION:   3.4.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v3.3.0 → v3.4.0 (snabbhet + minne, icke-brytande):
#   [P]       _compress_image(): explicit stängning av PIL-bilden
#             (finally) – frigör filhandtag + avkodade pixlar direkt
#             i stället för att vänta på GC. Säkrare och lägre toppminne
#             när många bilder komprimeras i följd.
#   [P]       refresh_video_list(): resultat-cache för ffprobe-duration
#             (nyckel: sökväg + storlek + mtime). Vid upprepad omladdning
#             av en oförändrad mapp hoppas onödiga ffprobe-subprocesser
#             över (stor vinst med många/långa videor).
#   [K]       Inga API-namn eller beteenden ändras.
#
# UPPDELAD (> 1800 rader):
#   plugins/video_processor.py     = huvudfil (logik, ~1441 rader)
#   plugins/video_processor_ui.py  = VideoProcessorUIMixin (UI, ~954 rader)
#   class VideoProcessor(VideoProcessorUIMixin, BasePlugin)
#   OBS: video_processor_ui.py ska klistras in/uppdateras i samma mapp
#        innan vi går vidare (regeln: alla filer i samma mapp).
#
# ÄNDRINGAR v3.2.0 → v3.3.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings – ALL %-formatering (logganrop,
#             UI-strängar, FFmpeg-filter, meddelanden)
#   [B3]      AUTHOR + COPYRIGHT (dynamiskt år) + PLATS i header
#   [A9]      save_config: komplett atomiskt mönster
#             (mkstemp -> fdopen -> flush -> fsync -> os.replace)
#   [A10]     load_config/save_config använder helpers.get_config_path()
#             (fallback till projektrotens config/ om helpers saknas)
#   [B1]      Ingen print() – all loggning via queue_log()/log()
#             (verifierat, behålls)
#
# BEVARAT FRÅN v3.1.0–v3.2.0:
#   Ingen print() - all loggning via queue_log() / log()
#   log() och log_error() egna metoder
#   load_config/save_config egna metoder (atomisk)
#   create_ui: tk.Frame(bg=...) istf ttk.Frame
#       -> ingen gra bakgrund i morkt tema
#   _build_ffmpeg_status: tk.LabelFrame(bg=...) istf ttk.LabelFrame
#   _build_image_compression: tk.LabelFrame(bg=...)
#   _build_quick_presets: tk.LabelFrame(bg=...)
#   _build_video_settings: tk.LabelFrame(bg=...)
#   _build_progress_section: tk.LabelFrame(bg=...)
#   _build_video_list: tk.LabelFrame(bg=...)
#   _build_log_section: tk.LabelFrame(bg=...)
#   on_closing: registreras INTE med app.protocol()
#       (system_tray-plugin ager WM_DELETE_WINDOW)
#   preview_video: subprocess.Popen (blockerar ej)
#   _handle_progress_update: tyst felhantering
#   Alla except-block loggar via queue_log()
#   FIX: import sys (anvandes i preview_video/start_processing)
#   FIX: nastlad vprogress-signatur (default-args)
#
# KLASSER I DENNA FIL:
#   VideoProcessor(BasePlugin) - PRIORITY=25
#
# IMPORTER:
#   tkinter as tk, ttk, messagebox, filedialog
#   pathlib.Path
#   subprocess, json, threading, shutil, os, sys
#   queue, time, re, webbrowser, tempfile
#   PIL: Image, ImageOps (valfritt, HAS_PIL)
#   .base_plugin: BasePlugin
#   .video_processor_ui: VideoProcessorUIMixin
#   helpers: get_config_path (valfritt, A10)
#
# CONTEXT SOM LASES:
#   '_tab_manager'   - add_tab()
#   '_settings'      - folder_var
#
# CONTEXT SOM SATTS:
#   '_video_processor' - self
#
# JSON: config/video_settings.json
# ============================================================

import app_paths
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import subprocess
import json
import threading
import shutil
import os
import sys
import queue
import time
import re
import webbrowser
import tempfile
from datetime import datetime

from .base_plugin import BasePlugin

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False

# -- Pillow for bildkomprimering -------------------------------
try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
from .video_processor_ui import VideoProcessorUIMixin


class VideoProcessor(VideoProcessorUIMixin, BasePlugin):
    """
    Plugin for video- och bildbearbetning.

    Video: komprimerar via FFmpeg.
    Bild: komprimerar via Pillow (JPG/PNG/WebP).

    UI fryser ALDRIG - all bearbetning i bakgrundstradar.
    Progress skickas via queue till main thread.

    v3.4.0:
    - Deterministik PIL-resursfrigöring i bildkomprimering (minne)
    - Cache för ffprobe-durationer vid mapp-omladdning (snabbhet)
    - Inga API-ändringar

    v3.3.0:
    - Inga f-strings (B1) - all %-formatering
    - Atomisk skrivning med fsync (A9)
    - config/ via helpers (A10)
    """

    PLUGIN_NAME = "Videobehandlare"
    PRIORITY    = 25
    VERSION     = "3.4.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # -- Bildformat --------------------------------------------
    IMAGE_FORMATS = {
        ".jpg", ".jpeg", ".png", ".webp",
        ".bmp", ".tiff", ".tif", ".heic", ".heif",
    }

    # -- Videoformat -------------------------------------------
    VIDEO_FORMATS = {
        ".mp4", ".avi", ".mov", ".qt", ".mkv", ".wmv", ".flv",
        ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts",
    }

    # -- Farger ------------------------------------------------
    COLOR_SUCCESS = "#22c55e"
    COLOR_ERROR   = "#ef4444"
    COLOR_WARNING = "#f59e0b"
    COLOR_INFO    = "#60a5fa"
    COLOR_BTN_RUN = "#22c55e"
    COLOR_BTN_PAU = "#f59e0b"
    COLOR_BTN_STP = "#ef4444"
    COLOR_BG      = "#1a1a2e"
    COLOR_BG_MID  = "#16213e"
    COLOR_FG      = "#ffffff"
    COLOR_MUTED   = "#888888"

    # ==========================================================================
    # PLUGIN-LIVSCYKEL
    # ==========================================================================

    def init(self, app) -> None:
        """
        Plugin-initiering.

        Steg:
          1. Spara app-referens, initiera state
          2. Ladda installningar
          3. Hitta FFmpeg/FFprobe
          4. Detektera hardvaruencoders
          5. Skapa UI
          6. Registrera i context
          7. Starta UI-uppdaterare
        """
        self.app       = app
        self.is_active = True

        # -- Process-state -------------------------------------
        self.processing       = False
        self.paused           = False
        self.cancel_requested = False
        self.current_process  = None
        self.process_lock     = threading.Lock()

        # -- Koer ----------------------------------------------
        self.progress_queue = queue.Queue()
        self.log_queue      = queue.Queue()

        # -- Statistik -----------------------------------------
        self._reset_stats()

        # -- Video-ko ------------------------------------------
        self.video_queue         = []
        self.current_video_index = 0
        # v3.4.0: cache för ffprobe-durationer (sökväg+storlek+mtime)
        self._duration_cache = {}

        # -- Installningar -------------------------------------
        self.settings = self._default_settings()
        saved = self.load_config("video_settings.json", default={})
        self.settings.update(saved)

        # -- FFmpeg --------------------------------------------
        self.ffmpeg_path       = self.find_ffmpeg()
        self.ffprobe_path      = self.find_ffprobe()
        self.ffmpeg_available  = self.ffmpeg_path is not None
        self.hardware_encoders = self.detect_hardware_encoders()

        # -- UI ------------------------------------------------
        tab_manager = app.context.get("_tab_manager")
        if tab_manager:
            parent = tab_manager.add_tab("video", "Video")
        else:
            parent = tk.Frame(app.main_frame, bg=self.COLOR_BG)
            parent.pack(fill=tk.BOTH, expand=True)

        self.create_ui(parent)

        # -- Registrera ----------------------------------------
        app.context["_video_processor"] = self

        # -- UI-uppdaterare ------------------------------------
        self.start_ui_updater()

        # -- Logg ----------------------------------------------
        if self.ffmpeg_available:
            self.log(
                "OK",
                "Videobehandlare v%s (FFmpeg: %s)"
                % (self.VERSION, self.ffmpeg_path)
            )
            if self.hardware_encoders:
                self.log(
                    "INFO",
                    "Hardvaruencoders: %s"
                    % ", ".join(self.hardware_encoders)
                )
        else:
            self.log("VARNING", "Videobehandlare klar (FFmpeg ej hittad)")

        if HAS_PIL:
            self.log("INFO", "Bildkomprimering tillganglig (Pillow)")
        else:
            self.log(
                "VARNING",
                "Pillow saknas - bildkomprimering ej tillganglig "
                "(pip install Pillow)"
            )

    def execute(self, context: dict, log=None) -> dict:
        """Pipeline-passthrough."""
        return context

    def _default_settings(self) -> dict:
        """Returnerar standardinstallningar."""
        return {
            "ffmpeg_path":           "",
            "ffprobe_path":          "",
            "target_size_mb":        12.0,
            "quality":               "faster",
            "format":                "mp4",
            "max_width":             1280,
            "max_fps":               30,
            "codec":                 "h264",
            "keep_audio":            True,
            "audio_bitrate":         96,
            "two_pass":              False,
            "generate_thumbnail":    True,
            "use_hardware_accel":    False,
            "threads":               0,
            "crf":                   28,
            "extra_args":            "",
            "auto_detect_hardware":  True,
            "compress_images":       True,
            "image_quality":         82,
            "image_max_width":       1920,
            "image_format":          "jpg",
            "image_output_subfolder": "",
            "image_strip_exif":      False,
            "image_progressive":     True,
        }

    def _reset_stats(self) -> None:
        """Aterstall statistik."""
        self.stats = {
            "total_videos":       0,
            "total_images":       0,
            "processed_videos":   0,
            "processed_images":   0,
            "failed":             0,
            "total_input_size":   0,
            "total_output_size":  0,
            "start_time":         None,
            "current_item_start": None,
        }

    def save_settings(self) -> None:
        """Spara config/video_settings.json atomiskt (A9)."""
        try:
            updates = {
                "ffmpeg_path":           self.ffmpeg_path_var.get(),
                "ffprobe_path":          self.ffprobe_path_var.get(),
                "target_size_mb":        self.target_size_var.get(),
                "quality":               self.quality_var.get(),
                "format":                self.format_var.get(),
                "max_width":             self.max_width_var.get(),
                "max_fps":               self.fps_var.get(),
                "codec":                 self.codec_var.get(),
                "keep_audio":            self.keep_audio_var.get(),
                "audio_bitrate":         self.audio_bitrate_var.get(),
                "two_pass":              self.two_pass_var.get(),
                "generate_thumbnail":    self.generate_thumbnail_var.get(),
                "use_hardware_accel":    self.use_hardware_var.get(),
                "threads":               self.threads_var.get(),
                "crf":                   self.crf_var.get(),
                "extra_args":            self.extra_args_var.get(),
                "compress_images":       self.compress_images_var.get(),
                "image_quality":         self.image_quality_var.get(),
                "image_max_width":       self.image_max_width_var.get(),
                "image_format":          self.image_format_var.get(),
                "image_strip_exif":      self.image_strip_exif_var.get(),
                "image_progressive":     self.image_progressive_var.get(),
            }
            self.settings.update(updates)
            self.save_config("video_settings.json", self.settings)
            self.queue_log("Installningar sparade", "success")
        except Exception as e:
            self.queue_log(
                "Kunde inte spara installningar: %s" % e, "error"
            )

    def detect_hardware_encoders(self) -> list:
        """Detektera NVENC/AMF/QSV/Videotoolbox."""
        encoders = []
        if not self.ffmpeg_path:
            return encoders
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True, text=True, timeout=10,
                creationflags=self._no_window_flag(),
            )
            output = result.stdout
            checks = [
                ("h264_nvenc",         "nvenc_h264"),
                ("hevc_nvenc",         "nvenc_hevc"),
                ("h264_amf",           "amf_h264"),
                ("hevc_amf",           "amf_hevc"),
                ("h264_qsv",           "qsv_h264"),
                ("hevc_qsv",           "qsv_hevc"),
                ("h264_videotoolbox",  "videotoolbox_h264"),
                ("hevc_videotoolbox",  "videotoolbox_hevc"),
            ]
            for ffmpeg_name, label in checks:
                if ffmpeg_name in output:
                    encoders.append(label)
        except Exception as e:
            self.queue_log(
                "Kunde inte detektera hardvaruencoders: %s" % e,
                "warning",
            )
        return encoders

    def find_ffmpeg(self):
        """Hitta FFmpeg i sparad sokvag -> PATH -> vanliga platser."""
        saved = self.settings.get("ffmpeg_path", "")
        if saved and Path(saved).exists() and self.test_ffmpeg(saved):
            return saved

        for name in ("ffmpeg", "ffmpeg.exe"):
            path = shutil.which(name)
            if path and self.test_ffmpeg(path):
                return path

        common = [
            Path(os.environ.get("PROGRAMFILES",      "")) / "ffmpeg/bin/ffmpeg.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "ffmpeg/bin/ffmpeg.exe",
            Path(os.environ.get("LOCALAPPDATA",      "")) / "ffmpeg/bin/ffmpeg.exe",
            Path.home() / "ffmpeg/bin/ffmpeg.exe",
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("/usr/local/bin/ffmpeg"),
            Path("/opt/homebrew/bin/ffmpeg"),
        ]
        for path in common:
            if path.exists() and self.test_ffmpeg(str(path)):
                return str(path)
        from media_support import bundled_ffmpeg
        bundled = bundled_ffmpeg()
        if bundled and self.test_ffmpeg(bundled):
            return bundled
        return None

    def find_ffprobe(self):
        """Hitta FFprobe intill FFmpeg -> PATH."""
        saved = self.settings.get("ffprobe_path", "")
        if saved and Path(saved).exists():
            return saved

        if self.ffmpeg_path:
            probe = Path(self.ffmpeg_path).with_name(
                "ffprobe.exe" if os.name == "nt" else "ffprobe"
            )
            if probe.exists():
                return str(probe)

        return shutil.which("ffprobe") or shutil.which("ffprobe.exe")

    def test_ffmpeg(self, path: str) -> bool:
        """Returnerar True om FFmpeg svarar korrekt."""
        try:
            result = subprocess.run(
                [path, "-version"],
                capture_output=True, text=True, timeout=5,
                creationflags=self._no_window_flag(),
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _no_window_flag() -> int:
        """CREATE_NO_WINDOW pa Windows, 0 annars."""
        return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    def _bind_mousewheel(self, event=None) -> None:
        """Bind mushjul till canvas."""
        if not self.is_active:
            return
        try:
            self.canvas.bind("<MouseWheel>", self._on_mousewheel)
            self.canvas.bind(
                "<Button-4>", lambda e: self._scroll(-3)
            )
            self.canvas.bind(
                "<Button-5>", lambda e: self._scroll(3)
            )
        except Exception:
            pass

    def _unbind_mousewheel(self, event=None) -> None:
        """Unbind mushjul fran canvas."""
        try:
            self.canvas.unbind("<MouseWheel>")
            self.canvas.unbind("<Button-4>")
            self.canvas.unbind("<Button-5>")
        except Exception:
            pass

    def _on_mousewheel(self, event) -> None:
        """Hantera mushjul (Windows/Mac) - 3 enheter."""
        if not self.is_active:
            return
        try:
            self.canvas.yview_scroll(
                -1 * (event.delta // 120) * 3, "units"
            )
        except Exception:
            pass

    def _scroll(self, direction: int) -> None:
        """Hantera mushjul (Linux) - direkt antal enheter."""
        if not self.is_active:
            return
        try:
            self.canvas.yview_scroll(direction, "units")
        except Exception:
            pass

    def start_ui_updater(self) -> None:
        """Starta UI-uppdaterare (20fps) i main thread."""
        def _update():
            if not self.is_active:
                return
            try:
                while not self.progress_queue.empty():
                    msg_type, data = self.progress_queue.get_nowait()
                    self._handle_progress_update(msg_type, data)
            except Exception:
                pass
            try:
                while not self.log_queue.empty():
                    msg, tag = self.log_queue.get_nowait()
                    self._write_log(msg, tag)
            except Exception:
                pass
            if self.is_active:
                self.app.after(50, _update)

        _update()

    def _handle_progress_update(self, msg_type: str, data) -> None:
        """Hantera progress-uppdatering i main thread."""
        try:
            if msg_type == "total":
                self.total_progress_var.set(data)
            elif msg_type == "current":
                self.current_progress_var.set(data)
                self.current_percent_label.config(text="%d%%" % int(data))
            elif msg_type == "status":
                self.status_label.config(text=data)
            elif msg_type == "file":
                self.current_file_label.config(text=str(data)[:32])
            elif msg_type == "overall":
                self.overall_label.config(text=data)
            elif msg_type == "eta":
                self.eta_label.config(text=data)
            elif msg_type == "speed":
                self.speed_label.config(text=data)
            elif msg_type == "done":
                self._on_processing_complete(data)
            elif msg_type == "error":
                self._on_processing_error(data)
            elif msg_type == "tree_update":
                self._update_tree_item(*data)
        except Exception:
            pass

    def _update_tree_item(self, item_id, status: str) -> None:
        """Uppdatera status i Treeview."""
        try:
            self.video_tree.set(item_id, "status", status)
        except Exception:
            pass

    def queue_log(self, message: str, tag: str = None) -> None:
        """Koa loggmeddelande (tradsakert)."""
        self.log_queue.put((message, tag))

    def _write_log(self, message: str, tag: str = None) -> None:
        """Skriv till logg i main thread."""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            self.log_text.insert(
                tk.END, "[%s] %s\n" % (ts, message), tag or ""
            )
            self.log_text.see(tk.END)
        except Exception:
            pass

    def refresh_video_list(self) -> None:
        """Skanna mapp och fyll Treeview med videofiler."""
        self.video_tree.delete(*self.video_tree.get_children())
        self.video_queue.clear()

        settings = self.app.context.get("_settings")
        folder   = None
        if settings and hasattr(settings, "folder_var"):
            folder = settings.folder_var.get()

        if not folder or not Path(folder).exists():
            self.video_count_label.config(text="Ingen mapp vald")
            return

        videos = self.find_videos(Path(folder))
        # v3.4.0: cachelagra ffprobe-resultat per (storlek, mtime) så att
        # oförändrade filer inte subprocess-probas om vid varje omladdning.
        cache = self._duration_cache
        for video in videos:
            st          = video.stat()
            size_mb     = st.st_size / (1024 * 1024)
            cache_key   = (str(video), st.st_size, st.st_mtime)
            duration_str = "-"
            duration_sec = 60.0

            dur = cache.get(cache_key)
            if dur is None:
                info = self.get_video_info_quick(video)
                dur  = (
                    info.get("duration", 0) if info else 0
                )
                cache[cache_key] = dur
            if dur:
                duration_sec = dur
                duration_str = "%d:%02d" % (
                    int(dur // 60), int(dur % 60)
                )

            item_id = self.video_tree.insert("", "end", values=(
                video.name,
                "%.1f MB" % size_mb,
                duration_str,
                "Vantar",
            ))
            self.video_queue.append({
                "path":     video,
                "item_id":  item_id,
                "size":     size_mb,
                "duration": duration_sec,
            })

        self.video_count_label.config(
            text="%d videor" % len(videos)
        )

    def find_videos(self, folder: Path) -> list:
        """Hitta videofiler i mapp (exklusive Removed)."""
        if not folder.exists():
            return []
        return sorted(
            [
                f for f in folder.iterdir()
                if f.is_file()
                and f.suffix.lower() in self.VIDEO_FORMATS
                and "Removed" not in str(f)
            ],
            key=lambda x: x.name.lower(),
        )

    def get_video_info_quick(self, path: Path):
        """Hamta bara duration via ffprobe."""
        if not self.ffprobe_path:
            from ffmpeg_progress import duration_from_ffmpeg
            try:
                duration = duration_from_ffmpeg(self.ffmpeg_path, path, self._no_window_flag())
                return {'duration': duration} if duration > 0 else None
            except Exception:
                return None
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "quiet",
                 "-print_format", "json", "-show_format", str(path)],
                capture_output=True, text=True, timeout=10,
                creationflags=self._no_window_flag(),
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "duration": float(
                        data.get("format", {}).get("duration", 0)
                    )
                }
        except Exception:
            pass
        return None

    def get_video_info(self, path: Path):
        """Fullstandig videoinfo via ffprobe."""
        if not self.ffprobe_path:
            return None
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "quiet",
                 "-print_format", "json",
                 "-show_format", "-show_streams", str(path)],
                capture_output=True, text=True, timeout=30,
                creationflags=self._no_window_flag(),
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None

    def show_video_info(self) -> None:
        """Visa videoinfo-dialog."""
        sel = self.video_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Valj en video i listan.")
            return

        filename = self.video_tree.item(sel[0])["values"][0]
        vd = next(
            (v for v in self.video_queue if v["path"].name == filename),
            None
        )
        if not vd:
            return

        info = self.get_video_info(vd["path"])
        if not info:
            messagebox.showerror(
                "Fel", "Kunde inte lasa videoinformation."
            )
            return

        fmt     = info.get("format", {})
        streams = info.get("streams", [])
        vs      = next(
            (s for s in streams if s.get("codec_type") == "video"), {}
        )
        as_     = next(
            (s for s in streams if s.get("codec_type") == "audio"), {}
        )

        duration = float(fmt.get("duration", 0))
        size     = int(fmt.get("size", 0))
        bitrate  = int(fmt.get("bit_rate", 0))

        fps = 0
        fps_str = vs.get("r_frame_rate", "0/1")
        try:
            if "/" in fps_str:
                n, d = fps_str.split("/")
                fps = float(n) / float(d) if float(d) else 0
            else:
                fps = float(fps_str)
        except Exception:
            pass

        msg = (
            "Fil: %s\n%s\n\n"
            "Langd:   %d:%02d\n"
            "Storlek: %.1f MB\n"
            "Bitrate: %.0f kbps\n\n"
            "Video:\n"
            "  Codec:      %s\n"
            "  Upplosning: %sx%s\n"
            "  FPS:        %.1f\n\n"
            "Ljud:\n"
            "  Codec:       %s\n"
            "  Kanaler:     %s\n"
            "  Sample rate: %s Hz"
            % (
                filename,
                "=" * 42,
                int(duration // 60), int(duration % 60),
                size / (1024 * 1024),
                bitrate / 1000,
                vs.get("codec_name", "Okand"),
                vs.get("width", "?"), vs.get("height", "?"),
                fps,
                as_.get("codec_name", "Inget"),
                as_.get("channels", "-"),
                as_.get("sample_rate", "-"),
            )
        )
        messagebox.showinfo("Videoinformation", msg)

    def preview_video(self) -> None:
        """Spela upp video i OS-standardspelare (Popen - blockerar ej)."""
        sel = self.video_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Valj en video i listan.")
            return

        filename = self.video_tree.item(sel[0])["values"][0]
        vd = next(
            (v for v in self.video_queue if v["path"].name == filename),
            None
        )
        if not vd:
            return

        path = vd["path"]
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            messagebox.showerror(
                "Fel", "Kunde inte spela upp video:\n%s" % e
            )

    def remove_from_list(self) -> None:
        """Ta bort valda videor fran Treeview och video_queue."""
        for item_id in self.video_tree.selection():
            filename = self.video_tree.item(item_id)["values"][0]
            self.video_queue = [
                v for v in self.video_queue
                if v["path"].name != filename
            ]
            self.video_tree.delete(item_id)
        self.video_count_label.config(
            text="%d videor" % len(self.video_queue)
        )

    def start_processing(self) -> None:
        """Starta bearbetning av video och/eller bilder."""
        do_video  = self.ffmpeg_available and bool(self.video_queue)
        do_images = self.compress_images_var.get() and HAS_PIL

        if not do_video and not do_images:
            if not self.ffmpeg_available:
                messagebox.showerror(
                    "Saknas", "FFmpeg kravs for videokomprimering."
                )
            elif not HAS_PIL:
                messagebox.showerror(
                    "Saknas",
                    "Pillow kravs for bildkomprimering.\n\n"
                    "pip install Pillow"
                )
            else:
                messagebox.showinfo(
                    "Info",
                    "Inga videor i listan och bildkomprimering inaktiverad."
                )
            return

        settings = self.app.context.get("_settings")
        folder   = None
        if settings and hasattr(settings, "folder_var"):
            folder = settings.folder_var.get()

        if not folder or not Path(folder).exists():
            messagebox.showerror("Fel", "Ingen kallmapp vald.")
            return

        source_path = Path(folder)

        if do_video and not self.video_queue:
            self.refresh_video_list()
            if not self.video_queue:
                do_video = False

        image_files = []
        if do_images:
            image_files = [
                f for f in source_path.iterdir()
                if f.is_file()
                and f.suffix.lower() in self.IMAGE_FORMATS
                and not f.name.startswith(".")
            ]

        if not do_video and not image_files:
            messagebox.showinfo("Info", "Inga filer att bearbeta.")
            return

        summary = []
        if do_video:
            summary.append("- %d videofil(er)" % len(self.video_queue))
        if image_files:
            summary.append(
                "- %d bildfil(er) (kvalitet %d%%)"
                % (len(image_files), self.image_quality_var.get())
            )

        if not messagebox.askyesno(
            "Starta bearbetning",
            "Bearbeta:\n"
            + "\n".join(summary)
            + "\n\nOutput: out/%s/" % source_path.name
        ):
            return

        app_dir   = Path(__file__).parent.parent
        video_out = app_dir / "out" / source_path.name / "video"
        image_out = app_dir / "out" / source_path.name / "image"

        if do_video:
            video_out.mkdir(parents=True, exist_ok=True)
        if image_files:
            image_out.mkdir(parents=True, exist_ok=True)

        self._reset_stats()
        self.stats["total_videos"] = len(self.video_queue) if do_video else 0
        self.stats["total_images"] = len(image_files)
        self.stats["start_time"]   = time.time()
        self.stats["total_input_size"] = (
            sum(v["size"] for v in self.video_queue)
            + sum(f.stat().st_size / (1024 * 1024) for f in image_files)
        )

        self.processing       = True
        self.paused           = False
        self.cancel_requested = False
        self.process_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.cancel_btn.config(state="normal")

        self.queue_log("=" * 42, "info")
        self.queue_log(
            "Startar: %d videor + %d bilder"
            % (self.stats["total_videos"], self.stats["total_images"]),
            "info"
        )
        self.queue_log("=" * 42, "info")

        threading.Thread(
            target=self._process_all_worker,
            args=(video_out, image_out, image_files,
                  do_video, bool(image_files)),
            daemon=True, name='MediaProcessingThread',
        ).start()

    def _process_all_worker(self, *args) -> None:
        progress = getattr(self.app, '_processing_progress', None)
        self._processing_progress_job = progress.begin('Bearbetar video och bilder') if progress else None
        failed = False
        try:
            self._process_all_work(*args)
        except Exception as exc:
            failed = True
            self.progress_queue.put(('error', exc))
        finally:
            if progress:
                progress.finish(self._processing_progress_job,
                                failed=failed or bool(self.stats.get('failed')),
                                cancelled=self.cancel_requested)

    def _process_all_work(
        self, video_out, image_out, image_files,
        do_video, do_images
    ) -> None:
        """
        Huvud-worker for all bearbetning.
        Kor video + bild sekventiellt.
        All kommunikation med UI via koer.
        """
        processed_videos = []
        processed_images = []
        failed           = []

        total_items = (
            (len(self.video_queue) if do_video else 0)
            + (len(image_files) if do_images else 0)
        )
        done_items = 0

        # -- Video ---------------------------------------------
        if do_video:
            for i, vd in enumerate(self.video_queue):
                if self.cancel_requested:
                    break
                while self.paused and not self.cancel_requested:
                    time.sleep(0.5)
                if self.cancel_requested:
                    break

                vp = vd["path"]
                progress = getattr(self.app, '_processing_progress', None)
                if progress:
                    progress.stage(self._processing_progress_job, 'Video %d/%d – %s' % (i + 1, len(self.video_queue), vp.name))
                self.progress_queue.put(
                    ("tree_update", (vd["item_id"], "Bearbetar..."))
                )
                self.progress_queue.put(("file",   vp.name))
                self.progress_queue.put(
                    ("status", "Video %d/%d" % (i + 1, len(self.video_queue)))
                )
                self.stats["current_item_start"] = time.time()

                out_file = video_out / ("%s.%s" % (vp.stem, self.format_var.get()))

                def vprogress(pct, _done=done_items, _total=total_items):
                    self.progress_queue.put(("current", pct))
                    progress = getattr(self.app, '_processing_progress', None)
                    if progress:
                        progress.stage(self._processing_progress_job, 'Konverterar ' + vp.name, pct if pct < 100 else None)
                    if pct > 5:
                        el  = time.time() - self.stats["current_item_start"]
                        eta = (el / pct) * (100 - pct)
                        self.progress_queue.put(("eta", "~%ds" % int(eta)))
                    global_pct = (
                        (_done + pct / 100) / _total
                    ) * 100
                    self.progress_queue.put(("total", global_pct))

                try:
                    self._compress_video(
                        vp, out_file, vd["duration"], vprogress
                    )

                    if self.generate_thumbnail_var.get() and out_file.exists():
                        self._generate_thumbnail(
                            vp,
                            video_out / ("%s_thumb.jpg" % vp.stem)
                        )

                    if out_file.exists():
                        size_mb = out_file.stat().st_size / (1024 * 1024)
                        self.stats["processed_videos"] += 1
                        self.stats["total_output_size"] += size_mb
                        processed_videos.append(
                            {"name": out_file.name, "size": size_mb}
                        )
                        self.progress_queue.put(
                            ("tree_update",
                             (vd["item_id"], "OK %.1f MB" % size_mb))
                        )
                        self.queue_log(
                            "OK %s -> %.1f MB" % (vp.name, size_mb),
                            "success"
                        )
                    else:
                        raise RuntimeError("Output-fil skapades inte")

                except Exception as e:
                    self.stats["failed"] += 1
                    failed.append((vp.name, str(e)[:60]))
                    self.progress_queue.put(
                        ("tree_update", (vd["item_id"], "Fel"))
                    )
                    self.queue_log("FEL %s: %s" % (vp.name, e), "error")

                done_items += 1
                progress = getattr(self.app, '_processing_progress', None)
                if progress:
                    progress.stage(self._processing_progress_job, '%d/%d filer behandlade' % (done_items, total_items), 100 * done_items / max(1, total_items))
                self.progress_queue.put(
                    ("overall", "%d/%d" % (done_items, total_items))
                )

        # -- Bilder --------------------------------------------
        if do_images and not self.cancel_requested:
            for i, img_path in enumerate(image_files):
                if self.cancel_requested:
                    break
                while self.paused and not self.cancel_requested:
                    time.sleep(0.5)
                if self.cancel_requested:
                    break

                progress = getattr(self.app, '_processing_progress', None)
                if progress:
                    progress.stage(self._processing_progress_job, 'Bild %d/%d – %s' % (i + 1, len(image_files), img_path.name))
                self.progress_queue.put(("file",   img_path.name))
                self.progress_queue.put(
                    ("status", "Bild %d/%d" % (i + 1, len(image_files)))
                )
                self.progress_queue.put(("current", 0))
                self.stats["current_item_start"] = time.time()

                out_fmt  = self.image_format_var.get()
                out_name = "%s.%s" % (img_path.stem, out_fmt)
                out_file = image_out / out_name

                try:
                    result = self._compress_image(img_path, out_file)
                    if result and out_file.exists():
                        size_mb = out_file.stat().st_size / (1024 * 1024)
                        orig_mb = img_path.stat().st_size / (1024 * 1024)
                        ratio   = (
                            (1 - size_mb / orig_mb) * 100
                            if orig_mb > 0 else 0
                        )
                        self.stats["processed_images"] += 1
                        self.stats["total_output_size"] += size_mb
                        processed_images.append(
                            {"name": out_name, "size": size_mb}
                        )
                        self.queue_log(
                            "OK %s -> %.1f MB (-%.0f%%)"
                            % (img_path.name, size_mb, ratio),
                            "success"
                        )
                    else:
                        raise RuntimeError("Output-fil skapades inte")

                except Exception as e:
                    self.stats["failed"] += 1
                    failed.append((img_path.name, str(e)[:60]))
                    self.queue_log(
                        "FEL %s: %s" % (img_path.name, e), "error"
                    )

                done_items += 1
                progress = getattr(self.app, '_processing_progress', None)
                if progress:
                    progress.stage(self._processing_progress_job, '%d/%d filer behandlade' % (done_items, total_items), 100 * done_items / max(1, total_items))
                self.progress_queue.put(("current", 100))
                self.progress_queue.put(
                    ("overall", "%d/%d" % (done_items, total_items))
                )
                self.progress_queue.put(
                    ("total", (done_items / total_items) * 100)
                )

        # -- Klar ---------------------------------------------
        self.progress_queue.put(("done", {
            "processed_videos": processed_videos,
            "processed_images": processed_images,
            "failed":           failed,
            "cancelled":        self.cancel_requested,
            "stats":            self.stats,
        }))

    def _compress_video(
        self, input_path, output_path, duration, progress_callback=None
    ) -> None:
        """
        Komprimera video med FFmpeg.
        Non-blocking progress via stdout (pipe:1).
        Avbryts omedelbart vid cancel_requested.
        """
        ffmpeg = self.ffmpeg_path_var.get() or self.ffmpeg_path
        if not ffmpeg:
            raise RuntimeError("FFmpeg ej konfigurerat")
        if duration <= 0:
            from ffmpeg_progress import duration_from_ffmpeg
            try:
                duration = duration_from_ffmpeg(ffmpeg, input_path, self._no_window_flag())
            except Exception:
                duration = 0

        codec     = self.codec_var.get()
        codec_map = {
            "h264": "libx264", "h265": "libx265", "vp9": "libvpx-vp9"
        }
        hw_map = {
            ("h264", "nvenc"):        "h264_nvenc",
            ("h264", "qsv"):          "h264_qsv",
            ("h264", "videotoolbox"): "h264_videotoolbox",
            ("h265", "nvenc"):        "hevc_nvenc",
            ("h265", "qsv"):          "hevc_qsv",
        }

        encoder = codec_map.get(codec, "libx264")
        if self.use_hardware_var.get() and self.hardware_encoders:
            for (c, hw), hw_enc in hw_map.items():
                if c == codec and any(hw in e for e in self.hardware_encoders):
                    encoder = hw_enc
                    break

        cmd = [ffmpeg, '-hide_banner', '-nostdin', "-y", "-i", str(input_path)]
        cmd.extend(["-c:v", encoder])
        cmd.extend(["-crf", str(self.crf_var.get())])
        if codec in ("h264", "h265") and encoder.startswith("lib"):
            cmd.extend(["-preset", self.quality_var.get()])

        mw = self.max_width_var.get()
        cmd.extend(["-vf", "scale=min(%d\\,iw):-2" % mw])
        cmd.extend(["-r", str(self.fps_var.get())])

        if self.keep_audio_var.get():
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "%dk" % self.audio_bitrate_var.get(),
                "-ac", "2",
            ])
        else:
            cmd.extend(["-an"])

        if self.threads_var.get() > 0:
            cmd.extend(["-threads", str(self.threads_var.get())])

        if codec == "h264" and encoder.startswith("lib"):
            cmd.extend([
                "-movflags", "+faststart", "-pix_fmt", "yuv420p"
            ])

        extra = self.extra_args_var.get().strip()
        if extra:
            cmd.extend(extra.split())

        cmd.extend(["-progress", "pipe:1", "-nostats"])
        cmd.append(str(output_path))

        with self.process_lock:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=self._no_window_flag(),
                bufsize=1,
            )

        try:
            from ffmpeg_progress import monitor
            latest_percent = None
            def report_progress(value):
                nonlocal latest_percent
                latest_percent = value
                if progress_callback:
                    progress_callback(value)
            def heartbeat(elapsed, silent):
                text = 'FFmpeg arbetar · %ds' % elapsed
                if silent >= 30:
                    text = 'FFmpeg kör · inga nya statusdata på %ds' % silent
                elif duration <= 0:
                    text += ' · okänd längd (procent saknas)'
                self.progress_queue.put(('status', text))
                self.progress_queue.put(('speed', 'Aktiv i %ds' % elapsed))
                progress = getattr(self.app, '_processing_progress', None)
                if progress:
                    progress.stage(self._processing_progress_job, input_path.name + ' · ' + text, latest_percent)
            monitor(self.current_process, duration=duration, progress=report_progress,
                    cancelled=lambda: self.cancel_requested, heartbeat=heartbeat,
                    timeout=max(3600, duration * 30))

        finally:
            with self.process_lock:
                self.current_process = None

    def _compress_image(self, input_path: Path, output_path: Path) -> bool:
        """
        Komprimera en bild med Pillow.

        Stodjer: JPEG, PNG, WebP, BMP, TIFF
        Hanterar EXIF-rotation, strip EXIF, max bredd,
        Progressive JPEG, RGB-konvertering.
        Returnerar True vid framgang.
        """
        if not HAS_PIL:
            raise RuntimeError("Pillow ej installerat")

        # v3.4.0: håll referens och stäng deterministiskt så att
        # filhandtag + avkodade pixlar frigörs direkt (lägre toppminne).
        _to_close = []
        try:
            opened = Image.open(input_path)
            _to_close.append(opened)
            img = opened
            try:
                img = ImageOps.exif_transpose(img)
                if img is not opened:
                    _to_close.append(img)
                    opened = img
            except Exception:
                pass

            max_w = self.image_max_width_var.get()
            if max_w > 0 and img.width > max_w:
                ratio = max_w / img.width
                img   = img.resize(
                    (max_w, int(img.height * ratio)),
                    Image.Resampling.LANCZOS
                )

            out_fmt = self.image_format_var.get().lower()

            if out_fmt in ("jpg", "jpeg") and img.mode in ("RGBA", "P", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(
                    img,
                    mask=img.split()[-1] if "A" in img.mode else None
                )
                img = bg
            elif out_fmt == "png" and img.mode not in (
                "RGBA", "RGB", "L", "P"
            ):
                img = img.convert("RGBA")
            elif out_fmt not in ("jpg", "jpeg", "png", "webp") \
                    and img.mode != "RGB":
                img = img.convert("RGB")

            quality     = self.image_quality_var.get()
            progressive = self.image_progressive_var.get()
            strip_exif  = self.image_strip_exif_var.get()
            save_kwargs = {}

            if out_fmt in ("jpg", "jpeg"):
                save_kwargs["format"]   = "JPEG"
                save_kwargs["quality"]  = quality
                save_kwargs["optimize"] = True
                if progressive:
                    save_kwargs["progressive"] = True
                if not strip_exif:
                    try:
                        exif = img.info.get("exif")
                        if exif:
                            save_kwargs["exif"] = exif
                    except Exception:
                        pass
            elif out_fmt == "png":
                compress = max(0, min(9, int((100 - quality) / 11)))
                save_kwargs["format"]         = "PNG"
                save_kwargs["compress_level"] = compress
                save_kwargs["optimize"]       = True
            elif out_fmt == "webp":
                save_kwargs["format"]  = "WEBP"
                save_kwargs["quality"] = quality
                save_kwargs["method"]  = 4

            img.save(output_path, **save_kwargs)
            return True

        except Exception as e:
            raise RuntimeError("Bildkomprimering misslyckades: %s" % e)
        finally:
            # v3.4.0: stäng deterministiskt – frigör resurser direkt
            for pil_img in _to_close:
                try:
                    pil_img.close()
                except Exception:
                    pass

    def _generate_thumbnail(
        self, video_path: Path, output_path: Path
    ) -> None:
        """Generera video-thumbnail med FFmpeg (1s in)."""
        ffmpeg = self.ffmpeg_path_var.get() or self.ffmpeg_path
        if not ffmpeg:
            return
        try:
            subprocess.run(
                [ffmpeg, "-y", "-ss", "00:00:01",
                 "-i", str(video_path),
                 "-vframes", "1", "-vf", "scale=320:-1",
                 str(output_path)],
                capture_output=True, timeout=30,
                creationflags=self._no_window_flag(),
            )
        except Exception:
            pass

    def toggle_pause(self) -> None:
        """Pausa/fortsatt bearbetning."""
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text="Fortsatt")
            self.progress_queue.put(("status", "Pausad"))
            self.queue_log("Bearbetning pausad", "warning")
        else:
            self.pause_btn.config(text="Pausa")
            self.progress_queue.put(("status", "Fortsatter..."))
            self.queue_log("Bearbetning fortsatter", "info")

    def cancel_processing(self) -> None:
        """Avbryt bearbetning."""
        if not messagebox.askyesno(
            "Avbryt", "Avbryta pagaende bearbetning?"
        ):
            return
        self.cancel_requested = True
        # The monitor sees this flag within ~200 ms and terminates/reaps FFmpeg.
        self.progress_queue.put(("status", "Avbryter..."))
        self.queue_log("Avbryter bearbetning...", "warning")

    def _on_processing_complete(self, result: dict) -> None:
        """Hantera avslutad bearbetning (main thread)."""
        self.processing = False
        self.process_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Pausa")
        self.cancel_btn.config(state="disabled")

        stats  = result["stats"]
        pv     = result["processed_videos"]
        pi     = result["processed_images"]
        failed = result["failed"]

        elapsed  = time.time() - stats["start_time"]
        mins     = int(elapsed // 60)
        secs     = int(elapsed % 60)
        in_size  = stats["total_input_size"]
        out_size = stats["total_output_size"]
        ratio    = (1 - out_size / in_size) * 100 if in_size > 0 else 0

        self.queue_log("=" * 42, "info")
        self.queue_log(
            "Klart! Videor: %d, Bilder: %d, Fel: %d"
            % (len(pv), len(pi), len(failed)),
            "success"
        )
        self.queue_log(
            "Tid: %dm %ds  |  Komprimering: -%.0f%%"
            % (mins, secs, ratio),
            "info"
        )
        self.queue_log("=" * 42, "info")

        self.progress_queue.put(
            ("status", "Klart! %d filer" % (len(pv) + len(pi)))
        )
        self.progress_queue.put(("total", 100))
        self.progress_queue.put(("eta",   ""))

        if result["cancelled"]:
            messagebox.showinfo(
                "Avbrutet",
                "Bearbetning avbruten.\n\n"
                "%d videor + %d bilder klara." % (len(pv), len(pi))
            )
        elif failed:
            messagebox.showwarning(
                "Delvis klart",
                "Bearbetning klar!\n\n"
                "OK %d videor + %d bilder\n"
                "FEL %d misslyckades\n\n"
                "Tid: %dm %ds  |  -%.0f%%"
                % (len(pv), len(pi), len(failed), mins, secs, ratio)
            )
        else:
            messagebox.showinfo(
                "Klart!",
                "Alla filer bearbetade!\n\n"
                "OK %d videor + %d bilder\n\n"
                "Tid: %dm %ds  |  -%.0f%%"
                % (len(pv), len(pi), mins, secs, ratio)
            )

    def _on_processing_error(self, error) -> None:
        """Hantera kritiskt fel (main thread)."""
        self.processing = False
        self.process_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.cancel_btn.config(state="disabled")
        self.queue_log("Kritiskt fel: %s" % error, "error")
        self.progress_queue.put(("status", "Fel: %s" % error))
        messagebox.showerror("Fel", str(error))

    def browse_ffmpeg(self) -> None:
        """Filvaljare for FFmpeg."""
        ft   = [("FFmpeg", "ffmpeg.exe" if os.name == "nt" else "*"),
                ("Alla", "*.*")]
        path = filedialog.askopenfilename(title="Valj FFmpeg", filetypes=ft)
        if path:
            self.ffmpeg_path_var.set(path)

    def browse_ffprobe(self) -> None:
        """Filvaljare for FFprobe."""
        ft   = [("FFprobe", "ffprobe.exe" if os.name == "nt" else "*"),
                ("Alla", "*.*")]
        path = filedialog.askopenfilename(title="Valj FFprobe", filetypes=ft)
        if path:
            self.ffprobe_path_var.set(path)

    def auto_find_ffmpeg(self) -> None:
        """Sok FFmpeg automatiskt."""
        self.settings["ffmpeg_path"]  = ""
        self.settings["ffprobe_path"] = ""
        self.ffmpeg_path  = self.find_ffmpeg()
        self.ffprobe_path = self.find_ffprobe()

        if self.ffmpeg_path:
            self.ffmpeg_path_var.set(self.ffmpeg_path)
            self.ffmpeg_available = True
            self.ffmpeg_status.config(
                text="FFmpeg hittad", fg=self.COLOR_SUCCESS
            )
            self.queue_log(
                "FFmpeg hittad: %s" % self.ffmpeg_path, "success"
            )
            if self.ffprobe_path:
                self.ffprobe_path_var.set(self.ffprobe_path)

            self.hardware_encoders = self.detect_hardware_encoders()
            hw_text = (
                " | HW: %s" % ", ".join(self.hardware_encoders[:3])
                if self.hardware_encoders
                else " | Ingen hardvaruacceleration"
            )
            if hasattr(self, "hw_label"):
                self.hw_label.config(text=hw_text)
        else:
            self.ffmpeg_available = False
            self.ffmpeg_status.config(
                text="FFmpeg hittades inte", fg=self.COLOR_ERROR
            )
            self.queue_log("FFmpeg hittades inte", "error")

    def test_ffmpeg_connection(self) -> None:
        """Testa konfigurerad FFmpeg."""
        path = self.ffmpeg_path_var.get()
        if not path:
            messagebox.showwarning(
                "Varning", "Ingen FFmpeg-sokvag angiven."
            )
            return
        if self.test_ffmpeg(path):
            self.ffmpeg_path      = path
            self.ffmpeg_available = True
            self.ffmpeg_status.config(
                text="FFmpeg fungerar", fg=self.COLOR_SUCCESS
            )
            try:
                r = subprocess.run(
                    [path, "-version"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=self._no_window_flag(),
                )
                ver = r.stdout.split("\n")[0] if r.stdout else "Okand"
                messagebox.showinfo(
                    "FFmpeg OK", "FFmpeg fungerar!\n\n%s" % ver
                )
            except Exception:
                messagebox.showinfo("FFmpeg OK", "FFmpeg fungerar!")
        else:
            self.ffmpeg_available = False
            self.ffmpeg_status.config(
                text="FFmpeg svarar inte", fg=self.COLOR_ERROR
            )
            messagebox.showerror("Fel", "FFmpeg svarar inte korrekt.")

    def download_ffmpeg(self) -> None:
        """Oppna FFmpeg-nedladdningssida."""
        urls = {
            "nt":     "https://www.gyan.dev/ffmpeg/builds/",
            "darwin": "https://evermeet.cx/ffmpeg/",
        }
        webbrowser.open(
            urls.get(os.name, "https://ffmpeg.org/download.html")
        )
        messagebox.showinfo(
            "Ladda ner FFmpeg",
            "Webbsida oppnad.\n\n"
            "Windows: Ladda ner 'ffmpeg-release-essentials.zip'\n"
            "macOS:   brew install ffmpeg\n"
            "Linux:   sudo apt install ffmpeg"
        )

    def log_action(self, message: str) -> None:
        """Extern loggning - tradsaker via queue_log()."""
        self.queue_log(message)

    def cleanup(self) -> None:
        """Stada upp vid avslutning (anropas fran app.quit_app())."""
        self.is_active        = False
        self.cancel_requested = True
        with self.process_lock:
            if self.current_process:
                try:
                    self.current_process.terminate()
                    time.sleep(0.5)
                    if self.current_process.poll() is None:
                        self.current_process.kill()
                except Exception:
                    pass
        self._unbind_mousewheel()

    def log(self, level: str, message: str) -> None:
        """
        Logga via advanced_logger + queue_log.
        Ingen print().
        """
        try:
            logger = self.app.context.get("_logger")
            if logger and hasattr(logger, "log"):
                logger.log(level, message)
        except Exception:
            pass
        self.queue_log(message)

    def log_error(self, message: str, exc: Exception = None) -> None:
        """Logga ett fel med valfritt undantag."""
        full = "%s: %s" % (message, exc) if exc else message
        self.log("FEL", full)

    def load_config(self, filename: str, default=None):
        """
        Ladda JSON-fil fran config/-mappen (A10).

        Anvander helpers.get_config_path() om tillgangligt,
        annars projektrotens config/.
        """
        try:
            if _HAS_HELPERS:
                cfg = get_config_path() / filename
            else:
                cfg = app_paths.config_dir() / filename
            if cfg.exists():
                return json.loads(cfg.read_text(encoding="utf-8"))
        except Exception as e:
            self.queue_log(
                "load_config(%s): %s" % (filename, e), "warning"
            )
        return default if default is not None else {}

    def save_config(self, filename: str, data: dict) -> None:
        """
        Spara JSON-fil till config/-mappen (A9 + A10).

        Monster: mkstemp -> fdopen -> flush -> fsync -> os.replace.
        Anvander helpers.get_config_path() om tillgangligt.
        """
        tmp_path = None
        try:
            if _HAS_HELPERS:
                config_dir = get_config_path()
            else:
                config_dir = app_paths.config_dir()
            config_dir.mkdir(parents=True, exist_ok=True)

            cfg = config_dir / filename
            fd, tmp_str = tempfile.mkstemp(
                dir=config_dir,
                prefix=".%s_" % cfg.stem,
                suffix=".tmp",
            )
            tmp_path = Path(tmp_str)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())   # A9

            os.replace(tmp_path, cfg)
        except Exception as e:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            self.queue_log(
                "save_config(%s): %s" % (filename, e), "error"
            )
