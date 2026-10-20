#!/usr/bin/env python3
# ============================================================
# Hjalpmodul (mixin) for plugins/gallery_view.py
# ============================================================
# FIL:       plugins/gallery_view_helpers.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/gallery_view_helpers.py)
# Klass:     GalleryViewMixin
# VERSION:   2.6.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
# Syfte:     Innehaller GalleryView:s interaktions-metoder for att
#            halla huvudfilen gallery_view.py under 1800 rader.
#            GalleryView arver fran denna mixin:
#                class GalleryView(GalleryViewMixin, BasePlugin)
#
#            OBS: Denna fil definierar INGEN PLUGIN_NAME och ignoreras
#            darfor av plugin-loadern (laddas bara som import).
#
# ÄNDRINGAR v2.5.0 → v2.6.0 (snabbhet/design, icke-brytande):
#   [R1] _cancel_pending_refresh() samlar efter-cancel (debounce/clear).
#   [R2] _build_photoimage()+_load_thumbnails() flyttade hit (hallen
#        gallery_view.py under 1800 rader). R3) VERSION-synk med main.
#
# ÄNDRINGAR v2.4.0 → v2.5.0 (snabbhet/minne/loggning, icke-brytande):
#   [Q1]      Sok-/filter-refresh debounce-as: refresh_gallery() (som
#             ritar om alla thumbnails) kordes vid VARJE tangenttryck.
#             Nu debounce i 160 ms -> en omritning per skrivpaus
#             (stor CPU-vinst vid stora mappar).
#   [Q2]      Deterministik PIL-stangning: save_rotations() och
#             _update_preview() stanger alla oppnade PIL-bilder i
#             finally (aven de som returneras av exif_transpose/rotate)
#             -> ingen oandlig minnesackumulering vid rotation/preview.
#   [Q3]      VERSION + AUTHOR + COPYRIGHT (versionen synkas med
#             gallery_view.py). Inga public-API/signaturandringar.
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings – ALL %-formatering (statusmeddelanden,
#             dialoger, raknare, preview-labels, logganrop)
#   [B1]      Inga hardkodade hex-farger i widgets – nya konstanter
#             COLOR_PREVIEW_BG/BAR/FG/INFO/ERR, COLOR_SAVED,
#             COLOR_UNSAVED; ovriga via self.COLOR_* fran GalleryView
#             (COLOR_SEL, COLOR_PINK, COLOR_BG_ITEM, COLOR_SEL_B,
#             COLOR_ROT, COLOR_FG, COLOR_MUTED)
#   [B3]      VERSION + AUTHOR + COPYRIGHT (dynamiskt år) + PLATS
#             (versionen synkas med gallery_view.py)
#
# INNEHALLER METODER FOR:
#   - Thumbnail-bygge (_build_photoimage + _load_thumbnails, fran
#     v2.6.0 flyttade hit for att halla gallery_view.py under 1800 rader)
#   - Mus-events + drag & drop
#   - Markering (select/clear/invert/toggle)
#   - Flytta markerade (upp/ner/forst/sist + drop)
#   - Sortering (A-O / O-A / datum / storlek / slump / vand)
#   - Rotation (vanster/hoger/180 + spara/aterstall)
#   - Undo/Redo
#   - Spara/ladda sorteringsordning (.gallery_sort.json)
#   - Ta bort (flytta till Removed/)
#   - Forhandsgranskningsfonster
#   - Kontextmeny
#   - Tangentbordsgenvagar + navigation
#   - Sok / filter
#
# BEROENDEN (forvantas finnas pa self via GalleryView):
#   self.app, self.is_active, self.image_files, self.filtered_files,
#   self.selected_indices, self.last_clicked_index, self.current_folder,
#   self.item_widgets, self.cols, self.image_rotations, self.thumbnails,
#   self.settings, self.canvas, self.inner_frame, samt hjalpmetoderna
#   self.log, self.log_error, self.widget_exists, self.safe_widget_config,
#   self.safe_after, self._btn, self._darken, self.refresh_gallery,
#   self._load_thumbnails, self._update_rotated_thumbnail,
#   self._show_instructions, self._update_context, self._set_status,
#   self.generate_html, self.show_in_folder, self._open_external,
#   self._copy_filename, self.show_settings_dialog
#
# IMPORTER:
#   tkinter as tk, messagebox
#   pathlib.Path
#   json, os, shutil, time, subprocess, sys, random
#   datetime
#   PIL: Image, ImageTk, ImageOps
# ============================================================

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import json
import os
import shutil
import time
import subprocess
import sys
import random
from datetime import datetime
from PIL import Image, ImageTk, ImageOps


class GalleryViewMixin:
    """Interaktions-metoder for GalleryView (se filhuvud)."""

    VERSION   = "2.6.0"
    AUTHOR    = "Rickard Längkvist"
    COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # -- Fargkonstanter for preview/dialoger (B1) --------------
    COLOR_PREVIEW_BG   = "#0a0a0a"
    COLOR_PREVIEW_BAR  = "#1a1a1a"
    COLOR_PREVIEW_FG   = "#888888"
    COLOR_PREVIEW_INFO = "#666666"
    COLOR_PREVIEW_ERR  = "#ef4444"
    COLOR_SAVED        = "#22c55e"
    COLOR_UNSAVED      = "#f59e0b"

    def _cancel_pending_refresh(self) -> None:
        """Avbryt en schemalagd debounce-refresh (v2.6.0)."""
        aid = getattr(self, "_refresh_after_id", None)
        if aid is not None:
            try:
                self.app.after_cancel(aid)
            except Exception:
                pass
            self._refresh_after_id = None

    def _build_photoimage(
        self, img_path: Path, size: int, rotation: int = 0
    ) -> "ImageTk.PhotoImage":
        """
        Bygg en PhotoImage fran en bildfil med deterministisk
        stangning av alla temporara PIL-bilder (v2.6.0).

        Undviker att halla oppna filhandtag/fullstora PIL-bilder
        kvar i minnet efter att thumbnails skapats - viktigt vid
        manga/stora bilder. exif_transpose()/rotate() returnerar
        NYA bilder; alla stangs i finally.
        """
        opened = []
        try:
            img = Image.open(img_path)
            opened.append(img)
            try:
                tx = ImageOps.exif_transpose(img)
            except Exception:
                tx = None
            if tx is not None:
                opened.append(tx)
                img = tx
            if rotation:
                img = img.rotate(-rotation, expand=True)
                opened.append(img)
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            # PhotoImage kopierar pixeldata -> PIL-bild kan stangas
            # direkt efter att PhotoImage byggts.
            return ImageTk.PhotoImage(img)
        finally:
            for im in opened:
                try:
                    im.close()
                except Exception:
                    pass

    def _load_thumbnails(self) -> None:
        """Ladda thumbnails med progress-bar."""
        if not self.is_active:
            return
        self.thumbnails.clear()
        size  = self.settings.get("thumbnail_size", 120)
        total = len(self.image_files)

        self.safe_widget_config(
            self._loading_label, text="Laddar thumbnails..."
        )
        if self.widget_exists(self._loading_bar):
            self._loading_bar.pack(side=tk.RIGHT, padx=4)
            self._loading_bar["maximum"] = total
            self._loading_bar["value"]   = 0

        failures = 0
        for i, img_path in enumerate(self.image_files):
            if not self.is_active:
                break
            try:
                rot   = self.image_rotations.get(img_path, 0)
                photo = self._build_photoimage(img_path, size, rot)
                if photo is None:
                    raise IOError("Empty photo")
                self.thumbnails[img_path] = photo
            except Exception as e:
                failures += 1
                self.log(
                    "DEBUG",
                    "Thumbnail %s: %s" % (img_path.name, e)
                )

            if i % 10 == 0:
                if self.widget_exists(self._loading_bar):
                    self._loading_bar["value"] = i
                self.safe_widget_config(
                    self._loading_label,
                    text="Laddar %d/%d..." % (i, total),
                )
                try:
                    self.app.update_idletasks()
                except Exception:
                    pass

        if self.widget_exists(self._loading_bar):
            self._loading_bar.pack_forget()
        self.safe_widget_config(self._loading_label, text="")
        if failures:
            self.log(
                "VARNING",
                "Kunde inte ladda %d av %d thumbnails"
                % (failures, total)
            )

    def _debounced_refresh(self, status_text: str = None) -> None:
        """
        Uppdatera galleriet debounce-at (Q1).

        refresh_gallery() ritar om ALLA thumbnails och är dyr. Den körs
        därför inte vid varje tangenttryck/ändring utan en gång per
        paus (~160 ms). Schema avbryts/störs av nästa anrop.
        """
        self._cancel_pending_refresh()
        self._refresh_after_id = self.app.after(
            160,
            lambda: self._flush_debounced_refresh(status_text),
        )

    def _flush_debounced_refresh(self, status_text: str) -> None:
        """Körs när debounce-tiden gått ut."""
        self._refresh_after_id = None
        if not self.is_active:
            return
        self.refresh_gallery()
        if status_text is not None:
            self._set_status(status_text)

    def _on_search_changed(self, *args) -> None:
        term = self._search_var.get().lower().strip()
        if not term:
            self.filtered_files = self.image_files.copy()
        else:
            self.filtered_files = [
                f for f in self.image_files
                if term in f.name.lower()
            ]
        self._debounced_refresh(
            "%d av %d bilder"
            % (len(self.filtered_files), len(self.image_files))
        )

    def clear_search(self) -> None:
        self._search_var.set("")
        self._filter_var.set("Alla")
        self.filtered_files = self.image_files.copy()
        # Rensa ev. schemalagd refresh innan den omedelbara körs
        self._cancel_pending_refresh()
        self.refresh_gallery()

    def _on_filter_changed(self, event=None) -> None:
        ft = self._filter_var.get()
        ext_map = {
            "JPEG":  [".jpg", ".jpeg"],
            "PNG":   [".png"],
            "GIF":   [".gif"],
            "WebP":  [".webp"],
            "Andra": [".bmp", ".tiff", ".tif"],
        }
        if ft == "Alla":
            self.filtered_files = self.image_files.copy()
        else:
            exts = ext_map.get(ft, [])
            self.filtered_files = [
                f for f in self.image_files
                if f.suffix.lower() in exts
            ]
        self._debounced_refresh(
            "Filter: %s - %d bilder" % (ft, len(self.filtered_files))
        )

    def _on_mouse_down(self, event, index: int) -> None:
        self.drag_start_pos   = (event.x_root, event.y_root)
        self.drag_start_index = index
        self.is_dragging      = False
        self._pending_toggle  = None

        ctrl  = bool(event.state & 0x4)
        shift = bool(event.state & 0x1)

        if shift and self.last_clicked_index is not None:
            s, e = sorted([self.last_clicked_index, index])
            if not ctrl:
                self.selected_indices.clear()
            for i in range(s, e + 1):
                self.selected_indices.add(i)
            self._update_selection_visual()
        elif ctrl:
            if index in self.selected_indices:
                self._pending_toggle = index
            else:
                self.selected_indices.add(index)
                self.last_clicked_index = index
                self._update_selection_visual()
        else:
            if index in self.selected_indices and \
               len(self.selected_indices) > 1:
                self._pending_toggle = "single"
            else:
                self.selected_indices   = {index}
                self.last_clicked_index = index
                self._update_selection_visual()

    def _on_mouse_move(self, event, index: int) -> None:
        if not self.drag_start_pos:
            return
        dx = abs(event.x_root - self.drag_start_pos[0])
        dy = abs(event.y_root - self.drag_start_pos[1])
        if dx < self.drag_threshold and dy < self.drag_threshold:
            return

        self._pending_toggle = None
        if not self.is_dragging:
            self.is_dragging = True
            try:
                self.canvas.config(cursor="fleur")
            except Exception:
                pass
            if self.widget_exists(self._drag_info_frame):
                self._drag_info_frame.pack(
                    fill=tk.X, before=self.canvas.master
                )

        widget = event.widget.winfo_containing(
            event.x_root, event.y_root
        )
        tgt = self._get_widget_index(widget)
        if tgt is not None:
            orig = self.item_widgets.get(tgt, {}).get(
                "original_index", tgt
            )
            if orig not in self.selected_indices:
                self.drop_target_index = orig
                self._show_drop_indicator(tgt)
                n = len(self.selected_indices)
                self.safe_widget_config(
                    self._drag_info_label,
                    text=(
                        "Flytta %d bild%s till position #%d"
                        % (n, "er" if n > 1 else "", orig + 1)
                    ),
                )
            else:
                self._hide_drop_indicator()
        else:
            self._hide_drop_indicator()

    def _on_mouse_up(self, event, index: int) -> None:
        try:
            self.canvas.config(cursor="")
        except Exception:
            pass
        if self.widget_exists(self._drag_info_frame):
            self._drag_info_frame.pack_forget()

        if self.is_dragging and self.drop_target_index is not None:
            self._hide_drop_indicator()
            self._save_to_history()
            self._move_images_to(self.drop_target_index)
        elif not self.is_dragging:
            ctrl = bool(event.state & 0x4)
            if self._pending_toggle == index and ctrl:
                self.selected_indices.discard(index)
                self.last_clicked_index = (
                    max(self.selected_indices)
                    if self.selected_indices else None
                )
                self._update_selection_visual()
            elif self._pending_toggle == "single":
                self.selected_indices   = {index}
                self.last_clicked_index = index
                self._update_selection_visual()

        self.is_dragging       = False
        self.drag_start_pos    = None
        self.drop_target_index = None
        self._pending_toggle   = None

    def _on_right_click(self, event, index: int) -> None:
        if index not in self.selected_indices:
            self.selected_indices   = {index}
            self.last_clicked_index = index
            self._update_selection_visual()
        self._context_menu.tk_popup(event.x_root, event.y_root)

    def _get_widget_index(self, widget):
        """Hitta index for en widget i item_widgets."""
        for idx, ws in self.item_widgets.items():
            for w in ws.values():
                if w is widget or (
                    isinstance(w, tk.Widget)
                    and hasattr(widget, "master")
                    and widget.master is w
                ):
                    return idx
        return None

    def _show_drop_indicator(self, target_index: int) -> None:
        ws = self.item_widgets.get(target_index)
        if not ws:
            return
        w = ws["outer"]
        try:
            self._drop_indicator.place(
                x=w.winfo_x() - 2, y=w.winfo_y(),
                height=w.winfo_height(), width=4,
            )
        except Exception:
            pass

    def _hide_drop_indicator(self) -> None:
        try:
            self._drop_indicator.place_forget()
        except Exception:
            pass
        self.safe_widget_config(self._drag_info_label, text="")

    def _update_selection_visual(self) -> None:
        """Uppdatera visuell markering utan full refresh."""
        for idx, ws in self.item_widgets.items():
            orig = ws.get("original_index", idx)
            sel  = orig in self.selected_indices
            path = (
                self.image_files[orig]
                if orig < len(self.image_files) else None
            )
            rot    = path in self.image_rotations if path else False
            bg     = self.COLOR_SEL     if sel else self.COLOR_BG_ITEM
            border = self.COLOR_SEL_B   if sel else (
                self.COLOR_ROT if rot else self.COLOR_BG_ITEM
            )
            fg = self.COLOR_FG if sel else self.COLOR_MUTED
            try:
                ws["outer"].config(bg=border)
                ws["inner"].config(bg=bg)
                ws["info"].config(bg=bg)
                ws["check"].config(text="X" if sel else "", bg=bg)
                ws["num"].config(bg=bg, fg=fg)
                if ws.get("name"):
                    ws["name"].config(bg=bg, fg=fg)
            except tk.TclError:
                pass
        self._update_counters()

    def _update_counters(self) -> None:
        self.safe_widget_config(
            self.count_label, text=str(len(self.image_files))
        )
        self.safe_widget_config(
            self.selected_label,
            text="%d valda" % len(self.selected_indices)
        )

    def select_all(self, event) -> str:
        self.selected_indices = set(range(len(self.image_files)))
        self._update_selection_visual()
        self._set_status(
            "Markerade alla %d bilder" % len(self.image_files)
        )
        return "break"

    def clear_selection(self, event) -> str:
        self.selected_indices.clear()
        self.last_clicked_index = None
        self._update_selection_visual()
        return "break"

    def invert_selection(self) -> None:
        self.selected_indices = (
            set(range(len(self.image_files))) - self.selected_indices
        )
        self._update_selection_visual()

    def select_every_other(self) -> None:
        self.selected_indices = set(range(0, len(self.image_files), 2))
        self._update_selection_visual()

    def toggle_selection(self, event=None) -> str:
        if self.last_clicked_index is not None:
            i = self.last_clicked_index
            if i in self.selected_indices:
                self.selected_indices.discard(i)
            else:
                self.selected_indices.add(i)
            self._update_selection_visual()
        return "break"

    def _move_images_to(self, target: int) -> None:
        if not self.selected_indices:
            return
        sel    = sorted(self.selected_indices)
        images = [self.image_files[i] for i in sel]
        for i in reversed(sel):
            self.image_files.pop(i)
        before  = sum(1 for i in sel if i < target)
        new_pos = max(
            0, min(target - before, len(self.image_files))
        )
        for i, img in enumerate(images):
            self.image_files.insert(new_pos + i, img)
        self.selected_indices = set(
            range(new_pos, new_pos + len(images))
        )
        self.filtered_files = self.image_files.copy()
        self._mark_changed()
        self.refresh_gallery()
        n = len(images)
        self._set_status(
            "Flyttade %d bild%s" % (n, "er" if n > 1 else "")
        )

    def move_up(self) -> None:
        if not self.selected_indices or min(self.selected_indices) == 0:
            return
        self._save_to_history()
        for i in sorted(self.selected_indices):
            self.image_files[i], self.image_files[i - 1] = (
                self.image_files[i - 1], self.image_files[i]
            )
        self.selected_indices = {i - 1 for i in self.selected_indices}
        self.filtered_files   = self.image_files.copy()
        self._mark_changed()
        self.refresh_gallery()

    def move_down(self) -> None:
        if not self.selected_indices or \
           max(self.selected_indices) >= len(self.image_files) - 1:
            return
        self._save_to_history()
        for i in sorted(self.selected_indices, reverse=True):
            self.image_files[i], self.image_files[i + 1] = (
                self.image_files[i + 1], self.image_files[i]
            )
        self.selected_indices = {i + 1 for i in self.selected_indices}
        self.filtered_files   = self.image_files.copy()
        self._mark_changed()
        self.refresh_gallery()

    def move_to_top(self) -> None:
        if not self.selected_indices:
            return
        self._save_to_history()
        sel    = sorted(self.selected_indices)
        images = [self.image_files[i] for i in sel]
        for i in reversed(sel):
            self.image_files.pop(i)
        for i, img in enumerate(images):
            self.image_files.insert(i, img)
        self.selected_indices = set(range(len(images)))
        self.filtered_files   = self.image_files.copy()
        self._mark_changed()
        self.refresh_gallery()

    def move_to_bottom(self) -> None:
        if not self.selected_indices:
            return
        self._save_to_history()
        sel    = sorted(self.selected_indices)
        images = [self.image_files[i] for i in sel]
        for i in reversed(sel):
            self.image_files.pop(i)
        start = len(self.image_files)
        self.image_files.extend(images)
        self.selected_indices = set(range(start, len(self.image_files)))
        self.filtered_files   = self.image_files.copy()
        self._mark_changed()
        self.refresh_gallery()

    def sort_az(self)   -> None: self._sort(lambda x: x.name.lower(), "A-O")

    def sort_za(self)   -> None: self._sort(lambda x: x.name.lower(), "O-A", True)

    def sort_date(self) -> None: self._sort(lambda x: x.stat().st_mtime, "Datum")

    def sort_size(self) -> None: self._sort(lambda x: x.stat().st_size, "Storlek")

    def sort_random(self) -> None:
        self._save_to_history()
        random.shuffle(self.image_files)
        self.filtered_files = self.image_files.copy()
        self.selected_indices.clear()
        self._mark_changed()
        self.refresh_gallery()
        self._set_status("Slumpad ordning")

    def reverse_order(self) -> None:
        self._save_to_history()
        self.image_files.reverse()
        self.filtered_files = self.image_files.copy()
        self.selected_indices.clear()
        self._mark_changed()
        self.refresh_gallery()
        self._set_status("Vande ordning")

    def _sort(
        self, key, label: str, reverse: bool = False
    ) -> None:
        self._save_to_history()
        self.image_files.sort(key=key, reverse=reverse)
        self.filtered_files = self.image_files.copy()
        self.selected_indices.clear()
        self._mark_changed()
        self.refresh_gallery()
        self._set_status("Sorterat %s" % label)

    def rotate_left(self)  -> None: self._rotate_selected(-90)

    def rotate_right(self) -> None: self._rotate_selected(90)

    def rotate_180(self)   -> None: self._rotate_selected(180)

    def _rotate_selected(self, degrees: int) -> None:
        if not self.selected_indices:
            self._set_status("Ingen bild markerad for rotation")
            return
        for idx in self.selected_indices:
            if 0 <= idx < len(self.image_files):
                p   = self.image_files[idx]
                rot = (self.image_rotations.get(p, 0) + degrees) % 360
                if rot == 0:
                    self.image_rotations.pop(p, None)
                else:
                    self.image_rotations[p] = rot
                self._update_rotated_thumbnail(p, rot)
        self.refresh_gallery()
        self._mark_changed()

    def save_rotations(self) -> None:
        """Spara rotationer permanent till bildfilerna."""
        if not self.image_rotations:
            self._set_status("Inga rotationer att spara")
            return
        if not messagebox.askyesno(
            "Spara rotationer",
            "Spara rotationer for %d bilder PERMANENT till disk?"
            % len(self.image_rotations),
        ):
            return
        saved = errors = 0
        for path, rot in list(self.image_rotations.items()):
            if rot == 0:
                continue
            opened = None
            to_close = []
            try:
                opened = Image.open(path)
                to_close.append(opened)
                try:
                    opened = ImageOps.exif_transpose(opened)
                    if opened is not None:
                        to_close.append(opened)
                except Exception:
                    pass
                if opened is None:
                    opened = to_close[0]
                rotated = opened.rotate(-rot, expand=True)
                to_close.append(rotated)
                fmt = self.IMAGE_FORMATS.get(
                    path.suffix.lower(), "JPEG"
                )
                opts = (
                    {"quality": 95, "optimize": True}
                    if fmt == "JPEG" else {}
                )
                rotated.save(path, fmt, **opts)
                del self.image_rotations[path]
                saved += 1
            except Exception as e:
                self.log_error("Rotation-spara %s" % path.name, e)
                errors += 1
            finally:
                # Q2: stäng alla öppnade PIL-bilder deterministiskt
                for im in to_close:
                    try:
                        im.close()
                    except Exception:
                        pass
        self._load_thumbnails()
        self.refresh_gallery()
        msg = "Sparade %d rotationer" % saved
        if errors:
            msg += ", %d fel" % errors
        self._set_status(msg)

    def reset_selected_rotation(self) -> None:
        count = 0
        for idx in self.selected_indices:
            if 0 <= idx < len(self.image_files):
                p = self.image_files[idx]
                if p in self.image_rotations:
                    del self.image_rotations[p]
                    self._update_rotated_thumbnail(p, 0)
                    count += 1
        if count:
            self.refresh_gallery()
            self._mark_changed()
            self._set_status(
                "Aterstallde %d rotation(er)" % count
            )

    def _save_to_history(self) -> None:
        if not self.image_files:
            return
        state = [f.name for f in self.image_files]
        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]
        self.history.append(state)
        if len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)
        self.history_index = len(self.history) - 1

    def undo(self) -> None:
        if self.history_index <= 0:
            self._set_status("Inget att angra")
            return
        self.history_index -= 1
        self._restore_history()
        self._set_status("Angrade")

    def redo(self) -> None:
        if self.history_index >= len(self.history) - 1:
            self._set_status("Inget att gora om")
            return
        self.history_index += 1
        self._restore_history()
        self._set_status("Gjorde om")

    def _restore_history(self) -> None:
        if not self.current_folder or self.history_index < 0:
            return
        names = self.history[self.history_index]
        self.image_files = [
            self.current_folder / n
            for n in names
            if (self.current_folder / n).exists()
        ]
        self.filtered_files   = self.image_files.copy()
        self.selected_indices.clear()
        self._mark_changed()
        self.refresh_gallery()

    def _load_sort_order(self):
        if not self.current_folder:
            return None
        sort_file = self.current_folder / self.SORT_FILENAME
        if not sort_file.exists():
            return None
        try:
            data = json.loads(sort_file.read_text(encoding="utf-8"))
            if "rotations" in data:
                for name, rot in data["rotations"].items():
                    p = self.current_folder / name
                    if p.exists():
                        self.image_rotations[p] = rot
            return data.get("order", [])
        except Exception as e:
            self.log("DEBUG", "_load_sort_order: %s" % e)
            return None

    def save_sort_order(self) -> None:
        """Spara sorteringsordning (knapp + Ctrl+S)."""
        if not self.current_folder:
            return
        try:
            self._save_sort_silent()
            self.sort_changed = False
            self._set_status("Ordningen sparad")
            self.safe_widget_config(
                self.save_indicator,
                text="Sparad", fg=self.COLOR_SAVED
            )
            self.safe_after(
                2000,
                lambda: self.safe_widget_config(
                    self.save_indicator, text=""
                )
            )
        except Exception as e:
            self._set_status("Sparningsfel: %s" % e)

    def _save_sort_silent(self) -> None:
        """Spara utan UI-feedback. Atomisk skrivning."""
        if not self.current_folder or not self.image_files:
            return
        rotations = {
            p.name: rot
            for p, rot in self.image_rotations.items()
            if p.exists()
        }
        data = {
            "order":     [f.name for f in self.image_files],
            "rotations": rotations,
            "updated":   time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        sort_file = self.current_folder / self.SORT_FILENAME
        tmp       = sort_file.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            os.replace(tmp, sort_file)
        except Exception as e:
            self.log("DEBUG", "_save_sort_silent: %s" % e)

    def _mark_changed(self) -> None:
        self.sort_changed = True
        self.safe_widget_config(
            self.save_indicator, text="* Osparad", fg=self.COLOR_UNSAVED
        )
        self._update_context()

    def delete_selected(self, event=None) -> str:
        if not self.selected_indices or not self.current_folder:
            return "break"
        n = len(self.selected_indices)
        if self.settings.get("confirm_delete", True):
            if not messagebox.askyesno(
                "Ta bort",
                "Flytta %d bild%s till 'Removed'?"
                % (n, "er" if n > 1 else ""),
            ):
                return "break"
        self._save_to_history()
        removed = self.current_folder / "Removed"
        removed.mkdir(exist_ok=True)
        for i in sorted(self.selected_indices, reverse=True):
            p   = self.image_files[i]
            dst = removed / p.name
            c   = 1
            while dst.exists():
                dst = removed / ("%s_%d%s" % (p.stem, c, p.suffix))
                c  += 1
            try:
                shutil.move(str(p), str(dst))
                self.image_files.pop(i)
                self.thumbnails.pop(p, None)
                self.image_rotations.pop(p, None)
            except Exception as e:
                self.log_error("Ta bort %s" % p.name, e)
        self.selected_indices.clear()
        self.filtered_files = self.image_files.copy()
        self._mark_changed()
        self.refresh_gallery()
        self._set_status(
            "Tog bort %d bild%s" % (n, "er" if n > 1 else "")
        )
        return "break"

    def preview_selected(self) -> None:
        if self.selected_indices:
            self.preview_image_at_index(min(self.selected_indices))

    def preview_image_at_index(self, index: int) -> None:
        if 0 <= index < len(self.image_files):
            self._open_preview_window(index)

    def _open_preview_window(self, start: int) -> None:
        self._preview_index = start
        win = tk.Toplevel(self.app)
        win.title("Forhandsgranska")
        win.configure(bg=self.COLOR_PREVIEW_BG)
        win.geometry("1000x750")
        self._preview_win = win

        # Header
        hdr = tk.Frame(win, bg=self.COLOR_PREVIEW_BAR, height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        self._btn(hdr, "Foregaende",
                  lambda: self._preview_nav(-1),
                  bg=self.COLOR_SEL, side=tk.LEFT)
        for label, deg in [("V90", -90), ("H90", 90), ("180", 180)]:
            self._btn(hdr, label,
                      lambda d=deg: self._rotate_in_preview(d),
                      bg=self.COLOR_PINK, side=tk.LEFT)
        self._preview_counter = tk.Label(
            hdr, text="", bg=self.COLOR_PREVIEW_BAR, fg="white",
            font=("Segoe UI", 11, "bold"),
        )
        self._preview_counter.pack(side=tk.LEFT, expand=True)
        self._btn(hdr, "Nasta",
                  lambda: self._preview_nav(1),
                  bg=self.COLOR_SEL, side=tk.RIGHT)

        # Bild
        self._preview_img_lbl = tk.Label(
            win, bg=self.COLOR_PREVIEW_BG, cursor="hand2"
        )
        self._preview_img_lbl.pack(expand=True)
        self._preview_img_lbl.bind(
            "<Button-1>", lambda e: self._preview_nav(1)
        )
        self._preview_img_lbl.bind(
            "<Button-3>", lambda e: self._preview_nav(-1)
        )

        # Footer
        ftr = tk.Frame(win, bg=self.COLOR_PREVIEW_BAR, height=60)
        ftr.pack(fill=tk.X)
        ftr.pack_propagate(False)
        self._preview_fname = tk.Label(
            ftr, text="", bg=self.COLOR_PREVIEW_BAR,
            fg=self.COLOR_PREVIEW_FG,
            font=("Segoe UI", 9),
        )
        self._preview_fname.pack(pady=4)
        self._preview_info = tk.Label(
            ftr, text="", bg=self.COLOR_PREVIEW_BAR,
            fg=self.COLOR_PREVIEW_INFO,
            font=("Segoe UI", 8),
        )
        self._preview_info.pack()
        self._preview_rot_lbl = tk.Label(
            ftr, text="", bg=self.COLOR_PREVIEW_BAR,
            fg=self.COLOR_PINK,
            font=("Segoe UI", 8, "bold"),
        )
        self._preview_rot_lbl.pack()

        for key, fn in [
            ("<Left>",    lambda e: self._preview_nav(-1)),
            ("<Right>",   lambda e: self._preview_nav(1)),
            ("<space>",   lambda e: self._preview_nav(1)),
            ("<Escape>",  lambda e: win.destroy()),
            ("<Delete>",  lambda e: self._delete_in_preview()),
            ("l",         lambda e: self._rotate_in_preview(-90)),
            ("r",         lambda e: self._rotate_in_preview(90)),
            ("u",         lambda e: self._rotate_in_preview(180)),
        ]:
            win.bind(key, fn)

        self._update_preview()
        win.focus_set()

    def _update_preview(self) -> None:
        if not hasattr(self, "_preview_win") or \
           not self.widget_exists(self._preview_win):
            return
        path = self.image_files[self._preview_index]
        opened = None
        to_close = []
        try:
            img = Image.open(path)
            opened = img
            to_close.append(img)
            orig_size = img.size
            try:
                img = ImageOps.exif_transpose(img)
                if img is not None:
                    to_close.append(img)
            except Exception:
                pass
            if img is None:
                img = opened
            rot = self.image_rotations.get(path, 0)
            if rot:
                img = img.rotate(-rot, expand=True)
                to_close.append(img)
            w = max(100, self._preview_win.winfo_width()  - 40)
            h = max(100, self._preview_win.winfo_height() - 140)
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._preview_img_lbl.config(image=photo, text="")
            self._preview_img_lbl.image = photo
            self._preview_counter.config(
                text="%d / %d"
                % (self._preview_index + 1, len(self.image_files))
            )
            self._preview_fname.config(text=path.name)
            kb  = path.stat().st_size / 1024
            if kb > 1024:
                sz = "%.1f MB" % (kb / 1024)
            else:
                sz = "%.0f KB" % kb
            self._preview_info.config(
                text="%dx%d - %s" % (orig_size[0], orig_size[1], sz)
            )
            if rot:
                self._preview_rot_lbl.config(
                    text="Roterad %d (ej sparad)" % rot
                )
            else:
                self._preview_rot_lbl.config(text="")
        except Exception as e:
            self._preview_img_lbl.config(
                text="Fel: %s" % e,
                fg=self.COLOR_PREVIEW_ERR, image=""
            )
        finally:
            # Q2: stäng alla öppnade PIL-bilder deterministiskt
            for im in to_close:
                try:
                    im.close()
                except Exception:
                    pass

    def _preview_nav(self, d: int) -> None:
        self._preview_index = (
            (self._preview_index + d) % len(self.image_files)
        )
        self._update_preview()

    def _rotate_in_preview(self, deg: int) -> None:
        p   = self.image_files[self._preview_index]
        rot = (self.image_rotations.get(p, 0) + deg) % 360
        if rot == 0:
            self.image_rotations.pop(p, None)
        else:
            self.image_rotations[p] = rot
        self._update_rotated_thumbnail(p, rot)
        self._update_preview()
        self._mark_changed()

    def _delete_in_preview(self) -> None:
        self.selected_indices = {self._preview_index}
        self.delete_selected(None)
        if self.image_files:
            self._preview_index = min(
                self._preview_index, len(self.image_files) - 1
            )
            self._update_preview()
        elif self.widget_exists(self._preview_win):
            self._preview_win.destroy()

    def _create_context_menu(self) -> None:
        m = tk.Menu(self.app, tearoff=0)
        m.add_command(
            label="Forhandsgranska", command=self.preview_selected
        )
        m.add_command(
            label="Oppna externt", command=self._open_external
        )
        m.add_separator()

        rot_m = tk.Menu(m, tearoff=0)
        rot_m.add_command(label="Vanster (90)", command=self.rotate_left)
        rot_m.add_command(label="Hoger (90)",   command=self.rotate_right)
        rot_m.add_command(label="180",          command=self.rotate_180)
        rot_m.add_separator()
        rot_m.add_command(
            label="Spara till disk", command=self.save_rotations
        )
        rot_m.add_command(
            label="Aterstall", command=self.reset_selected_rotation
        )
        m.add_cascade(label="Rotera", menu=rot_m)
        m.add_separator()

        for label, cmd in [
            ("Flytta upp",    self.move_up),
            ("Flytta ner",    self.move_down),
            ("Flytta forst",  self.move_to_top),
            ("Flytta sist",   self.move_to_bottom),
        ]:
            m.add_command(label=label, command=cmd)
        m.add_separator()
        m.add_command(
            label="Kopiera filnamn", command=self._copy_filename
        )
        m.add_command(
            label="Visa i mappen", command=self.show_in_folder
        )
        m.add_separator()
        m.add_command(
            label="Ta bort",
            command=lambda: self.delete_selected(None)
        )
        self._context_menu = m

    def _bind_keyboard_shortcuts(self) -> None:
        bindings = {
            "<Delete>":       self.delete_selected,
            "<BackSpace>":    self.delete_selected,
            "<Control-a>":    self.select_all,
            "<Control-A>":    self.select_all,
            "<Escape>":       self.clear_selection,
            "<Return>":
                lambda e: (self.preview_selected(), "break")[1],
            "<Control-z>":    lambda e: self.undo(),
            "<Control-Z>":    lambda e: self.undo(),
            "<Control-y>":    lambda e: self.redo(),
            "<Control-Y>":    lambda e: self.redo(),
            "<Control-s>":    lambda e: self.save_sort_order(),
            "<Control-S>":    lambda e: self.save_sort_order(),
            "<Control-g>":    lambda e: self.generate_html(),
            "<Control-G>":    lambda e: self.generate_html(),
            "<Control-f>":    lambda e: self._focus_search(),
            "<Control-F>":    lambda e: self._focus_search(),
            "<F5>":           lambda e: self.refresh_gallery(),
            "<Up>":           self._nav_up,
            "<Down>":         self._nav_down,
            "<Left>":         self._nav_left,
            "<Right>":        self._nav_right,
            "<Home>":         self._nav_home,
            "<End>":          self._nav_end,
            "<Control-Home>": lambda e: self.move_to_top(),
            "<Control-End>":  lambda e: self.move_to_bottom(),
            "<Alt-Up>":       lambda e: self.move_up(),
            "<Alt-Down>":     lambda e: self.move_down(),
            "<space>":        self.toggle_selection,
            "<Control-l>":    lambda e: self.rotate_left(),
            "<Control-L>":    lambda e: self.rotate_left(),
            "<Control-r>":    lambda e: self.rotate_right(),
            "<Control-R>":    lambda e: self.rotate_right(),
            "<Control-u>":    lambda e: self.rotate_180(),
            "<Control-U>":    lambda e: self.rotate_180(),
        }
        for key, fn in bindings.items():
            try:
                self.app.bind(key, fn)
            except Exception:
                pass

    def _focus_search(self) -> None:
        if self.widget_exists(self.search_entry):
            self.search_entry.focus_set()
            self.search_entry.select_range(0, tk.END)

    def _nav_up(self, e=None):    return self._navigate(-self.cols, e)

    def _nav_down(self, e=None):  return self._navigate(self.cols,  e)

    def _nav_left(self, e=None):  return self._navigate(-1, e)

    def _nav_right(self, e=None): return self._navigate(1,  e)

    def _navigate(self, delta: int, event=None) -> str:
        if not self.image_files:
            return "break"
        shift = event and bool(event.state & 0x1)
        cur   = (
            self.last_clicked_index
            if self.last_clicked_index is not None else -1
        )
        new   = max(0, min(len(self.image_files) - 1, cur + delta))
        if shift and self.last_clicked_index is not None:
            s, e_ = sorted([self.last_clicked_index, new])
            for i in range(s, e_ + 1):
                self.selected_indices.add(i)
        else:
            self.selected_indices   = {new}
            self.last_clicked_index = new
        self._update_selection_visual()
        self._scroll_to(new)
        return "break"

    def _nav_home(self, event=None) -> str:
        if not self.image_files:
            return "break"
        shift = event and bool(event.state & 0x1)
        if shift and self.last_clicked_index:
            for i in range(0, self.last_clicked_index + 1):
                self.selected_indices.add(i)
        else:
            self.selected_indices   = {0}
            self.last_clicked_index = 0
        self._update_selection_visual()
        self._scroll_to(0)
        return "break"

    def _nav_end(self, event=None) -> str:
        if not self.image_files:
            return "break"
        last  = len(self.image_files) - 1
        shift = event and bool(event.state & 0x1)
        if shift and self.last_clicked_index is not None:
            for i in range(self.last_clicked_index, last + 1):
                self.selected_indices.add(i)
        else:
            self.selected_indices   = {last}
            self.last_clicked_index = last
        self._update_selection_visual()
        self._scroll_to(last)
        return "break"

    def _scroll_to(self, index: int) -> None:
        if not self.image_files or not self.cols:
            return
        row        = index // self.cols
        total_rows = (
            len(self.image_files) + self.cols - 1
        ) // self.cols
        if total_rows > 0:
            pos = max(0.0, (row - 1) / total_rows)
            try:
                self.canvas.yview_moveto(pos)
            except Exception:
                pass
