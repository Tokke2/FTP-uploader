Gallery Uploader
# ============================================================
# Gallery Uploader – KOMPLETT SPECIFIKATION (spec.md)
# ============================================================
# Version: 4.11.12
# Datum:   2026-09-22 (senaste session)
# Status:  Aktiv utveckling
# Projekt: ftp_gallery_uploader
# AI Compliance: 500%
#
# v4.11.12: Checklista avstamd mot kod: start/arkitektur (BUG-002,
#         single-instance, withdraw, tema, visa/dolj tabbar,
#         mushjul x3, FreeConsole/BUG-018, BUG-008b) + G1/G2
#         importera/lagg till/ta bort + FS-26 layout. FS-27
#         (menu_manager A/A/O) och PORT-1 kvar oppen.
# v4.11.11: Implementerat: systray EN ikon (main.pyw v2.8.1 +
#         system_tray v3.6.0); BUG-021 kant-auto-scroll
#         (image_sorter v4.3.0); FS-24 inkrementell HTML +
#         radera overblivna bilder/thumbs (html_generator v3.4.0).
# v4.11.10: Checklistan (avsnitt 21) utokad med godkannade forslag:
#         FS-24 inkrementell HTML + ta bort bilder anvandaren tar bort;
#         FS-26 DPI + fit_window pa historikdialog;
#         FS-27 A/A/O i dialogtexter (mixin + meny).
#         STAENDE: appen ska fungera efter flytt till ny disk; allt
#         (config/logs/out/historik) halls INOM appmappen; inga absoluta
#         diskbokstavs-sokvagar som bryts vid flytt (PORT-1).
# v4.11.9: FS-11 rensa doda historikposter (saknad index.html) nar
#         historiken oppnas. Ror ALDRIG filer i out/ - bara JSON.
#         Saknad sokvag pekas om till out/<namn>/ om index.html finns dar.
#         ui_settings_gallery.py v1.2.0 + mixin-import i ui_settings v2.7.1.
# v4.11.8: Historik for genererade gallerier (config/gallery_history.json).
#         Importera fran historik/index.html, lagg till/ta bort, generera om.
# v4.11.6: menu_manager.py v2.5.0 - idempotent menyrad vid plugin-reload,
#         bind add="+", macOS Command, genvagar hoppar over textfalt.
# v4.11.5: menu_manager.py v2.4.0 - text/fonster (DPI + fit_window), arvda
#         log/config/tema-dispatcher, minne (prune dialoger), snabbare
#         senaste-mappar/plugins-meny, Ctrl+G/R/F5.
# v4.11.4: HTML-generator v3.3.0 - inga videolankar under titeln (PDF kvar);
#         videokort far JPEG-thumbnails (ffmpeg/OpenCV) eller webblasar-ruta.
# v4.11.3: HTML-generator v3.2.2 (render_template pa klassen + versionsrad
#         i execute). Loggvisare v2.5.1: temabyte-dedupe, falsk Destroy
#         hoppas over, parse_geometry tar Windows +-N+-N (maximerat).
# v4.11.2: Disk komplett - advanced_logger_ui/diag + html_generator_css/js
#         finns pa disk. Inga saknade hjalpfiler. Inställningar, Loggvisare
#         och HTML-generator kan alla laddas.
# v4.11.1: Spec §2 synkad mot disk (anvandarens trad 2026-09-21):
#         icon/ komplett, app_icon.py, main_guards.py, config-filer,
#         out/hpm653 + mkt2014. plugins/ har advanced_logger_guards.py.
# v4.11.0: Kanonisk ikonmapp icon/ anvands OVERALLT (fonster,
#         aktivitetsfalt, systray). Ny app_icon.py: get_icon_path,
#         resolve_icon_file (icon/ sedan assets/), load_app_icon,
#         apply_tk_window_icon. Filer: icon.ico, icon.png,
#         icon_16/32/64/256.png. Fallback: generate_app_icon().
# v4.10.1: BUGFIX inställningsfliken saknades.
#   ui_settings v2.6.1: fliken skapas alltid (tab_manager, fallback
#   app.add_tab), väljs explicit, Arkiv → Inställningar (Ctrl+,),
#   titel med ä. tab_manager: Visa-menyn listar alla flikar,
#   DPI-säker flikhöjd, hide/show som faktiskt gömmer knappen.
#   main.pyw: tom notebook packas inte (stal ytan från tab_manager).
# v4.10.0: main.pyw v2.7.0 -> v2.8.0 (KOD/DESIGN/TEXT/FONSTER/MINNE/
#         SNABBHET-pass) + STAENDE ORDRAR KLARA.
#         [M1] Sista f-strangen i main.pyw borttagen (safe_write) -
#         main har nu 0 f-strangar/0 print.
#         [M2] MAINLOOP-VAKT (staende order klar): _safe_mainloop()
#         fangar KeyboardInterrupt/TclError/ovrigt, loggar i
#         startup.log, spar dubbel mainloop.
#         [M3] FONSTERLAGES-VAKTER (staende order klar): geometri
#         sparas bara i normal-lage, aldrig 0x0/iconified/withdrawn/
#         zoomed; _on_configure hoppar onormala lagen.
#         [M4] 1800-TAKET KLART: guard-/startup-logik flyttad till
#         NYA main_guards.py (safe_write, excepthook, autostart-
#         primitiv, cleanup_pycache) - aven latent bugg fixad
#         (excepthooken anropade log_startup_crash fore importen).
#         Dod kod borttagen (_autostart_is_enabled). main: 1849->1789.
#         [M5-M9] Design/robusthet: enklare except-tupler, init-tid
#         loggas, invalidate_caches vid reload, adaptiv startgeometri
#         (M8), mappar via BASE_DIR inte cwd (M9).
#         [S1/S2] STAENDE ORDER "fixa 10 f-strangar" KLAR:
#         slideshow_generator.py v1.2.0 -> v1.3.0 - alla 9 f-strangar
#         borttagna (HTML-mallen via __PLATSHALLARE__ + replace),
#         dessutom NameError i preview_slideshow() fixad (S2).
#         Verifierat: py_compile alla, 0 f-strangar/print i main +
#         slideshow, hel App-start under Xvfb (M2/M3/M6/M8 + A6
#         trigger + quit_app).
# v4.9.0: plugins/image_processor.py v2.2.0 -> v2.3.0
#         (MINNE/SNABBHET/KOD-pass).
#         [E1] load_settings/save_settings borttagna (~60 rader
#         duplikat) - config arvs fran base_plugin v1.4.1
#         (atomisk + .bak + korrupt-karantan).
#         [E2] _log()/_progress(): EN kalla for meddelanden, saker
#         wrapper, progress-% fixat ((index+1)/total).
#         [E3] MINNE: engangsnedskalning - thumbnail ur nedskalad
#         fullsize (inga img.copy() pa originalet), EXIF-rotation
#         fore RGB-konvertering (RGBA roteras nu), progressive-JPEG.
#         [E4] SNABBHET: JPEG draft() mot malet vid inlasning
#         (>2x malet) + parallell bearbetning med ThreadPoolExecutor
#         (1-3 workers), ordning via index, cancel per slutford bild,
#         sekventiell fallback.
#         [E5] TEXT: enhetliga prefix + summering med tid/bilder-s
#         (pluginet ar huvudlost - inget fonster att anpassa).
#         Verifierat: py_compile, 0 f-strangar/print, smoke-test med
#         8 riktiga bilder: parallell ordning, sekventiell, cancel,
#         felisolering (korrupt.jpg), config-roundtrip.
# v4.8.0: plugins/ui_settings.py v2.5.0 -> v2.6.0 (KOD/DESIGN +
#         ANPASSAD TEXT & FONSTER-pass).
#         [Z1] register_theme_callback()-override BORTTAGEN - den egna
#         app.bind() ersatte andra plugins bindningar (BUG-024-familjen);
#         nu base_plugin v1.4.1s delade dispatcher.
#         [Z2] Duplicerade log/log_error/load_config/save_config/
#         widget_exists borttagna (~95 rader) - arvs fran base_plugin
#         (atomisk sjalvlakande config: .bak + korrupt-karantan).
#         [Z3] Anpassad text: teckenstorlek fran DPI/tk-scaling via
#         advanced_logger_guards (suggest/clamp_font_size), skalade
#         entry-bredder + slider-langd.
#         [Z4] Anpassat fonster: NORMALT/KOMPAKT lage (<640 px) -
#         padding, wraplength pa output-sokvagen, slider-langd;
#         layoutskiftet loggas.
#         [Z5] Design: farger via get_theme_color (TTL-cachad), knappar
#         + paneler i base_plugins tema-register, varning vid sparande
#         av saknad bildmapp.
#         Verifierat: py_compile alla filer, 0 f-strangar/print i
#         ui_settings, headless smoke-test (Xvfb): Z1-Z5 alla OK.
# v4.7.0: advanced_logger.py v2.4.0 -> v2.5.0 (LEVANDE LOGG-pass).
#         [Y1] ContextObserver: app.context loggar varje nyckelskrivning
#         (varden aldrig). [Y2] Handelsedigest: EN summeringsrad/minut.
#         [Y3] Fel-navigering: Ctrl+Down/Up + "Nasta fel" + "Folj fel".
#         [Y4] AI-chatt SYMTOMGUIDE: bocka i symtom -> riktade svar.
#         [Y5] Fonstervakt: lage jamfors var 5:e minut, loggar andringar.
#         [Y6] Diskkontroll vid start + i rapport. [Y7] Sessionsdiff:
#         fel jamfors mot forra sessionen (nya/aterkommande). Nya metoder
#         flyttade till advanced_logger_ui.py (LogLiveMixin +
#         SymptomWindowMixin); alla 4 filer inom taket, 0 f-strangar/print.
# v4.6.0: advanced_logger.py v2.3.1 -> v2.4.0 (STORT PASS). Filen narmade
#         sig 1800-taket (1767) och delas nu i FYRA filer:
#         advanced_logger.py (1688) + advanced_logger_ui.py (593, mixiner)
#         + advanced_logger_diag.py (1103, AI-felsokning) +
#         advanced_logger_guards.py (991, vakter/LogFiles/text+fonster).
#         Nytt: loggning av 13 handelseslag + ultra-lage (W3), anpassad
#         text/fonster (W4/W5), 21-reglers AI-felsokning (W6),
#         fonsterdiagnostik "varfor syns inte fonstret" (W7), tydlig
#         AI-chatt-rapport + diagnostikfil (W8/W9), shutdown_logging (W2).
#         Ny BUG-026 (uppdelning) + BUG-027 (shutdown_logging saknades).
# v4.5.0: Avsnitt 7 synkat med requirements.txt v1.1.0 (==-pinningar
#         + Python 3.14/Tcl-Tk 9.0-regeln). Avsnitt 20 har aktuella
#         radantal. BUG-023 åtgärdad (html_generator uppdelad i 4 filer).
#         Ny BUG-024 (namnkollision base_plugin v1.4.0 -> v1.4.1) och
#         BUG-025 (try/except/else i system_tray -> v3.5.2). FS-4 klar.
# v4.4.0: Adopterade robusthets-/arkitekturmonster ADOPT-1..6
#         (källa: externa referensspecer PDF Sorter + DesktopTodoPy,
#          endast de generiska, app-oberoende mönstren tas in).
#         Se avsnitt 19A. De externa referensspecerna är arkiverade
#         utanför denna spec och behöver INTE ligga i workspace.
# ============================================================
#
# REGLER FOR DENNA SPEC OCH FOR AI-ASSISTENTEN:
#   - Skriv ABSOLUT ingen kod utan uttrycklig order. Anvandaren klistrar in
#     kod som ska uppdateras - invanta den.
#   - Anvand workspace om det finns, men lanka/presentera alltid filen.
#   - ALLT (spec + uppdaterad kod) ska kunna skrivas ut i kodruta for enkel
#     kopiering. Helst aven via nedladdningsknappen i filvyn.
#   - Skriv ut hela filer utan att korta ner dem.
#   - Om en plugin ligger i en mapp med flera filer i samma mapp ska ALLA
#     filer i samma mapp uppdateras innan vi gar vidare till nasta fil.
#   - PORTABILITET (staende, v4.11.10): appen ska fungera aven om hela
#     mappen flyttas till ny disk/sokvag. All data halls INOM appmappen
#     (config/, logs/, out/, icon/). Spara relativa sokvagar mot
#     projektroten, inte D:\\... som bryts vid flytt. Genererade gallerier
#     ligger i out/.
#   - Om en Python-fil overstiger 1800 rader ska en hjalpfil (max 1200 rader)
#     foreslas och skapas (mixin-monster).
#   - Om hela koden inte far plats i ett svar: skriv i 2 delar med ett
#     anvandarkommando emellan.
#   - Inga profiler skapas - det ar fran app till app. Anvandaren sager till
#     om profiler behovs.
#   - Allt som inte ar kod ska vara bortkommenterat (#).
#   - Appnamnet star pa rad 1 (fore #) sa att nya AI-chattar dops efter appen.
#   - VARJE .py-fil ska ha "# FIL:" och "# PLATS:" overst (efter shebang) sa
#     att fil och sokvag ar solklara vid inklistring i ny chatt.
#
# MAKROKOMMANDON (spec-regel - anvandarens styrord till assistenten):
#   "Förslag"          -> ge 25 NYA (ej återanvända) forslag som gor
#                         appen/designen/minnesanvandningen battre.
#                         Anvandaren valjer bland dem vilka som ska
#                         laggas till i checklistan (avsnitt 21) for att
#                         implementeras.
#   "töm"              -> Rensa workspace: behall ENDAST de AKTIVA
#                         filerna (denna spec + aktuella kodfiler under
#                         arbete). Ta bort ovriga temporara/skrappfiler.
#   "checklista"/"lista" -> Visa checklistan fran spec (avsnitt 21) sa
#                         anvandaren kan markera vilka krav/saker som
#                         ska implementeras.
#   Efter VARJE 5 koduppdateringar -> ge automatiskt 10 NYA forslag
#                         (ej återanvända) som gor koden/designen/
#                         minnes- och CPU-anvandningen battre.
#
# ============================================================
# INNEHALLSFORTECKNING
# ============================================================
# 1.  Projektoversikt och syfte
# 2.  Faktisk mappstruktur (fran disk)
# 3.  Sammanfattning - vad som gjorts denna session
# 4.  Sammanfattning - vad som ar kvar
# 5.  Framtidsplan (fasindelad)
# 6.  Vad programmet gor (funktionellt)
# 7.  Teknisk miljo och beroenden
# 8.  Huvudfil: main.py (fullstandig analys)
# 9.  Hjalpfil: helpers.py (fullstandig analys)
# 10. Plugin-system - fullstandig beskrivning
# 11. Varje plugin-fil - importer + funktion for funktion
# 12. Konfigurationsfiler - JSON-struktur
# 13. UI/UX-krav
# 14. Tema-system (3 teman)
# 15. Systray och single-instance
# 16. Fonsterhantering
# 17. Scroll via mushjul (globalt och lokalt)
# 18. Visa/Dolj tabbar
# 19. Mediahantering (bilder, PDF, video)
# 19A. Robusthets-/arkitekturmonster (ADOPT-1..6, NYTT v4.4.0)
# 20. Filstatus - radantal och hjalpfiler
# 21. Checklista - alla krav
# 22. Kanda fel och buggar med atgardsplan
# 23. Acceptanskriterier
# ============================================================


# ============================================================
# 1. PROJEKTOVERSIKT OCH SYFTE
# ============================================================
#
# Gallery Uploader ar ett desktop-verktyg for att:
#
#   1. Bladdra i lokala bildmappar                (gallery_view.py)
#   2. Sortera bilder manuellt med drag & drop     (image_sorter.py / gallery_view.py)
#   3. Komprimera bilder vid export                (video_processor.py)
#   4. Bearbeta bilder - resize, thumbnails, EXIF  (image_processor.py)
#   5. Generera HTML-gallerisidor                  (html_generator.py)
#   6. Generera slideshows                         (html_generator.py / slideshow_generator.py)
#   7. Ladda upp via FTP                           (ftp_uploader.py)
#   8. Hantera och komprimera video med FFmpeg     (video_processor.py)
#   9. Overvaka mappar i realtid (watchdog)        (watch_folder.py)
#   10. Redigera CSS for galleriet                 (custom_css_editor.py)
#   11. Logga alla operationer                     (advanced_logger.py)
#   12. Hantera tabbar med navigation              (tab_manager.py)
#   13. Kontrollpanel med knappar och logg         (ui_controls.py)
#   14. Installningspanel                          (ui_settings.py)
#   15. Inkludera och lanka PDF- och videofiler    (html_generator.py + gallery_view.py)
#
# Arkitekturprinciper:
#   - main.py ar ett minimalt skal (delar logik med helpers.py)
#   - All funktionalitet i plugins/ (PRIORITY-styrd ordning)
#   - Delad data via context-dictionary
#   - Alla installningar sparas i JSON-filer under config/
#   - Startar ALLTID minimerat i systray (aldrig synligt vid start)
#   - Kors UTAN terminalfonster (pythonw / ctypes pa Windows, aven som .py)
#   - Single-instance-lock via socket (port 47200) inbyggt
#   - Endast EN systray-ikon (aldrig dubbletter)
#   - 3 teman: morkt / ljust / system
#   - Scroll via mushjul i ALLA scrollbara ytor (3 enheter per klick)
#   - Visa/dolj tabbar dynamiskt (Visa-menyn + hogerklick pa flik)
#   - Dynamisk anpassning till alla fonsterstorlekar/skarmar
#   - Inga profiler - fran app till app, anvandaren bestammer
#   - Gallerititeln kopierar ALLTID mappnamnet automatiskt
#   - Genererade bildfiler dops till lopnummer (1.jpg, 2.jpg, ...)
#   - PDF- och videofiler i bildmappen inkluderas och lankas i exporten
#   - Robusthets-/arkitekturmonster ADOPT-1..6 (se avsnitt 19A)
#   - Om koden i en fil overstiger 1800 rader skapas en hjalpfil (max 1200 rader)
#
# ============================================================
# 2. FAKTISK MAPPSTRUKTUR (fran disk)
# ============================================================
#
# ftp_gallery_uploader/
# |
# |-- main.pyw                         # Huvudapplikation (skal). .pyw = ingen terminal.
# |-- main_guards.py                   # Guard-/startup-logik for main.pyw (v2.8.0)
# |-- app_icon.py                      # Kanonisk ikonladdning fran icon/ (v1.0.0)
# |-- helpers.py                       # Hjalpmodul for main.pyw (under 1800 rader-regeln)
# |-- ftp_uploader.py                  # FTP-uppladdningsmodul (legacy/helper)
# |-- slideshow_generator.py           # Slideshow-generator (legacy/helper)
# |-- config.json                      # Globala installningar (rot, legacy)
# |-- watch_config.json                # Mappovervakare-config (rot, migreras till config/)
# |-- spec.md                          # Denna specifikation (appnamn pa rad 1)
# |
# |-- config/                          # Alla JSON-konfigurationer
# |   |-- css_last_session.json        # Senaste CSS-session
# |   |-- gallery_settings.json        # Galleri-specifika installningar
# |   |-- plugin_states.json           # Plugin pa/av
# |   |-- recent_folders.json          # Senast oppnade mappar (macss_last_session.json        # Senaste CSS-session
# |   |-- gallery_settings.json        # Galleri-specifika installningar
# |   |-- plugin_states.json           # Plugin pa/av
# |   |-- recent_folders.json          # Senast oppnade mappar (max 10)
# |   |-- settings.json                # Appinstallningar (tema, geometri, etc.)
# |   |-- tab_state.json               # Flikstatus (aktiv flik, ordning)
# |   |-- tab_visibility.json          # Flik-synlighet (Visa-menyn)
# |   |-- video_settings.json          # Video+bildkomprimering
# |   \-- window_state.json            # Fonstergeometri
# |
# IKONER (v4.11.0) - icon/ ANVANDS OVERALLT:
#   Fonster / titelrad     apply_tk_window_icon()  -> icon.ico + PNG-storlekar
#   Aktivitetsfalt/Alt-Tab Windows iconbitmap(icon/icon.ico)
#   Systray                load_app_icon(64)       -> icon_64.png (sedan 32/png/ico)
#   Sokordning: icon/  ->  assets/  ->  generate_app_icon() (samma design)
#   ikon_oversikt.png ar dokumentation, inte runtime.
#
# |-- logs/                            # Automatiska loggfiler
# |   \-- gallery_YYYYMMDD_HHMMSS.log  # En logg per session (max 50 filer, aldsta roteras ut)
# |
# |-- icon/                            # KANONISK ikonkalla (v4.11.0)
# |   |-- icon.ico                     # Windows: fonster + aktivitetsfalt + Alt-Tab
# |   |-- icon.png                     # Standard-PNG (Linux/Mac fonster)
# |   |-- icon_16.png                  # Titelrad / liten systray
# |   |-- icon_32.png                  # Aktivitetsfalt
# |   |-- icon_64.png                  # Systray (foretrad)
# |   |-- icon_256.png                 # Hog DPI / Alt-Tab
# |   \-- ikon_oversikt.png            # Oversikt (anvands inte runtime)
# |
# |-- assets/                          # Ovriga resurser (legacy-ikonfallback)
# |   |-- icon.ico                     # (bakat: anvands bara om icon/ saknas)
# |   \-- icon.png                     # (bakat: anvands bara om icon/ saknas)
# |
# |-- out/                             # Output-katalog
# |   |-- hpm653/                      # image/ thumb/ video/ index.html slideshow.html
# |   \-- mkt2014/                     # image/ thumb/ index.html slideshow.html
# |
# \-- plugins/
#     |-- __init__.py                  # Gor plugins till paket
#     |-- base_plugin.py               # Basklass (ignoreras av loader)
#     |-- advanced_logger.py           # PRIORITY=-1  Loggvisare
#     |-- advanced_logger_guards.py    # Hjalpfil - vakter/DPI
#     |-- advanced_logger_ui.py        # Hjalpfil - UI-mixins
#     |-- advanced_logger_diag.py      # Hjalpfil - AI-felsokning
#     |-- ui_settings.py               # PRIORITY=1   Installningar
#     |-- ui_controls.py               # PRIORITY=2   Kontroller
#     |-- tab_manager.py               # PRIORITY=-10 Flikhanterare
#     |-- menu_manager.py              # PRIORITY=2   Menyer
#     |-- system_tray.py               # PRIORITY=3   Systray
#     |-- gallery_view.py              # PRIORITY=5   Galleri
#     |-- gallery_view_helpers.py      # Hjalpfil
#     |-- watch_folder.py              # PRIORITY=6   Mappovervakare
#     |-- image_sorter.py              # PRIORITY=11  Bildsorterare
#     |-- image_sorter_helpers.py      # Hjalpfil
#     |-- image_processor.py           # PRIORITY=20  Bildbehandling
#     |-- video_processor.py           # PRIORITY=25  Video
#     |-- video_processor_ui.py        # Hjalpfil
#     |-- html_generator.py            # PRIORITY=30  HTML
#     |-- html_generator_templates.py  # Hjalpfil
#     |-- html_generator_css.py        # Hjalpfil - CSS-motor
#     |-- html_generator_js.py         # Hjalpfil - JS-motor
#     |-- slideshow_generator.py       # PRIORITY=31  Bildspel
#     \-- custom_css_editor.py         # PRIORITY=32  CSS-redigerare
#
# OUTPUT-GALLERISTRUKTUR:
#   Variant A (standard):
#     <gallerinamn>/image/   - Fullstora bilder (1.jpg, 2.jpg, ...)  [LOPNUMMER]
#     <gallerinamn>/thumb/   - Thumbnails (1.jpg, 2.jpg, ...)        [LOPNUMMER]
#     <gallerinamn>/video/   - Videofiler (video1.mp4, video2.mp4, ...)
#     <gallerinamn>/pdf/     - PDF-filer (pdf1.pdf, pdf2.pdf, ...)
#     <gallerinamn>/index.html
#     <gallerinamn>/slideshow.html
#
#   Variant B (flat, legacy lbj960):
#     <gallerinamn>/full_1.jpg, full_2.jpg, ...     [LOPNUMMER]
#     <gallerinamn>/thumb_1.jpg, thumb_2.jpg, ...   [LOPNUMMER]
#     <gallerinamn>/video1.mp4, video2.mp4, ...
#     <gallerinamn>/pdf1.pdf, pdf2.pdf, ...
#     <gallerinamn>/index.html
#     <gallerinamn>/slideshow.html
#
# ============================================================
# 3. SAMMANFATTNING - VAD SOM GJORTS DENNA SESSION
# ============================================================
#
# KODFILER SOM RENSATS/UPPDATERATS DENNA SESSION (alla verifierade
# med py_compile + funktionstest, FIL/PLATS-header tillagd):
#
# [x] app_icon.py v1.0.0 + helpers v1.6.0: icon/ ar kanonisk ikonkalla
#     (fonster, aktivitetsfalt, systray). Filer: icon.ico, icon.png,
#     icon_16/32/64/256.png. Fallback assets/ sedan generate_app_icon.
#
# [x] main.pyw -> v2.8.0 + NY main_guards.py (staende ordrar klara)
#     - M1 0 f-strangar/0 print. M2 mainloop-vakt (_safe_mainloop).
#     - M3 fonsterlage-vakter (spara bara normal, aldrig 0x0).
#     - M4 main_guards.py (safe_write/excepthook/autostart/pycache);
#       main 1849 -> 1789 rader (1800-taket klart, spec §20).
#     - M6 init-tid i startup.log + invalidate_caches vid reload.
#     - M8 adaptiv startgeometri. M9 mappar via BASE_DIR (ej cwd).
#     - Latent bugg fixad: excepthook anropade log_startup_crash
#       innan helpers importerats (tyst NameError).
#     - Dod kod bort: _autostart_is_enabled (aldrig anropad).
#     - Verifierat: hel App-start under Xvfb, alla vakter testade.
#
# [x] plugins/slideshow_generator.py -> v1.3.0 (staende order: f-strangar)
#     - S1 Alla 9 f-strangar borttagna; HTML-mallen konverterad till
#       vanlig strang + __PLATSHALLARE__ + replace()-kedja.
#     - S2 preview_slideshow() fixad (odefinierad output_path =
#       NameError vid klick) - nu context-mapp eller temp-fil.
#
# [x] plugins/image_processor.py -> v2.3.0 (MINNE/SNABBHET/KOD)
#     - E1 config via base_plugin (load/save_settings-duplikat bort).
#     - E2 _log()/_progress() - en kalla for meddelanden.
#     - E3 minne: thumbnail ur nedskalad fullsize (ej img.copy() pa
#       originalet), EXIF fore RGB, progressive-JPEG.
#     - E4 snabbhet: JPEG draft() mot malet + 1-3 parallella workers
#       (ordning bevarad, cancel-check, sekventiell fallback).
#     - E5 text: [OK]/[FEL]/[VARNING]-prefix + tid/bilder-s.
#     - Bevarat: processed_images/temp_dir-nycklar, safe_filename,
#       DecompressionBomb-skydd, ingen print/f-strang.
#     - Verifierat: 8-bilders smoke-test (parallell+sekventiell+cancel
#       +korrupt fil+config-roundtrip).
#
# [x] plugins/ui_settings.py -> v2.6.0 (KOD/DESIGN + ANPASSAD TEXT/FONSTER)
#     - Z1 register_theme_callback via base_plugins delade dispatcher
#       (egen override med app.bind() borttagen - ersatte andras).
#     - Z2 log/log_error/load_config/save_config/widget_exists borttagna
#       (~95 rader) -> arvade base_plugin-versioner (battre: sjalvlakande
#       config med .bak-rotation + korrupt-karantan, traceback i log_error).
#     - Z3 Anpassad text: DPI-baserad teckenstorlek (9->12 pt), alla
#       labels/sektioner/knappar/entry/slider skalar.
#     - Z4 Anpassat fonster: kompakt lage <640 px (padding, wraplength,
#       slider-langd), loggar "Installningar: KOMPAKT/NORMALT lage".
#     - Z5 Farger via get_theme_color, knappar/paneler i base_plugins
#       tema-register, varning vid sparande av saknad bildmapp.
#     - Bevarat: ingen print/f-strang, _collect_settings, FTP-losenord
#       sparas aldrig, exakt 3 teman, PDF/video-export i execute().
#     - Verifierat: py_compile, headless smoke-test (Xvfb) - alla Z OK.
#
# [x] plugins/ui_settings.py -> v2.7.0 + ui_settings_gallery.py
#     - G1 oppna out/<namn>/ med index.html, las output fast.
#     - G2 lagg till bilder/videor. G3 video/pdf fran output vid uppdatering.
# [x] plugins/menu_manager.py -> v2.6.0 (Arkiv: Oppna genererat / lagg till)
#
# [x] plugins/menu_manager.py -> v2.5.0
#     - Z8 idempotent menyrad (reload duplicerade inte poster).
#     - Z9 bind add="+" + macOS Command. Z10 hoppa over Entry.
#     - Z11 senaste-mappar skip identisk. Z12 lift/focus + after_cancel.
#
# [x] plugins/menu_manager.py -> v2.4.0
#     - Z1 tema-dispatcher arvs (stal inte <<ThemeChanged>>).
#     - Z2 log/config arvs fran base_plugin.
#     - Z3 DPI-text, Z4 fit_window + kompakt dialog, Z5 prune,
#       Z6 after_idle senaste-mappar + plugins-meny cache, Z7 Ctrl+G/R.
#
# [x] plugins/html_generator.py -> v3.3.0
#     - V5 videolankar under titeln bort (korten i galleriet kvar).
#     - V6 videothumbnails: ffmpeg/OpenCV JPEG, fallback webblasar-ruta.
#     - html_generator_css.py v3.3.0 (.vthumb img/video object-fit cover).
#
# [x] plugins/advanced_logger.py -> v2.5.0 (LEVANDE LOGG-pass)
#     - Y1 ContextObserver: context-skrivningar loggas (varden aldrig,
#       throttle per nyckel, wrap/rewrap vid pipeline).
#     - Y2 Handelsedigest: EN rad/minut summerar klick/val/scroll mm.
#     - Y3 Fel-navigering: Ctrl+Down/Up, knapp "Nasta fel", "Folj fel".
#     - Y4 Symtomguide: AI-chatt-fonster med valbara symtom -> svar.
#     - Y5 Fonstervakt: var 5:e minut, loggar bara vid andring.
#     - Y6 Diskkontroll (startup + rapport). Y7 Sessionsdiff mot forra
#       gallery-loggen (nya/aterkommande fel) i diagnostikrapporten.
#     - Ny kod i advanced_logger_ui.py (LogLiveMixin, SymptomWindowMixin)
#       och advanced_logger_guards.py (ContextObserver, disk_free_mb).
#     - Verifierat: py_compile, 0 f-strangar/print, guards 26/26,
#       headless smoke-test av Y1-Y7 inkl. end-to-end-rapport.
#
# [x] plugins/advanced_logger.py -> v2.4.0 (STORT PASS, uppdelad i 4 filer)
#     - W1 Uppdelning: advanced_logger.py (1688) + _ui.py (593) + _diag.py
#       (1103) + _guards.py (991). Alla <= taket (BUG-026).
#     - W2 shutdown_logging() (saknades, BUG-027) - sista loggar tappas ej.
#     - W3 Loggning av 13 handelseslag + ultra-lage (tangenter/mus/hover);
#       tangentinnehall loggas ALDRIG (losenordsskydd).
#     - W4/W5 Anpassad text (DPI/A-/A+/Ctrl+hjul/radbryt) + anpassat
#       fonster (kompakt toolbar, skarm-anpassat diagnostikfonster).
#     - W6 21 felmonster-regler (AI-felsokning) i _diag.py.
#     - W7 "Varfor syns inte fonstret?" - 13 kontroller vid start + manuell.
#     - W8/W9 Tydlig AI-chatt-rapport (kopiera/spara) + logs/diagnostik_*.txt.
#     - Verifierat: py_compile 4 filer, 0 f-strangar/print, MRO, guards
#       self-test 24/24, headless smoke-test (loggning/fangst/diagnostik).
#
# [x] plugins/html_generator.py -> v2.5.0
#     - BUG-016 (KeyError 'bg_primary') lost: anvander str.replace() med
#       {{...}}-platshallare istf .format() -> inga brace-konflikter
#     - PDF/video: _collect_media() + _copy_and_rename_media() kopierar OCH
#       doper om till pdf1/pdf2.. och video1/video2.. (BUG-020)
#     - _build_attachment_links(): lankar PDF/video DIREKT UNDER TITELN
#       (anvands i bade index.html och slideshow.html)
#     - Titel = mappnamn som fallback (BUG-019)
#     - Genererade bilder dops till LOPNUMMER 1.jpg, 2.jpg, 3.jpg (ej originalnamn)
#       - standard: image/N.ext + thumb/N.ext
#       - flat: full_N.ext + thumb_N.ext
#     - Gallerikort laddar FULLSTORLEKSBILD (image/N) for skarpa thumbnails
#       (loste grynig thumbnail), med loading="lazy" + decoding="async"
#     - CSS: image-rendering optimize-contrast + translateZ(0)
#     - context: processed_pdfs / processed_videos satts
#     - FTP-lista (_build_files_to_upload) inkluderar pdf/ och video/
#
# [x] helpers.py -> v1.1.0 (aterstalld fran markdown-skadad inklistring)
#     - safe_print, get_base_path, get_config_path, get_assets_path
#     - load_json, save_json (atomisk), bind_mousewheel (3 enheter)
#     - get_system_theme (darkdetect/registry/gsettings)
#     - Klasser: SingleInstanceLock (port 47200, SO_REUSEADDR=0),
#       ThemeEngine (DARK/LIGHT + gra-ruta-fix via TNotebook),
#       TabVisibilityManager, WindowStateManager (skarmbounds),
#       SystrayManager (EN ikon, Wayland-fallback, genererad kamera-ikon)
#     - Verifierat: JSON round-trip, lock acquire/release, geometri-validering
#
# [x] plugins/advanced_logger.py -> v2.1.0 (aterstalld)
#     - PRIORITY=-1, fil-loggning + UI-flik + smart cache (deque 5000)
#     - Loggrotation max 50 filer (BUG-010)
#     - Global excepthook, pipeline-hook (run_pipeline + reload_plugins)
#     - FIX: filedialog 'initialfile' (var ogiltig 'initialfilename')
#     - FIX: widget_exists() lades till (saknades, anvandes pa 8+ stallen)
#     - Verifierat: loggfil skapas, _logger registreras, pipeline-wrap funkar
#
# [x] plugins/base_plugin.py -> v1.1.0 (aterstalld)
#     - Basklass: init/execute/cleanup, log/log_error, load_config/save_config
#       (atomisk), widget_exists, safe_after, safe_update, bind_mousewheel,
#       make_button + _darken_color (alias darken), tema-hjalp
#     - FIX: load_config/save_config anvander get_config_path() (absolut)
#     - Verifierat: execute returnerar context, darken, log-fallback
#
# [x] plugins/custom_css_editor.py -> v2.2.0 (aterstalld)
#     - PRIORITY=32, CSS-editor + HTML head/footer + mallar + snippets
#     - CSS-minifiering (auto + manuell), forhandsgranskning via Popen
#     - Atomisk JSON (css_templates.json, css_last_session.json)
#     - Verifierat: minifiering, _darken, mall-laddning
#     - OBS: snippets riktar .item/.gallery/header - html_generator anvander
#       .card. Harmonisering kvarstar (se notering BUG-022).
#
# [x] plugins/gallery_view.py -> v2.3.0 (aterstalld + UPPDELAD)
#     - Bildgalleri: sortering, rotation, multi-select, drag & drop, undo/redo,
#       preview, sok/filter, zoom, autostart av senaste mapp
#     - DELAD i tva filer (var 2508 rader > 1800-gransen):
#         gallery_view.py         = 1480 rader (karna + UI + thumbnails)
#         gallery_view_helpers.py =  978 rader (GalleryViewMixin: interaktion)
#       class GalleryView(GalleryViewMixin, BasePlugin)
#     - AST-exakt uppdelning: alla 110 metoder bevarade, MRO verifierad
#
# [x] plugins/gallery_view_helpers.py (NY hjalpfil)
#     - GalleryViewMixin (INGEN PLUGIN_NAME -> ignoreras av loadern)
#     - Innehaller: mus/drag&drop, markering, flytta, sortera, rotation,
#       undo/redo, sortspara, ta bort, preview, kontextmeny, tangentbord,
#       navigation, sok/filter
#
# DIAGNOSTIK / ANALYS DENNA SESSION:
# [x] Bekraftat att workspace-filerna ar rena (0 markdown-skador) medan
#     inklistrade versioner var skadade (*build*, [self.app], &lt; &gt;).
# [x] Klargjort: workspace kopieras INTE automatiskt till anvandarens D:\ -
#     filer maste laddas ner via filvyns nedladdningsknapp.
#
# SPEC-ARBETE DENNA SESSION:
# [x] Granskat tva externa referensspecer (PDF Sorter + DesktopTodoPy).
# [x] Adopterat de generiska, app-oberoende robusthetsmonstren som
#     avsnitt 19A (ADOPT-1..6). Hojt version till 4.4.0.
# [x] Rensat workspace sa att endast denna gallery-spec ar kvar.
#
# ============================================================
# 4. SAMMANFATTNING - VAD SOM AR KVAR
# ============================================================
#
# KODFILER EJ ANNU GENOMGANGNA DENNA SESSION (vantar pa inklistring):
# [ ] main.py            - single-instance, withdraw, tray, tema, None-fix,
#                          terminalfri .py, gra-ruta, skarmbounds
# [ ] plugins/tab_manager.py    - anpassad flikrad, visa/dolj, historik
# [ ] plugins/menu_manager.py   - Arkiv/Visa/Kor/Hjalp, tabb-checkboxar
# [ ] plugins/system_tray.py    - EN ikon, enkeltryck, fallback-ikon
# [ ] plugins/ui_settings.py    - titel=mappnamn (BUG-019), FTP, validering
# [ ] plugins/ui_controls.py    - kontroller, logg, generera, ETA
# [ ] plugins/image_sorter.py   - 9 sorteringar, kant-auto-scroll (BUG-021)
# [ ] plugins/image_processor.py- standard + flat, storre thumbnails
# [ ] plugins/video_processor.py- FFmpeg + Pillow bildkomprimering
# [ ] plugins/watch_folder.py   - watchdog, auto-reload, config-migrering
# [ ] ftp_uploader.py           - FTP-uppladdning (anvander files_to_upload)
# [ ] slideshow_generator.py    - (ev. ersatt av html_generator slideshow)
#
# KRITISKT (main.py):
# [ ] single-instance-lock (socket port 47200) - via helpers.SingleInstanceLock
# [ ] self.withdraw() vid start (fonster ALDRIG synligt vid start)
# [ ] systray-integration (helpers.SystrayManager) - EN ikon + enkeltryck
# [ ] tema-system (helpers.ThemeEngine) med <<ThemeChanged>>
# [ ] visa/dolj tabbar (Visa-menyn + hogerklick)
# [ ] mushjul globalt (bind_all, 3 enheter)
# [ ] fonsterposition (helpers.WindowStateManager) + skarmbounds (BUG-004)
# [ ] JSON load/save for config/settings.json
# [ ] run_pipeline: None-fix (BUG-002)
# [ ] ctypes: dolj konsol pa Windows aven om filen heter .py (BUG-018)
# [ ] on_close -> hide_to_tray (minimera istallet for att avsluta)
# [ ] Ta bort gra ruta/falt ovanfor toolbar och meny (BUG-017)
#
# NYA FUNKTIONSKRAV:
# [x] Genererade bilder doupta till lopnummer 1,2,3 (KLART i html_generator)
# [x] Gallerititel = mappnamn (fallback KLART i html_generator; ui_settings kvar)
# [x] PDF/video inkluderas + lankas under titeln + doupta pdf1/video1 (KLART)
# [x] Skarpa (icke-gryniga) gallerikort (KLART i html_generator)
# [ ] Endast EN systray-ikon (main.py + system_tray.py)
# [ ] image_sorter: kant-auto-scroll under drag (BUG-021)
# [ ] gallery_view: bladdra bland PDF/video som bland bilder (ej i v2.3.0)
#
# NYA ROBUSTHETSMONSTER (ADOPT-1..6, se avsnitt 19A):
# [ ] ADOPT-1 Tung atomisk sparning med sjalvlakning (i kod)
# [ ] ADOPT-2 Schema-version i varje JSON-fil + migrering/coerce
# [ ] ADOPT-3 Anti-frys: save i worker-trad med timeout
# [ ] ADOPT-4 Separata data-/I/O-las (tva RLock)
# [ ] ADOPT-5 Global excepthook + kraschlogg + dialog
# [ ] ADOPT-6 Kategoriserad logg med session-id (alternativ)
#
# CONFIG:
# [ ] config/settings.json - tema, fonsterposition, geometri
# [~] config/tab_state.json - tabb-synlighet/ordning (delvis)
# [~] config/recent_folders.json - senast oppnade (delvis)
# [x] config/gallery_settings.json - galleri (lases/skrivs av gallery_view)
# [x] config/video_settings.json - video+bild
# [x] config/css_templates.json + css_last_session.json (custom_css_editor)
# [ ] watch_config.json -> flytta till config/ (BUG-011)
#
# ============================================================
# 5. FRAMTIDSPLAN (fasindelad)
# ============================================================
#
# FAS 1 - Stabilisering (nu)
# ---------------------------
# [ ] main.py: single-instance + EN systray + tema + visa/dolj + terminalfri
# [x] Atgarda KeyError 'bg_primary' i html_generator.py (BUG-016)
# [ ] Ta bort gratt tomt falt mellan meny och toolbar (BUG-017)
# [~] Titel = mappnamn (html_generator klart; ui_settings kvar) (BUG-019)
# [x] PDF/video inkludering + lankning + namngivning (BUG-020)
# [x] Lopnummer pa genererade bilder (1,2,3)
# [ ] image_sorter kant-auto-scroll (BUG-021)
# [ ] gallery_view: bladdring av PDF/video
# [ ] Implementera ADOPT-1..6 i helpers.py / main.py / berorda plugins
# [ ] Verifiera resterande plugins (tab_manager, menu_manager, system_tray,
#     ui_settings, ui_controls, image_sorter, image_processor, video_processor,
#     watch_folder) + main.py
# [ ] Loggrotation testas (max 50 filer i logs/)
# [ ] Flytta watch_config.json till config/
#
# FAS 2 - UI-polish
# ------------------
# [ ] Enhetligt tema i alla plugins (ThemeEngine event <<ThemeChanged>>)
# [ ] Animerade overgangar vid tabb-byte
# [ ] Progress-dialog vid FTP-uppladdning
# [ ] Systray-balloon-notifikationer vid fardig generering
# [ ] Responsiv layout (1024x768 -> 4K)
# [ ] Inbaddad PDF-viewer / videospelare i HTML-galleriet (lightbox)
#
# FAS 3 - Funktionsutokning
# --------------------------
# [ ] Fullt stod for flat output-variant i alla generatorer
# [ ] Batch-bearbetning med kosystem
# [ ] Bildoptimering (WebP, automatisk komprimering)
# [ ] Vattenstampel-plugin
# [ ] SFTP-stod (utover FTP)
# [ ] Molnlagring (S3, GCS, Azure Blob)
# [ ] Schemalagd uppladdning (cron-style)
# [ ] PDF-thumbnails (forsta sidan) via pdf2image/Pillow
#
# FAS 4 - Distribution
# ---------------------
# [ ] PyInstaller - Windows .exe (--noconsole)
# [ ] AppImage - Linux
# [ ] DMG - Mac
# [ ] Auto-uppdateringsfunktion
# [ ] Installer med startmenypost + autostart
#
# FAS 5 - Avancerat
# ------------------
# [ ] Plugin-marketplace
# [ ] REST API (fjarrstyr via HTTP)
# [ ] Flersprakstod (sv/en/de)
# [ ] Tillganglighet (screen readers, a11y)
#
# ============================================================
# 6. VAD PROGRAMMET GOR (funktionellt)
# ============================================================
#
# ARBETSFLODE (typisk session):
#
# 1. Starta programmet (aven som main.py, utan terminal)
#    -> Startar minimerat i systray (ingen terminal, ingen konsol)
#    -> Sakrar single-instance lock via socket port 47200
#    -> Visar EN enda systray-ikon
#    -> Laddar alla plugins i prioritetsordning (tab_manager forst)
#    -> Laddar sparade installningar fran config/settings.json
#
# 2. Oppna programmet (enkelklick pa systray-ikon)
#    -> Fonstret visas med alla tabbar enligt tab_state.json
#    -> Senaste tabb-konfiguration och fonstergeometri aterstalls
#
# 3. Valj bildmapp (Installningar-tabben eller Galleri "Oppna mapp")
#    -> Bildmapp sparas
#    -> Output-sokvag berannas automatiskt under out/<mappnamn>/
#    -> Gallerititeln SATTS ALLTID automatiskt till mappnamnet
#    -> PDF- och videofiler i mappen upptacks och tas med i exporten
#
# 4. Sortera bilder (Galleri / Bildsorterare)
#    -> Drag & drop, multi-select (klick/Ctrl/Shift)
#    -> 9 sorteringsalternativ + undo/redo + zoom + sok
#    -> (KOMMANDE) auto-scroll vid kant under drag
#
# 5. Komprimera bilder/video (Video-tabben)
#    -> Pillow bildkomprimering + FFmpeg videokomprimering
#
# 6. Generera HTML (Ctrl+G)
#    -> index.html + slideshow.html
#    -> Genererade bilder doupta till LOPNUMMER (1.jpg, 2.jpg, ...)
#    -> Skarpa gallerikort (full bild som kalla, lazy/async)
#    -> PDF -> pdf/pdfN.pdf, lankas under titeln
#    -> Video -> video/videoN.ext, lankas under titeln
#    -> Valfri custom CSS fran custom_css_editor
#
# 7. Ladda upp via FTP
#    -> files_to_upload (inkl. image/, thumb/, pdf/, video/) laddas upp
#    -> FTP-losenord SPARAS INTE pa disk
#
# 8. Overvaka mappar (Overvakare-tabben)
#    -> Realtid (watchdog), auto-reload, fargkodad logg
#
# KNAPPAR OCH TABBAR:
#   -> Alltid tydliga med BOLD text i alla teman
#   -> Ljust tema: morkgra bakgrund, svart text
#   -> Morkt tema: mellangra bakgrund, vit text
#
# ============================================================
# 7. TEKNISK MILJO OCH BEROENDEN
# ============================================================
#
# Sprak:     Python 3.12 - 3.14 (utvecklarmiljo: 3.14 pa Windows)
# GUI:       tkinter, tkinter.ttk (Tcl/Tk 8.6 ELLER 9.0 - se regeln nedan)
# Bilder:    Pillow / PIL
# Systray:   pystray (graceful fallback om saknas)
# Filer:     watchdog (valfritt, auto-install stods)
# FTP:       ftplib (stdlib)
# JSON:      json (stdlib)
# Filsystem: pathlib.Path (stdlib)
# Tradar:    threading, queue (stdlib)
# OS:        sys, os, platform, subprocess, ctypes, shutil (stdlib)
# Regex:     re (stdlib)
# Tema:      darkdetect (valfritt, for "system"-tema)
#
# requirements.txt (v1.1.0 - ALLA beroenden pinnade med ==, aldrig >=):
#   Pillow==12.3.0                     # krav
#   pystray==0.19.5                    # krav (tray-ikon)
#   six==1.17.0                        # transitivt krav fran pystray
#   watchdog==6.0.0                    # valfritt (watch_folder)
#   darkdetect==0.8.0                  # valfritt (system-tema)
#   python-xlib==0.33 ; sys_platform == "linux"
#   pyobjc-framework-Quartz==12.2.2 ; sys_platform == "darwin"
#   (tkinter ingar i Python pa Windows/macOS; pa Linux via pakethanterare.
#    FFmpeg/FFprobe ar externa binarer - installeras INTE via pip.)
#   Installeras med: python -m pip install -r requirements.txt
#   OBS: spec.md ar source of truth - vid andrad pinning, synka HAR.
#
# PYTHON 3.14 / TCL-TK 9.0 - OAVVIKLIG REGEL:
#   Python 3.14 pa Windows skeppas med Tcl/Tk 9.0 som TOG BORT det gamla
#   "trace variable"-kommandot. Utfasad tkinter-API kraschar med:
#       TclError: bad option "variable": must be add, info, or remove
#   FORBJUDET: Variable.trace("w", cb), trace_variable, trace_vdelete,
#              trace_vinfo   (borttagna i Python 3.14/tkinter)
#   SKA ANVANDAS: var.trace_add("write", cb) / var.trace_remove("write", id)
#   Ovriga Tcl/Tk 9.0-andringar att ta hansyn till: ingen "~"-tolkning som
#   hemkatalog, strikt I/O-encoding-profil (ogiltig encoding kastar fel) och
#   %b/%d/%o/%x-format modifierare trunkeras till 32 bitar.
#   Fixat 2026-09-15 i ui_controls.py v2.4.1 och image_sorter.py v4.2.1;
#   ingen legacy-trace finns kvar i projektet.
#
# TERMINALFRI KORNING:
#   Windows:  pythonw main.py / main.pyw, ELLER main.py med
#             ctypes.windll.kernel32.FreeConsole() tidigt i main.py.
#   Linux:    nohup python main.py &
#   Mac:      python main.py &
#   PyInstaller: --noconsole --windowed
#
# ============================================================
# 8. HUVUDFIL: main.py (fullstandig analys)
# ============================================================
#
# Fil: main.py   (STATUS: ej genomgangen denna session - vantar pa inklistring)
# Syfte: Minimalt skal - initierar allt, hanterar eventloopen, koordinerar plugins.
# Importerar fran helpers.py (se sektion 9).
#
# IMPORTER (forvantade):
#   import tkinter as tk
#   from tkinter import ttk, messagebox
#   import importlib, pkgutil, sys, os, json
#   from pathlib import Path
#   from threading import Thread
#   from helpers import (SingleInstanceLock, ThemeEngine, SystrayManager,
#       TabVisibilityManager, WindowStateManager, load_json, save_json,
#       get_config_path, get_assets_path, bind_mousewheel, get_system_theme)
#
# KLASS App(tk.Tk) - forvantade metoder:
#   __init__            : ctypes FreeConsole -> SingleInstanceLock -> withdraw ->
#                         ladda settings -> ThemeEngine -> meny/flikrad UTAN
#                         topp-padding (BUG-017) -> load_plugins -> mushjul ->
#                         geometri+skarmbounds -> WM_DELETE_WINDOW=on_close ->
#                         SystrayManager (EN ikon) i trad
#   load_plugins        : pkgutil, ignorera '_*' + 'base_plugin' + '*_helpers',
#                         break efter forsta klass-match (BUG-001),
#                         init i PRIORITY-ordning, ladda plugin_states.json
#   get_plugins         : sortera pa PRIORITY (lagst forst)
#   run_pipeline        : if result is not None: self.context = result (BUG-002)
#   reload_plugins      : stoppa systray FORE reload (BUG-008b), rensa sys.modules
#   show_window         : deiconify + lift + focus + bounds (BUG-004)
#   hide_to_tray        : spara position, withdraw()
#   on_close            : X -> hide_to_tray (avslutar ALDRIG)
#   quit_app            : save_all -> systray.stop -> lock.release -> destroy
#   save_all_settings   : settings.json, tab_state.json, plugin_states.json
#   apply_theme         : ThemeEngine.apply + event_generate <<ThemeChanged>>
#   toggle_tab          : visa/dolj enskild flik
#   setup_mousewheel    : bind_all <MouseWheel>/<Button-4>/<Button-5> (3 enh)
#
# ADOPT-3/4 (nytt): save_all_settings ska kunna anropa worker-save med
#   timeout och anvanda tva separata RLock (se avsnitt 19A).
#
# ============================================================
# 9. HJALPFIL: helpers.py (fullstandig analys)  [v1.1.0 - KLAR]
# ============================================================
#
# Fil: helpers.py   (STATUS: aterstalld + verifierad denna session)
# Syfte: Haller main.py under 1800 rader. Alla hjalpklasser/funktioner.
# (Vid nasta uppdatering: utokas med ADOPT-1..6 - se avsnitt 19A.)
#
# IMPORTER:
#   tkinter as tk, ttk; json, os, sys, socket, threading, platform,
#   tempfile, re; pathlib.Path
#
# FUNKTIONER:
#   safe_print(message)            - skriv utan att krascha (stderr/loggfil)
#   get_base_path() -> Path        - projektrot (PyInstaller-medveten)
#   get_config_path() -> Path      - config/ (skapas)
#   get_assets_path() -> Path      - assets/
#   load_json(path, default)       - ladda JSON med fallback
#   save_json(path, data) -> bool  - atomisk skrivning (tmp -> replace)
#   bind_mousewheel(widget, cb, units=3) - mushjul Win/Mac/Linux
#   get_system_theme() -> "dark"|"light" - darkdetect/registry/gsettings
#
# PLANERADE TILLAG G FOR ADOPT-1..6 (helpers.py):
#   save_json_heavy(...)  - ADOPT-1: tmp + fsync + las-tillbaka + os.replace
#                           + .bak-rotation (max 5) + .corrupt-backup
#                           + aterstallning fran .bak vid korrupt huvudfil
#   rotate_bak(path)      - ADOPT-1: rotera .bak/.bak.1/...
#   save_json_async(...)  - ADOPT-3: save i worker-trad + Event + timeout
#   Schemavalidering       - ADOPT-2: '_meta.schema_version' + _coerce_*
#   install_excepthooks()  - ADOPT-5: sys/threading excepthook -> kraschlogg
#   get_session_id()       - ADOPT-6: uuid[:12], skrivs i loggbanderoll
#   DataLock-helper         - ADOPT-4: tva RLock per store
#
# KLASSER:
#   SingleInstanceLock(port=47200) : acquire()/release()/is_held()
#                                    SO_REUSEADDR=0 (korrekt lock)
#   ThemeEngine(app)               : DARK/LIGHT dicts, apply(name),
#                                    get_colors/get_color, current_theme,
#                                    TNotebook gra-ruta-fix (bg=bg, bw=0,
#                                    tabmargins=[0,0,0,0])
#   TabVisibilityManager(path)     : is_visible/set_visible/save/get_all
#   WindowStateManager(path)       : get_geometry/save_state/_is_valid
#                                    (min 400x300, skarmbounds at main.py)
#   SystrayManager(app)            : start/stop, _run (Wayland-fallback),
#                                    _on_show (enkelklick), _on_quit,
#                                    _load_icon (assets eller genererad
#                                    kamera-ikon), notify
#
# ============================================================
# 10. PLUGIN-SYSTEM - FULLSTANDIG BESKRIVNING
# ============================================================
#
# DISCOVERY:
#   pkgutil.iter_modules([str(plugins_path)])
#   Ignorerar: '_*', 'base_plugin', samt hjalpfiler utan PLUGIN_NAME
#              (t.ex. gallery_view_helpers - har INGEN PLUGIN_NAME)
#   Identifierar: isinstance(cls, type) AND hasattr(cls, 'PLUGIN_NAME')
#                 AND cls.__name__ != 'BasePlugin'
#   break efter FORSTA match (BUG-001 fix)
#
# PLUGIN-KONTRAKT (duck typing):
#   Obligatoriskt: PLUGIN_NAME: str
#   Valfritt:      PRIORITY: int (default=100, lagre=tidigare),
#                  VERSION: str, TAB_NAME: str
#   Valfria metoder:
#     init(self, app) -> None
#     execute(self, context, log_func=None) -> dict  (None ignoreras, BUG-002)
#     cleanup(self) -> None
#
# CONTEXT-NYCKLAR (kanda):
#   '_tab_manager', '_gallery_view', '_watch_folder', '_logger', '_settings',
#   '_controls', '_video_processor', '_menu_manager', '_system_tray',
#   '_css_editor'
#   'gallery' (dict, inkl 'title' = mappnamn), 'gallery.images_path'
#   'gallery_images' [Path], 'sorted_images' [Path], 'gallery_order' bool
#   'image_rotations' dict {Path:int}, 'get_gallery_images' callable
#   'processed_images' [dict], 'processed_pdfs' [dict], 'processed_videos' [dict]
#   'pdf_files'/'gallery_pdfs', 'video_files'/'gallery_videos'
#   'custom_css', 'custom_html_header', 'custom_html_footer'
#   'output_format' ("standard"|"flat"), 'output_path', 'html_output'
#   'files_to_upload' [str], 'ftp_settings' dict, 'ftp_enabled' bool
#   'progress_callback', 'cancel_check'
#
# INIT-ORDNING (PRIORITY, lagst forst):
#   -10  tab_manager        (ALLRA FORST)
#    -1  advanced_logger
#     1  ui_settings
#     2  ui_controls
#     2  menu_manager
#     5  system_tray
#     5  gallery_view
#     6  watch_folder
#    10  image_sorter
#    20  image_processor
#    25  video_processor
#    30  html_generator
#    32  custom_css_editor
#   OBS: samma PRIORITY -> alfabetisk ordning.
#   OBS: gallery_view har PRIORITY=5 i nuvarande kod (specens 10 var aldre).
#
# ============================================================
# 11. VARJE PLUGIN-FIL - IMPORTER + FUNKTION FOR FUNKTION
# ============================================================
#
# (Endast filer som ar genomgangna denna session beskrivs i detalj.
#  Ovriga fylls i nar de klistras in och uppdateras.)
#
# ------------------------------------------------------------
# plugins/base_plugin.py  [v1.1.0 - KLAR]
# ------------------------------------------------------------
# Klass: BasePlugin (IGNORERAS av loadern). Ingen PLUGIN_NAME-baserad laddning.
# Importer: tkinter as tk; sys, os, json, traceback, tempfile; pathlib.Path
# Metoder: __init__, init, init_ui, init_menu, execute (returnerar ALLTID
#   context), cleanup (is_active=False + unbind_all_mousewheels), on_closing,
#   refresh, log/log_action/log_error/log_debug/log_warning/log_success,
#   safe_after, safe_update, widget_exists, safe_widget_config,
#   bind_mousewheel (3 enheter), unbind_all_mousewheels,
#   get/set_context_value, get_logger/get_tab_manager/get_settings,
#   load_config/save_config (atomisk, via get_config_path),
#   ensure_path/get_base_path/get_config_path/get_logs_path,
#   get_theme_colors/get_theme_color/on_theme_changed/register_theme_callback,
#   make_button, _darken_color (staticmethod), darken (alias)
#   Modulfunktion: _safe_write(message)
#
# ------------------------------------------------------------
# plugins/ui_settings.py  [v2.6.0 - KLAR]
# ------------------------------------------------------------
# Klass: SettingsUI(BasePlugin). PRIORITY=1. config/settings.json.
# v2.6.0: Z1 tema via base_plugins delade dispatcher (ingen egen
#   register_theme_callback-override). Z2 log/config/widget_exists arvade
#   fran base_plugin v1.4.1. Z3 DPI-anpassad text (advanced_logger_guards
#   suggest_font_size/clamp_font_size) - _font()/_scaled() driver labels,
#   sektioner, entry-bredder och slider. Z4 fonsteranpassning: <Configure>
#   vaxlar NORMALT/KOMPAKT (<640 px) med wraplength + slider-langd.
#   Z5 tema-farger via get_theme_color + knapp/panel-register +
#   saknad-mapp-varning i save_settings.
# BEVARAT: ingen print/f-strang, _collect_settings (en datakalla),
#   FTP-losenord sparas aldrig, exakt 3 teman, PDF/video-export i
#   execute(), BUG-019/020-beteenden.
#
# ------------------------------------------------------------
# plugins/image_processor.py  [v2.3.0 - KLAR]
# ------------------------------------------------------------
# Klass: ImageProcessor(BasePlugin). PRIORITY=20. Huvudlost plugin.
# v2.3.0: E1 config arvs fran base_plugin (gallery_settings.json).
#   E2 _log()/_progress() hjalpare. E3 minne: engangsnedskalning
#   (thumbnail ur fullsize), EXIF fore RGB, progressive-JPEG.
#   E4 snabbhet: JPEG draft() mot fullsize-malet vid >2x storlek +
#   ThreadPoolExecutor (max 3 workers, minst 4 bilder), resultat per
#   index (ordning bevaras), cancel_check pollas, fallback sekventiell.
#   E5 text: enhetliga prefix + atgangstid/bilder-s i summeringen.
# CONTEXT: laser gallery/sorted_images/progress_callback/cancel_check;
#   satter processed_images [dict: index/filename/thumbnail/fullsize/
#   title/original_path/original_name] + temp_dir.
# BEVARAT: safe_filename/create_title/_to_rgb/_resolve_image_path,
#   load_image_safely (draft, DecompressionBomb), ingen print/f-strang.
#
# ------------------------------------------------------------
# plugins/slideshow_generator.py  [v1.3.0 - KLAR]
# ------------------------------------------------------------
# Klass: SlideshowGenerator(BasePlugin). PRIORITY typiskt efter HTML.
# v1.3.0: S1 alla 9 f-strangar borttagna (%-formatering). Den stora
#   HTML-mallen ar nu vanlig strang med __PLATSHALLARE__ +
#   replace()-kedja (samma monster som html_generator, BUG-016).
#   S2 preview_slideshow() fixad: refererade odefinierad output_path
#   (NameError vid klick) - nu output-mapp fran context, fallback
#   temp_slideshow.html. Ingen print().
#
# ------------------------------------------------------------
# plugins/advanced_logger.py  [v2.5.1 - KLAR, UPPDELAD i 4 filer (BUG-026)]
# ------------------------------------------------------------
# Klass: AdvancedLogger(BasePlugin, UiCaptureMixin, DiagWindowMixin,
#       LogLiveMixin, SymptomWindowMixin).
# PRIORITY=-1. context['_logger']. Loggar till logs/ (gallery_*.log +
# errors_*.log + diagnostik_*.txt), rotation max 50/30.
# FILER:
#   advanced_logger.py        karna: init, log-API, vakter, pipeline-hooks,
#                             UI-flik (filter/sok/statistik/anpassad text),
#                             W7-fonsterdiagnostik, execute/cleanup/
#                             shutdown_logging
#   advanced_logger_ui.py     UiCaptureMixin (W3) + DiagWindowMixin (W8) +
#                             LogLiveMixin (Y1 context-observator, Y2 digest,
#                             Y3 felnavigering, Y5 fonstervakt, Y7 sessions-
#                             diff-block) + SymptomWindowMixin (Y4 symtomguide)
#   advanced_logger_diag.py   21 felmonster-regler (W6) + window_report
#                             (W7) + environment_report (Y6 disk) + session_
#                             diff/diff_current (Y7) + render/chat (W8)
#   advanced_logger_guards.py vakter, LogFiles, text/fonster-hjalp,
#                             ContextObserver + disk_free_mb (Y1/Y6)
# INSTALLNINGAR: config/logger_settings.json (capture/ultra/font_size/wrap/
#   level/auto_scroll/only_errors/diag_on_start/context_watch/follow_errors/
#   digest/watchdog).
# KORTKOMMANDON (i loggrutan): Ctrl+F sok, Ctrl+D felsok, Ctrl+/- text,
#   Ctrl+/- mushjul text, Ctrl+E endast fel, Ctrl+Down/Up nasta/forega fel.
# (ADOPT-5/6 redan uppfyllda: sys/threading/Tk-excepthook + SESSION_ID i
#   startbanderollen; ADOPT-6 valfritt kvar.)
#
# ------------------------------------------------------------
# plugins/html_generator.py  [v3.3.0 - KLAR]
# ------------------------------------------------------------
# Klass: HtmlGenerator(BasePlugin). PRIORITY=30.
# Importer: os, json, shutil, re; pathlib.Path; datetime; .base_plugin
# Klassattribut: IMAGE_FORMATS, PDF_FORMATS, VIDEO_FORMATS, _INDEX_TEMPLATE,
#   _SLIDESHOW_TEMPLATE (vanliga strangar med {{...}}-platshallare)
# Metoder:
#   execute - pipeline: laser gallery, output_format, bygger entries,
#             kopierar bilder (LOPNUMMER), samlar+doaupter PDF/video, genererar
#             index.html + slideshow.html, satter files_to_upload.
#   _get_output_format - context | gallery_settings.json | "standard"
#   _get_image_entries - processed_images | sorted_images | glob; filnamn=N.ext
#   _copy_images - standard: image/N + thumb/N; flat: full_N + thumb_N
#   _safe_copy
#   _collect_media - samla PDF/video fran context-nycklar eller glob
#   _normalize_media_item - dict/str/Path -> Path
#   _copy_and_rename_media - pdf1.., video1.. (subdir vid standard)
#   _natural_sort_paths
#   _build_files_to_upload - rglob (inkl pdf/ video/)
#   _build_attachment_links - lankfält UNDER TITELN (pdf/video)
#   _generate_index_html / _generate_slideshow_html
#   _build_gallery_cards - laddar FULL bild (skarp), lazy+async
#   _build_slides / _build_js_images
#   _get_theme_css (dark/light/colorful)
#   _write_file (atomisk), _safe_stem, _make_title, _esc, _esc_js
#
# ------------------------------------------------------------
# plugins/custom_css_editor.py  [v2.2.0 - KLAR]
# ------------------------------------------------------------
# Klass: CustomCSSEditor(BasePlugin). PRIORITY=32. context['_css_editor'].
# JSON: config/css_templates.json, config/css_last_session.json
# Importer: tkinter as tk, ttk, messagebox, filedialog, simpledialog;
#   json, os, re, sys, subprocess, tempfile; pathlib.Path; datetime
# Metoder (urval): init, _build_ui/_build_toolbar/_build_css_tab/
#   _build_header_tab/_build_footer_tab/_build_snippets_tab, _setup_css_tags,
#   _make_editor, _on_tab_key, _insert_at_cursor, _insert_snippet,
#   _on_key_release, _schedule_highlight, _highlight_css, _update_char_count,
#   _minify_css, _minify_css_string, _load_builtin_presets,
#   _load_saved_templates, _save_templates_to_disk, _get_template_names,
#   _update_template_combo, _get_editor_content, _set_editor_content,
#   _load_selected_template, _save_current_template, _import_css, _export_css,
#   _preview (Popen), _build_preview_html, _apply_css, _reset_css,
#   _load_last_session, _save_last_session, _set_status, execute, cleanup,
#   on_theme_changed, log/log_error, load_config/save_config, widget_exists,
#   safe_widget_config, safe_after, _bind_mousewheel, _make_button, _darken
#
# ------------------------------------------------------------
# plugins/gallery_view.py  [v2.3.0 - KLAR, UPPDELAD]
# ------------------------------------------------------------
# Klass: GalleryView(GalleryViewMixin, BasePlugin). PRIORITY=5.
# context['_gallery_view'], context['get_gallery_images'].
# JSON: config/gallery_settings.json; <mapp>/.gallery_sort.json
# Importer: tkinter as tk, ttk, filedialog, messagebox; pathlib.Path;
#   json, os, shutil, time, subprocess, sys, random; PIL Image/ImageTk/ImageOps;
#   .base_plugin.BasePlugin; .gallery_view_helpers.GalleryViewMixin
# HUVUDFIL (1480 rader) - metoder: init, _load_settings, _save_settings,
#   _build_ui, _build_toolbar1/2/3, _build_drag_info, _build_gallery_canvas,
#   _build_statusbar, _btn, _darken, _add_tooltip, _bind_wheel/_unbind_wheel/
#   _on_wheel/_on_ctrl_wheel/_scroll_canvas, _on_zoom_changed/_apply_zoom,
#   load_images, _load_images_from_folder, _load_thumbnails,
#   _update_rotated_thumbnail, refresh_gallery, _create_item, _show_instructions,
#   generate_html, show_settings_dialog, execute, cleanup, on_theme_changed,
#   log/log_error, load_config/save_config, widget_exists, safe_widget_config,
#   safe_after, get_sorted_images, _set_status, _update_context, _update_counters
#
# ------------------------------------------------------------
# plugins/gallery_view_helpers.py  [NY - KLAR]
# ------------------------------------------------------------
# Klass: GalleryViewMixin (INGEN PLUGIN_NAME -> ej eget plugin).
# Importer: tkinter as tk, messagebox; pathlib.Path; json, os, shutil, time,
#   subprocess, sys, random; PIL Image/ImageTk/ImageOps
# Innehaller (62 metoder): _on_mouse_down/_move/_up/_on_right_click,
#   _on_canvas_click, _get_widget_index, _show_drop_indicator/_hide_drop_indicator,
#   _update_selection_visual, select_all/clear_selection/invert_selection/
#   select_every_other/toggle_selection, _move_images_to/move_up/move_down/
#   move_to_top/move_to_bottom, sort_az/za/date/size/random/reverse_order/_sort,
#   rotate_left/right/180/_rotate_selected/save_rotations/reset_selected_rotation,
#   _save_to_history/undo/redo/_restore_history, _load_sort_order/save_sort_order/
#   _save_sort_silent/_mark_changed, delete_selected, preview_selected/
#   preview_image_at_index/_open_preview_window/_update_preview/_preview_nav/
#   _rotate_in_preview/_delete_in_preview, _create_context_menu,
#   _bind_keyboard_shortcuts/_focus_search, _nav_up/down/left/right/_navigate/
#   _nav_home/_nav_end/_scroll_to, _on_frame_configure/_on_canvas_configure,
#   _open_external/_copy_filename/show_in_folder, _on_search_changed/clear_search/
#   _on_filter_changed
#   BEROENDEN (forvantas pa self via GalleryView): se filhuvudet i hjalpfilen.
#
# ============================================================
# 12. KONFIGURATIONSFILER - JSON-STRUKTUR
# ============================================================
#
# -- config/settings.json --
# {
#   "folder": "...", "title": "<mappnamn>", "description": "",
#   "theme": "dark", "columns": 4, "thumbnail_size": "300x300",
#   "fullsize_max": "1920x1080", "quality": 85, "preserve_exif": false,
#   "auto_rotate": true, "geometry": "800x650+100+100",
#   "include_pdf": true, "include_video": true,
#   "ftp": { "enabled": false, "server": "", "user": "", "path": "/public_html/gallery" }
# }
# OBS: FTP-losenord sparas ALDRIG.
# (ADOPT-2: filen ska fa '_meta.schema_version'.)
#
# -- config/gallery_settings.json --
# { thumbnail_size, show_filenames, show_numbers, show_filesize,
#   show_dimensions, confirm_delete, auto_save, animation_enabled,
#   double_click_preview, rotation_saves_file, load_last_folder_on_start,
#   last_folder, output_format }
#
# -- config/recent_folders.json --   { "folders": [...] }  (max 10)
# -- config/tab_state.json --        { last_tab, tab_order, tab_visibility{} }
# -- config/video_settings.json --   (FFmpeg + Pillow-installningar)
# -- config/css_templates.json --    { "<namn>": {css, header, footer} }
# -- config/css_last_session.json -- { css, header, footer }
# -- config/watch_config.json --     { folders, auto_reload, notify, recursive, auto_start }
# -- <mapp>/.gallery_sort.json --    { order[], rotations{}, updated }
# -- logs/gallery_YYYYMMDD_HHMMSS.log -- [YYYY-MM-DD HH:MM:SS] LEVEL: msg (rotation 50)
#
# ============================================================
# 13. UI/UX-KRAV
# ============================================================
#
# - Python 3.12+, tkinter/ttk. Modernt, fargglatt, stilrent.
# - fill=BOTH, expand=True konsekvent. Min 600x400, standard 800x650. 1024x768 -> 4K.
# - INGEN gra tom ruta ovanfor toolbar/meny (BUG-017).
# - Knappar: Segoe UI 10pt BOLD; ljust=morkgra/svart, morkt=mellangra/vit;
#   hover 20% morkare (_darken); min 80x30; cursor=hand2.
# - Tabbar (anpassad flikrad i tab_manager, INTE ttk.Notebook): BOLD,
#   hogerklick-meny, mushjul horisontell scroll.
# - Monospace Consolas (logg, CSS-editor). Mushjul 3 enheter; Linux Button-4/5.
# - Systray: EN ikon (assets/icon.ico|png, fallback genererad). Enkeltryck=visa.
#
# ============================================================
# 14. TEMA-SYSTEM (3 TEMAN)
# ============================================================
#
# "light" / "dark" / "system". Sparas i settings.json. ThemeEngine i helpers.py.
# Event <<ThemeChanged>>. system: darkdetect -> dark/light, fallback light.
# Krav: knappar/tabbar ALLTID BOLD + hog kontrast (WCAG AA 4.5:1).
# DARK: bg #1e1e1e, fg #fff, button_bg #404040; LIGHT: bg #f0f0f0, fg #000,
# button_bg #d0d0d0. (Fullstandiga dicts i helpers.ThemeEngine.)
# Endast 3 teman - inga accentpaletter.
#
# ============================================================
# 15. SYSTRAY OCH SINGLE-INSTANCE
# ============================================================
#
# SINGLE-INSTANCE: helpers.SingleInstanceLock, port 47200, SO_REUSEADDR=0.
#   Misslyckad bind -> varning + avsluta ny instans. Frigors i quit_app.
# SYSTRAY: helpers.SystrayManager. EN ikon (aven efter reload, BUG-008b).
#   Startar dolt (withdraw). Enkeltryck -> show_window. Hogerklick -> Visa|Avsluta.
#   Wayland -> fallback (visa fonster direkt). Terminalfri (FreeConsole).
# X-KNAPP: hide_to_tray (avslutar ALDRIG). AVSLUTA: endast via meny/tray.
#
# ============================================================
# 16. FONSTERHANTERING
# ============================================================
#
# helpers.WindowStateManager. geometry "WxH+X+Y" i settings.json.
# Min 400x300 (validering). Skarmbounds (BUG-004): utanfor -> centrera.
# Debounce resize 500ms.
#
# ============================================================
# 17. SCROLL VIA MUSHJUL (globalt och lokalt)
# ============================================================
#
# GLOBALT (main.py): bind_all <MouseWheel>/<Button-4>/<Button-5>, 3 enheter.
# PER WIDGET: tab_manager (horisontell), watch_folder, gallery_view (canvas),
#   video_processor (canvas+tree+logg), ui_settings, ui_controls, advanced_logger,
#   custom_css_editor. Win delta//120*3, Mac delta, Linux Button-4/5.
#
# ============================================================
# 18. VISA/DOLJ TABBAR
# ============================================================
#
# Visa-menyn (menu_manager): Checkbutton per flik -> toggle_tab.
# Hogerklick (tab_manager): "Dolj denna flik". Sparas i tab_state.json
# (tab_visibility). Dynamiskt utan omstart. Nav (back/forward) uppdateras.
#
# ============================================================
# 19. MEDIAHANTERING (bilder, PDF, video)
# ============================================================
#
# TITEL: kopierar ALLTID mappnamnet (BUG-019). html_generator har fallback;
#   ui_settings ska satta title_var = Path(folder).name vid mappbyte.
#
# BILDER: genererade filer doupta till LOPNUMMER (1.jpg, 2.jpg, ...).
#   Gallerikort laddar full bild for skarpa (lazy/async).
#
# PDF: alla .pdf i mappen samlas, kopieras + dops pdf1.pdf, pdf2.pdf...
#   standard: pdf/  | flat: rot. Lankas DIREKT UNDER TITELN.
#
# VIDEO: alla videoformat samlas, kopieras + dops video1.<ext>, video2.<ext>...
#   standard: video/ | flat: rot. Lankas DIREKT UNDER TITELN.
#
# BLADDRING (KOMMANDE): gallery_view ska kunna bladdra bland PDF/video som bilder.
# AUTO-SCROLL (KOMMANDE, BUG-021): image_sorter ska auto-scrolla vid kant under drag.
#
# ============================================================
# 19A. ROBUSTHETS-/ARKITEKTURMONSTER (ADOPT-1..6)  [NYTT v4.4.0]
# ============================================================
#
# KALLA: Dessa generiska monster adopterades fran tva externa,
# app-specifika referensspecer (en PDF-klassificerare "PDF Sorter" och en
# desktop-todo "DesktopTodoPy v6.3"). Endast de app-oberoende
# robusthetsideerna tas in - sjalva matchnings-/todo-/OCR-/PySide6-logiken
# darifran ar INTE relevant och tas INTE in. Inga profiler skapas.
#
# ------------------------------------------------------------------
# ADOPT-1  TUNG ATOMISK SPARNING MED SJALVLAKNING
# ------------------------------------------------------------------
# Kalla: PDF REQ-I2 AC-2.5 + DesktopTodoPy SAVE-001 / MUST-010
# Nuvarande: atomisk skrivning (tmp -> os.replace) finns i genomgangna
#   plugins (BUG-007). Saknas: fsync, las-tillbaka-verifiering,
#   .bak-rotation och .corrupt-backup.
# Atgard (centralisera i helpers.save_json() / BasePlugin.save_config()):
#   1. Skapa '{fil}.json.tmp'
#   2. Skriv data + f.flush() + os.fsync(f.fileno())  (tvinga till disk)
#   3. Las tillbaka tmp + json.load()  (verifiera lasbarhet)
#   4. os.replace(tmp, original)  (atomisk pa alla OS)
#   5. Auto-backup: fore varje save rotera '.bak','.bak.1'... max 5.
#   6. Corrupt-backup: vid JSON-fel spara undan '<namn>.corrupt-backup-<tid>'
#      och - om en frisk '.bak' finns - aterstall darifran (sjalvlakning).
# Prio: HOG.  Krav: BUG-007 utokad.
#
# ------------------------------------------------------------------
# ADOPT-2  SCHEMA-VERSION I VARJE JSON-FIL + MIGRERING
# ------------------------------------------------------------------
# Kalla: DesktopTodoPy MUST-014 + schema v4/v8 + _coerce_task()
# Nuvarande: Gallery config-filer saknar schema-versionering.
# Atgard: (1) '_meta.schema_version' i varje config/JSON-fil;
#   (2) vid lasning, om version < nuvarande kor _migrate_<fil>();
#   (3) 'coerce'-hjalpfunktion normaliserar varje post (fyller saknade
#   falt med default) sa gamla filer aldrig kraschar.
# Berorda: settings.json, gallery_settings.json, tab_state.json,
#   recent_folders.json, video_settings.json, watch_config.json,
#   css_templates.json, css_last_session.json.
# Prio: MEDEL-HOG.
#
# ------------------------------------------------------------------
# ADOPT-3  ANTI-FRYS: SPARA I WORKER-TRAD MED TIMEOUT
# ------------------------------------------------------------------
# Kalla: DesktopTodoPy MUST-013 + 5.4 (3 s timeout -> return False)
# Nuvarande: JSON-sparning sker synkront pa UI-traden.
# Atgard: save via liten worker-helper som kor skrivning i en trad med
#   threading.Event + timeout (t.ex. 3 s). Om I/O hanger returneras False
#   i stallet for att blockera/frysa UI. Kritiska saves (avslut) kan
#   koras synkront men ocksa med timeout-skydd.
# Prio: MEDEL.
#
# ------------------------------------------------------------------
# ADOPT-4  SEPARATA DATA-/I/O-LAS (tva RLock)
# ------------------------------------------------------------------
# Kalla: DesktopTodoPy 5.5 (_lock + _save_lock)
# Atgard: I main.py (context) och store-liknande plugins anvands tva
#   separata threading.RLock:
#     - self._lock      (mutering av delat state)
#     - self._save_lock (en enda skrivare i taget till disk)
#   En hangande I/O blockerar da aldrig lasning/mutering av data.
# Prio: MEDEL.
#
# ------------------------------------------------------------------
# ADOPT-5  GLOBAL EXCEPTION HOOK + KRASCHLOGG + DIALOG
# ------------------------------------------------------------------
# Kalla: PDF REQ-N1 (sys/threading excepthook) + DesktopTodoPy 17.8
# Nuvarande: advanced_logger loggar normal drift; ohanterade undantag i
#   godtyckliga tradar fangas inte alltid.
# Atgard: installera vid start (main.py/advanced_logger):
#   - sys.excepthook + threading.excepthook -> kraschlogg med traceback.
#   - Visa tydlig fel-dialog (ej blocking i olamplig trad).
#   - Ateraktivera hook vid reload_plugins.
# Prio: HOG.  Forstarker BUG-010/loggning.
#
# ------------------------------------------------------------------
# ADOPT-6  KATEGORISERAD LOGG MED SESSION-ID (ALTERNATIV)
# ------------------------------------------------------------------
# Kalla: PDF REQ-N1 (logs/<AAAA-MM>/ + SESSION_ID)
# Nuvarande: 'max 50 filer i logs/' (BUG-010).
# Alternativ/kompletterande modell:
#   - logs/<AAAA-MM>/app.log + gui.log + errors.log (roterande 5MB x3).
#   - Varje session far SESSION_ID = uuid[:12], skrivs i loggbanderoll.
# OBS: enkel-logg-per-session + rotation (max 50) far KVARSTA som default.
# Prio: LAG-MEDEL.
#
# ------------------------------------------------------------------
# CHECKLISTA ADOPT-1..6:
# [ ] ADOPT-1 Tung atomisk sparning (i kod, ej enbart spec)
# [ ] ADOPT-2 Schema-version + migrering/coerce
# [ ] ADOPT-3 Anti-frys worker-save med timeout
# [ ] ADOPT-4 Separata data-/I/O-las
# [ ] ADOPT-5 Global excepthook + kraschlogg + dialog
# [ ] ADOPT-6 Kategoriserad logg med session-id (alternativ)
#
# INTE ADOPTERAT (forklaring):
#   - Matchningsmotor/stodord/OCR (PDF-doman)
#   - Todo/taggar/prioritet/snooze/voice (todo-doman)
#   - PySide6/glas/desktop-widget-paradigm (motsats till Gallery-kravet
#     "starta minimerat i tray")
#   - Tungt stability-system (ErrorBoundary/CircuitBreaker/HealthMonitor)
#     - endast latt delmangd ADOPT-5 rekommenderas for Tkinter-plugin-app
#   - Accent-paletter utover de 3 teman (morkt/ljust/system)
# ============================================================
#
# ============================================================
# 20. FILSTATUS - RADANTAL OCH HJALPFILER
# ============================================================
#
# (Uppmatt i workspace tidigare. Gransen: .py 1800 rader, hjalpfil 1200.)
#
#   (Uppmatt 2026-09-21 i workspace. Gransen: .py 1800, hjalpfil 1200.)
#
#   main.pyw                         1755 rader   OK (v2.8.0 + ikon via app_icon)
#   main_guards.py                    322 rader   OK (hjalpfil: vakter)
#   app_icon.py                       197 rader   OK (v1.0.0, icon/)
#   helpers.py                       1700 rader   OK (v1.6.0, reexport icon-API)
#   plugins/base_plugin.py           1345 rader   OK (v1.4.1)
#   plugins/advanced_logger.py       1755 rader   OK (v2.5.1, uppdelad BUG-026)
#   plugins/advanced_logger_ui.py    1035 rader   OK (hjalpfil v1.1.0, mixiner)
#   plugins/advanced_logger_diag.py  1190 rader   OK (hjalpfil, AI-felsokning)
#   plugins/advanced_logger_guards.py 1114 rader   OK (hjalpfil v1.1.0, vakter)
#   plugins/custom_css_editor.py     1596 rader   OK
#   plugins/gallery_view.py          1797 rader   OK (nara gransen)
#   plugins/gallery_view_helpers.py  1199 rader   OK (mixin-hjalpfil)
#   plugins/html_generator.py        1395 rader   OK (v3.3.0, uppdelad)
#   plugins/html_generator_templates.py 1200 rader OK (hjalpfil, vid gransen)
#   plugins/html_generator_css.py    1179 rader   OK (hjalpfil)
#   plugins/html_generator_js.py     1197 rader   OK (hjalpfil)
#   plugins/image_processor.py        715 rader   OK (v2.3.0, E1-E5)
#   plugins/image_sorter.py          1219 rader   OK
#   plugins/image_sorter_helpers.py   835 rader   OK (hjalpfil)
#   plugins/menu_manager.py          1563 rader   OK (v2.5.0)
#   plugins/slideshow_generator.py    933 rader   OK (v1.3.0, S1/S2)
#   plugins/system_tray.py           1367 rader   OK (v3.5.2)
#   plugins/tab_manager.py           1370 rader   OK
#   plugins/ui_controls.py           1777 rader   OK
#   plugins/ui_settings.py           1338 rader   OK (v2.6.0, Z1-Z5)
#   plugins/video_processor.py       1575 rader   OK
#   plugins/video_processor_ui.py    1178 rader   OK (hjalpfil)
#   plugins/watch_folder.py          1451 rader   OK
#
#   ATGARDAD: html_generator.py (1931) delad i fyra filer (BUG-023, v3.0.0).
#   ATGARDAD: advanced_logger.py (1767) delad i fyra filer (BUG-026, v2.4.0).
#   ATGARDAD: main.pyw (1849) -> 1789: guard-/startup-logik flyttad
#     till main_guards.py (v2.8.0, M4). Alla filer nu inom taket.
#
# ============================================================
# 21. CHECKLISTA - ALLA KRAV
# ============================================================
#
# ARKITEKTUR & START:
# [x] Plugin-baserad (main.py + helpers.py + plugins/)
# [x] Plugin-discovery via pkgutil
# [x] PRIORITY-styrd init och korning
# [x] Pipeline med context-overforing
# [x] break efter forsta plugin-klass (BUG-001)
# [x] run_pipeline None-fix (BUG-002) - main.pyw ignorerar None. KLART.
# [x] single-instance socket 47200 - helpers + main.pyw. KLART.
# [x] withdraw() vid start. KLART.
# [x] systray EN ikon - helpers KLAR, main.pyw v2.8.1 + system_tray v3.6.0
#     (plugin ager ikonen; main skapar inte en andra). KLART.
# [x] tema-system - ThemeEngine + apply_theme + <<ThemeChanged>>. KLART.
# [x] visa/dolj tabbar - Visa-meny + tab_manager. KLART.
# [x] bind_all mushjul (3 enheter). KLART.
# [x] ctypes konsol-doljning aven som .py (BUG-018, FreeConsole). KLART.
# [ ] Ingen gra ruta ovanfor toolbar/meny (BUG-017)
#
# ROBUSTHET (ADOPT-1..6, NYTT v4.4.0):
# [ ] Tung atomisk sparning med sjalvlakning (ADOPT-1)
# [ ] Schema-version + migrering/coerce (ADOPT-2)
# [ ] Anti-frys worker-save med timeout (ADOPT-3)
# [ ] Separata data-/I/O-las (ADOPT-4)
# [ ] Global excepthook + kraschlogg + dialog (ADOPT-5)
# [ ] Kategoriserad logg med session-id, alternativ (ADOPT-6)
#
# KODKVALITET (per fil genomgangen denna session):
# [x] Inga print() (allt via logger/safe_write)
# [x] Atomisk JSON-skrivning (tmp -> replace)
# [x] FIL/PLATS-header overst
# [x] tk.Frame istf ttk.Frame dar gra bakgrund annars uppstar
# [x] subprocess.Popen for OS-kommandon (blockerar ej)
#
# MEDIA / EXPORT:
# [x] Lopnummer pa genererade bilder (1,2,3)
# [x] Skarpa gallerikort (full bild, lazy/async)
# [x] PDF/video kopieras + dops + lankas under titeln
# [x] Titel = mappnamn (fallback i html_generator)
# [ ] gallery_view: bladdra PDF/video som bilder
# [x] image_sorter: kant-auto-scroll (BUG-021) - v4.3.0 live pekare
#     + 30 ms poll. KLART.
# [x] Importera genererat galleri (G1): Arkiv -> historik/out/,
#     laser index.html, laser output fast. KLART.
# [x] Lagg till bilder/videor i oppnat galleri (G2). KLART.
# [x] Ta bort bilder i Bildgalleri (Removed/) + Generera HTML
#     rensar overblivna image/+thumb/ (FS-24). KLART.
# [x] Historikdialog layout: DPI, fit_window, tva paneler, sok,
#     out/Namn, thumb (FS-26, v1.3.0). KLART.
#
# GODKANDA FOR IMPLEMENTERING (v4.11.10, anvandaren valde):
# [x] FS-24 Inkrementell HTML vid omgenerering av SAMMA mapp:
#           kopiera bara nya/andrade bilder, ror inte ororda image/+thumb/.
#           TA AVEN BORT bilder (och motsvarande thumb) som anvandaren
#           tagit bort i galleriet. html_generator v3.4.0. KLART.
# [x] FS-26 DPI + fit_window pa historikdialog (samma Z3/Z4 som
#           Installningar): teckenstorlek, kompakt lage, inte fast 480x360.
#           ui_settings_gallery.py v1.3.0. KLART.
# [ ] FS-27 A/A/O i dialogtexter: Oppna/Valj/Bladdra/lagg till -> korrekt
#           svenska. Ett pass i mixin + menu_manager.
# [ ] PORT-1 Flyttbar app: fungerar pa ny disk. Allt halls i appmappen
#           (config/, logs/, out/, icon/). Historik och ovrig config
#           sparar relativa sokvagar mot projektroten, inte absolut
#           diskbokstav. Genererade filer ligger i out/.
#
# PLUGINS - KLARA DENNA SESSION:
# [x] base_plugin.py v1.1.0
# [x] advanced_logger.py v2.1.0
# [x] html_generator.py v2.5.0
# [x] custom_css_editor.py v2.2.0
# [x] gallery_view.py v2.3.0 (+ gallery_view_helpers.py)
# [x] helpers.py v1.1.0
#
# PLUGINS - EJ GENOMGANGNA:
# [ ] main.py, tab_manager.py, menu_manager.py, system_tray.py, ui_settings.py,
#     ui_controls.py, image_sorter.py, image_processor.py, video_processor.py,
#     watch_folder.py, ftp_uploader.py, slideshow_generator.py
#
# ============================================================
# 21A. FÖRESLAGNA - VÄNTAR PÅ GODKÄNNANDE (implementeras INTE forran
#      anvandaren sager till). Satt [x] pa de som godkans for implementering.
# ============================================================
# OBS: Varje bat om 10 forslag roteras ut nar nasta omgang kommer.
#
# [ ] FS-1  Global farg-cache per tema i ThemeEngine - los farg-dict:et en
#           gang per tema-byte, sa _restyle_all bara laser (inte fallback/
#           logik per widget). Lagre CPU/minne.
# [ ] FS-2  after()-ko-sparning: begransa koade UI-uppdateringar fran
#           worker-tradar till en deque (max ~50); droppa aldsta om full.
#           Lagre CPU/minne vid intensiv loggning.
# [ ] FS-3  Lazy-import av tunga plugins (video_processor, image_processor,
#           watch_folder) sa deras import/PIL-init sker forst nar fliken
#           oppnas forsta gangen. Snabbare start + lagre toppminne.
# [x] FS-4  Centralisera tema-registrering i BasePlugin. KLART i
#           base_plugin v1.4.0: register_panel/register_label/
#           register_button + restyle_registered (de-dup, dod-widget-rensning).
#           OBS v1.4.1: registren heter _theme_reg_* eftersom namnen
#           _reg_panels/_reg_labels redan ar METODER i fem plugins (BUG-024).
# [ ] FS-5  Cacha den genererade PIL-ikonen (RGBA) i en instansvariabel och
#           ateranvand vid systray-start/tema-byte. Ingen onodig CPU.
# [ ] FS-6  Bounded display-buffer i advanced_logger (Text-widget haller bara
#           senaste N raderna, entries i deque) - ingen oandlig tillvaxt.
# [ ] FS-7  Inkrementell statistik i ui_controls.update_counts(): cacha
#           (storlek, mtime)-summa, rakna om bara nar katalogen andrats.
#           Mycket lagre CPU vid upprepade anrop.
# [ ] FS-8  Bygg hogerklick- och hamburger-menyer EN gang och ateranvand
#           (uppdatera bara labels) dar menyer idag byggs om varje oppning.
#           Mindre minne/allokering.
# [ ] FS-9  Centralisera app-ikon/farg-design i en design.py-konstantmodul
#           sa alla fallback-ikoner ar identiska (C2) och andras pa en plats.
# [ ] FS-10 Foresla/Separera ut eventuella ovriga aterstående duplicerade
#           farg-/ikonkonstanter fran helpers/system_tray/video till samma
#           design-modul (se FS-9) for enhetlighet.
# [x] FS-11 Rensa doda historikposter nar historiken oppnas (saknad
#           index.html). Sparar JSON. Raderar ALDRIG filer i out/.
#           Dod sokvag pekas om till out/<namn>/ om galleriet finns dar.
#           ui_settings_gallery.py v1.2.0. KLART.
# [x] FS-24 Inkrementell HTML + ta bort bilder anvandaren tar bort.
#           html_generator v3.4.0. KLART.
# [x] FS-26 DPI + fit_window pa historikdialog.
#           ui_settings_gallery.py v1.3.0. KLART.
# [x] FS-27 A/A/O i dialogtexter (mixin + meny). Godkant -> avsnitt 21.
#           EJ KLART.
#
# ============================================================
# 22. KANDA FEL OCH BUGGAR MED ATGARDSPLAN
# ============================================================
#
# BUG-001: Flera plugin-klasser per modul. Status: ATGARDAD (break). Prio LAG.
#
# BUG-002: execute() returnerar None -> context=None. Status: ATGARDAD
#   (main.pyw run_pipeline: if result is not None). Prio HOG -> LOST.
#
# BUG-003: Systray kraschar pa Wayland. Status: HANTERAT i helpers.SystrayManager
#   (XDG_SESSION_TYPE-detektering -> fallback). Prio MEDEL.
#
# BUG-004: Fonsterposition utanfor skarm. Status: helpers.WindowStateManager
#   validerar storlek; main.py ska centrera vid out-of-bounds. Prio HOG.
#
# BUG-005: Tema-byte paverkar inte alla widgets. Status: <<ThemeChanged>> stods
#   av base_plugin.register_theme_callback; main.py-anrop kvar. Prio MEDEL.
#
# BUG-007: JSON-korruption vid krasch. Status: ATGARDAD i genomgangna filer
#   (atomisk tmp -> os.replace). Utokas av ADOPT-1 (fsync+verify+.bak+
#   corrupt-backup+sjalvlakning). Kontrollera main.py. Prio MEDEL.
#
# BUG-008b: Flera systray-ikoner efter reload. Status: ATGARDAD
#   (stop FORE reload + _start_systray anvander plugin, v2.8.1). Prio HOG -> LOST.
#
# BUG-010: logs/ fylls. Status: ATGARDAD i advanced_logger._rotate_logs (max 50).
#   Alternativ: ADOPT-6 (kategoriserad logg + session-id). Prio MEDEL (test kvarstar).
#
# BUG-011: watch_config.json i rot. Status: KANT. Atgard: config/watch_config.json
#   med bakatkompatibel laddning. Prio LAG.
#
# BUG-016: KeyError 'bg_primary' i HTML-generering. Status: ATGARDAD (v2.5.0,
#   str.replace + {{...}}). Prio HOG -> LOST.
#
# BUG-017: Gra tom ruta ovanfor toolbar/meny. Status: AKTIV. Atgard: ingen
#   topp-padding pa main_frame; flikrad side=TOP fill=X direkt under meny;
#   helpers.ThemeEngine TNotebook-fix. Prio HOG.
#
# BUG-018: main.pyw saknas + terminalfri .py. Status: ATGARDAD
#   (main.pyw finns; FreeConsole forst). Prio HOG -> LOST.
#
# BUG-019: Gallerititel foljer inte alltid mappnamnet. Status: DELVIS (fallback
#   i html_generator KLAR). Atgard: ui_settings.on_folder_changed satter
#   title_var = Path(folder).name. Prio HOG.
#
# BUG-020: PDF/video inkluderas inte i exporten. Status: ATGARDAD (v2.5.0).
#   Prio HOG -> LOST (gallery_view-insamling kvar for full kedja).
#
# BUG-021: Ingen auto-scroll vid sortering nara kant. Status: ATGARDAD
#   (image_sorter v4.3.0: live pekare + 30 ms poll). Prio MEDEL -> LOST.
#
# BUG-022: CSS-snippets riktar .item/.gallery medan html_generator anvander
#   .card. Status: AKTIV. Atgard: harmonisera klassnamn. Prio MEDEL.
#
# BUG-023: html_generator.py = 1931 rader > 1800. Status: ATGARDAD (v3.0.0).
#   Delad i fyra filer: html_generator.py (logik, 1179) +
#   html_generator_templates.py (1200) + html_generator_css.py (1179) +
#   html_generator_js.py (1197). Alla hjalpfiler <= 1200. Prio LAG -> LOST.
#
# BUG-024: Namnkollision base_plugin <-> fem plugins. Status: ATGARDAD (v1.4.1).
#   Symtom (logg 2026-09-21 09:14:53): "TypeError: 'list' object is not
#   callable" i plugin.init() for ui_settings, watch_folder och
#   video_processor -> deras UI byggdes aldrig (Inställningar, Bevakad mapp
#   och Videobearbetning saknades helt).
#   Orsak: base_plugin v1.4.0 (FS-4) satte self._reg_panels = [],
#   self._reg_labels = [] och self._reg_buttons = [] i __init__, medan
#   def _reg_panels()/def _reg_labels() finns som METODER i ui_settings,
#   menu_manager, system_tray, watch_folder och video_processor_ui.
#   Instansattribut vinner alltid over klassmetoder i Python.
#   Atgard: registren heter nu _theme_reg_panels/_theme_reg_labels/
#   _theme_reg_buttons (AST-verifierat unika), plus skuggningsvakt (R2):
#   _detect_shadowing() hittar instansattribut som skuggar en metod och
#   loggar VARNING vid forsta log()-anropet efter init.
#   Test: _test_bp141.py (63 kontrollpunkter). Prio HOG -> LOST.
#
# BUG-025: Falsk "pystray/Pillow saknas" + tvingad fOnstervisning.
#   Status: ATGARDAD (system_tray v3.5.2, P14-14).
#   Symtom (samma logg): VARNING "pystray/Pillow saknas - pip install pystray
#   Pillow" fast bade pystray och Pillow ar installerade; fOnstret visades
#   200 ms efter start trots start_minimized=true och minimerades sedan
#   vid 400 ms (flimmer).
#   Orsak: try/except/ELSE i init() steg 5-6. else-grenen kOrs nar
#   after()-anropet LYCKAS (alltsa alltid), inte nAr pystray saknas.
#   Atgard: else-grenen borttagen; varning + show_window sker nu bara nar
#   TRAY_AVAILABLE ar False. AST-skanning av hela projektet visar att detta
#   var det enda try/except/else-blocket. Test: _test_tray352.py (16 punkter).
#   Prio HOG -> LOST.
#
# BUG-026: advanced_logger.py = 1767 rader, nara 1800-taket.
#   Status: ATGARDAD (v2.4.0). Delad i fyra filer:
#     advanced_logger.py        1688 (karnlogik + publik API + UI-flik)
#     advanced_logger_ui.py      593 (UiCaptureMixin + DiagWindowMixin)
#     advanced_logger_diag.py   1103 (21 felmonster-regler + fonsterrapport)
#     advanced_logger_guards.py  991 (vakter + LogFiles + text/fonster-hjalp)
#   Alla hjalpfiler <= 1200. Alla 27 flyttade + 21 publika metoder bevarade,
#   MRO verifierad, 0 f-strangar / 0 print(). Prio MEDEL -> LOST.
#
# BUG-027: shutdown_logging() anropas av main.pyw (A8, hasattr-guardat) men
#   SAKNADES i advanced_logger <= v2.3.1 -> tyst no-op, sista sekundens
#   loggar kunde tappas. Status: ATGARDAD (v2.4.0, W2): flush + stang filer
#   + aterstall stdout/stderr + avboka after-jobb. Prio MEDEL -> LOST.
#
# ============================================================
# 23. ACCEPTANSKRITERIER
# ============================================================
#
# 1. Programmet startar helt osynligt (withdraw) i systray utan terminalfonster,
#    aven som "python main.py" (BUG-018).
# 2. Endast EN systray-ikon, aven efter reload_plugins (BUG-008b).
# 3. Enkeltryck pa ikonen oppnar fonstret pa ratt position, UTAN gra ruta i
#    toppen (BUG-017).
# 4. X-knappen doljer endast tildfiler heter 1.jpg, 2.jpg, 3.jpg ... [LOST]
# 9. Gallerikort ar skarpa (ej gryniga). [LOST]
# 10. PDF exporteras som pdf1, pdf2 ... och lankas under titeln (BUG-020). [LOST]
# 11. Video exporteras som video1, video2 ... och lankas under titeln. [LOST]
# 12. PDF/video gar att bladdra bland i galleriet som bilder.
# 13. Vid sortering: hall bild + for mot kant -> auto-scroll (BUG-021).
# 14. Alla installningar sparas/laddas korrekt fran config/*.json.
# 15. Mushjul (3 enheter) fungerar i alla scrollbara ytor (Win/Linux/Mac).
# 16. Knappar/tabbar BOLD + hog kontrast i alla 3 teman.
# 17. Filer > 1800 rader har en separat hjalpfil (max 1200) [gallery_view KLAR;
#     html_generator KLAR (BUG-023); advanced_logger KLAR (BUG-026);
#     main.pyw KLAR (v2.8.0 -> main_guards.py, 1789 rader)].
# 20. Inget instansattribut i BasePlugin far skugga en pluginmetod (BUG-024);
#     base_plugin v1.4.1 har skuggningsvakt som loggar vid avvikelse.
# 21. Ingen try/except/else dar else-grenen innehaller felrapportering
#     (BUG-025) - else kOrs nar try-blocket LYCKAS.
# 18. Alla plugins laddas i korrekt PRIORITY-ordning (tab_manager forst).
# 19. (ADOPT-1..6) Sparning ar sjalvlakande (.bak/corrupt-backup), config har
#     schema-version, UI fryser inte vid langsam I/O, och ohanterade fel
#     loggas till kraschlogg med traceback. [NYTT v4.4.0]
# 22. advanced_logger.shutdown_logging() finns och anropas av main.pyw (A8):
#     sista loggarna flushas, filer stangs, stdout/stderr aterstalls
#     (BUG-027). [NYTT v4.6.0]
# 23. advanced_logger loggar UI-handelser utan att nagonsin skriva
#     tangentinnehall fran inmatningsfalt (losenordsskydd, W3). [NYTT v4.6.0]
# 24. Context-observatorn (Y1) loggar context-nycklar men ALDRIG varden;
#     kan stangas av via context_watch=false. Handelsedigest (Y2) ger hogst
#     EN summeringsrad per minut utover detaljraderna. [NYTT v4.7.0]
# 25. Diagnostiken innehaller sessionsdiff (Y7): fel klassas som NYA eller
#     ATERKOMMANDE mot foregaende gallery-logg. [NYTT v4.7.0]
# 26. ui_settings anpassar texten till skarmens DPI (Z3) och vaxlar
#     NORMALT/KOMPAKT lage (<640 px, Z4) utan omstart; layoutskiften
#     loggas. [NYTT v4.8.0]
# 27. ui_settings har INGEN egen register_theme_callback/log/config/
#     widget_exists - allt arvs fran base_plugin v1.4.1 (delad tema-
#     dispatcher, sjalvlakande config). [NYTT v4.8.0]
# 28. image_processor bearbetar parallellt (1-3 workers) men bevarar
#     sorteringsordningen via index, pollar cancel_check och isolerar
#     per-bild-fel; thumbnailen gors ur nedskalad fullsize (minne).
#     [NYTT v4.9.0]
# 29. image_processor har INGEN egen load/save_settings - config
#     (gallery_settings.json) skots av base_plugin v1.4.1. [NYTT v4.9.0]
# 30. main.pyw har en vaktad mainloop (_safe_mainloop): dubbel-anrop
#     sparras, KeyboardInterrupt/TclError/krasch loggas och avslutet
#     ar alltid sakert. [NYTT v4.10.0]
# 31. Fonstergeometri sparas ALDRIG i iconified/withdrawn/zoomed-lage
#     eller med ogiltig storlek (<50x50) - main.pyw M3-vakter.
#     [NYTT v4.10.0]
# 32. main.pyw och slideshow_generator.py har 0 f-strangar och 0
#     print(); main.pyw <= 1800 rader via main_guards.py.
#     [NYTT v4.10.0]
# 33. Appens ikon lases fran icon/ (icon.ico, icon.png,
#     icon_16/32/64/256.png) och anvands i fonster, aktivitetsfalt
#     och systray. Sokordning: icon/ -> assets/ -> generate_app_icon.
#     [NYTT v4.11.0]
# ============================================================
 med ogiltig storlek (<50x50) - main.pyw M3-vakter.
#     [NYTT v4.10.0]
# 32. main.pyw och slideshow_generator.py har 0 f-strangar och 0
#     print(); main.pyw <= 1800 rader via main_guards.py.
#     [NYTT v4.10.0]
# 33. Appens ikon lases fran icon/ (icon.ico, icon.png,
#     icon_16/32/64/256.png) och anvands i fonster, aktivitetsfalt
#     och systray. Sokordning: icon/ -> assets/ -> generate_app_icon.
#     [NYTT v4.11.0]
# ============================================================
 lases fran icon/ (icon.ico, icon.png,
#     icon_16/32/64/256.png) och anvands i fonster, aktivitetsfalt
#     och systray. Sokordning: icon/ -> assets/ -> generate_app_icon.
#     [NYTT v4.11.0]
# ============================================================
