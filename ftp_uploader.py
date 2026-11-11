#!/usr/bin/env python3
# ============================================================
# Plugin: FTP-uppladdning
# ============================================================
# FIL:       plugins/ftp_uploader.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/ftp_uploader.py)
# Syfte:     Ladda upp galleri-filer till FTP-server
# PLUGIN_NAME: "FTP-uppladdning"
# PRIORITY:  35
# VERSION:   1.2.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v1.1.0 → v1.2.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings i logganrop – ALL %-formatering
#             (lazy %s; även progress_callback-strängar och
#             STOR-kommandot konverterade)
#   [B3]      AUTHOR + COPYRIGHT (dynamiskt år) + PLATS i header
#   [B1]      Ingen print() – all loggning via log-callback
#             (verifierat, behålls)
#
# BEVARAT FRÅN v1.1.0:
#   Docstrings på alla metoder
#   context['ftp_enabled'] kontrolleras FÖRST
#   Tydligare felhantering per FTP-feltyp
#   ensure_remote_dir: robustare (återgår till root vid fel)
#   Uppladdning: progress_callback stöd
#   cancel_check stöd (avbryt mitt i uppladdning)
#   Stöd för context['output_path'] som Path eller str
#   Stöd för context['files_to_upload'] = [] → skanna output_path
#   upload_result: fler fält (total_kb, elapsed_s)
#   Tydligare loggformat
#
# METODER I FTPUploader:
#   execute(context, log)      – Pipeline-ingång
#   _get_ftp_settings(ctx)     – Hämta och validera FTP-inställningar
#   _get_files(ctx, output)    – Hämta fillista (eller skanna mapp)
#   _upload_all(ftp, files,    – Ladda upp alla filer
#     output, remote, log, cb, cancel)
#   _upload_file(ftp, local,   – Ladda upp en fil
#     remote_path, log)
#   ensure_remote_dir(ftp, p)  – Skapa mappar rekursivt
#
# CONTEXT SOM LÄSES:
#   'ftp_settings'      dict  – server, user, password, path, port
#   'ftp_enabled'       bool  – om False: hoppar över
#   'output_path'       str|Path – lokal output-mapp
#   'files_to_upload'   [str] – relativa sökvägar ([] = skanna mapp)
#   'progress_callback' funktion(value, msg)
#   'cancel_check'      funktion() -> bool
#
# CONTEXT SOM SÄTTS:
#   'upload_result'     dict  – success, uploaded, failed,
#                               host, path, total_kb, elapsed_s
#
# IMPORTER:
#   ftplib
#   pathlib.Path
#   time
#   .base_plugin: BasePlugin
# ============================================================

import ftplib
from pathlib import Path
import time
from datetime import datetime
from .base_plugin import BasePlugin


class FTPUploader(BasePlugin):
    """
    Plugin för FTP-uppladdning.

    Laddar upp alla filer i context['files_to_upload']
    (eller hela output_path om listan är tom) till
    en konfigurerad FTP-server.

    Stöder:
    - progress_callback(value, msg) för UI-uppdatering
    - cancel_check() för att avbryta mitt i uppladdning
    - Rekursiv mappstruktur på servern
    - Graceful fallback om ftp_enabled=False
    """

    PLUGIN_NAME = "FTP-uppladdning"
    PRIORITY    = 35
    VERSION     = "1.2.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # ==========================================================================
    # PIPELINE-INGÅNG
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """
        Kör FTP-uppladdning.

        Steg:
          1. Kontrollera ftp_enabled
          2. Hämta och validera FTP-inställningar
          3. Hämta fillista
          4. Anslut och ladda upp
          5. Sätt context['upload_result']

        Returnerar context (alltid).
        """
        tray_status = context.get('_tray_status')
        # ── 1. Kontrollera ftp_enabled ────────────────────────
        if not context.get("ftp_enabled", False):
            if log:
                log("  [HOPPAR] FTP-uppladdning ej aktiverad")
            context["upload_result"] = {
                "success": False,
                "reason":  "FTP ej aktiverat",
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        # ── 2. FTP-inställningar ──────────────────────────────
        ftp_cfg, error = self._get_ftp_settings(context)
        if error:
            if log:
                log("  [HOPPAR] %s" % error)
            context["upload_result"] = {
                "success": False,
                "reason":  error,
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        host     = ftp_cfg["host"]
        user     = ftp_cfg["user"]
        password = ftp_cfg["password"]
        port     = ftp_cfg["port"]
        remote   = ftp_cfg["remote"]

        # ── 3. Output-mapp ────────────────────────────────────
        output_raw = context.get("output_path")
        if not output_raw:
            if log:
                log("  [HOPPAR] Ingen output_path i context")
            context["upload_result"] = {
                "success": False,
                "reason":  "Ingen output-mapp",
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context
        output_path = Path(output_raw)

        # ── 4. Fillista ───────────────────────────────────────
        files = self._get_files(context, output_path)
        if not files:
            if log:
                log("  [HOPPAR] Inga filer att ladda upp")
            context["upload_result"] = {
                "success": False,
                "reason":  "Ingen filer",
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        # ── 5. Hjälpfunktioner från context ───────────────────
        progress_cb  = context.get("progress_callback")
        cancel_check = context.get("cancel_check")

        if log:
            log("  Ansluter till %s:%s..." % (host, port))
            log("  Fjärrsökväg: %s" % (remote or "/"))
            log("  Filer: %s" % len(files))

        # ── 6. Anslut och ladda upp ───────────────────────────
        uploaded  = []
        failed    = []
        start     = time.time()

        try:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=30)
            ftp.login(user, password)

            if log:
                log("  ✓ Ansluten till %s" % host)

            if remote:
                self.ensure_remote_dir(ftp, remote)
                try:
                    ftp.cwd(remote)
                except Exception as e:
                    if log:
                        log("  [VARNING] Kunde inte byta till %s: %s" % (remote, e))

            uploaded, failed = self._upload_all(
                ftp, files, output_path, remote,
                log, progress_cb, cancel_check, tray_status
            )

            try:
                ftp.quit()
            except Exception:
                try:
                    ftp.close()
                except Exception:
                    pass

        except ftplib.error_perm as e:
            if log:
                log("  ✗ FTP-behörighetsfel: %s" % e)
            context["upload_result"] = {
                "success":  False,
                "reason":   str(e),
                "uploaded": uploaded,
                "failed":   failed,
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        except ftplib.error_temp as e:
            if log:
                log("  ✗ FTP-tillfälligt fel: %s" % e)
            context["upload_result"] = {
                "success":  False,
                "reason":   str(e),
                "uploaded": uploaded,
                "failed":   failed,
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        except ConnectionRefusedError:
            msg = "Anslutning nekad till %s:%s" % (host, port)
            if log:
                log("  ✗ %s" % msg)
            context["upload_result"] = {
                "success":  False,
                "reason":   msg,
                "uploaded": uploaded,
                "failed":   failed,
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        except TimeoutError:
            msg = "Timeout vid anslutning till %s" % host
            if log:
                log("  ✗ %s" % msg)
            context["upload_result"] = {
                "success":  False,
                "reason":   msg,
                "uploaded": uploaded,
                "failed":   failed,
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        except Exception as e:
            if log:
                log("  ✗ FTP-fel: %s" % e)
            context["upload_result"] = {
                "success":  False,
                "reason":   str(e),
                "uploaded": uploaded,
                "failed":   failed,
            }
            if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
                tray_status.issue()
            return context

        # ── 7. Resultat ───────────────────────────────────────
        elapsed  = time.time() - start
        total_kb = sum(f.get("size_kb", 0) for f in uploaded)
        total    = len(files)
        success  = len(failed) == 0

        context["upload_result"] = {
            "success":   success,
            "uploaded":  uploaded,
            "failed":    failed,
            "host":      host,
            "path":      remote,
            "total_kb":  total_kb,
            "elapsed_s": elapsed,
        }

        if log:
            log(
                "  ✓ %s/%s filer uppladdade till %s  (%.0f KB, %.1fs)"
                % (len(uploaded), total, host, total_kb, elapsed)
            )
            if failed:
                log("  ⚠ %s fel" % len(failed))

        if progress_cb:
            progress_cb(
                100,
                "Klart – %s/%s filer uppladdade"
                % (len(uploaded), total)
            )

        if tray_status is not None and context.get('ftp_enabled') and context.get('upload_result', {}).get('success') is False:
            tray_status.issue()
        return context

    # ==========================================================================
    # HJÄLPMETODER
    # ==========================================================================

    def _get_ftp_settings(self, context: dict) -> tuple:
        """
        Hämta och validera FTP-inställningar från context.

        Söker i context['ftp_settings'] och
        self.config['ftp'] (fallback).

        Returnerar:
            (dict, None)     om OK
            (None, str)      vid valideringsfel
        """
        ftp_settings = context.get("ftp_settings", {})
        if not ftp_settings:
            ftp_settings = getattr(self, "config", {}).get("ftp", {})

        if not ftp_settings:
            return None, "Ingen FTP-konfiguration"

        host = (
            ftp_settings.get("server")
            or ftp_settings.get("host", "")
        )
        if not host:
            return None, "FTP-server ej angiven"

        return {
            "host":     host,
            "user":     (
                ftp_settings.get("user")
                or ftp_settings.get("username", "")
            ),
            "password": ftp_settings.get("password", ""),
            "port":     int(ftp_settings.get("port", 21)),
            "remote":   (
                ftp_settings.get("path")
                or ftp_settings.get("remote_path", "")
            ),
        }, None

    def _get_files(self, context: dict, output_path: Path) -> list:
        """
        Hämta fillista.

        Om context['files_to_upload'] är tom:
          Skanna output_path rekursivt och returnera
          alla filer som relativa sökvägar.

        Returnerar [str] med relativa sökvägar.
        """
        files = context.get("files_to_upload", [])
        if files:
            return files

        # Skanna output_path
        if not output_path.exists():
            return []

        return [
            str(f.relative_to(output_path))
            for f in output_path.rglob("*")
            if f.is_file()
        ]

    def _upload_all(
        self,
        ftp: ftplib.FTP,
        files: list,
        output_path: Path,
        remote_base: str,
        log,
        progress_cb,
        cancel_check,
        tray_status=None,
    ) -> tuple:
        """
        Ladda upp alla filer.

        Skapar remote-mappar rekursivt vid behov.
        Stöder progress_callback och cancel_check.

        Returnerar:
            ([uploaded], [failed])
        """
        uploaded = []
        failed   = []
        total    = len(files)
        if tray_status is not None:
            tray_status.stage('Laddar upp')
            tray_status.progress(0, total)

        for i, file_rel in enumerate(files):

            # Avbryt om cancel_check returnerar True
            if cancel_check and cancel_check():
                if tray_status is not None:
                    tray_status.cancelled()
                if log:
                    log("  [AVBRUTEN] FTP-uppladdning avbruten")
                break

            local_file = output_path / file_rel
            if not local_file.exists():
                if tray_status is not None:
                    tray_status.issue()
                    tray_status.progress(i + 1, total)
                if log:
                    log("  [VARNING] Lokal fil saknas: %s" % file_rel)
                failed.append({
                    "file":   file_rel,
                    "reason": "Lokal fil saknas",
                })
                continue

            # Bygg remote-sökväg
            remote_file = str(file_rel).replace("\\", "/")
            remote_dir  = "/".join(remote_file.split("/")[:-1])
            if remote_dir:
                full_remote_dir = (
                    "%s/%s" % (remote_base, remote_dir)
                    if remote_base else remote_dir
                )
                self.ensure_remote_dir(ftp, full_remote_dir)

            remote_full = (
                "%s/%s" % (remote_base, remote_file)
                if remote_base else remote_file
            )

            size_kb = local_file.stat().st_size / 1024

            success, error = self._upload_file(
                ftp, local_file, remote_full, log
            )

            if success:
                uploaded.append({
                    "file":    file_rel,
                    "remote":  remote_full,
                    "size_kb": size_kb,
                })
                # Logga var 5:e fil (+ första och sista)
                if (
                    log
                    and (i == 0 or (i + 1) % 5 == 0 or i == total - 1)
                ):
                    log(
                        "  [%s/%s] ✓ %s (%.0f KB)"
                        % (i + 1, total, file_rel, size_kb)
                    )
            else:
                failed.append({
                    "file":   file_rel,
                    "reason": error,
                })
                if log:
                    log(
                        "  [%s/%s] ✗ %s: %s"
                        % (i + 1, total, file_rel, error)
                    )

            if tray_status is not None:
                tray_status.progress(i + 1, total)
                if failed:
                    tray_status.issue()
            # Progress-callback
            if progress_cb:
                pct = int(((i + 1) / total) * 100)
                progress_cb(
                    pct,
                    "%s/%s – %s" % (i + 1, total, local_file.name)
                )

        return uploaded, failed

    def _upload_file(
        self,
        ftp: ftplib.FTP,
        local_path: Path,
        remote_path: str,
        log,
    ) -> tuple:
        """
        Ladda upp en enda fil via FTP.

        Returnerar:
            (True, None)     vid framgång
            (False, str)     vid fel
        """
        try:
            with open(local_path, "rb") as f:
                ftp.storbinary("STOR %s" % remote_path, f)
            return True, None
        except ftplib.error_perm as e:
            return False, "Behörighetsfel: %s" % e
        except ftplib.error_temp as e:
            return False, "Tillfälligt fel: %s" % e
        except Exception as e:
            return False, str(e)

    def ensure_remote_dir(self, ftp: ftplib.FTP, path: str) -> None:
        """
        Skapa FTP-mappar rekursivt om de inte finns.

        Går igenom sökvägen steg för steg.
        Ignorerar fel (mappen finns förmodligen redan).

        Återgår till root om ett steg misslyckas katastrofalt.
        """
        if not path:
            return

        dirs    = [d for d in path.split("/") if d]
        current = ""

        for dir_name in dirs:
            current += "/" + dir_name
            try:
                ftp.cwd(current)
            except ftplib.error_perm:
                try:
                    ftp.mkd(current)
                    ftp.cwd(current)
                except ftplib.error_perm:
                    # Mappen finns förmodligen redan eller
                    # saknar vi behörighet – fortsätt ändå
                    pass
                except Exception:
                    # Oväntad situation – hoppa över detta steg
                    pass
            except Exception:
                # Fallback: återgå till root och fortsätt
                try:
                    ftp.cwd("/")
                except Exception:
                    pass
