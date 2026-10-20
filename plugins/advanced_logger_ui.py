#!/usr/bin/env python3
# ============================================================
# advanced_logger_ui.py  -  UI-mixin for Loggvisaren
# ============================================================
# FIL:       plugins/advanced_logger_ui.py
# VERSION:   1.1.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist
#
# SYFTE: advanced_logger.py narmade sig 1800-radersgransen (spec §20).
#   Tva stora, sjalvstandiga UI-block flyttas hit som mixiner sa att
#   huvudfilen haller sig under taket utan att nagot beteende andras.
#   Alla metoder behaller sina namn och nar logger-instansen via self.
#
#   [X1]  UiCaptureMixin - central fangst av ALLT som hander i UI (W3):
#         13 handelseslag + ultra-lage (tangenter/musrorelse/hover).
#         Tangentinnehall loggas ALDRIG - bara antal, sa att losenord
#         och FTP-uppgifter inte hamnar i loggen.
#   [X2]  DiagWindowMixin - AI-felsokningsfonstret (W6/W8): rapport i
#         eget Toplevel, fargkodat allvar, kopiera/spara/ratta.
#
#   Denna fil ar en HJALPFIL utan PLUGIN_NAME och ignoreras av
#   plugin-loadern - den importeras enbart av advanced_logger.py.
#
#   Konventioner: inga f-strangar (%), ingen print(), reser aldrig
#   (varje publik yta ligger i try/except).
#
# ANDRINGAR v1.0.0 -> v1.1.0 (loggspam):
#   [L1]  _on_theme_event loggar bara nar temat FAKTISKT andras.
#         bind_all(<<ThemeChanged>>) tradde varje widget vid start
#         (~60x dark + hundratals light).
#   [L2]  _on_window_event: falsk Destroy (widgeten lever fortfarande)
#         hoppas over. Map/Unmap/Visibility throttlas 800 ms sa
#         flikbyte inte spammar "fonster-Destroy | Gallery Uploader".
# ============================================================

import time
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .advanced_logger_diag import (
    ALLVAR_TEXT,
    diff_current,
    session_diff,
    window_report,
)
from .advanced_logger_guards import ContextObserver, UNKNOWN
from .advanced_logger_guards import fit_window, readable_width


def _screen_height(app):
    """Skarmhojd i px (0 = okant) - for att dimensionera fönster."""
    try:
        if app is None:
            return 0
        return int(app.winfo_screenheight())
    except Exception:
        return 0


class UiCaptureMixin(object):
    """Central fangst av allt som hander i UI:t (U2, utokad i W3)."""

    def _install_ui_capture(self, app) -> None:
        """
        Central global UI-aktivitetsfångare (U2, utökad i W3).

        13 händelseslag via bind_all(add="+") så att inga befintliga
        bindningar ersätts. Allt ligger i try/except - en felaktig
        binding kan aldrig krascha appen. Ultra-läget (W3) binder
        dessutom Key/Motion/Enter/Leave.

        SÄKERHET: tangenter i inmatningsfält loggas ALDRIG som text,
        bara antal ("3 tecken i Entry") - lösenord hamnar inte i loggen.
        """
        if self._ui_installed:
            return
        if not self._setting("capture", True):
            self.log("INFO", "UI-fångst avstängd i config/logger_settings.json")
            return
        try:
            if not (app and hasattr(app, "bind_all")):
                return
            binds = (
                ("<<NotebookTabChanged>>", self._on_tab_changed),
                ("<Button-1>",             self._on_ui_click),
                ("<Button-3>",             self._on_ui_click),
                ("<Return>",               self._on_activate_key),
                ("<space>",                self._on_activate_key),
                ("<<ComboboxSelected>>",   self._on_combo),
                ("<FocusIn>",              self._on_focus),
                ("<Map>",                  self._on_window_event),
                ("<Unmap>",                self._on_window_event),
                ("<Visibility>",           self._on_window_event),
                ("<Destroy>",              self._on_window_event),
                ("<Configure>",            self._on_configure),
                ("<<ThemeChanged>>",       self._on_theme_event),
                ("<MouseWheel>",           self._on_scroll_event),
                ("<Button-4>",             self._on_scroll_event),
                ("<Button-5>",             self._on_scroll_event),
            )
            for seq, handler in binds:
                try:
                    app.bind_all(seq, handler, add="+")
                except Exception:
                    continue
            self._ui_installed = True
            self._bind_ultra(bool(self._setting("ultra")))
        except Exception:
            self._ui_installed = False

    def _bind_ultra(self, on: bool) -> None:
        """
        Bind/avbind ultra-händelser (tangenter, musrörelse, hover) (W3).

        Avbindning sker med bind_all(seq, None) vilket bara tar bort
        bind_all-nivån - widget-specifika bindningar påverkas inte.
        """
        app = self.app
        if not (app and hasattr(app, "bind_all")):
            return
        seqs = (("<Key>",    self._on_ui_key),
                ("<Motion>", self._on_ui_motion),
                ("<Enter>",  self._on_hover),
                ("<Leave>",  self._on_hover))
        try:
            for seq, handler in seqs:
                if on:
                    app.bind_all(seq, handler, add="+")
                else:
                    app.bind_all(seq, None)
            self._ultra_bound = bool(on)
        except Exception:
            pass

    def _throttled(self, key: str, ms: int) -> bool:
        """True om `key` inträffade för mindre än ms sedan (W3-throttle)."""
        now = time.monotonic() * 1000.0
        last = self._throttles.get(key, 0.0)
        if now - last < ms:
            return True
        self._throttles[key] = now
        return False

    def _widget_label(self, w) -> str:
        """Returnera text/etikett for en widget, eller tom strang."""
        if w is None:
            return ""
        for opt in ("text", "label"):
            try:
                if hasattr(w, "cget"):
                    v = w.cget(opt)
                    if v:
                        return str(v)[:60]
            except Exception:
                continue
        return ""

    def _widget_class(self, w) -> str:
        """Widgetklass som sträng (tom vid fel)."""
        try:
            return str(w.winfo_class())
        except Exception:
            return ""

    def _widget_id(self, w) -> str:
        """Kort igenkänning: Klass!etikett (används i throttle-nycklar)."""
        label = self._widget_label(w)
        return "%s!%s" % (self._widget_class(w), label[:24])

    def _is_toplevel(self, w) -> bool:
        """True om widgeten är ett eget fönster (Tk/Toplevel)."""
        try:
            return bool(w) and w.winfo_toplevel() is w
        except Exception:
            return False

    def _on_tab_changed(self, event) -> None:
        """Logga flikbyte (ttk.Notebook)."""
        try:
            w = getattr(event, "widget", None)
            if w is None:
                return
            sel = w.select()
            label = w.tab(sel, "text") if sel else ""
            self._dedupe_ui("FLIK", label or "?")
        except Exception:
            pass

    def _on_ui_click(self, event) -> None:
        """
        Logga klick på interaktiva widgets (vänster = KLICK, höger = MENY).

        Filtrerar till knapp-/meny-/check-/combobox-/listbox-widgets så att
        inte varje musklick var som helst loggas (W3).
        """
        try:
            w = getattr(event, "widget", None)
            if w is None:
                return
            wclass = self._widget_class(w)
            action = "HÖGERKLICK" if getattr(event, "num", 1) == 3 else "KLICK"
            if wclass == "Menu":
                label = ""
                try:
                    label = w.entrycget(w.index("active"), "label")
                except Exception:
                    label = ""
                self._dedupe_ui("MENYVAL", label or "meny")
                return
            if not any(k in wclass for k in self.INTERACTIVE):
                return
            label = self._widget_label(w)
            detail = "%s [%s]" % (label or wclass, wclass)
            if any(k in wclass for k in ("Checkbutton", "Radiobutton")):
                try:
                    detail += " = %s" % w.var.get() if hasattr(w, "var") else ""
                except Exception:
                    pass
            self._dedupe_ui(action, detail)
        except Exception:
            pass

    def _on_activate_key(self, event) -> None:
        """Logga tangentaktivering (Return/Space) på knappar (W3)."""
        try:
            w = getattr(event, "widget", None)
            wclass = self._widget_class(w)
            if wclass not in ("Button", "TButton", "Checkbutton",
                              "TCheckbutton", "Radiobutton", "TRadiobutton"):
                return
            keysym = getattr(event, "keysym", "?")
            self._dedupe_ui("TANGENT", "%s -> %s [%s]"
                            % (keysym, self._widget_label(w) or wclass, wclass))
        except Exception:
            pass

    def _on_ui_key(self, event) -> None:
        """
        ULTRA: logga tangenter (W3) - ALDRIG innehåll i inmatningsfält.

        * Kontrolltangenter (Return/Tab/Escape/pil/Ctrl+X) loggas med namn.
        * I Entry/Text/Combobox loggas endast antal tecken per sekundintervall,
          aldrig tecknen - lösenord och FTP-uppgifter hamnar inte i loggen.
        """
        try:
            w = getattr(event, "widget", None)
            wclass = self._widget_class(w)
            keysym = str(getattr(event, "keysym", ""))
            state = int(getattr(event, "state", 0) or 0)
            combo = bool(state & 0x4) or bool(state & 0x8)   # Ctrl/Alt

            if wclass in self.TEXT_ENTRY:
                if keysym in ("Return", "Tab", "Escape", "KP_Enter"):
                    self._dedupe_ui("TANGENT", "%s i %s [%s]"
                                    % (keysym, self._widget_id(w), wclass))
                    return
                if len(keysym) == 1 and not combo:
                    wid = self._widget_id(w)
                    self._key_counts[wid] = self._key_counts.get(wid, 0) + 1
                    if self._throttled("keycount" + wid, 3000):
                        return
                    self.log_ui("TANGENT", "%d tecken skrivna i %s "
                                "(innehåll loggas ej)"
                                % (self._key_counts[wid], wid))
                    self._key_counts[wid] = 0
                    return
            if len(keysym) == 1 and not combo:
                return                      # enstaka bokstav utanför fält
            self._dedupe_ui("TANGENT", "%s%s [%s]"
                            % ("Ctrl+" if combo else "", keysym, wclass or "?"))
        except Exception:
            pass

    def _on_ui_motion(self, event) -> None:
        """ULTRA: musrörelse, throttlat (W3)."""
        try:
            if self._throttled("motion", self.THROTTLE_MOTION):
                return
            w = getattr(event, "widget", None)
            self.log_ui("MUS", "position %s,%s över %s"
                        % (getattr(event, "x_root", "?"),
                           getattr(event, "y_root", "?"),
                           self._widget_id(w)))
        except Exception:
            pass

    def _on_hover(self, event) -> None:
        """ULTRA: hover in/ut, throttlat per widget (W3)."""
        try:
            w = getattr(event, "widget", None)
            wid = self._widget_id(w)
            if self._throttled("hover" + wid, self.THROTTLE_HOVER):
                return
            self.log_ui("HOVER", "%s %s" % (event.type.name
                                            if hasattr(event.type, "name")
                                            else "in/ut", wid))
        except Exception:
            pass

    def _on_combo(self, event) -> None:
        """Logga combobox-val med det nya värdet (W3)."""
        try:
            w = getattr(event, "widget", None)
            value = ""
            try:
                value = str(w.get())[:60]
            except Exception:
                value = ""
            self._dedupe_ui("VAL", "%s = %s" % (self._widget_id(w), value))
        except Exception:
            pass

    def _on_focus(self, event) -> None:
        """Logga fokus på interaktiv widget (W3, throttlat per widget)."""
        try:
            w = getattr(event, "widget", None)
            wclass = self._widget_class(w)
            if not any(k in wclass for k in self.INTERACTIVE + self.TEXT_ENTRY):
                return
            wid = self._widget_id(w)
            if self._throttled("focus" + wid, self.UI_DEDUPE_MS):
                return
            self.log_ui("FOKUS", wid)
        except Exception:
            pass

    def _on_window_event(self, event) -> None:
        """
        Logga fönsterlivscykel: Map/Unmap/Visibility/Destroy (U3/W3).

        Endast for riktiga fonster (Tk/Toplevel), inte varje barnwidget.
        Destroy dar widgeten fortfarande lever ar falsk (bind_all pa
        vissa Tk-versioner) - hoppas over. Map/Unmap/Visibility
        throttlas sa flikbyte inte spammar.
        """
        try:
            w = getattr(event, "widget", None)
            if not self._is_toplevel(w):
                return
            typ = getattr(event, "type", "?")
            name = getattr(typ, "name", str(typ))
            if name == "Destroy":
                try:
                    if w.winfo_exists():
                        return
                except Exception:
                    return
            elif self._throttled("win-" + name, 800):
                return
            state = "?"
            try:
                state = w.state()
            except Exception:
                pass
            self.log_lifecycle("fönster-%s" % name,
                               "%s state=%s" % (self._window_title(w), state))
        except Exception:
            pass

    def _window_title(self, w) -> str:
        """Fönstrets titel (kort, utan sökvägar)."""
        try:
            return str(w.wm_title())[:60] or "utannamn"
        except Exception:
            return "?"

    def _on_configure(self, event) -> None:
        """Logga rotfönstrets storleksändring, throttlat (W3/W5)."""
        try:
            w = getattr(event, "widget", None)
            if not self.app or w is not self.app:
                return
            if self._throttled("configure-root", self.THROTTLE_CONFIGURE):
                return
            geo = ""
            try:
                geo = w.geometry()
            except Exception:
                pass
            self.log_lifecycle("fönster-storlek", geo)
            self._update_info_bar()
        except Exception:
            pass

    def _on_theme_event(self, event=None) -> None:
        """Logga temabyte (<<ThemeChanged>>) med nytt tema (W3).

        bind_all gor att VARJE widget far eventet vid ett enda
        theme_use(). Utan dedupe blev det hundratals rader
        'temabyte | tema=dark' foljt av 'tema=light' vid start.
        Logga bara nar temat faktiskt andras.
        """
        try:
            tema = "?"
            engine = getattr(self.app, "theme_engine", None)
            if engine is not None:
                tema = str(getattr(engine, "current_theme", "?"))
            last = getattr(self, "_last_tema", None)
            if last == tema:
                return
            self._last_tema = tema
            self.log_lifecycle("temabyte", "tema=%s" % tema)
        except Exception:
            pass

    def _on_scroll_event(self, event) -> None:
        """Logga scrollriktning, throttlat (W3)."""
        try:
            if self._throttled("scroll", self.THROTTLE_SCROLL):
                return
            w = getattr(event, "widget", None)
            delta = getattr(event, "delta", 0) or 0
            riktning = "upp" if delta > 0 else ("ner" if delta < 0 else "?")
            if getattr(event, "num", 0) == 4:
                riktning = "upp"
            elif getattr(event, "num", 0) == 5:
                riktning = "ner"
            self.log_ui("SCROLL", "%s i %s" % (riktning, self._widget_id(w)))
        except Exception:
            pass

    def _dedupe_ui(self, action: str, detail: str) -> None:
        """
        Deduplicera snabba identiska UI-handelser (en klick = en rad).

        Hoppar bara om exakt samma handling intraffade inom UI_DEDUPE_MS.
        """
        key = "%s|%s" % (action, detail)
        now = time.monotonic() * 1000.0
        if key == self._last_ui_key and (now - self._last_ui_ms) < self.UI_DEDUPE_MS:
            return
        self._last_ui_key = key
        self._last_ui_ms  = now
        self.log_ui(action, detail)


class DiagWindowMixin(object):
    """AI-felsokningsfonstret (W6/W8): visa/kopiera/spara/stanga."""

    def _diag_from_ui(self, *_args) -> None:
        """Knapp/kortkommando: kör felsökning och visa fönster."""
        try:
            self.run_diagnostics(show=True, source="manuell")
        except Exception as exc:
            self.log("FEL", "Diagnostik misslyckades: %s" % exc)

    def _open_diag_window(self, report: dict) -> None:
        """
        Visa rapporten i ett eget fönster (W8).

        Anpassas till skärmen (T6): bredd från teckenbredd, höjd max 70 %
        av skärmen, alltid centrerat. Färgkodat allvar per rad.
        """
        text = report.get("text", "")
        worst = report.get("worst", 1)
        try:
            if self._diag_win is not None and self.widget_exists(self._diag_win):
                self._diag_win.deiconify()
                self._diag_win.lift()
                self._set_diag_text(text, worst)
                return
            if self.app is None:
                return
            win = tk.Toplevel(self.app)
            self._diag_win = win
            win.title("AI-felsökning - Gallery Uploader (%s)"
                      % ALLVAR_TEXT.get(worst, "?"))
            win.configure(bg=self.COLOR_BG)
            try:
                win.transient(self.app)
            except Exception:
                pass
            width, height, x, y = fit_window(
                readable_width(self.app, 96, self._effective_font_size()),
                int(_screen_height(self.app) * 0.72) or 560,
                self.app,
            )
            win.geometry("%dx%d+%d+%d" % (width, height, x, y))
            win.minsize(420, 260)

            head = tk.Frame(win, bg=self.COLOR_BG_MID)
            head.pack(fill=tk.X)
            tk.Label(
                head,
                text="AI-FELSÖKNING  •  allvar: %s  •  %s"
                     % (ALLVAR_TEXT.get(worst, "?"),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                bg=self.COLOR_BG_MID, fg=self.COLOR_FG,
                font=("Segoe UI", self._effective_font_size(), "bold"),
                anchor="w", padx=10, pady=6,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

            bar = tk.Frame(win, bg=self.COLOR_BG_MID)
            bar.pack(fill=tk.X, padx=8, pady=(0, 6))
            for label, cmd, color in (
                ("Uppdatera", self._diag_from_ui, self.COLOR_BTN_DEFAULT),
                ("Kopiera till AI-chatt", self._copy_chat, self.COLOR_BTN_BLUE),
                ("Spara som...", self._save_diag_as, self.COLOR_BTN_DEFAULT),
                ("Rätta fönsterposition", self._fix_geometry,
                 self.COLOR_BTN_DEFAULT),
                ("Öppna loggmapp", self.open_logs_folder, self.COLOR_BTN_GRAY),
                ("Stäng", win.destroy, self.COLOR_BTN_GRAY),
            ):
                self._make_btn(bar, label, cmd, color)

            body = tk.Frame(win, bg=self.COLOR_BG)
            body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
            vbar = ttk.Scrollbar(body, orient=tk.VERTICAL)
            vbar.pack(side=tk.RIGHT, fill=tk.Y)
            self._diag_text = tk.Text(
                body, bg=self.COLOR_BG, fg=self.COLOR_FG,
                font=("Consolas", self._effective_font_size()),
                wrap=tk.WORD, relief=tk.FLAT, state=tk.DISABLED,
                yscrollcommand=vbar.set, padx=8, pady=6,
                selectbackground=self.COLOR_SELECT,
            )
            self._diag_text.pack(fill=tk.BOTH, expand=True)
            vbar.config(command=self._diag_text.yview)
            for tag, color in (("FEL", self.TAG_COLORS["FEL"]),
                               ("VARN", self.TAG_COLORS["VARNING"]),
                               ("OK", self.TAG_COLORS["OK"]),
                               ("INFO", self.TAG_COLORS["INFO"]),
                               ("RUBRIK", self.TAG_COLORS["SYSTEM"]),
                               ("CHATT", self.TAG_COLORS["DIAG"])):
                self._diag_text.tag_configure(tag, foreground=color)
            self._diag_text.tag_configure(
                "RUBRIK", font=("Consolas", self._effective_font_size(),
                                "bold"))
            self._set_diag_text(text, worst)
            win.protocol("WM_DELETE_WINDOW", self._close_diag)
            win.bind("<Control-d>", lambda e: self._diag_from_ui())
            win.bind("<Escape>", lambda e: self._close_diag())
        except Exception as exc:
            self.log("FEL", "Kunde inte öppna diagnostikfönster: %s" % exc)
            self.log("DEBUG", traceback.format_exc())

    def _set_diag_text(self, text: str, worst: int = 1) -> None:
        """Fyll diagnostikfönstret med färgkodad text (W8)."""
        if not self.widget_exists(self._diag_text):
            return
        try:
            self._diag_text.config(state=tk.NORMAL)
            self._diag_text.delete("1.0", tk.END)
            for line in str(text).splitlines():
                tag = None
                if line.startswith("===") or line.startswith("---"):
                    tag = "RUBRIK"
                elif line.startswith(("1.", "2.", "3.", "4.", "5.", "AI-CHATT",
                                      "NÄSTA STEG")):
                    tag = "RUBRIK"
                elif "[FEL]" in line or "KRITISKT" in line or "ALLVARLIGT" in line:
                    tag = "FEL"
                elif "[VARN]" in line or "MEDEL" in line:
                    tag = "VARN"
                elif "[OK]" in line:
                    tag = "OK"
                elif line.startswith(("  Du:", "  AI:", "Du:", "AI:")):
                    tag = "CHATT"
                elif "[INFO]" in line or "[?]" in line:
                    tag = "INFO"
                self._diag_text.insert(tk.END, line + "\n",
                                       tag if tag else ())
            self._diag_text.config(state=tk.DISABLED)
            self._diag_text.see("1.0")
        except tk.TclError:
            pass

    def _close_diag(self) -> None:
        """Stäng diagnostikfönstret (W8)."""
        try:
            if self._diag_win is not None:
                self._diag_win.destroy()
        except Exception:
            pass
        self._diag_win = None
        self._diag_text = None

    def _copy_chat(self) -> None:
        """
        Kopiera rapporten i chatt-format (W8).

        Texten inleds med en instruktionsrad så att valfri AI-chatt direkt
        förstår sammanhanget - precis det användaren klistrar in.
        """
        try:
            body = self._last_report or ""
            payload = (
                "Jag klistrar in en automatisk felsökningsrapport från "
                "Gallery Uploader (Python/tkinter, Windows).\n"
                "Svara på svenska: 1) mest allvarliga felet, 2) exakt vad "
                "jag ska ändra (fil + rad), 3) hur jag verifierar.\n\n"
                "%s" % body
            )
            self.app.clipboard_clear()
            self.app.clipboard_append(payload)
            self.log("OK", "Diagnostikrapport kopierad för AI-chatt "
                           "(%d tecken)" % len(payload))
            messagebox.showinfo(
                "Kopierad",
                "Rapporten är kopierad (%d tecken).\n\nKlistra in i valfri "
                "AI-chatt eller i supportärendet." % len(payload),
            )
        except Exception as exc:
            self.log("FEL", "Kunde inte kopiera rapport: %s" % exc)

    def _save_diag_as(self) -> None:
        """Spara diagnostikrapporten som valfri fil (W9)."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Textfil", "*.txt"), ("Alla filer", "*.*")],
            initialfile="diagnostik_%s.txt"
                        % datetime.now().strftime("%Y%m%d_%H%M%S"),
            initialdir=self.logs_dir,
        )
        if not filename:
            return
        try:
            Path(filename).write_text(self._last_report or "",
                                      encoding="utf-8")
            self.log("OK", "Diagnostikrapport sparad: %s" % filename)
        except Exception as exc:
            self.log("FEL", "Kunde inte spara rapport: %s" % exc)

# ============================================================
# Y4. SYMTOMGUIDE - tydlig AI-chatt via valbara symtom
# ============================================================

# ============================================================
# SYMTOMGUIDE (Y4) - tydlig AI-chatt via valbara symtom
# ============================================================

SYMPTOM_GUIDE = (
    {"id": "fonster_syns_inte",
     "fraga": "Fonstret syns inte / ar tomt",
     "svar": "Oppna Loggvisare -> Felsok (AI). Se sektion 1 i rapporten: "
             "den visar exakt varfor (state, geometri utanfor skarmen, "
             "systray, start_minimized). Atgard: 'Ratta fonsterposition'."},
    {"id": "plugin_saknas",
     "fraga": "En flik/plugin saknas eller ar tom",
     "svar": "Sok 'init-fel' i logs/errors_*.log. Trolig orsak: "
             "namnkollision (BUG-024) eller saknat beroende. "
             "Reglerna NAME-SHADOW och PLUGIN-INIT nedan matchar da."},
    {"id": "krasch",
     "fraga": "Appen kraschar / stangs",
     "svar": "Se TK-CALLBACK / THREAD-CRASH / WINERROR6 i rapporten. "
             "Fullt traceback finns i logs/errors_*.log precis under felet."},
    {"id": "upload_fail",
     "fraga": "FTP-uppladdning misslyckas",
     "svar": "Reglerna FTP och PERMISSION. Kontrollera ftp_settings i "
             "config/ samt att utdata-mappen ar skrivbar."},
    {"id": "seg",
     "fraga": "Appen ar seg / fryser",
     "svar": "Titta pa RECURSION/MEMORY i rapporten och mangden "
             "UI-handelser i loggen. Overvag att stanga av Ultra-fangst."},
    {"id": "inga_bilder",
     "fraga": "Inga bilder visas / gallaret ar tomt",
     "svar": "Kontrollera att en mapp ar vald och att den innehaller "
             "bildfiler. SOK 'gallery_images' i loggen for att se "
             "hur manga bilder som hittades."},
)


def guide_answers(selected_ids, window=None, findings=None):
    """
    Bygg ett chatt-svar for valda symtom (Y4).

    Parametrar:
        selected_ids: lista av SYMPTOM_GUIDE-idn som anvandaren bockat i
        window/findings: for att vikt anpassade pekar
    Returnerar: textblock (strang) att visa/kopiera.
    """
    rows = ["AI-CHATT - SYMTOMGUIDE", "-" * 40]
    ids = set(selected_ids or [])
    picked = [s for s in SYMPTOM_GUIDE if s["id"] in ids]
    if not picked:
        rows.append("Inget symtom valt. Bocka i ett eller flera ovan.")
        return "\n".join(rows)
    finding_ids = set(f["id"] for f in (findings or []))
    for s in picked:
        rows.append("")
        rows.append("Du : %s" % s["fraga"])
        rows.append("AI : %s" % s["svar"])
    if window:
        rows.append("")
        rows.append("AI : Fönsterstatus just nu: %s"
                    % window.get("verdict", UNKNOWN))
    if finding_ids:
        rows.append("AI : Matchade felmonster i din logg: %s"
                    % ", ".join(sorted(finding_ids)))
    rows.append("")
    rows.append("AI : Klistra in hela diagnostikrapporten (knappen "
                "'Kopiera till AI-chatt') for en djupare analys.")
    return "\n".join(rows)




# ============================================================
# Y2/Y3/Y5. LogLiveMixin - digest, felnavigation, fonstervakt
# ============================================================

class LogLiveMixin(object):
    """
    Levande logg (Y2/Y3/Y5): handelsesammanfattning per minut,
    fel-nagivation och lopande fonstervakt. Mixas in i AdvancedLogger.
    """

    #: Handelsehinkar for digest (okand action -> "ovrigt")
    _DIGEST_KEYS = ("KLICK", "HÖGERKLICK", "TANGENT", "VAL", "FLIK",
                    "MENYVAL", "SCROLL", "FOKUS", "MUS", "HOVER",
                    "LIVSCYKEL")

    def _bump_event(self, action):
        """Rakna en UI-/livscykelhandelse for digesten (Y2)."""
        try:
            key = action if action in self._DIGEST_KEYS else "ovrigt"
            counts = getattr(self, "_event_counts", None)
            if counts is None:
                counts = self._event_counts = {}
            counts[key] = counts.get(key, 0) + 1
        except Exception:
            pass

    def _digest_tick(self):
        """
        Sammanfatta handelserna sedan forega tick till EN loggrad (Y2).

        "Loggning av precis allt" utan att dranka loggen: detaljraderna
        finns dar, plus en minutsumma som gar att lasa i farten.
        """
        if not getattr(self, "is_active", False):
            return
        try:
            counts = getattr(self, "_event_counts", None) or {}
            total = sum(counts.values())
            if total > 0:
                parts = ", ".join(
                    "%d %s" % (v, k.lower())
                    for k, v in sorted(counts.items(),
                                       key=lambda kv: -kv[1])[:6]
                )
                self.log("SYSTEM",
                         "HÄNDELSER (%d s): %d st - %s"
                         % (self.DIGEST_MS // 1000, total, parts))
            self._event_counts = {}
        except Exception:
            pass
        try:
            self.safe_after(self.DIGEST_MS, self._digest_tick)
        except Exception:
            pass

    def _goto_error(self, direction=1):
        """
        Hoppa till nasta/foregaende FEL-rad i loggrutan (Y3).

        direction=1 framat, -1 bakat. Wrap-around vid filslut.
        """
        if not self.widget_exists(getattr(self, "log_text", None)):
            return
        try:
            txt = self.log_text
            if direction > 0:
                pos = txt.search("[FEL", "insert", stopindex=tk.END,
                                 forwards=True)
                if not pos:
                    pos = txt.search("[FEL", "1.0", stopindex=tk.END,
                                     forwards=True)
            else:
                pos = txt.search("[FEL", "insert linestart",
                                 stopindex="1.0", backwards=True)
                if not pos:
                    pos = txt.search("[FEL", tk.END, stopindex="1.0",
                                     backwards=True)
            if not pos:
                self.log("INFO", "Fel-navigering: inga FEL-rader i visningen")
                return
            txt.mark_set("insert", pos)
            txt.see(pos)
            line = pos.split(".")[0]
            txt.tag_remove("NAV", "1.0", tk.END)
            txt.tag_add("NAV", "%s.0" % line, "%s.0 lineend" % line)
            self._goto_count = getattr(self, "_goto_count", 0) + 1
        except Exception:
            pass

    def _toggle_follow_errors(self):
        """Folj senaste fel: auto-scrolla vid nya FEL (Y3)."""
        try:
            on = bool(self.follow_var.get()) if getattr(
                self, "follow_var", None) else False
            self._follow_errors = on
            self._settings["follow_errors"] = on
            self._save_settings()
            self.log("INFO", "Folj senaste fel: %s" % ("pa" if on else "av"))
        except Exception:
            pass

    def _visibility_watchdog(self):
        """
        Lopande fonstervakt (Y5): jamfor fönsterlage var 5:e minut.

        Loggar BARA vid forandring (annars tyst), och slar larm vid
        allvarlig avvikelse (severity >= 4) - "varfor syns inte
        fonstret" besvaras da lopande, inte bara vid start.
        """
        if not getattr(self, "is_active", False):
            return
        try:
            app = getattr(self, "app", None)
            if app is not None:
                rep = window_report(app, {}, self.logs_dir, [], [])
                data = rep.get("data", {})
                key = "%s|%s|%s" % (data.get("state"), data.get("mapped"),
                                    data.get("on_screen"))
                last = getattr(self, "_last_watch_key", None)
                if last is not None and key != last:
                    self.log_lifecycle(
                        "fonster-vakt",
                        "lage andrat: %s -> %s | %s"
                        % (last, key, rep.get("verdict", "?")))
                    if int(data.get("severity", 1)) >= 4:
                        self.log("VARNING", "FÖNSTERVAKT: %s"
                                 % rep.get("verdict", "?"))
                self._last_watch_key = key
        except Exception:
            pass
        try:
            self.safe_after(self.WATCHDOG_MS, self._visibility_watchdog)
        except Exception:
            pass




    # -- Y1: context-observator ---------------------------------


    def _install_context_observer(self, app) -> None:
        """
        Wrappa app.context i ContextObserver (Y1).

        Varje nyckel som satts/andras/tas bort loggas (CONTEXT-niva,
        throttle per nyckel - varden loggas ALDRIG). Installeras EN gang
        per app-instans; kan inte krascha appen.
        """
        try:
            if getattr(self, "_context_wrapped", False):
                return
            if getattr(app, "_al_ctx_wrapped", False):
                self._context_wrapped = True
                return
            current = getattr(app, "context", None)
            if isinstance(current, ContextObserver):
                self._context_wrapped = True
                return
            obs = ContextObserver(current if isinstance(current, dict)
                                  else None, logger=self)
            app.context = obs
            try:
                app._al_ctx_wrapped = True
            except Exception:
                pass
            self._context_wrapped = True
            self.log("SYSTEM", "Context-observator aktiv: alla "
                               "context-skrivningar loggas (Y1)")
        except Exception:
            self._context_wrapped = False

    def _rewrap_context(self, app) -> None:
        """
        Wrappa om context om run_pipeline bytte ut den mot en ny dict (Y1).

        anropas fran den lindade run_pipeline efter varje korning.
        """
        try:
            ctx = getattr(app, "context", None)
            if isinstance(ctx, dict) and not isinstance(ctx, ContextObserver):
                app.context = ContextObserver(ctx, logger=self)
                self.log("DEBUG", "Context utbytt av pipeline - "
                                  "observatorn wrappades om (Y1)")
        except Exception:
            pass

    # ==========================================================================

    # -- Y7: sessionsdiff i rapporten ---------------------------

    def _session_diff_block(self, entries) -> str:
        """
        Rapportblock: fel i denna session mot foregaende session (Y7).

        "NYA" = fel som inte fanns i forra gallery-loggen (borstas forst),
        "ATERKOMMANDE" = kanda fel som hanger kvar. Tom strang vid fel
        eller om det inte finns nagon tidigare session att jamfora med.
        """
        try:
            current = self.log_file_path.name if self.log_file_path else None
            info = session_diff(self.logs_dir, current_name=current)
            prev_set = info.get("_prev_set")
            if not info or not prev_set:
                return ""
            nya, ater = diff_current(entries, prev_set)
            if not nya and not ater:
                return ""
            width = 78
            rows = ["", "5. SESSIONSDIFF - MOT %s (Y7)" % info.get("prev_file", "?"),
                    "-" * width]
            if nya:
                rows.append("  NYA FEL denna session (%d):" % len(nya))
                for n in nya:
                    rows.append("    + %s" % n)
            if ater:
                rows.append("  ATERKOMMANDE fran forra sessionen (%d):" % len(ater))
                for a in ater:
                    rows.append("    = %s" % a)
            return "\n".join(rows)
        except Exception:
            return ""


# ============================================================
# Y4. SymptomWindowMixin - symtomguide-fonstret
# ============================================================

class SymptomWindowMixin(object):
    """Symtomguide: bocka i symtom -> fa riktade AI-chatt-svar (Y4)."""

    def _open_symptom_window(self, *_args):
        """Oppna (eller fokusera) symtomguide-fonstret."""
        try:
            if self.widget_exists(getattr(self, "_sym_win", None)):
                self._sym_win.deiconify()
                self._sym_win.lift()
                return
            if getattr(self, "app", None) is None:
                return
            win = tk.Toplevel(self.app)
            self._sym_win = win
            win.title("AI-chatt - symtomguide")
            win.configure(bg=self.COLOR_BG)
            try:
                win.transient(self.app)
            except Exception:
                pass
            w, h, x, y = fit_window(580, 460, self.app)
            win.geometry("%dx%d+%d+%d" % (w, h, x, y))
            win.minsize(420, 300)

            tk.Label(
                win, text="VAD HAR HÄNT? Bocka i det som stammer:",
                bg=self.COLOR_BG_MID, fg=self.COLOR_FG,
                font=("Segoe UI", 10, "bold"), anchor="w", padx=10, pady=8,
            ).pack(fill=tk.X)

            box = tk.Frame(win, bg=self.COLOR_BG)
            box.pack(fill=tk.X, padx=10)
            self._sym_vars = {}
            for item in SYMPTOM_GUIDE:
                var = tk.BooleanVar(value=False)
                self._sym_vars[item["id"]] = var
                ttk.Checkbutton(box, text=item["fraga"], variable=var
                                ).pack(anchor="w", pady=1)

            bar = tk.Frame(win, bg=self.COLOR_BG)
            bar.pack(fill=tk.X, padx=10, pady=6)
            self._make_btn(bar, "Skapa svar", self._sym_generate,
                           self.COLOR_BTN_DIAG)
            self._make_btn(bar, "Kopiera svar", self._sym_copy,
                           self.COLOR_BTN_BLUE)
            self._make_btn(bar, "Stäng", win.destroy, self.COLOR_BTN_GRAY)

            self._sym_text = tk.Text(
                win, bg=self.COLOR_BG, fg=self.COLOR_FG,
                font=("Consolas", 9), wrap=tk.WORD, relief=tk.FLAT,
                state=tk.DISABLED, padx=8, pady=6,
                selectbackground=self.COLOR_SELECT,
            )
            self._sym_text.pack(fill=tk.BOTH, expand=True, padx=10,
                                pady=(0, 10))
            win.protocol("WM_DELETE_WINDOW", self._sym_close)
        except Exception as exc:
            self.log("FEL", "Kunde inte oppna symtomguide: %s" % exc)

    def _sym_generate(self):
        """Skapa svaret for de valda symtomen (mot farsk rapport)."""
        try:
            selected = [sid for sid, var in self._sym_vars.items()
                        if var.get()]
            report = self._build_report(source="symtomguide")
            answer = guide_answers(selected, report.get("window"),
                                   report.get("findings"))
            self._last_sym_answer = answer
            self.log("INFO", "Symtomguide: %d symtom valda" % len(selected))
            if not self.widget_exists(getattr(self, "_sym_text", None)):
                return
            self._sym_text.config(state=tk.NORMAL)
            self._sym_text.delete("1.0", tk.END)
            self._sym_text.insert(tk.END, answer + "\n")
            self._sym_text.config(state=tk.DISABLED)
            self._sym_text.see("1.0")
        except Exception as exc:
            self.log("FEL", "Symtomguide kunde inte skapa svar: %s" % exc)

    def _sym_copy(self):
        """Kopiera symtomguidens svar till urklipp (for AI-chatt)."""
        try:
            body = getattr(self, "_last_sym_answer", "") or ""
            if not body:
                self._sym_generate()
                body = getattr(self, "_last_sym_answer", "") or ""
            payload = ("Symtomguide fran Gallery Uploader (svar pa valda "
                       "symtom):\n\n%s" % body)
            self.app.clipboard_clear()
            self.app.clipboard_append(payload)
            self.log("OK", "Symtomguidens svar kopierat (%d tecken)"
                     % len(payload))
            messagebox.showinfo("Kopierad",
                                "Svaret ar kopierat - klistra in i valfri "
                                "AI-chatt.")
        except Exception as exc:
            self.log("FEL", "Kunde inte kopiera symtomsvaret: %s" % exc)

    def _sym_close(self):
        """Stang symtomguide-fonstret."""
        try:
            if getattr(self, "_sym_win", None) is not None:
                self._sym_win.destroy()
        except Exception:
            pass
        self._sym_win = None