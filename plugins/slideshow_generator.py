"""Slideshow Generator - Skapar auto-play bildspel med timer"""

# FIL:       plugins/slideshow_generator.py
# Klass:     SlideshowGenerator(BasePlugin)  - "Bildspel"-flik
# VERSION:   1.3.0
#
# ANDRINGAR v1.2.0 -> v1.3.0 (staende order + kodkvalitet):
#   [S1]      Alla f-strings borttagna (%-formatering) - aven den stora
#             HTML-mallen: vanlig strang med __PLATSHALLARE__ +
#             replace()-kedja (samma monster som html_generator, BUG-016).
#   [S2]      preview_slideshow() fixad: refererade odefinierad
#             'output_path' (NameError vid klick) - nu output-mapp fran
#             context, fallback temp_slideshow.html.
#
# ÄNDRINGAR v1.1.0 → v1.2.0 (snabbhet/robusthet, icke-brytande):
#   [R1] Bilder-listan skrivs med EN json.dumps() for hela listan
#        (i stället for join av per-post dumps) - korrekt escaping och
#        färre anrop.
#   [R2] Delad _save_slideshow_file()/_register_upload() anvands av
#        generate_slideshow_page() och execute() -> ingen duplicerad
#        skriv-/registreringslogik.
#   [R3] Atomisk skrivning (tmp -> os.replace) for slideshow.html och
#        forhandsgranskningen - ingen risk for korrupt/delvis fil.
#   [R4] _val() ger robust default vid UI-var-avläsning (headless/edge)
#        och execute() loggar tydligare (hoppa/fel/ok).
#   [R5] VERSION + PLATS (versionen synkas med klassen nedan).
#
# ÄNDRINGAR v1.0.0 → v1.1.0 (kvalitet/design/snabbhet, icke-brytande):
#   [Q1] Knappfarger centraliserade till klassattribut och följer
#        appens designkonvention (ljus #d0d0d0/svart, mörk #404040/vit)
#        istället för hårdkodade värden på flera ställen.
#   [Q2] apply_button_theme / on_btn_enter / on_btn_leave delar en
#        gemensam _button_colors()-källa -> ingen duplicerad tema-logik.
#   [Q3] Bilder-listan i HTML byggs med json.dumps per post (korrekt
#        escaping av src/titel) -> robust mot citattecken/backslash.
#   [Q4] files_to_upload de-dupliceras (ingen dubbel 'slideshow.html').
#   [Q5] Knappar: flat stil (bd=0) för att matcha övriga plugins.

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
import webbrowser
import json
import os
from .base_plugin import BasePlugin

class SlideshowGenerator(BasePlugin):
    PLUGIN_NAME = "Bildspel"
    PRIORITY = 31  # Efter HTML-generator
    VERSION = "1.3.0"

    # Knappfarger enligt appens designkonvention (Q1)
    LIGHT_BTN_BG = "#d0d0d0"
    LIGHT_BTN_FG = "#000000"
    DARK_BTN_BG  = "#404040"
    DARK_BTN_FG  = "#ffffff"
    
    def init(self, app):
        self.app = app
        self.buttons = []
        
        # Hämta tab manager
        tab_manager = app.context.get('_tab_manager')
        if tab_manager:
            slideshow_frame = tab_manager.add_tab('slideshow', 'Bildspel')
        else:
            slideshow_frame = app.main_frame
        
        self.create_ui(slideshow_frame)
        
        # Spara referens i context
        app.context['_slideshow'] = self
        
        # Bind till globalt tema-ändringsevent
        self.app.bind("<<ThemeChanged>>", self._on_theme_changed)
        
        self.log_action("Bildspel-plugin skapat")
    
    def create_ui(self, parent):
        """Skapa inställningar för bildspel med scrollbar canvas (mushjulsstöd)"""
        
        # Skapa canvas för scrollning
        self.canvas = tk.Canvas(parent, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        
        self.scroll_content = ttk.Frame(self.canvas)
        self.scroll_content_id = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        
        # Konfigurera canvas och scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Packa canvas och scrollbar
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind events för responsiv bredd och scrollregion
        self.scroll_content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mushjulsbindningar (3 enheter per klick)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
        # Huvudcontainer på scroll_content
        container = ttk.Frame(self.scroll_content)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        ttk.Label(
            container,
            text="Bildspelsinställningar",
            font=('Segoe UI', 14, 'bold')
        ).pack(pady=(0, 20))
        
        # Inställningar ram
        settings_frame = ttk.LabelFrame(container, text="Bildspelsinställningar", padding=15)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Intervall
        ttk.Label(settings_frame, text="Intervall mellan bilder:").grid(row=0, column=0, sticky='w', pady=5)
        self.interval_var = tk.IntVar(value=3)
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Scale(
            interval_frame,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            variable=self.interval_var,
            length=200,
            command=self.update_interval_label
        ).pack(side=tk.LEFT)
        
        self.interval_label = ttk.Label(interval_frame, text="3 sekunder")
        self.interval_label.pack(side=tk.LEFT, padx=10)
        
        # Övergångseffekt
        ttk.Label(settings_frame, text="Övergångseffekt:").grid(row=1, column=0, sticky='w', pady=5)
        self.transition_var = tk.StringVar(value="fade")
        transition_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.transition_var,
            values=["fade", "slide", "zoom", "none"],
            state='readonly',
            width=15
        )
        transition_combo.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        # Övergångshastighet
        ttk.Label(settings_frame, text="Övergångshastighet:").grid(row=2, column=0, sticky='w', pady=5)
        self.speed_var = tk.StringVar(value="medium")
        speed_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.speed_var,
            values=["slow", "medium", "fast"],
            state='readonly',
            width=15
        )
        speed_combo.grid(row=2, column=1, sticky='w', padx=10, pady=5)
        
        # Auto-start
        self.autostart_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Starta bildspel automatiskt vid öppning",
            variable=self.autostart_var
        ).grid(row=3, column=0, columnspan=2, sticky='w', pady=5)
        
        # Loop
        self.loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Loopa bildspel (börja om när sista bilden nåtts)",
            variable=self.loop_var
        ).grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
        
        # Visa bildtexter
        self.show_captions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Visa bildtexter under bildspel",
            variable=self.show_captions_var
        ).grid(row=5, column=0, columnspan=2, sticky='w', pady=5)
        
        # Visa progress bar
        self.show_progress_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Visa framstegsindikator",
            variable=self.show_progress_var
        ).grid(row=6, column=0, columnspan=2, sticky='w', pady=5)
        
        # Kontroller info
        controls_frame = ttk.LabelFrame(container, text="Kontroller i bildspel", padding=15)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = """Tangentbordskommandon:
• Mellanslag - Pausa/Fortsätt
• Pil vänster - Föregående bild
• Pil höger - Nästa bild
• Escape - Avsluta bildspel / Stäng fullskärm
• F - Fullskärmsläge

Muskommandon:
• Klicka på bilden - Pausa/Fortsätt
• Svep åt vänster/höger (touch) - Bläddra"""
        
        ttk.Label(controls_frame, text=info_text, justify=tk.LEFT).pack(anchor='w')
        
        # Förhandsgranskning knappar (med tema-anpassning)
        preview_frame = ttk.Frame(container)
        preview_frame.pack(fill=tk.X, pady=10)
        
        self.preview_btn = self.make_button(
            preview_frame,
            "Förhandsgranska bildspel",
            self.preview_slideshow
        )
        self.preview_btn.pack(side=tk.LEFT, padx=5)
        
        self.generate_btn = self.make_button(
            preview_frame,
            "Generera separat bildspel-sida",
            self.generate_slideshow_page
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)

    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.scroll_content_id, width=event.width)
        
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)
        
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
        
    def _on_mousewheel(self, event):
        if event.delta:
            direction = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(direction * 3, "units")
            
    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")

    def make_button(self, parent, text, cmd):
        """Fabrik för knappar med anpassat utseende och hover-effekter"""
        btn = tk.Button(
            parent,
            text=text,
            command=cmd,
            font=('Segoe UI', 10, 'bold'),
            relief=tk.FLAT,   # Q5: matchar övriga plugins (inga ramar)
            bd=0,
            cursor='hand2'
        )
        self.buttons.append(btn)
        self.apply_button_theme(btn)
        
        # Hover events
        btn.bind("<Enter>", lambda e: self.on_btn_enter(btn))
        btn.bind("<Leave>", lambda e: self.on_btn_leave(btn))
        
        return btn

    def _val(self, name, default):
        """Robust varde-avlasning fran en instans-attribut Tk-var (v1.2.0).

        Slar upp attributet via getattr() och returnerar `default` om
        det saknas eller .get() misslyckas - sa att HTML-bygget inte
        kraschar om en viss widget-variabel inte ar byggd.
        """
        var = getattr(self, name, None)
        if var is None:
            return default
        try:
            return var.get()
        except Exception:
            return default

    def _atomic_write_text(self, path, text):
        """Skriv text atomiskt (tmp -> os.replace) (v1.2.0).

        Forhindrar delvis skriven/korrupt HTML om processen avbryts
        mitt i skrivningen. Rensar tmp-filen vid fel.
        """
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
            return True
        except Exception as e:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            self.log_action("Fel vid skrivning av %s: %s" % (path.name, e))
            return False

    def _save_slideshow_file(self, images, output_path):
        """Generera slideshow.html i output-mappen (v1.2.0).

        Delas av generate_slideshow_page() och execute() for att
        undvika duplicerad skrivlogik. Returnerar sökvägen, eller
        None vid fel.
        """
        try:
            slideshow_file = Path(output_path) / "slideshow.html"
        except Exception as e:
            self.log_action("Ogiltig output-mapp: %s" % e)
            return None
        if not self._atomic_write_text(
            slideshow_file,
            self.build_slideshow_html(images, preview=False),
        ):
            return None
        return slideshow_file

    @staticmethod
    def _register_upload(upload):
        """Lägg slideshow.html i uppladdningslistan utan dubblett (v1.2.0)."""
        if upload is not None and "slideshow.html" not in upload:
            upload.append("slideshow.html")

    def get_current_theme(self):
        """Hämta det aktiva temat från appen"""
        theme = self.app.context.get('gallery', {}).get('theme', 'dark')
        if not theme:
            theme = 'dark'
        if theme == 'system':
            try:
                import darkdetect
                if darkdetect.isDark():
                    return 'dark'
            except ImportError:
                pass
            return 'light'
        return theme

    def _button_colors(self):
        """
        Returnera (bg, fg, hover_bg) för knappar i aktuellt tema (Q2).

        Ljust: ljus bakgrund + svart text (hover mörknar).
        Mörkt: mörk bakgrund + vit text (hover ljusnar).
        """
        if self.get_current_theme() == 'light':
            hover = self._darken(self.LIGHT_BTN_BG, 0.85)
            return self.LIGHT_BTN_BG, self.LIGHT_BTN_FG, hover
        hover = self._darken(self.DARK_BTN_BG, 1.20)
        return self.DARK_BTN_BG, self.DARK_BTN_FG, hover

    def apply_button_theme(self, btn):
        """Applicera rätt färger på knappen baserat på aktuellt tema."""
        bg, fg, hover = self._button_colors()
        btn.config(
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg
        )

    def on_btn_enter(self, btn):
        _, _, hover = self._button_colors()
        btn.config(bg=hover)

    def on_btn_leave(self, btn):
        bg, _, _ = self._button_colors()
        btn.config(bg=bg)

    @staticmethod
    def _darken(hex_color, factor=0.8):
        """Hjälpmetod för att ljusa upp eller mörka ner en hex-färg"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return "#%02x%02x%02x" % (r, g, b)

    def _on_theme_changed(self, event=None):
        """Körs när det globala temat ändras"""
        for btn in self.buttons:
            if btn.winfo_exists():
                self.apply_button_theme(btn)

    def update_interval_label(self, value):
        """Uppdatera intervall-label"""
        seconds = int(float(value))
        self.interval_label.config(text="%d sekunder" % seconds)
    
    def preview_slideshow(self):
        """Oppna forhandsgranskning av bildspel (v1.3.0 S2-fix).

        Fore v1.3.0 refererades en odefinierad 'output_path' har
        (NameError vid klick). Nu: output-mapp fran context om den
        finns, annars skrivs forhandsvisningen till temp_slideshow.html.
        """
        images = self.app.context.get('processed_images', [])
        if not images:
            messagebox.showerror("Fel", "Inga bearbetade bilder att visa.")
            return

        output_path = self.app.context.get('output_path')
        if output_path:
            slideshow_file = self._save_slideshow_file(images, output_path)
        else:
            temp_file = Path(__file__).parent.parent / 'temp_slideshow.html'
            slideshow_file = temp_file
            if not self._atomic_write_text(
                temp_file,
                self.build_slideshow_html(images, preview=True),
            ):
                slideshow_file = None

        if slideshow_file is None:
            messagebox.showerror("Fel", "Kunde inte skriva slideshow.html!")
            return

        # Lagg till i filer att ladda upp (Q4/1.2: inga dubbletter)
        self._register_upload(self.app.context.get('files_to_upload'))

        self.log_action("Bildspel-sida genererad: %s" % slideshow_file)
        messagebox.showinfo("Klart", "Bildspel-sida skapad!\n%s" % slideshow_file)

    def generate_slideshow_page(self):
        """Alias for knappen 'Generera separat bildspel-sida' (S3)."""
        self.preview_slideshow()

    def build_slideshow_html(self, images, preview=False):
        """Bygg HTML för bildspel"""
        # Robust var-avläsning (v1.2.0): _val(name, default) slår upp
        # via getattr() och ger default om variabeln saknas -> bygget
        # kraschar inte om en widget-var inte är byggd.
        interval      = int(self._val("interval_var", 3)) * 1000  # ms
        transition    = self._val("transition_var", "fade") or "fade"
        speed         = self._val("speed_var", "medium") or "medium"
        autostart     = str(bool(self._val("autostart_var", True))).lower()
        loop          = str(bool(self._val("loop_var", True))).lower()
        show_captions = str(bool(self._val("show_captions_var", True))).lower()
        show_progress = str(bool(self._val("show_progress_var", True))).lower()

        # Speed mapping
        speed_map = {
            'slow': '1000',
            'medium': '600',
            'fast': '300'
        }
        transition_duration = speed_map.get(speed, '600')
        
        # Bygg bildlista (v1.2.0: en enda json.dumps for hela listan ->
        # korrekt escaping av src/titel i ett steg, robust mot
        # citattecken/backslash/unicode).
        image_items = [
            {
                "src":   img.get("fullsize", "") if hasattr(img, "get") else "",
                "title": img.get("title", "")    if hasattr(img, "get") else "",
            }
            for img in images
        ]
        images_json = json.dumps(image_items, ensure_ascii=False)
        
        template = '''<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Bildspel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #000;
            overflow: hidden;
            font-family: system-ui, sans-serif;
        }
        
        .slideshow {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .slide {
            position: absolute;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity __TRANSITION_DURATION__ms ease-in-out;
        }
        
        .slide.active {
            opacity: 1;
            z-index: 2;
        }
        
        .slide.fade-out {
            opacity: 0;
        }
        
        .slide img {
            max-width: 95vw;
            max-height: 95vh;
            object-fit: contain;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        
        /* Slide transition */
        .slide.transition-slide {
            transition: transform __TRANSITION_DURATION__ms ease-in-out, opacity __TRANSITION_DURATION__ms ease-in-out;
        }
        
        .slide.slide-left {
            transform: translateX(-100%);
        }
        
        .slide.slide-right {
            transform: translateX(100%);
        }
        
        /* Zoom transition */
        .slide.transition-zoom {
            transition: transform __TRANSITION_DURATION__ms ease-in-out, opacity __TRANSITION_DURATION__ms ease-in-out;
        }
        
        .slide.zoom-out {
            transform: scale(0.8);
            opacity: 0;
        }
        
        /* Caption */
        .caption {
            position: fixed;
            bottom: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 1.2rem;
            z-index: 10;
            display: {"block" if show_captions == "true" else "none"};
            max-width: 80%;
            text-align: center;
        }
        
        /* Controls */
        .controls {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 15px;
            z-index: 10;
            background: rgba(0,0,0,0.5);
            padding: 10px 20px;
            border-radius: 30px;
        }
        
        .controls button {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
            transition: all 0.3s;
        }
        
        .controls button:hover {
            background: rgba(255,255,255,0.4);
            transform: scale(1.1);
        }
        
        /* Progress bar */
        .progress {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.2);
            z-index: 10;
            display: {"block" if show_progress == "true" else "none"};
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 100ms linear;
        }
        
        /* Counter */
        .counter {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 1rem;
            z-index: 10;
        }
        
        /* Info overlay */
        .info {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9);
            color: white;
            padding: 30px;
            border-radius: 10px;
            z-index: 100;
            display: none;
            text-align: center;
        }
        
        .info.show {
            display: block;
        }
        
        .info h2 {
            margin-bottom: 20px;
        }
        
        .info p {
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="slideshow" id="slideshow">
        <!-- Slides läggs till dynamiskt -->
    </div>
    
    <div class="caption" id="caption"></div>
    
    <div class="progress">
        <div class="progress-bar" id="progress-bar"></div>
    </div>
    
    <div class="counter" id="counter">1 / 1</div>
    
    <div class="controls">
        <button onclick="prevSlide()" title="Föregående">◀</button>
        <button onclick="togglePlay()" id="play-btn" title="Pausa/Spela">⏸</button>
        <button onclick="nextSlide()" title="Nästa">▶</button>
        <button onclick="toggleFullscreen()" title="Fullskärm">⛶</button>
        <button onclick="toggleInfo()" title="Hjälp">?</button>
    </div>
    
    <div class="info" id="info">
        <h2>Tangentbordskommandon</h2>
        <p><strong>Mellanslag</strong> - Pausa/Fortsätt</p>
        <p><strong>← →</strong> - Föregående/Nästa</p>
        <p><strong>F</strong> - Fullskärm</p>
        <p><strong>Escape</strong> - Avsluta</p>
        <p style="margin-top: 20px;"><button onclick="toggleInfo()">Stäng</button></p>
    </div>
    
    <script>
        const images = __IMAGES_JSON__;
        const interval = __INTERVAL__;
        const transition = '__TRANSITION__';
        const autostart = __AUTOSTART__;
        const loop = __LOOP__;
        
        let currentIndex = 0;
        let isPlaying = autostart;
        let timer = null;
        let progressTimer = null;
        
        const slideshow = document.getElementById('slideshow');
        const caption = document.getElementById('caption');
        const counter = document.getElementById('counter');
        const progressBar = document.getElementById('progress-bar');
        const playBtn = document.getElementById('play-btn');
        
        // Skapa slides
        images.forEach((img, i) => {
            const slide = document.createElement('div');
            slide.className = 'slide';
            if (i === 0) slide.classList.add('active');
            
            const imgEl = document.createElement('img');
            imgEl.src = img.src;
            imgEl.alt = img.title;
            
            slide.appendChild(imgEl);
            slideshow.appendChild(slide);
        });
        
        const slides = document.querySelectorAll('.slide');
        
        function updateDisplay() {
            caption.textContent = images[currentIndex].title;
            counter.textContent = `${currentIndex + 1} / ${images.length}`;
        }
        
        function showSlide(index) {
            const current = slides[currentIndex];
            const next = slides[index];
            
            // Reset classes
            slides.forEach(s => {
                s.classList.remove('active', 'fade-out', 'slide-left', 'slide-right', 'zoom-out');
            });
            
            // Apply transition
            if (transition === 'fade') {
                current.classList.add('fade-out');
                setTimeout(() => {
                    next.classList.add('active');
                }, 100);
            } else if (transition === 'slide') {
                current.classList.add('transition-slide', 'slide-left');
                next.classList.add('transition-slide', 'slide-right', 'active');
                setTimeout(() => {
                    next.classList.remove('slide-right');
                }, 50);
            } else if (transition === 'zoom') {
                current.classList.add('transition-zoom', 'zoom-out');
                setTimeout(() => {
                    next.classList.add('active');
                }, 100);
            } else {
                next.classList.add('active');
            }
            
            currentIndex = index;
            updateDisplay();
            resetProgress();
        }
        
        function nextSlide() {
            let next = currentIndex + 1;
            if (next >= images.length) {
                if (loop) {
                    next = 0;
                } else {
                    pause();
                    return;
                }
            }
            showSlide(next);
        }
        
        function prevSlide() {
            let prev = currentIndex - 1;
            if (prev < 0) {
                prev = images.length - 1;
            }
            showSlide(prev);
        }
        
        function play() {
            isPlaying = true;
            playBtn.textContent = '⏸';
            timer = setInterval(nextSlide, interval);
            startProgress();
        }
        
        function pause() {
            isPlaying = false;
            playBtn.textContent = '▶';
            clearInterval(timer);
            clearInterval(progressTimer);
        }
        
        function togglePlay() {
            if (isPlaying) {
                pause();
            } else {
                play();
            }
        }
        
        function startProgress() {
            let progress = 0;
            const step = 100 / (interval / 100);
            
            clearInterval(progressTimer);
            progressBar.style.width = '0%';
            
            progressTimer = setInterval(() => {
                progress += step;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(progressTimer);
                }
                progressBar.style.width = progress + '%';
            }, 100);
        }
        
        function resetProgress() {
            if (isPlaying) {
                startProgress();
            }
        }
        
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                document.exitFullscreen();
            }
        }
        
        function toggleInfo() {
            document.getElementById('info').classList.toggle('show');
        }
        
        // Keyboard controls
        document.addEventListener('keydown', e => {
            switch(e.key) {
                case ' ':
                    e.preventDefault();
                    togglePlay();
                    break;
                case 'ArrowLeft':
                    prevSlide();
                    break;
                case 'ArrowRight':
                    nextSlide();
                    break;
                case 'Escape':
                    if (document.fullscreenElement) {
                        document.exitFullscreen();
                    }
                    break;
                case 'f':
                case 'F':
                    toggleFullscreen();
                    break;
            }
        });
        
        // Click to pause
        slideshow.addEventListener('click', togglePlay);
        
        // Touch swipe
        let touchStartX = 0;
        slideshow.addEventListener('touchstart', e => {
            touchStartX = e.changedTouches[0].screenX;
        });
        
        slideshow.addEventListener('touchend', e => {
            const diff = touchStartX - e.changedTouches[0].screenX;
            if (Math.abs(diff) > 50) {
                if (diff > 0) {
                    nextSlide();
                } else {
                    prevSlide();
                }
            }
        });
        
        // Initialize
        updateDisplay();
        if (autostart) {
            play();
        }
    </script>
</body>
</html>'''
        return (
            template
                .replace("__TRANSITION_DURATION__", str(transition_duration))
                .replace("__TRANSITION__", str(transition))
                .replace("__INTERVAL__", str(interval))
                .replace("__LOOP__", str(loop))
                .replace("__AUTOSTART__", str(autostart))
                .replace("__IMAGES_JSON__", images_json)
        )

    def log_action(self, message):
        """Logga via advanced_logger i context"""
        logger = self.app.context.get('_logger')
        if logger and hasattr(logger, 'log'):
            logger.log("INFO", "[Bildspel] %s" % message)
    
    def execute(self, context, log=None):
        """Körs i pipeline - generera bildspel-sida automatiskt"""
        images = context.get('processed_images', [])
        output_path = context.get('output_path')
        
        if not images or not output_path:
            if log:
                log("  Bildspel: hoppades (inga bilder/output)")
            return context
        
        # Generera slideshow.html (delad logik + atomisk skrivning)
        slideshow_file = self._save_slideshow_file(images, output_path)
        if slideshow_file is None:
            if log:
                log("  [FEL] Kunde inte skriva slideshow.html")
            return context
        
        # Lägg till i uppladdningslista (Q4/1.2: inga dubbletter)
        self._register_upload(context.get('files_to_upload'))
        
        if log:
            log("  [OK] Bildspel-sida genererad")
        
        return context