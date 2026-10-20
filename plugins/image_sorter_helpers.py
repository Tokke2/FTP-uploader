#!/usr/bin/env python3
# ============================================================
# Bildsorterare - Mixin (hjalpfil)
# ============================================================
# FIL:       plugins/image_sorter_helpers.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/image_sorter_helpers.py)
# Klass:     SorterWindowMixin
# VERSION:   4.2.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v4.1.0 → v4.2.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings – ALL %-formatering (labels, rakare,
#             storleksstrangar, felmeddelanden, preview-titlar)
#   [B3]      VERSION + AUTHOR + COPYRIGHT (dynamiskt år) + PLATS
#             (versionen synkas med image_sorter.py)
#
# SYFTE:
#   Avlastar image_sorter.py (>1800 rader) genom mixin-monster.
#   Innehaller thumbnail-laddning, rendering, undo/redo,
#   flytta-operationer, markering, sortering, info-panel,
#   navigation och forhandsgranskning.
#
# ANVANDS SA HAR:
#   from .image_sorter_helpers import SorterWindowMixin
#   class SorterWindow(SorterWindowMixin): ...
#
# VIKTIGT:
#   - Denna fil har INGET PLUGIN_NAME -> plugin-loadern
#     i main.py ignorerar den (den ar inte ett plugin).
#   - Maste ligga i plugins/ tillsammans med image_sorter.py.
#   - Alla metoder anropas via self pa SorterWindow-instansen,
#     sa fargkonstanter (COLOR_*) och widgets (self.win, self.canvas
#     m.fl.) ar tillgangliga aven om de definieras i image_sorter.py.
#
# IMPORTER (kravs av metoderna nedan):
#   tkinter as tk
#   PIL: Image, ImageTk, ImageOps
#   threading, random, re
#   datetime
#
# MODUL-FUNKTIONER:
#   natural_sort_key(text) - definieras HAR (inte i image_sorter.py)
#   for att undvika cirkular import. Aterexporteras av image_sorter.
# ============================================================

import tkinter as tk
from PIL import Image, ImageTk, ImageOps
import threading
import random
import re
from datetime import datetime


def natural_sort_key(text):
    """
    Naturlig sorteringsnyckel.

    Exempel: ['img1', 'img2', 'img10'] sorteras ratt
    istallet for ['img1', 'img10', 'img2'].

    Delar upp text i strangar och siffror alternativt.
    Anvands av: ImageSorter.execute(), SorterWindow._sort()

    Definieras har (inte i image_sorter.py) for att undvika
    cirkular import: image_sorter.py importerar bade denna
    funktion och SorterWindowMixin harifran.
    """
    parts = re.split(r"(\d+)", text.lower())
    return [int(p) if p.isdigit() else p for p in parts]


class SorterWindowMixin:
    """
    Mixin med tunga SorterWindow-metoder.

    Bryts ut fran image_sorter.py for att halla bada filerna
    under radgranserna (image_sorter.py < 1800, denna < 1200).

    Metoderna ar oforandrade (byte-identiska) jamfort med
    originalet - bara flyttade. SorterWindow arver dem via
    class SorterWindow(SorterWindowMixin).

    v4.2.0:
    - Inga f-strings (B1) - all %-formatering
    """

    VERSION   = "4.2.0"
    AUTHOR    = "Rickard Längkvist"
    COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    def load_thumbs_async(self):
        """Ladda thumbnails i bakgrundstrad."""
        self.loading = True
        self.loading_label.config(text="Laddar bilder...")
        self.loading_progress["maximum"] = max(1, len(self.images))
        self.loading_progress["value"]   = 0
        self.loading_progress.pack(side=tk.LEFT, padx=5)

        def _load():
            for i, path in enumerate(self.images):
                if not self.loading or not self.is_open:
                    break
                try:
                    img = Image.open(path)
                    try:
                        img = ImageOps.exif_transpose(img)
                    except Exception:
                        pass
                    img.thumbnail(
                        (self.thumb_size, self.thumb_size),
                        Image.Resampling.LANCZOS,
                    )
                    self.thumbs[path] = ImageTk.PhotoImage(img)

                    if (i % 5 == 0 or i == len(self.images) - 1) \
                            and self.is_open:
                        try:
                            self.win.after(
                                0, lambda n=i: self._update_loading(n)
                            )
                        except Exception:
                            break
                except Exception:
                    pass

            self.loading = False
            if self.is_open:
                try:
                    self.win.after(0, self._finish_loading)
                except Exception:
                    pass

        threading.Thread(target=_load, daemon=True).start()

    def _update_loading(self, count):
        """Uppdatera progress-indikator under laddning."""
        if not self.is_open:
            return
        try:
            self.loading_progress["value"] = count + 1
            self.loading_label.config(
                text="Laddar %d/%d" % (count + 1, len(self.images))
            )
            self.refresh_visual()
        except Exception:
            pass

    def _finish_loading(self):
        """Avsluta laddningsfas."""
        if not self.is_open:
            return
        try:
            self.loading_progress.pack_forget()
            self.loading_label.config(text="")
            self.refresh()
        except Exception:
            pass

    def refresh(self):
        """Fullstandig UI-refresh - forstor och aterskapa widgets."""
        if not self.is_open:
            return
        try:
            for w in self.inner.winfo_children():
                if w is not self.drop_indicator:
                    w.destroy()
            self.item_widgets.clear()

            for i, path in enumerate(self.filtered_images):
                self._create_item(i, path)

            self.update_info()
        except Exception:
            pass

    def refresh_visual(self):
        """Snabb visuell uppdatering - uppdaterar befintliga widgets."""
        if not self.is_open:
            return
        try:
            for idx, w in list(self.item_widgets.items()):
                if idx >= len(self.filtered_images):
                    continue
                path        = self.filtered_images[idx]
                is_selected = idx in self.selected

                bg     = self.COLOR_SELECTED if is_selected else self.COLOR_BG_ITEM
                border = self.COLOR_SELECTED_B if is_selected else self.COLOR_BORDER
                fg     = self.COLOR_TEXT if is_selected else "#aaaaaa"

                w["container"].config(bg=border)
                w["inner"].config(bg=bg)
                w["check"].config(text="X" if is_selected else "", bg=bg)

                stem = path.stem
                name = stem[:13] + "..." if len(stem) > 13 else stem
                w["name"].config(
                    text="#%d %s" % (idx + 1, name), bg=bg, fg=fg
                )

                if path in self.thumbs:
                    try:
                        w["thumb"].config(image=self.thumbs[path])
                    except Exception:
                        pass

            self.update_info()
        except Exception:
            pass

    def _create_item(self, index, path):
        """Skapa ett bild-item i galleriet."""
        if not self.is_open:
            return
        is_selected = index in self.selected
        row, col    = divmod(index, self.cols)

        bg     = self.COLOR_SELECTED if is_selected else self.COLOR_BG_ITEM
        border = self.COLOR_SELECTED_B if is_selected else self.COLOR_BORDER
        fg     = self.COLOR_TEXT if is_selected else "#aaaaaa"

        container = tk.Frame(self.inner, bg=border, padx=2, pady=2)
        container.grid(row=row, column=col, padx=3, pady=3, sticky="n")

        inner = tk.Frame(container, bg=bg, padx=3, pady=3)
        inner.pack()

        if path in self.thumbs:
            thumb = tk.Label(
                inner, image=self.thumbs[path],
                bg="#1a1a1a", cursor="hand2"
            )
        else:
            cell_w = max(4, self.thumb_size // 20)
            cell_h = max(2, self.thumb_size // 40)
            thumb  = tk.Label(
                inner, text="[bild]",
                font=("Segoe UI", 12),
                bg="#1a1a1a", fg="#555555",
                width=cell_w, height=cell_h,
                cursor="hand2",
            )
        thumb.pack()

        for widget in (thumb, container, inner):
            widget.bind(
                "<Button-1>",
                lambda e, i=index: self.on_click(e, i)
            )
            widget.bind(
                "<B1-Motion>",
                lambda e, i=index: self.on_drag(e, i)
            )
            widget.bind(
                "<ButtonRelease-1>",
                lambda e, i=index: self.on_drop(e, i)
            )

        thumb.bind(
            "<Double-1>",
            lambda e, p=path: self.preview_image(p)
        )
        thumb.bind(
            "<Button-3>",
            lambda e, i=index: self.on_right_click(e, i)
        )

        info = tk.Frame(inner, bg=bg)
        info.pack(fill=tk.X)

        check = tk.Label(
            info, text="X" if is_selected else "",
            bg=bg, fg=self.COLOR_TEXT,
            font=("Segoe UI", 8, "bold"), width=2,
        )
        check.pack(side=tk.LEFT)

        stem         = path.stem
        display_name = stem[:13] + "..." if len(stem) > 13 else stem
        name_label   = tk.Label(
            info, text="#%d %s" % (index + 1, display_name),
            bg=bg, fg=fg, font=("Segoe UI", 8),
        )
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        name_label.bind(
            "<Button-1>",
            lambda e, i=index: self.on_click(e, i)
        )

        suffix     = path.suffix.lower()
        fmt_colors = {
            ".jpg": "#22c55e", ".jpeg": "#22c55e",
            ".png": "#3b82f6",
            ".gif": "#f59e0b",
            ".webp": "#8b5cf6",
            ".bmp": "#ef4444",
            ".tiff": "#06b6d4", ".tif": "#06b6d4",
        }
        tk.Label(
            info, text=suffix[1:].upper(),
            bg=bg, fg=fmt_colors.get(suffix, "#666666"),
            font=("Segoe UI", 7, "bold"),
        ).pack(side=tk.RIGHT)

        self.item_widgets[index] = {
            "container": container,
            "inner":     inner,
            "thumb":     thumb,
            "check":     check,
            "name":      name_label,
            "path":      path,
        }

    def _natural_sort_key(self, path):
        """Naturlig sorteringsnyckel for en Path (instans-wrapper)."""
        return natural_sort_key(path.name)

    def update_info(self):
        """Uppdatera raknare, preview och undo/redo-knappar."""
        if not self.is_open:
            return
        try:
            count = len(self.selected)
            self.selected_label.config(text="%d valda" % count)

            if count == 0:
                self.preview_name.config(text="Ingen vald")
                self.preview_info.config(text="")
                self.preview_label.config(image="", text="")
            elif count == 1:
                idx = next(iter(self.selected))
                if idx < len(self.filtered_images):
                    path = self.filtered_images[idx]
                    stem = path.stem
                    name = stem[:22] + "..." if len(stem) > 22 else stem
                    self.preview_name.config(
                        text="#%d: %s" % (idx + 1, name)
                    )
                    try:
                        kb       = path.stat().st_size / 1024
                        if kb > 1024:
                            size_str = "%.1f MB" % (kb / 1024)
                        else:
                            size_str = "%.0f KB" % kb
                        self.preview_info.config(text=size_str)
                    except Exception:
                        self.preview_info.config(text="")
                    if path in self.thumbs:
                        self.preview_label.config(
                            image=self.thumbs[path], text=""
                        )
                    else:
                        self.preview_label.config(image="", text="[bild]")
            else:
                self.preview_name.config(
                    text="%d bilder valda" % count
                )
                self.preview_info.config(text="")
                self.preview_label.config(image="", text="[flera]")

            can_undo = self.history_index > 0
            can_redo = self.history_index < len(self.history) - 1
            self.undo_btn.config(state="normal" if can_undo else "disabled")
            self.redo_btn.config(state="normal" if can_redo else "disabled")
        except Exception:
            pass

    def navigate(self, delta):
        """Navigera med piltangenter."""
        if not self.filtered_images:
            return
        current = self.last_clicked if self.last_clicked is not None else -1
        new_idx = max(0, min(len(self.filtered_images) - 1, current + delta))
        self.selected     = {new_idx}
        self.last_clicked = new_idx
        self.refresh_visual()
        self._scroll_to(new_idx)

    def toggle_current_selection(self):
        """Space-tangent: toggle markering."""
        if self.last_clicked is not None:
            if self.last_clicked in self.selected:
                self.selected.discard(self.last_clicked)
            else:
                self.selected.add(self.last_clicked)
            self.refresh_visual()

    def _scroll_to(self, index):
        """Scrolla canvaset sa att index ar synligt."""
        if not self.is_open:
            return
        try:
            row        = index // self.cols
            total_rows = (
                len(self.filtered_images) + self.cols - 1
            ) // self.cols
            if total_rows > 0:
                frac = max(0.0, (row - 1) / total_rows)
                self.canvas.yview_moveto(frac)
        except Exception:
            pass

    def save_state(self):
        """Spara aktuell bildordning till undo-historiken (max 50)."""
        state = [p.name for p in self.images]
        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.history_index = len(self.history) - 1

    def undo(self):
        """Angra senaste operation (Ctrl+Z)."""
        if self.history_index <= 0:
            return
        self.history_index -= 1
        self._restore_state()

    def redo(self):
        """Gor om angrad operation (Ctrl+Y)."""
        if self.history_index >= len(self.history) - 1:
            return
        self.history_index += 1
        self._restore_state()

    def _restore_state(self):
        """Aterstall bildordning fran historiken."""
        state  = self.history[self.history_index]
        lookup = {p.name: p for p in self.images}
        new_order = [
            lookup[name] for name in state if name in lookup
        ]
        self.images          = new_order
        self.selected.clear()
        self.search_var.set("")
        self.filtered_images = self.images.copy()
        self.refresh()

    def reset_order(self):
        """Aterstall till ursprunglig ordning (index 0 i historiken)."""
        self.save_state()
        self.history_index = 0
        self._restore_state()

    def move_selected_to(self, target):
        """Flytta alla markerade bilder till position target."""
        if not self.selected:
            return
        indices = sorted(self.selected)
        items   = [self.filtered_images[i] for i in indices]

        for item in items:
            if item in self.images:
                self.images.remove(item)
            if item in self.filtered_images:
                self.filtered_images.remove(item)

        removed_before = sum(1 for i in indices if i < target)
        adjusted = max(
            0, min(target - removed_before, len(self.filtered_images))
        )

        for i, item in enumerate(items):
            self.filtered_images.insert(adjusted + i, item)

        if not self.search_var.get():
            self.images = self.filtered_images.copy()

        self.selected     = set(range(adjusted, adjusted + len(items)))
        self.last_clicked = adjusted
        self.refresh()

    def move_up(self):
        """Flytta valda bilder ett steg uppat."""
        if not self.selected or min(self.selected) == 0:
            return
        self.save_state()
        new_selected = set()
        for i in sorted(self.selected):
            self.filtered_images[i], self.filtered_images[i - 1] = (
                self.filtered_images[i - 1],
                self.filtered_images[i],
            )
            new_selected.add(i - 1)
        self.selected = new_selected
        if not self.search_var.get():
            self.images = self.filtered_images.copy()
        self.refresh()

    def move_down(self):
        """Flytta valda bilder ett steg nedat."""
        if not self.selected or \
                max(self.selected) >= len(self.filtered_images) - 1:
            return
        self.save_state()
        new_selected = set()
        for i in sorted(self.selected, reverse=True):
            self.filtered_images[i], self.filtered_images[i + 1] = (
                self.filtered_images[i + 1],
                self.filtered_images[i],
            )
            new_selected.add(i + 1)
        self.selected = new_selected
        if not self.search_var.get():
            self.images = self.filtered_images.copy()
        self.refresh()

    def to_top(self):
        """Flytta valda bilder till forsta position."""
        if self.selected:
            self.save_state()
            self.move_selected_to(0)

    def to_bottom(self):
        """Flytta valda bilder till sista position."""
        if self.selected:
            self.save_state()
            self.move_selected_to(len(self.filtered_images))

    def select_all(self):
        """Markera alla synliga bilder (Ctrl+A)."""
        self.selected = set(range(len(self.filtered_images)))
        self.refresh_visual()

    def deselect_all(self):
        """Avmarkera alla bilder (Ctrl+D)."""
        self.selected.clear()
        self.last_clicked = None
        self.refresh_visual()

    def invert_selection(self):
        """Invertera markeringen (Ctrl+I)."""
        all_indices = set(range(len(self.filtered_images)))
        self.selected = all_indices - self.selected
        self.refresh_visual()

    def remove_selected(self):
        """Ta bort markerade bilder fran listan (INTE fran disk)."""
        if not self.selected:
            return
        self.save_state()
        to_remove = [
            self.filtered_images[i] for i in sorted(self.selected)
        ]
        for item in to_remove:
            if item in self.images:
                self.images.remove(item)
            if item in self.filtered_images:
                self.filtered_images.remove(item)
        self.selected.clear()
        self.refresh()

    def _sort(self, key, reverse=False, label="Sorterar..."):
        """
        Intern DRY-hjalpmetod for alla sorteringsoperationer.
        Sparar state, sorterar, uppdaterar UI.
        Feedback i help_label forsvinner efter 1.0s.
        """
        self.save_state()
        self.help_label.config(text=label)
        self.images.sort(key=key, reverse=reverse)
        self.filtered_images = self.images.copy()
        self.search_var.set("")
        self.selected.clear()
        self.refresh()
        self.win.after(1000, lambda: self.help_label.config(text=""))

    def sort_natural(self):
        """Naturlig sortering: img1, img2, img10 - DEFAULT."""
        self._sort(
            key=lambda x: natural_sort_key(x.name),
            label="Naturlig sortering (1, 2, 10)",
        )

    def sort_az(self):
        """Alfabetisk A-O."""
        self._sort(
            key=lambda x: x.name.lower(),
            label="Sorterat A-O",
        )

    def sort_za(self):
        """Alfabetisk O-A."""
        self._sort(
            key=lambda x: x.name.lower(),
            reverse=True,
            label="Sorterat O-A",
        )

    def sort_date(self):
        """Aldst fil forst."""
        self._sort(
            key=lambda x: x.stat().st_mtime,
            label="Sorterat - aldst fil forst",
        )

    def sort_date_created(self):
        """Nyast fil forst."""
        self._sort(
            key=lambda x: x.stat().st_mtime,
            reverse=True,
            label="Sorterat - nyast fil forst",
        )

    def sort_size(self):
        """Minst fil forst."""
        self._sort(
            key=lambda x: x.stat().st_size,
            label="Sorterat - minst fil forst",
        )

    def sort_size_desc(self):
        """Storst fil forst."""
        self._sort(
            key=lambda x: x.stat().st_size,
            reverse=True,
            label="Sorterat - storst fil forst",
        )

    def sort_type(self):
        """Filtyp + naturlig inom grupp."""
        self._sort(
            key=lambda x: (x.suffix.lower(), natural_sort_key(x.stem)),
            label="Sorterat efter filtyp",
        )

    def shuffle(self):
        """Slumpa ordning."""
        self.save_state()
        random.shuffle(self.images)
        self.filtered_images = self.images.copy()
        self.search_var.set("")
        self.selected.clear()
        self.refresh()
        self.help_label.config(text="Ordning slumpad")
        self.win.after(1000, lambda: self.help_label.config(text=""))

    def preview_selected(self):
        """Oppna forhandsgranskning for markerad bild."""
        if self.selected:
            idx = min(self.selected)
            if idx < len(self.filtered_images):
                self.preview_image(self.filtered_images[idx])

    def preview_image(self, path):
        """
        Oppna forhandsgranskningsfonster.

        Funktioner:
        - Foregaende / Nasta
        - Ta bort fran lista (utan att stanga fonstret)
        - Klick pa bild -> nasta
        - Hogerklick -> foregaende
        - Left Right Space: navigation
        - Delete/Backspace: ta bort
        - Escape: stang
        """
        if not self.is_open:
            return
        if path not in self.filtered_images:
            return

        win = tk.Toplevel(self.win)
        win.title(path.name)
        win.configure(bg="#0a0a0a")
        win.geometry("900x700")
        win.minsize(400, 300)

        idx_ref = [self.filtered_images.index(path)]

        def nav(delta):
            if not self.filtered_images:
                win.destroy()
                return
            idx_ref[0] = (idx_ref[0] + delta) % len(self.filtered_images)
            show_image(self.filtered_images[idx_ref[0]])

        def remove_current():
            if not self.filtered_images or \
                    idx_ref[0] >= len(self.filtered_images):
                win.destroy()
                return
            self.save_state()
            current_path = self.filtered_images[idx_ref[0]]
            if current_path in self.filtered_images:
                self.filtered_images.remove(current_path)
            if current_path in self.images:
                self.images.remove(current_path)
            self.selected.clear()

            if not self.filtered_images:
                self.refresh()
                win.destroy()
                return

            new_idx = max(0, idx_ref[0] - 1)
            if new_idx >= len(self.filtered_images):
                new_idx = len(self.filtered_images) - 1
            idx_ref[0] = new_idx
            new_path   = self.filtered_images[new_idx]
            self.refresh()
            show_image(new_path)
            win.title(
                "%s  -  borttagen: %s" % (new_path.name, current_path.name)
            )

        def show_image(p):
            try:
                if p in self.filtered_images:
                    idx_ref[0] = self.filtered_images.index(p)

                img = Image.open(p)
                orig_w, orig_h = img.size
                try:
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass
                max_w = max(100, win.winfo_width()  - 40)
                max_h = max(100, win.winfo_height() - 130)
                img.thumbnail(
                    (max_w, max_h), Image.Resampling.LANCZOS
                )
                photo = ImageTk.PhotoImage(img)
                img_label.config(image=photo, text="")
                img_label.image = photo

                counter_lbl.config(
                    text="%d/%d"
                    % (idx_ref[0] + 1, len(self.filtered_images))
                )
                name_lbl.config(text=p.name)
                win.title(p.name)

                kb       = p.stat().st_size / 1024
                if kb > 1024:
                    size_str = "%.1f MB" % (kb / 1024)
                else:
                    size_str = "%.0f KB" % kb
                size_lbl.config(
                    text="%dx%d px  -  %s" % (orig_w, orig_h, size_str)
                )

                remove_btn.config(
                    state=(
                        "disabled"
                        if len(self.filtered_images) <= 1
                        else "normal"
                    )
                )
            except Exception as e:
                img_label.config(
                    image="",
                    text="Kunde inte visa:\n%s" % e,
                    fg="#ef4444",
                    font=("Segoe UI", 12),
                )

        # -- Toolbar -----------------------------------------------------------
        toolbar = tk.Frame(win, bg="#1a1a1a", height=44)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        tk.Button(
            toolbar, text="< Foregaende",
            command=lambda: nav(-1),
            bg="#3b82f6", fg=self.COLOR_TEXT,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2", relief="flat",
        ).pack(side=tk.LEFT, padx=10, pady=7)

        remove_btn = tk.Button(
            toolbar, text="Ta bort",
            command=remove_current,
            bg=self.COLOR_DANGER, fg=self.COLOR_TEXT,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2", relief="flat",
        )
        remove_btn.pack(side=tk.LEFT, padx=4, pady=7)

        counter_lbl = tk.Label(
            toolbar,
            text="%d/%d" % (idx_ref[0] + 1, len(self.filtered_images)),
            bg="#1a1a1a", fg=self.COLOR_TEXT,
            font=("Segoe UI", 10, "bold"),
        )
        counter_lbl.pack(side=tk.LEFT, expand=True)

        tk.Button(
            toolbar, text="Nasta >",
            command=lambda: nav(1),
            bg="#3b82f6", fg=self.COLOR_TEXT,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2", relief="flat",
        ).pack(side=tk.RIGHT, padx=10, pady=7)

        # -- Bildyta -----------------------------------------------------------
        canvas_frame = tk.Frame(win, bg="#0a0a0a")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        img_label = tk.Label(canvas_frame, bg="#0a0a0a", cursor="hand2")
        img_label.pack(expand=True)
        img_label.bind("<Button-1>",  lambda e: nav(1))
        img_label.bind("<Button-3>",  lambda e: nav(-1))

        # -- Inforad -----------------------------------------------------------
        info_bar = tk.Frame(win, bg="#1a1a1a", height=52)
        info_bar.pack(fill=tk.X)
        info_bar.pack_propagate(False)

        name_lbl = tk.Label(
            info_bar, text="",
            bg="#1a1a1a", fg=self.COLOR_TEXT,
            font=("Segoe UI", 10),
        )
        name_lbl.pack(pady=(5, 0))

        size_lbl = tk.Label(
            info_bar, text="",
            bg="#1a1a1a", fg="#888888",
            font=("Segoe UI", 9),
        )
        size_lbl.pack()

        # -- Shortcuts ---------------------------------------------------------
        win.bind("<Left>",      lambda e: nav(-1))
        win.bind("<Right>",     lambda e: nav(1))
        win.bind("<space>",     lambda e: nav(1))
        win.bind("<Escape>",    lambda e: win.destroy())
        win.bind("<Delete>",    lambda e: remove_current())
        win.bind("<BackSpace>", lambda e: remove_current())

        show_image(path)
