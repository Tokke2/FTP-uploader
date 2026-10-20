# ============================================================
# Hjalpfil: Oppna/uppdatera genererat galleri
# ============================================================
# FIL:       plugins/ui_settings_gallery.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/ui_settings_gallery.py)
# VERSION:   1.3.7
# Ingen PLUGIN_NAME - ignoreras av plugin-loadern.
# Mixin for ui_settings.py (G1-G4). Inga f-strangar, ingen print().
#
# v1.3.7: Historik tom: skanna out/ REKURSIVT (undermappar), valj den
#         out/-rot som faktiskt har gallerier, visa sokvag i dialogen.
# v1.3.5: Tk 9-sakker importdialog: INGA padx/pady-tupler nagonstans,
#         fallback till mappval om dialog kraschar. Logg: v1.3.5.
# v1.3.4: Loggar versionsrad vid import. pad alltid int (Tk 9).
# v1.3.3: Tk 9.0 krasch: pady=(12, 4) -> "expected screen distance".
#         Inga tupler i padx/pady pa widgets. Logg 14:01:34.
# v1.3.2: Dialog visade BARA rubriken (lista/knappar kapades). Packa
#         footer forst, geometry EFTER widgets, os.scandir, lista ALLA
#         undermappar i out/, hogkontrast-listbox, visa skanningsfel.
# v1.3.1: Import-listan visade tomt: kravde index.html + fel out/-rot
#         + mork listbox mot ljust tema. Nu: hitta out/ via projektrot,
#         lista ALLA gallerimappar (index.html ELLER image/ ELLER bilder),
#         alltid visa dialogen med skannad sokvag, tema-kontrast.
# v1.3.0: FS-26 historikdialog: DPI-text, fit_window, tva paneler,
#         sok, tema-farger, relativ out/-sokvag. FS-27 A/A/O i
#         dialogtexter (Oppna/Valj/Bladdra/lagg till).
# v1.2.0: FS-11 rensa doda historikposter nar historiken oppnas.
#         Raderar ALDRIG filer i out/ - bara rader i JSON.
# v1.1.0: Historik (config/gallery_history.json) + importera index.html.
# ============================================================

import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime


class GeneratedGalleryMixin(object):
    """Oppna historik/out/-galleri, lagg till bilder/videor, las output fast."""

    HISTORY_FILE = "gallery_history.json"
    MAX_HISTORY  = 40
    _SKIP_DIRS = frozenset((
        "image", "images", "thumb", "thumbs", "video", "videos",
        "pdf", "css", "js", "assets", "icon", "full", "originals",
        "removed", "__pycache__", "node_modules",
    ))

    # ==========================================================================
    # GENERERAT GALLERI (G1-G3)
    # ==========================================================================

    def _out_root(self) -> Path:
        """Projektets out/-mapp. Foredra den som INNEHALLER gallerier."""
        cands = []
        try:
            from helpers import get_base_path
            cands.append(get_base_path() / "out")
        except Exception:
            pass
        try:
            cands.append(Path(__file__).resolve().parent.parent / "out")
        except Exception:
            pass
        try:
            cands.append(Path.cwd() / "out")
        except Exception:
            pass
        try:
            ov = getattr(self, "output_var", None)
            s = ov.get() if ov is not None else ""
            if s:
                p = Path(s)
                if p.name.lower() != "out":
                    p = p.parent if p.is_dir() else p
                while p.name and p.name.lower() != "out":
                    if p.parent == p:
                        break
                    p = p.parent
                if p.name.lower() == "out":
                    cands.append(p)
        except Exception:
            pass
        seen = set()
        uniq = []
        for p in cands:
            try:
                key = str(p.resolve()) if p.exists() else str(p)
            except Exception:
                key = str(p)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        best = None
        best_n = -1
        first_dir = None
        for p in uniq:
            try:
                if not p.is_dir():
                    continue
            except Exception:
                continue
            if first_dir is None:
                first_dir = p
            n = 0
            try:
                n = self._count_gallery_dirs(p, 0)
            except Exception:
                n = 0
            if n > best_n:
                best_n = n
                best = p
        if best is not None:
            return best
        if first_dir is not None:
            return first_dir
        return uniq[0] if uniq else Path("out")

    def _path_from_stored(self, s):
        """PORT-1: relativ mot appen, gammal absolut pekas om till out/<namn>."""
        try:
            from helpers import from_app_rel
            p = from_app_rel(s)
            if p is not None:
                return Path(p)
        except Exception:
            pass
        try:
            p = Path(s) if s else None
            if p is not None and p.exists():
                return p
        except Exception:
            pass
        try:
            name = Path(s).name if s else ""
            if name:
                cand = self._out_root() / name
                if cand.is_dir():
                    return cand
        except Exception:
            pass
        return None

    def _has_index(self, folder) -> bool:
        """True om mappen har index.html (skiftlagessokert)."""
        try:
            p = Path(folder)
            if (p / "index.html").is_file():
                return True
            for f in p.iterdir():
                if f.is_file() and f.name.lower() == "index.html":
                    return True
        except Exception:
            pass
        return False

    def _looks_like_gallery(self, folder) -> bool:
        """Galleri: index.html, image/, video/ eller bildfiler."""
        try:
            p = Path(folder)
            if not p.is_dir():
                return False
            if self._has_index(p):
                return True
            if (p / "image").is_dir() or (p / "video").is_dir():
                return True
            fmts = getattr(self, "IMAGE_FORMATS", None) or {
                ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
                ".tiff", ".tif",
            }
            n = 0
            for f in p.iterdir():
                if f.is_file() and f.suffix.lower() in fmts:
                    n += 1
                    if n >= 1:
                        return True
        except Exception:
            pass
        return False

    def _iter_out_dirs(self, root, depth, max_depth=4):
        """os.scandir-undermappar, hoppar image/thumb/video/..."""
        import os
        if depth > max_depth:
            return
        try:
            with os.scandir(str(root)) as it:
                ents = list(it)
        except Exception:
            return
        for ent in ents:
            try:
                if not ent.is_dir(follow_symlinks=True):
                    continue
                name = ent.name
                if name.startswith("."):
                    continue
                if name.lower() in self._SKIP_DIRS:
                    continue
                yield Path(ent.path), depth
            except Exception:
                continue

    def _walk_galleries(self, root, max_depth=4):
        """Hitta gallerimappar under root (rekursivt)."""
        found = []
        stack = [(Path(root), 0)]
        while stack:
            cur, depth = stack.pop()
            for child, d in self._iter_out_dirs(cur, depth, max_depth):
                is_g = False
                try:
                    is_g = self._looks_like_gallery(child)
                except Exception:
                    is_g = False
                if is_g:
                    found.append(child)
                    continue
                if d < max_depth:
                    stack.append((child, d + 1))
        return found

    def _count_gallery_dirs(self, root, depth=0) -> int:
        try:
            return len(self._walk_galleries(root, max_depth=3))
        except Exception:
            return 0

    def list_generated_galleries(self) -> list:
        """Gallerimappar i out/ och dess undermappar."""
        found = []
        root = self._out_root()
        try:
            if not root.is_dir():
                self._last_scan_note = "out/ finns inte: %s" % root
                return found
        except Exception as e:
            self._last_scan_note = "out/ lasfel: %s" % e
            return found
        try:
            if self._looks_like_gallery(root):
                found.append(Path(root))
        except Exception:
            pass
        try:
            found.extend(self._walk_galleries(root, max_depth=4))
        except Exception as e:
            self._last_scan_note = "Kunde inte lasa %s: %s" % (root, e)
            try:
                self.log("VARNING", self._last_scan_note)
            except Exception:
                pass
            return found
        uniq = []
        seen = set()
        for p in found:
            try:
                key = str(p.resolve())
            except Exception:
                key = str(p)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        uniq.sort(key=lambda x: x.name.lower())
        if uniq:
            self._last_scan_note = "Hittade %d i %s: %s" % (
                len(uniq),
                root,
                ", ".join(x.name for x in uniq[:12]),
            )
        else:
            names = []
            try:
                import os
                with os.scandir(str(root)) as it:
                    names = [ent.name for ent in it][:20]
            except Exception:
                names = []
            extra = ", ".join(names) if names else "(tom)"
            self._last_scan_note = "0 gallerier i %s. Innehall: %s" % (
                root, extra,
            )
        try:
            self.log("INFO", "Historik-scan: %s" % self._last_scan_note)
        except Exception:
            pass
        return uniq

    def record_generated_gallery(
        self, output_path, title="", n_img=0, n_vid=0,
    ) -> None:
        """Spara/uppdatera en post i historiken efter lyckad HTML (G4)."""
        try:
            p = Path(output_path)
            if not p.exists():
                return
            if p.is_file() and p.name.lower() == "index.html":
                p = p.parent
            if not (p / "index.html").is_file():
                return
            try:
                from helpers import to_app_rel
                path_s = to_app_rel(p)
            except Exception:
                path_s = p.name
            item = {
                "path":   path_s,
                "title":  str(title or p.name)[:80],
                "name":   p.name,
                "when":   datetime.now().strftime("%Y-%m-%d %H:%M"),
                "images": int(n_img or 0),
                "videos": int(n_vid or 0),
            }
            data = self.load_config(self.HISTORY_FILE, default={})
            if not isinstance(data, dict):
                data = {}
            items = data.get("galleries", [])
            if not isinstance(items, list):
                items = []
            items = [
                g for g in items
                if g.get("path") != path_s and g.get("name") != p.name
            ]
            items.insert(0, item)
            self.save_config(
                self.HISTORY_FILE,
                {"galleries": items[: self.MAX_HISTORY]},
            )
        except Exception as e:
            self.log("DEBUG", "historik kunde inte sparas: %s" % e)

    def list_history_galleries(self) -> list:
        """
        Historik (nyast forst) + ovriga mappar i out/.

        Returnerar list[(Path, meta-dict)]. Mappar med index.html,
        image/ eller bildfiler.
        """
        seen = set()
        out = []
        try:
            data = self.load_config(self.HISTORY_FILE, default={})
            items = data.get("galleries", []) if isinstance(data, dict) else []
        except Exception:
            items = []
        for g in items:
            try:
                p = self._path_from_stored(g.get("path") or g.get("name") or "")
                if p is None or not p.is_dir():
                    continue
                if not self._looks_like_gallery(p):
                    continue
                key = str(p.resolve())
                if key in seen:
                    continue
                seen.add(key)
                out.append((p, g))
            except Exception:
                continue
        for p in self.list_generated_galleries():
            try:
                key = str(p.resolve())
            except Exception:
                key = str(p)
            if key in seen:
                continue
            seen.add(key)
            out.append((p, {
                "path": str(p), "name": p.name, "title": p.name,
                "when": "", "images": 0, "videos": 0,
            }))
        return out

    def prune_history_galleries(self) -> int:
        """
        FS-11: ta bort JSON-rader dar index.html saknas.

        Raderar ALDRIG nagot i out/ - bara historikfilen.
        Om sokvagen ar dod men out/<namn>/index.html finns, peka om dit
        (genererade filer ligger i out/).
        Returnerar antal borttagna poster.
        """
        removed = 0
        try:
            data = self.load_config(self.HISTORY_FILE, default={})
            if not isinstance(data, dict):
                data = {}
            items = data.get("galleries", [])
            if not isinstance(items, list):
                items = []
        except Exception:
            return 0
        if not items:
            return 0

        out_root = self._out_root()
        kept = []
        changed = False
        seen = set()
        for g in items:
            if not isinstance(g, dict):
                changed = True
                removed += 1
                continue
            try:
                p = self._path_from_stored(
                    g.get("path") or g.get("name") or ""
                )
            except Exception:
                p = None

            alive = None
            try:
                if p is not None and p.is_dir() and self._looks_like_gallery(p):
                    alive = p
            except Exception:
                alive = None

            if alive is None:
                name = g.get("name") or (p.name if p is not None else "")
                try:
                    cand = out_root / name if name else None
                    if (
                        cand is not None
                        and cand.is_dir()
                        and self._looks_like_gallery(cand)
                    ):
                        alive = cand
                        g = dict(g)
                        try:
                            from helpers import to_app_rel
                            g["path"] = to_app_rel(cand)
                        except Exception:
                            g["path"] = cand.name
                        g["name"] = cand.name
                        changed = True
                except Exception:
                    alive = None

            if alive is None:
                changed = True
                removed += 1
                continue

            try:
                key = str(alive.resolve())
            except Exception:
                key = str(alive)
            if key in seen:
                changed = True
                continue
            seen.add(key)
            kept.append(g)

        if not changed:
            return 0
        try:
            self.save_config(
                self.HISTORY_FILE,
                {"galleries": kept[: self.MAX_HISTORY]},
            )
        except Exception as e:
            self.log("DEBUG", "historik kunde inte rensas: %s" % e)
            return 0
        if removed:
            self.log(
                "INFO",
                "Historik: tog bort %d doda poster (filer i out/ ororda)"
                % removed,
            )
        return removed

    def _resolve_gallery_root(self, path) -> Path:
        """Hitta gallerimappen (index.html, image/ eller bildfiler)."""
        p = Path(path)
        try:
            if self._has_index(p) or self._looks_like_gallery(p):
                return p
            if p.name.lower() == "image" and p.parent.is_dir():
                return p.parent
            if p.is_file() and p.name.lower() == "index.html":
                return p.parent
        except Exception:
            pass
        return None

    def _parse_index_meta(self, index_path: Path):
        """Titel + beskrivning ur index.html."""
        title, desc = "", ""
        try:
            text = index_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return title, desc
        m = re.search(
            r'<h1[^>]*class="[^"]*site-title[^"]*"[^>]*>([^<]+)',
            text, re.I,
        )
        if not m:
            m = re.search(r"<title>([^<]+)</title>", text, re.I)
        if m:
            title = (
                m.group(1).replace("&amp;", "&").replace("&quot;", '"')
                .replace("&#39;", "'").strip()
            )
        m = re.search(
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)',
            text, re.I,
        )
        if m:
            desc = m.group(1).replace("&amp;", "&").strip()
        return title, desc

    def _hist_font(self, style=None):
        """DPI-font (Z3). Fallback om Inställningar inte initierat."""
        try:
            if hasattr(self, "_font") and getattr(self, "_base_font_size", None):
                return self._font(style)
        except Exception:
            pass
        size = 10
        try:
            size = int(getattr(self, "_base_font_size", 10) or 10)
        except Exception:
            size = 10
        if style:
            return ("Segoe UI", size, style)
        return ("Segoe UI", size)

    def _hist_scaled(self, value):
        """Skala pixlar med teckenstorlek (Z3)."""
        try:
            if hasattr(self, "_scaled"):
                return int(self._scaled(value))
        except Exception:
            pass
        return int(value)

    def _hist_colors(self):
        """Tema-farger for historikdialog."""
        bg = getattr(self, "_bg", None) or getattr(self, "COLOR_BG", "#1a1a2e")
        mid = getattr(self, "COLOR_BG_MID", "#16213e")
        fg = getattr(self, "COLOR_FG", "#ffffff")
        muted = getattr(self, "COLOR_MUTED", "#8892b0")
        accent = getattr(self, "COLOR_ACCENT", "#4a90d9")
        card = mid if mid != bg else bg
        line = muted
        return {
            "bg": bg, "mid": mid, "fg": fg, "muted": muted,
            "accent": accent, "card": card, "line": line,
            "ok": "#16a34a", "danger": "#7f1d1d",
        }

    def _rel_out_label(self, path) -> str:
        """Visa out/Namn istallet for absolut diskvag."""
        try:
            p = Path(path)
            root = self._out_root().resolve()
            rel = p.resolve().relative_to(root)
            return "out/%s" % rel.as_posix()
        except Exception:
            try:
                return "out/%s" % Path(path).name
            except Exception:
                return str(path or "")

    def _gallery_media_counts(self, root: Path):
        """Antal bilder/videor (hoppar Removed/)."""
        n_img = 0
        n_vid = 0
        try:
            img_dir = root / "image" if (root / "image").is_dir() else root
            for f in img_dir.iterdir():
                try:
                    if not f.is_file():
                        continue
                    if f.name.startswith("."):
                        continue
                    if f.suffix.lower() in self.IMAGE_FORMATS:
                        n_img += 1
                except Exception:
                    continue
        except Exception:
            pass
        try:
            vdir = root / "video"
            if vdir.is_dir():
                for f in vdir.iterdir():
                    try:
                        if f.is_file() and f.suffix.lower() in self.VIDEO_FORMATS:
                            n_vid += 1
                    except Exception:
                        continue
        except Exception:
            pass
        return n_img, n_vid

    def _place_hist_dialog(self, dlg, width, height) -> None:
        """Centrera pa foralder, klamp mot skarm (Z4 fit_window)."""
        try:
            dlg.update_idletasks()
            sw = int(dlg.winfo_screenwidth() or 1200)
            sh = int(dlg.winfo_screenheight() or 800)
            width = max(420, min(int(width), sw - 48))
            height = max(300, min(int(height), sh - 72))
            x = max(0, (sw - width) // 2)
            y = max(24, (sh - height) // 3)
            try:
                app = self.app
                if app is not None:
                    px = int(app.winfo_rootx())
                    py = int(app.winfo_rooty())
                    pw = int(app.winfo_width())
                    ph = int(app.winfo_height())
                    if pw > 80 and ph > 80:
                        x = px + max(0, (pw - width) // 2)
                        y = py + max(0, (ph - height) // 2)
            except Exception:
                pass
            if x + width > sw:
                x = max(0, sw - width - 16)
            if y + height > sh:
                y = max(0, sh - height - 32)
            dlg.geometry("%dx%d+%d+%d" % (width, height, x, y))
            dlg.minsize(min(420, width), min(280, height))
        except Exception:
            try:
                dlg.geometry("%dx%d" % (int(width), int(height)))
            except Exception:
                pass

    def _hist_preview_photo(self, root: Path, max_px: int):
        """Forsta thumb/bild som PhotoImage, eller None."""
        try:
            from PIL import Image, ImageTk
        except Exception:
            return None
        folders = []
        try:
            if (root / "thumb").is_dir():
                folders.append(root / "thumb")
            if (root / "image").is_dir():
                folders.append(root / "image")
            folders.append(root)
        except Exception:
            return None
        src = None
        for folder in folders:
            try:
                files = [
                    f for f in folder.iterdir()
                    if f.is_file()
                    and f.suffix.lower() in self.IMAGE_FORMATS
                    and not f.name.startswith(".")
                ]
            except Exception:
                files = []
            if files:
                files.sort(key=lambda x: x.name.lower())
                src = files[0]
                break
        if src is None:
            return None
        try:
            im = Image.open(src)
            im.thumbnail((max_px, max_px))
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")
            kw = {}
            try:
                if self.app is not None:
                    kw["master"] = self.app
            except Exception:
                kw = {}
            return ImageTk.PhotoImage(im, **kw)
        except Exception:
            return None

    def browse_generated_gallery(self) -> None:
        """Valj ett redan genererat galleri (out/ eller valfri mapp)."""
        try:
            self.prune_history_galleries()
        except Exception:
            pass
        rows = []
        try:
            rows = self.list_history_galleries()
        except Exception as e:
            try:
                self.log("FEL", "Historiklista: %s" % e)
            except Exception:
                pass
        initial = str(self._out_root())
        try:
            self.log(
                "INFO",
                "Historikdialog v1.3.7: %d poster, out/ = %s"
                % (len(rows), initial),
            )
        except Exception:
            pass
        chosen = None
        try:
            chosen = self._pick_generated_dialog(rows)
        except Exception as e:
            try:
                self.log("FEL", "Historikdialog krasch: %s" % e)
            except Exception:
                pass
            try:
                messagebox.showerror(
                    "Historik",
                    "Kunde inte visa listan:\n%s\n\nOppnar mappval i out/."
                    % e,
                )
            except Exception:
                pass
            chosen = ""
        if chosen is None:
            return
        if chosen == "":
            start = initial if Path(initial).is_dir() else str(Path.home())
            folder = filedialog.askdirectory(
                title="Valj gallerimapp i out/",
                initialdir=start,
            )
            if not folder:
                return
            self.load_generated_gallery(Path(folder))
            return
        self.load_generated_gallery(chosen)

    def _pick_generated_dialog(self, galleries) -> Path:
        """Lista out/-mappar. Tk 9: inga padx/pady-tupler."""
        result = {"val": None}
        paths = []
        for item in galleries or []:
            if isinstance(item, (tuple, list)) and item:
                p = item[0]
            else:
                p = item
            try:
                p = Path(p)
            except Exception:
                continue
            if not p.is_dir():
                continue
            n_img, n_vid = 0, 0
            try:
                n_img, n_vid = self._gallery_media_counts(p)
            except Exception:
                pass
            extra = "%d bilder" % n_img
            if n_vid:
                extra += ", %d videor" % n_vid
            try:
                shown = p.relative_to(self._out_root()).as_posix()
            except Exception:
                shown = p.name
            paths.append((p, "%s    (%s)" % (shown, extra)))

        dlg = tk.Toplevel(getattr(self, "app", None))
        dlg.title("Oppna genererat galleri")
        try:
            dlg.configure(bg="#1e1e1e")
        except Exception:
            pass
        try:
            dlg.transient(self.app)
        except Exception:
            pass
        dlg.resizable(True, True)

        def _ok(event=None):
            try:
                sel = lb.curselection()
                if not sel:
                    return
                result["val"] = paths[int(sel[0])][0]
            except Exception:
                return
            try:
                dlg.destroy()
            except Exception:
                pass

        def _browse(event=None):
            result["val"] = ""
            try:
                dlg.destroy()
            except Exception:
                pass

        def _cancel(event=None):
            result["val"] = None
            try:
                dlg.destroy()
            except Exception:
                pass

        # Footer FORST sa listan inte kapar knapparna (Tk pack).
        # Inga padx/pady-tupler pa widgets (Tk 9).
        btns = tk.Frame(dlg, bg="#1e1e1e")
        btns.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(
            btns, text="Oppna", command=_ok,
            bg="#16a34a", fg="#ffffff", relief="flat",
        ).pack(side=tk.LEFT)
        tk.Button(
            btns, text="Bladdra...", command=_browse,
            bg="#374151", fg="#ffffff", relief="flat",
        ).pack(side=tk.LEFT)
        tk.Button(
            btns, text="Avbryt", command=_cancel,
            bg="#7f1d1d", fg="#ffffff", relief="flat",
        ).pack(side=tk.RIGHT)

        note = getattr(self, "_last_scan_note", "") or ""
        info = tk.Label(
            dlg,
            text="out/  %s" % self._out_root(),
            anchor=tk.W,
            bg="#1e1e1e",
            fg="#93c5fd",
        )
        info.pack(side=tk.TOP, fill=tk.X)
        sub = tk.Label(
            dlg,
            text=note[:180] if note else "",
            anchor=tk.W,
            bg="#1e1e1e",
            fg="#9ca3af",
        )
        sub.pack(side=tk.TOP, fill=tk.X)

        lb = tk.Listbox(
            dlg,
            height=14,
            bg="#111827",
            fg="#f9fafb",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            font=("Segoe UI", 11),
            exportselection=False,
        )
        lb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        for _p, label in paths:
            lb.insert(tk.END, label)
        if paths:
            lb.selection_set(0)
            lb.see(0)
        else:
            lb.insert(tk.END, "(inga gallerier hittades - anvand Bladdra)")

        lb.bind("<Double-Button-1>", _ok)
        dlg.bind("<Return>", _ok)
        dlg.bind("<Escape>", _cancel)
        try:
            self._place_hist_dialog(dlg, 720, 460)
        except Exception:
            try:
                dlg.geometry("720x460")
            except Exception:
                pass
        try:
            dlg.grab_set()
        except Exception:
            pass
        try:
            lb.focus_set()
        except Exception:
            pass
        dlg.wait_window()
        return result["val"]

    def load_generated_gallery(self, gallery_dir) -> bool:
        """
        Ladda ett genererat galleri: bilder, videor, titel, output=samma mapp.
        """
        root = self._resolve_gallery_root(gallery_dir)
        if root is None:
            messagebox.showerror(
                "Inte ett galleri",
                "Hittade ingen gallerimapp i:\n%s\n\n"
                "Valj en mapp i out/ (med index.html, image/ eller bilder)."
                % gallery_dir,
            )
            return False

        img_dir = root / "image"
        src = img_dir if img_dir.is_dir() else root
        title, desc = "", ""
        try:
            idx = None
            try:
                if (root / "index.html").is_file():
                    idx = root / "index.html"
            except Exception:
                idx = None
            if idx is None:
                try:
                    for f in root.iterdir():
                        if f.is_file() and f.name.lower() == "index.html":
                            idx = f
                            break
                except Exception:
                    idx = None
            if idx is not None:
                title, desc = self._parse_index_meta(idx)
        except Exception:
            title, desc = "", ""

        self._output_override = str(root)
        self._suppress_auto_title = True
        try:
            self.folder_var.set(str(src))
            if title:
                self.title_var.set(title)
            elif root.name:
                self.title_var.set(root.name)
            if desc:
                self.desc_var.set(desc)
        finally:
            self._suppress_auto_title = False

        try:
            self.output_var.set(str(root))
        except Exception:
            pass

        if self.app is not None:
            self.app.context["output_path"] = str(root)
            self.app.context["selected_folder"] = str(src)

        gv = None
        try:
            gv = self.app.context.get("_gallery_view")
        except Exception:
            gv = None
        if gv and hasattr(gv, "_load_images_from_folder"):
            try:
                gv._load_images_from_folder(Path(src))
            except Exception as e:
                self.log("VARNING", "Kunde inte ladda gallerivy: %s" % e)

        n_vid = 0
        try:
            vdir = root / "video"
            if vdir.is_dir():
                n_vid = sum(
                    1 for f in vdir.iterdir()
                    if f.is_file()
                    and f.suffix.lower() in self.VIDEO_FORMATS
                )
        except Exception:
            pass

        try:
            n_img = 0
            gv2 = self.app.context.get("_gallery_view") if self.app else None
            if gv2 and getattr(gv2, "image_files", None):
                n_img = len(gv2.image_files)
            self.record_generated_gallery(root, title or root.name, n_img, n_vid)
        except Exception:
            pass

        self.log(
            "OK",
            "Importerade galleri: %s (lägg till/ta bort, sedan Generera HTML)"
            % root.name,
        )
        messagebox.showinfo(
            "Galleriet öppnat",
            "Öppnade '%s'.\n\n"
            "Lägg till bilder/videor via Arkiv, ta bort i "
            "Bildgalleri-fliken, klicka sedan Generera HTML."
            % root.name,
        )
        return True

    def _unique_dest(self, dest_dir: Path, name: str) -> Path:
        """Unikt filnamn i dest_dir (foo.jpg, foo_2.jpg, ...)."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / name
        if not dest.exists():
            return dest
        stem = Path(name).stem
        ext = Path(name).suffix
        i = 2
        while i < 1000:
            cand = dest_dir / ("%s_%d%s" % (stem, i, ext))
            if not cand.exists():
                return cand
            i += 1
        return dest

    def add_images_to_gallery(self) -> None:
        """Kopiera bilder till aktiv bildmapp och ladda om vyn."""
        dest = Path(self.folder_var.get() or "")
        if not dest.is_dir():
            messagebox.showwarning(
                "Ingen mapp",
                "Öppna ett genererat galleri eller välj bildmapp först.",
            )
            return
        files = filedialog.askopenfilenames(
            title="Lägg till bilder",
            filetypes=[
                ("Bilder",
                 "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tif *.tiff"),
                ("Alla filer", "*.*"),
            ],
        )
        if not files:
            return
        n = 0
        for f in files:
            src = Path(f)
            if src.suffix.lower() not in self.IMAGE_FORMATS:
                continue
            try:
                shutil.copy2(src, self._unique_dest(dest, src.name))
                n += 1
            except Exception as e:
                self.log_error("Kunde inte kopiera %s" % src.name, e)
        if n == 0:
            messagebox.showinfo("Inget kopierat", "Inga bilder kopierades.")
            return
        gv = self.app.context.get("_gallery_view") if self.app else None
        if gv and hasattr(gv, "_load_images_from_folder"):
            try:
                gv._load_images_from_folder(dest)
            except Exception:
                pass
        self.log(
            "OK",
            "Lade till %d bilder. Generera HTML för att uppdatera." % n,
        )
        messagebox.showinfo(
            "Bilder tillagda",
            "%d bilder kopierades in.\n\nKlicka Generera HTML för att "
            "uppdatera galleriet." % n,
        )

    def add_videos_to_gallery(self) -> None:
        """Kopiera videor till output/video/."""
        output = self.get_output_path()
        if output is None:
            messagebox.showwarning(
                "Ingen output",
                "Öppna ett genererat galleri eller välj bildmapp först.",
            )
            return
        files = filedialog.askopenfilenames(
            title="Lägg till videor",
            filetypes=[
                ("Video", "*.mp4 *.webm *.mov *.avi *.mkv *.m4v *.ogv"),
                ("Alla filer", "*.*"),
            ],
        )
        if not files:
            return
        vdir = Path(output) / "video"
        n = 0
        next_i = 1
        try:
            if vdir.is_dir():
                for f in vdir.iterdir():
                    m = re.match(r"^video(\d+)", f.stem, re.I)
                    if m:
                        next_i = max(next_i, int(m.group(1)) + 1)
        except Exception:
            pass
        for f in files:
            src = Path(f)
            if src.suffix.lower() not in self.VIDEO_FORMATS:
                continue
            try:
                new_name = "video%d%s" % (next_i, src.suffix.lower())
                shutil.copy2(src, self._unique_dest(vdir, new_name))
                next_i += 1
                n += 1
            except Exception as e:
                self.log_error("Kunde inte kopiera %s" % src.name, e)
        if n == 0:
            messagebox.showinfo("Inget kopierat", "Inga videor kopierades.")
            return
        self.log(
            "OK",
            "Lade till %d videor. Generera HTML för att uppdatera." % n,
        )
        messagebox.showinfo(
            "Videor tillagda",
            "%d videor kopierades till video/.\n\nKlicka Generera HTML "
            "för att uppdatera galleriet." % n,
        )

