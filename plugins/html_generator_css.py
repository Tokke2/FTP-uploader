#!/usr/bin/env python3
# ============================================================
# Hjalpmodul (CSS) for plugins/html_generator_templates.py
# ============================================================
# FIL: plugins/html_generator_css.py  VERSION: 3.5.0
# Ingen PLUGIN_NAME (laddas som import). Tokens + teman for export.
#
# ÄNDRINGAR v3.3.0 → v3.4.0 (export-design):
#   Nytt visuellt system: FTP-Galleri-brand (kobolt + smaragd),
#   varmt ljust galleritema, aurora-header, kicker, filmiska
#   videokort, lyftta bildkort, glas-lightbox, grain, footer-mark.
#
# ÄNDRINGAR v3.1.0 → v3.2.0 (radjämnt galleri):
#   [L1] flex-radjamnt med --w/--h.  [L2] data-layout=grid.
#   [L3] --cols per brytpunkt.
#
# ÄNDRINGAR v3.0.0 → v3.1.0:
#   [D13-D16] temaväxlare, densitet, THEME_EXTRAS, flex-wrap.
#
# ÄNDRINGAR v2.9.0 → v3.0.0: tokens, auto-tema, a11y, sticky bar,
#   kort/lightbox/video/slideshow, print, reduced-motion, ingen CDN.
#   Legacy-alias --bg2/--fg2/--card-shadow bevarade. Inga f-strings.
# ============================================================

from datetime import datetime

VERSION   = "3.6.0"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

# ============================================================
# 1. DESIGN-TOKENS (tema-oberoende)
# ============================================================

TOKENS_CSS = """
    :root {
      --font-sans: "Segoe UI Variable Display", "Segoe UI", system-ui,
        -apple-system, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, "Cascadia Mono", "Segoe UI Mono", Menlo,
        Consolas, monospace;
      --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
      --sp-5: 24px; --sp-6: 32px; --sp-7: 56px;
      --r-sm: 8px;  --r-md: 14px; --r-lg: 20px; --r-xl: 28px; --r-pill: 999px;
      --t-fast: 140ms; --t-base: 260ms; --t-slow: 520ms;
      --ease: cubic-bezier(.22, .61, .36, 1);
      --ease-out: cubic-bezier(.16, 1, .3, 1);
      --z-bar: 60; --z-totop: 900; --z-lb: 9999;
      --shell: 2200px; --pad: clamp(10px, 2.2vw, 24px); --gap: 8px;
      --thumb-min: 148px; --thumb-ratio: 4 / 3; --radius-card: var(--r-lg);
      --header-pad: clamp(40px, 7vw, 88px);
      --bg2: var(--bg-elev); --fg2: var(--fg-muted);
      --card-shadow: var(--shadow-1);
      --card-hover-shadow: var(--shadow-2);
    }
"""

# ============================================================
# 2. RESET + GRUND + A11Y-BAS
# ============================================================

RESET_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    img, video { max-width: 100%; }
    button, input { font: inherit; color: inherit; }
    ul, ol { list-style: none; }
"""

BASE_CSS = """
    html {
      -webkit-text-size-adjust: 100%;
      scroll-behavior: smooth;
      scroll-padding-top: 96px;
      color-scheme: var(--color-scheme, dark);
    }
    body {
      font-family: var(--font-sans); font-size: 16px; line-height: 1.55;
      min-height: 100vh; color: var(--fg); overflow-x: hidden;
      background-color: var(--bg);
      background-image: var(--page-bg, none);
      background-attachment: fixed;
      -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
    }
    body::before {
      content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
      opacity: var(--grain, .035);
      background-image:
        repeating-linear-gradient(0deg, transparent, transparent 2px,
          rgba(255,255,255,.04) 3px),
        repeating-linear-gradient(90deg, transparent, transparent 3px,
          rgba(0,0,0,.03) 4px);
      mix-blend-mode: overlay;
    }
    body.lb-open { overflow: hidden; }
    a { color: inherit; }
    ::selection { background: var(--accent); color: var(--accent-fg); }
    :focus-visible { outline: 3px solid var(--ring); outline-offset: 3px; }
    .sr-only {
      position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0;
      overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
    }
    * { scrollbar-width: thin; scrollbar-color: var(--border-strong) transparent; }
    ::-webkit-scrollbar { width: 11px; height: 11px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
      background: var(--border-strong); background-clip: content-box;
      border: 2px solid transparent; border-radius: var(--r-pill);
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--accent); background-clip: content-box;
    }
    .skip-link {
      position: absolute; left: var(--sp-4); top: -80px; z-index: 10001;
      padding: 10px 16px; border-radius: var(--r-md);
      background: var(--accent); color: var(--accent-fg);
      font-weight: 700; text-decoration: none;
      transition: top var(--t-base) var(--ease);
    }
    .skip-link:focus { top: var(--sp-4); }
"""

# ============================================================
# 3. HEADER + ATTACHMENTS
# ============================================================

HEADER_CSS = """
    .site-header {
      position: relative; z-index: 1; overflow: hidden; text-align: center;
      isolation: isolate;
      padding: var(--header-pad) var(--pad) clamp(22px, 3.4vw, 40px);
      background: var(--header-bg);
      border-bottom: 1px solid var(--border);
    }
    .site-header::before {
      content: ""; position: absolute; inset: -40% -20% auto; height: 120%;
      pointer-events: none; z-index: 0;
      background:
        radial-gradient(ellipse 50% 70% at 18% 10%,
          var(--accent-soft), transparent 62%),
        radial-gradient(ellipse 46% 60% at 86% 0%,
          color-mix(in srgb, var(--accent-2) 28%, transparent), transparent 58%);
      filter: blur(8px);
    }
    .site-header::after {
      content: ""; position: absolute; left: 50%; bottom: 0; z-index: 1;
      width: min(420px, 56vw); height: 3px; transform: translateX(-50%);
      border-radius: var(--r-pill);
      background: linear-gradient(90deg, transparent, var(--accent) 22%,
        var(--accent-2) 78%, transparent);
      opacity: .85;
    }
    .header-inner {
      position: relative; z-index: 1; max-width: 820px; margin: 0 auto;
    }
    .kicker {
      display: inline-flex; align-items: center; gap: 8px;
      margin: 0 0 var(--sp-4); padding: 5px 14px 5px 10px;
      border: 1px solid var(--border-strong); border-radius: var(--r-pill);
      background: color-mix(in srgb, var(--bg-elev) 70%, transparent);
      color: var(--accent); font-size: .68rem; font-weight: 800;
      letter-spacing: .18em; text-transform: uppercase;
      -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
    }
    .kicker::before {
      content: ""; width: 7px; height: 7px; border-radius: 50%;
      background: var(--accent-2); box-shadow: 0 0 0 4px
        color-mix(in srgb, var(--accent-2) 28%, transparent);
    }
    .site-title {
      margin-bottom: var(--sp-3); color: var(--fg);
      font-size: clamp(2rem, 5.2vw, 3.6rem); font-weight: 800;
      line-height: 1.06; letter-spacing: -.038em; text-wrap: balance;
    }
    .description {
      max-width: 62ch; margin: 0 auto var(--sp-3); color: var(--fg-muted);
      font-size: clamp(1.02rem, 1.5vw, 1.18rem); text-wrap: pretty;
    }
    .meta {
      margin-top: var(--sp-5); color: var(--fg-subtle); font-size: .84rem;
      letter-spacing: .04em; font-variant-numeric: tabular-nums;
    }
    .attachments {
      display: flex; justify-content: center; flex-wrap: wrap;
      gap: var(--sp-3); margin: var(--sp-5) auto var(--sp-1);
    }
    .attachment-link {
      display: inline-flex; align-items: center; gap: 8px; min-height: 40px;
      padding: 8px 16px; border: 1px solid var(--border-strong);
      border-radius: var(--r-pill);
      background: color-mix(in srgb, var(--bg-elev) 80%, transparent);
      color: var(--fg); font-size: .86rem; font-weight: 650;
      text-decoration: none; box-shadow: var(--shadow-1);
      -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
      transition: transform var(--t-fast) var(--ease),
        background var(--t-base) var(--ease),
        border-color var(--t-base) var(--ease), color var(--t-base) var(--ease);
    }
    .attachment-link:hover {
      background: var(--accent); border-color: var(--accent);
      color: var(--accent-fg); transform: translateY(-2px);
    }
"""

# ============================================================
# 4. ACTIONBAR (sticky nav + sok/filter)
# ============================================================

ACTIONBAR_CSS = """
    .actionbar {
      position: sticky; top: 0; z-index: var(--z-bar);
      display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: var(--sp-3); padding: 12px var(--pad);
      background: color-mix(in srgb, var(--bg-elev) 78%, transparent);
      -webkit-backdrop-filter: blur(18px) saturate(170%);
      backdrop-filter: blur(18px) saturate(170%);
      border-bottom: 1px solid var(--border); box-shadow: var(--shadow-1);
    }
    .nav-bar { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2); }
    .nav-btn {
      display: inline-flex; align-items: center; justify-content: center;
      gap: 8px; min-height: 42px; padding: 9px 22px;
      border: 1px solid transparent; border-radius: var(--r-pill);
      background: var(--accent); color: var(--accent-fg);
      font-size: .92rem; font-weight: 750; text-decoration: none;
      cursor: pointer; box-shadow: 0 8px 22px color-mix(in srgb, var(--accent) 32%, transparent);
      transition: transform var(--t-fast) var(--ease),
        box-shadow var(--t-base) var(--ease), filter var(--t-base) var(--ease);
    }
    .nav-btn:hover {
      transform: translateY(-2px); filter: brightness(1.06);
      box-shadow: 0 12px 28px color-mix(in srgb, var(--accent) 42%, transparent);
    }
    .nav-btn.nav-alt {
      background: var(--accent-2); color: #ffffff;
      box-shadow: 0 8px 22px color-mix(in srgb, var(--accent-2) 32%, transparent);
    }
    .nav-btn[aria-current="page"] { box-shadow: inset 0 0 0 2px rgba(255,255,255,.32); }
    .tools { display: none; }
    .js .tools { display: flex; align-items: center; gap: var(--sp-3); }
    .search { position: relative; display: flex; align-items: center; }
    .search-icon {
      position: absolute; left: 13px; display: flex; align-items: center;
      color: var(--fg-subtle); pointer-events: none;
    }
    .search input {
      width: min(38vw, 260px); min-height: 42px; padding: 8px 36px 8px 38px;
      border: 1px solid var(--border-strong); border-radius: var(--r-pill);
      background: var(--bg-sunken); color: var(--fg); font-size: .9rem;
      transition: border-color var(--t-base) var(--ease),
        box-shadow var(--t-base) var(--ease), width var(--t-base) var(--ease);
    }
    .search input::placeholder { color: var(--fg-subtle); }
    .search input:focus {
      width: min(48vw, 340px); border-color: var(--accent);
      box-shadow: 0 0 0 4px var(--accent-soft); outline: none;
    }
    .search input::-webkit-search-cancel-button { display: none; }
    #filter-clear {
      position: absolute; right: 7px; display: none; width: 26px; height: 26px;
      border: 0; border-radius: 50%; background: var(--border-strong);
      color: var(--fg); font-size: .78rem; line-height: 1; cursor: pointer;
    }
    #filter-clear:hover { background: var(--accent); color: var(--accent-fg); }
    .search.filled #filter-clear { display: block; }
    .count-pill {
      padding: 7px 13px; border: 1px solid var(--border);
      border-radius: var(--r-pill); background: var(--bg-sunken);
      color: var(--fg-muted); font-size: .82rem; font-weight: 700;
      white-space: nowrap; font-variant-numeric: tabular-nums;
      transition: color var(--t-base), border-color var(--t-base);
    }
    .count-pill.filtered { color: var(--accent); border-color: var(--accent); }
"""

# ============================================================
# 4b. BESOKARENS VAL (tema-vaxlare + densitet, D13/D14)
# ============================================================

PREFS_CSS = """
    .tool-btn {
      display: inline-flex; align-items: center; justify-content: center;
      gap: 6px; min-height: 42px; padding: 8px 14px; white-space: nowrap;
      border: 1px solid var(--border-strong); border-radius: var(--r-pill);
      background: var(--bg-sunken); color: var(--fg-muted);
      font-size: .82rem; font-weight: 700; cursor: pointer;
      transition: color var(--t-base) var(--ease),
        border-color var(--t-base) var(--ease),
        background var(--t-base) var(--ease),
        transform var(--t-fast) var(--ease);
    }
    .tool-btn:hover {
      color: var(--fg); border-color: var(--accent);
      transform: translateY(-1px);
    }
    .tool-btn[aria-pressed="true"] {
      background: var(--accent-soft); border-color: var(--accent);
      color: var(--accent);
    }
    .tool-btn svg { display: block; }
    /* Densitet (D14) */
    [data-density="compact"] { --gap: 6px; --thumb-min: 110px; --radius-card: var(--r-sm); }
    [data-density="compact"] .card img { aspect-ratio: 1 / 1; }
    [data-density="compact"] .card-overlay {
      padding: 22px 10px 8px; font-size: .78rem;
    }
    [data-density="comfortable"] { --gap: 18px; --thumb-min: 188px; }
    [data-density="comfortable"] .card img { aspect-ratio: 3 / 2; }
    @media (max-width: 700px) {
      .tool-label { display: none; }
      .tool-btn { padding: 8px 11px; }
      .tools { flex-wrap: wrap; justify-content: center; }
    }
"""

# ============================================================
# 5. VIDEOREMSA
# ============================================================

VIDEO_CSS = """
    .video-strip {
      position: relative; z-index: 1; max-width: var(--shell);
      margin: 0 auto; padding: var(--sp-6) var(--pad) 0;
    }
    .video-strip h2 {
      display: flex; align-items: center; gap: 10px; margin: 0 0 var(--sp-4);
      color: var(--fg); font-size: 1.05rem; font-weight: 750;
      letter-spacing: .02em;
    }
    .video-strip h2::after {
      content: ""; flex: 1; height: 1px; background: var(--border);
    }
    .video-grid {
      display: grid; gap: 16px;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--thumb-min)), 1fr));
    }
    .vcard {
      position: relative; isolation: isolate; overflow: hidden;
      border: 1px solid var(--border); border-radius: var(--r-xl);
      background: var(--card-bg); box-shadow: var(--shadow-1); cursor: pointer;
      transition: transform var(--t-base) var(--ease),
        box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease);
    }
    .vcard:hover {
      transform: translateY(-5px);
      border-color: color-mix(in srgb, var(--accent) 55%, var(--border));
      box-shadow: var(--shadow-2);
    }
    .vcard.hidden-by-filter { display: none; }
    .vthumb {
      position: relative; display: flex; align-items: center;
      justify-content: center; width: 100%; aspect-ratio: 16 / 9;
      color: #ffffff; overflow: hidden;
      background:
        radial-gradient(circle at 30% 25%, rgba(255,255,255,.12), transparent 62%),
        linear-gradient(140deg, var(--bg-elev), var(--bg-sunken));
    }
    .vthumb img, .vthumb video {
      position: absolute; inset: 0; width: 100%; height: 100%;
      object-fit: cover; display: block; pointer-events: none; z-index: 0;
      transition: transform var(--t-slow) var(--ease);
    }
    .vcard:hover .vthumb img, .vcard:hover .vthumb video { transform: scale(1.06); }
    .vthumb::after {
      content: ""; position: absolute; inset: 0; pointer-events: none;
      z-index: 1; background: linear-gradient(180deg,
        transparent 48%, rgba(0,0,0,.5) 100%);
    }
    .vthumb .play {
      position: relative; z-index: 2; display: flex; align-items: center;
      justify-content: center; width: 58px; height: 58px;
      border: 2px solid rgba(255,255,255,.78); border-radius: 50%;
      background: rgba(16,24,40,.35); font-size: 1.3rem;
      -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
      box-shadow: 0 10px 28px rgba(0,0,0,.35);
      transition: transform var(--t-base) var(--ease),
        background var(--t-base) var(--ease), border-color var(--t-base);
    }
    .vcard:hover .play {
      transform: scale(1.1); background: var(--accent-2); border-color: #ffffff;
    }
    .vname {
      display: block; padding: 11px 14px; color: var(--fg-muted);
      font-size: .82rem; font-weight: 650; text-align: center;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
"""

# ============================================================
# 6. GALLERI + BILDKORT
# ============================================================

GALLERY_CSS = """
    .gallery {
      position: relative; z-index: 1; display: grid; gap: var(--gap);
      --cols: {{COLUMNS}};
      grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--thumb-min)), 1fr));
      max-width: var(--shell); margin: 0 auto;
      padding: var(--sp-6) var(--pad) var(--sp-7);
    }
    .card {
      position: relative; isolation: isolate; overflow: hidden;
      border: 1px solid var(--border); border-radius: var(--radius-card);
      background: var(--card-bg); box-shadow: var(--card-shadow);
      cursor: pointer; content-visibility: auto;
      contain-intrinsic-size: auto 148px;
      transition: transform var(--t-base) var(--ease),
        box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease);
    }
    .card:hover {
      transform: translateY(-6px) scale(1.016);
      border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
      box-shadow: var(--card-hover-shadow);
    }
    .card img {
      display: block; width: 100%; aspect-ratio: var(--thumb-ratio);
      object-fit: cover; background: var(--bg-sunken); opacity: 0;
      transition: opacity var(--t-slow) var(--ease),
        transform var(--t-slow) var(--ease), filter var(--t-slow) var(--ease);
    }
    .card img.loaded { opacity: 1; }
    .card:hover img { transform: scale(1.07); filter: brightness(1.06) saturate(1.06); }
    .card img.failed {
      opacity: 1; object-fit: contain; padding: 16% 12%;
      filter: grayscale(1) opacity(.6);
    }
    .card::before {
      content: ""; position: absolute; inset: 0; z-index: 0;
      pointer-events: none; opacity: .55;
      background: linear-gradient(105deg, transparent 18%,
        var(--accent-soft) 46%, transparent 68%);
      background-size: 220% 100%;
      animation: shimmer 1.6s linear infinite;
    }
    .card.done::before { display: none; }
    @keyframes shimmer {
      from { background-position: 120% 0; }
      to   { background-position: -120% 0; }
    }
    .card::after {
      content: ""; position: absolute; inset: 0; z-index: 1;
      pointer-events: none;
      background: linear-gradient(180deg, rgba(255,255,255,.06),
        transparent 26%, transparent 58%, rgba(0,0,0,.28));
    }
    .card-overlay {
      position: absolute; left: 0; right: 0; bottom: 0; z-index: 2;
      padding: 40px 14px 12px; color: #ffffff; font-size: .86rem;
      font-weight: 650; letter-spacing: .01em;
      text-shadow: 0 1px 8px rgba(0,0,0,.85);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      background: linear-gradient(transparent, rgba(0,0,0,.82));
      opacity: 0; transform: translateY(8px);
      transition: opacity var(--t-base) var(--ease),
        transform var(--t-base) var(--ease);
    }
    .card:hover .card-overlay,
    .card:focus-visible .card-overlay { opacity: 1; transform: none; }
    .card-num {
      position: absolute; top: 10px; left: 10px; z-index: 3; padding: 4px 10px;
      border-radius: var(--r-pill);
      background: color-mix(in srgb, var(--overlay) 88%, transparent);
      color: #ffffff; font-size: .72rem; font-weight: 750; letter-spacing: .04em;
      font-variant-numeric: tabular-nums;
      box-shadow: 0 4px 14px rgba(0,0,0,.35);
      -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
    }
    .card-fmt {
      position: absolute; top: 10px; right: 10px; z-index: 3; padding: 4px 9px;
      border-radius: var(--r-pill);
      background: color-mix(in srgb, var(--overlay) 88%, transparent);
      color: #ffffff; font-size: .62rem; font-weight: 800; letter-spacing: .08em;
      text-transform: uppercase; opacity: 0;
      -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
      transition: opacity var(--t-base) var(--ease);
    }
    .card:hover .card-fmt,
    .card:focus-visible .card-fmt { opacity: 1; }
    /* More legible cards and a calm, keyboard-accessible inspection state. */
    .card:focus-visible {
      outline: 3px solid var(--ring); outline-offset: 3px;
      border-color: var(--accent); z-index: 4;
    }
    [data-density="comfortable"] .card img {
      object-fit: contain; background: var(--bg-sunken);
    }
    [data-density="comfortable"] .card-overlay {
      opacity: 1; transform: none;
    }
    .card.hidden-by-filter { display: none; }
    @media (hover: none) {
      .card-overlay { opacity: 1; transform: none; }
      .card-fmt { opacity: 1; }
      .card:hover, .js .card.in:hover { transform: none; }
      .card:hover img { transform: none; filter: none; }
    }
    .empty-state {
      max-width: var(--shell); margin: 0 auto; padding: var(--sp-7) var(--pad);
      color: var(--fg-subtle); font-size: 1rem; text-align: center;
    }
    .empty-state[hidden] { display: none; }
    .js .card { opacity: 0; transform: translateY(18px) scale(.98); }
    .js .card.in {
      opacity: 1; transform: none;
      transition: opacity var(--t-slow) var(--ease),
        transform var(--t-slow) var(--ease-out),
        box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease);
    }
    .js .card.in:hover { transform: translateY(-6px) scale(1.016); }
"""

# ============================================================
# 6b. RADJAMN LAYOUT (L1) - bilder i sina egna proportioner
# ============================================================

LAYOUT_CSS = """
    /* Med JS ar radjamnt standard; utan JS galler rutnatet ovan (L1).
       Kortens bredd/hojd satts av JS (--w/--h) utifran bildens
       proportion (--ar, injicerad av html_generator.py). Fore dess
       galler --w-fallback sa forsta paint inte hoppar. */
    .js .gallery {
      display: flex;
      flex-wrap: wrap;
      align-content: flex-start;
    }
    .js .gallery .card {
      --w-fallback: calc(
        (100% - ({{COLUMNS}} - 1) * var(--gap)) / {{COLUMNS}}
      );
      /* shrink 1: om avrundade --w summerar over radbredden krymper
         korten i stallet for att sista kortet bryts till ny rad. */
      flex: 0 1 auto; min-width: 0;
      width: var(--w, var(--w-fallback));
      height: var(--h, 144px);
      contain-intrinsic-size: auto var(--h, 144px);
    }
    .js .gallery .card img {
      height: 100%;
      aspect-ratio: auto;
    }
    /* Besokaren har valt rutnat (L2) - attributet sitter pa <html>
       precis som data-theme/data-density, sa BOOT_JS kan satta det
       fore forsta paint. Specificiteten slar .js .gallery ovan. */
    html[data-layout="grid"] .gallery {
      display: grid;
      align-content: stretch;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--thumb-min)), 1fr));
    }
    html[data-layout="grid"] .gallery .card { width: auto; height: auto; }
    html[data-layout="grid"] .gallery .card img {
      height: auto;
      aspect-ratio: var(--thumb-ratio);
    }
    /* Peko/Smalt: lagre rader sa att radjamnt inte ger jattebilder */
    @media (max-width: 700px) {
      .js .gallery .card { height: var(--h, 120px); }
    }
    @media (hover: none) {
      .js .gallery .card img { aspect-ratio: auto; }
    }
"""

# ============================================================
# 7. LIGHTBOX
# ============================================================

LIGHTBOX_CSS = """
    #lightbox {
      position: fixed; inset: 0; z-index: var(--z-lb); display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto; gap: var(--sp-2);
      padding: var(--sp-3) clamp(8px, 2vw, 20px)
        calc(var(--sp-3) + env(safe-area-inset-bottom, 0px));
      background: var(--scrim);
      -webkit-backdrop-filter: blur(22px) saturate(140%);
      backdrop-filter: blur(22px) saturate(140%);
      opacity: 0; visibility: hidden;
      transition: opacity var(--t-base) var(--ease), visibility var(--t-base);
    }
    #lightbox.active { opacity: 1; visibility: visible; }
    .lb-top { display: flex; align-items: center; justify-content: flex-end; gap: var(--sp-3); }
    .lb-counter {
      margin-right: auto; color: #e8ecf6; font-size: .88rem; font-weight: 750;
      letter-spacing: .08em; font-variant-numeric: tabular-nums;
    }
    .lb-actions { display: flex; align-items: center; gap: 6px; }
    .lb-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 44px; height: 44px; border: 1px solid rgba(255,255,255,.16);
      border-radius: 50%; background: rgba(255,255,255,.1); color: #ffffff;
      font-size: 1rem; text-decoration: none; cursor: pointer;
      -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
      transition: background var(--t-fast) var(--ease),
        transform var(--t-fast) var(--ease);
    }
    .lb-icon:hover { background: rgba(255,255,255,.24); transform: translateY(-1px); }
    .lb-icon.off { opacity: .35; pointer-events: none; }
    .lb-icon.ok {
      color: var(--accent-2); border-color: var(--accent-2);
      background: rgba(34, 197, 94, .18);
    }
    #lb-close { width: 48px; height: 48px; font-size: 1.2rem; }
    .lb-icon svg, .lb-btn svg, .to-top svg, .tb-btn svg,
    .nav-arrow svg, .search-icon svg { display: block; }
    .lb-stage {
      position: relative; display: flex; align-items: center;
      justify-content: center; min-height: 0; touch-action: pan-y;
    }
    #lb-img, #lb-video {
      max-width: min(94vw, 1680px); max-height: 78vh; object-fit: contain;
      border-radius: var(--r-md);
      box-shadow: 0 28px 80px rgba(0,0,0,.62), 0 0 0 1px rgba(255,255,255,.08);
      user-select: none; -webkit-user-select: none;
    }
    #lb-img { cursor: zoom-in; transition: transform var(--t-base) var(--ease); }
    #lb-img.zoomed {
      max-width: none; max-height: none; cursor: grab;
      transform: scale(var(--z, 2)) translate(var(--tx, 0px), var(--ty, 0px));
    }
    #lb-img.dragging { cursor: grabbing; transition: none; }
    #lb-video { display: none; width: auto; background: #000000; outline: none; }
    .lb-spinner {
      position: absolute; width: 48px; height: 48px; border-radius: 50%;
      border: 3px solid rgba(255,255,255,.16); border-top-color: var(--accent);
      animation: spin .85s linear infinite; opacity: 0; pointer-events: none;
      transition: opacity var(--t-base) var(--ease);
    }
    .lb-spinner.show { opacity: 1; }
    @keyframes spin { to { transform: rotate(360deg); } }
    #lb-error {
      position: absolute; display: none; padding: 8px 15px;
      border-radius: var(--r-pill); background: rgba(140,26,26,.72);
      color: #ffe1e1; font-size: .88rem;
    }
    #lb-error.show { display: block; }
    .lb-btn {
      position: absolute; top: 50%; z-index: 2; display: flex;
      align-items: center; justify-content: center; width: 58px; height: 58px;
      transform: translateY(-50%); border: 1px solid rgba(255,255,255,.16);
      border-radius: 50%; background: rgba(255,255,255,.1); color: #ffffff;
      font-size: 2rem; line-height: 1; cursor: pointer;
      -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
      transition: background var(--t-fast) var(--ease),
        transform var(--t-fast) var(--ease);
    }
    .lb-btn:hover { background: rgba(255,255,255,.26); transform: translateY(-50%) scale(1.06); }
    #lb-prev { left: clamp(4px, 1.4vw, 18px); }
    #lb-next { right: clamp(4px, 1.4vw, 18px); }
    .lb-bottom { display: grid; justify-items: center; gap: 8px; text-align: center; }
    .lb-caption { max-width: 86vw; color: #f2f4fa; font-size: 1rem; line-height: 1.4; }
    .lb-hint { color: #9aa3b8; font-size: .76rem; letter-spacing: .02em; }
    .lb-strip {
      display: flex; gap: 8px; max-width: min(94vw, 1100px);
      padding: 8px 4px; overflow-x: auto; scroll-behavior: smooth;
    }
    .lb-strip.hidden { display: none; }
    .strip-item {
      flex: 0 0 auto; width: 68px; height: 50px; padding: 0; overflow: hidden;
      border: 2px solid transparent; border-radius: var(--r-sm);
      background: rgba(255,255,255,.08); cursor: pointer; opacity: .45;
      transition: opacity var(--t-fast) var(--ease),
        border-color var(--t-fast) var(--ease), transform var(--t-fast) var(--ease);
    }
    .strip-item img { display: block; width: 100%; height: 100%; object-fit: cover; }
    .strip-item:hover { opacity: .95; transform: translateY(-2px); }
    .strip-item.active { opacity: 1; border-color: var(--accent); }
    .strip-item.video {
      display: flex; align-items: center; justify-content: center;
      color: #ffffff; font-size: .95rem;
    }
"""

# ============================================================
# 8. OVRIGT (tillbaka-till-topp, footer)
# ============================================================

EXTRA_CSS = """
    .to-top {
      position: fixed; right: 18px; z-index: var(--z-totop); display: none;
      bottom: calc(18px + env(safe-area-inset-bottom, 0px));
      width: 48px; height: 48px; border: 1px solid var(--border-strong);
      border-radius: 50%; background: var(--bg-elev); color: var(--fg);
      font-size: 1.05rem; cursor: pointer; box-shadow: var(--shadow-2);
      opacity: 0; visibility: hidden; transform: translateY(10px);
      transition: opacity var(--t-base) var(--ease),
        transform var(--t-base) var(--ease), visibility var(--t-base),
        background var(--t-base) var(--ease), color var(--t-base) var(--ease);
    }
    .js .to-top { display: block; }
    .to-top.show { opacity: 1; visibility: visible; transform: none; }
    .to-top:hover { background: var(--accent); color: var(--accent-fg); }
    .site-footer {
      position: relative; z-index: 1; color: var(--fg-subtle);
      font-size: .78rem; letter-spacing: .08em; text-transform: uppercase;
      text-align: center;
      padding: var(--sp-6) var(--pad)
        calc(var(--sp-6) + env(safe-area-inset-bottom, 0px));
    }
    .site-footer::before {
      content: ""; display: block; width: 52px; height: 3px;
      margin: 0 auto 16px; border-radius: var(--r-pill);
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }
"""

# ============================================================
# 9. RESPONSIVT + REDUCED MOTION + PRINT
# ============================================================

RESPONSIVE_CSS = """
    @media (max-width: 1300px) {
      .gallery { --cols: {{COLUMNS_4}}; --thumb-min: 140px; }
    }
    @media (max-width: 950px) {
      .gallery { --cols: {{COLUMNS_3}}; --thumb-min: 132px; }
    }
    @media (max-width: 700px) {
      :root { --gap: 8px; --thumb-min: 124px; }
      .gallery { --cols: 2; }
      .nav-btn, .attachment-link, .prefs-btn { min-height: 44px; }
      .card-overlay { font-size: .82rem; padding: 32px 10px 10px; }
      .actionbar {
        flex-direction: column; align-items: stretch; gap: 8px;
        padding: 8px 12px;
      }
      .nav-btn { flex: 1 1 auto; }
      .search input, .search input:focus { width: 100%; }
      .count-pill { text-align: center; }
      .attachments { gap: 8px; }
      .attachment-link { flex: 1 1 auto; justify-content: center; }
      #lb-img, #lb-video { max-width: 96vw; max-height: 68vh; }
      .lb-btn { width: 48px; height: 48px; font-size: 1.6rem; }
      .lb-hint { display: none; }
      .strip-item { width: 54px; height: 40px; }
      .lb-icon { width: 44px; height: 44px; }
      #lb-close { width: 44px; height: 44px; }
    }
    @media (max-width: 420px) {
      .gallery { --cols: 1; --thumb-min: 160px; }
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      *, *::before, *::after {
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
      }
      .js .card { opacity: 1; transform: none; }
      .card img { opacity: 1; }
    }
    @media print {
      .actionbar, .to-top, #lightbox, .site-header::after { display: none; }
      body { background: #ffffff; color: #000000; }
      .gallery {
        grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px;
        padding: 0;
      }
      .card { break-inside: avoid; border: 1px solid #cccccc; box-shadow: none; }
      .card::before { display: none; }
      .card img { opacity: 1; }
      .card-overlay {
        opacity: 1; transform: none; background: none; color: #000000;
        text-shadow: none;
      }
    }
"""

# ============================================================
# 10. SLIDESHOW-CSS
# ============================================================

SS_BASE_CSS = """
    html, body { height: 100%; }
    body {
      display: flex; flex-direction: column; overflow: hidden;
      background: #000000;
    }
    .ss-toolbar {
      display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
      z-index: 5; padding: 10px 18px; color: #ffffff;
      background: rgba(0,0,0,.42);
      -webkit-backdrop-filter: blur(10px) saturate(140%);
      backdrop-filter: blur(10px) saturate(140%);
      border-bottom: 1px solid rgba(255,255,255,.08);
      transition: opacity var(--t-slow) var(--ease),
        transform var(--t-slow) var(--ease);
    }
    .ss-toolbar.idle {
      opacity: 0; transform: translateY(-102%); pointer-events: none;
    }
    .ss-toolbar h1 {
      max-width: 38vw; margin-right: auto; font-size: 1rem; font-weight: 750;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .attachments { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
    .attachment-link {
      display: inline-flex; align-items: center; gap: 5px; padding: 5px 11px;
      border: 1px solid rgba(255,255,255,.18); border-radius: var(--r-pill);
      background: rgba(255,255,255,.08); color: #ffffff; font-size: .8rem;
      font-weight: 650; text-decoration: none;
      transition: background var(--t-base), border-color var(--t-base);
    }
    .attachment-link:hover { background: var(--accent); border-color: var(--accent); }
    .tb-btn {
      display: inline-flex; align-items: center; justify-content: center;
      gap: 6px; min-height: 38px; padding: 8px 15px;
      border: 1px solid rgba(255,255,255,.14); border-radius: var(--r-pill);
      background: var(--btn-bg, rgba(255,255,255,.12)); color: #ffffff;
      font-size: .85rem; font-weight: 700; white-space: nowrap;
      text-decoration: none; cursor: pointer;
      transition: background var(--t-base) var(--ease),
        transform var(--t-fast) var(--ease), opacity var(--t-base) var(--ease);
    }
    .tb-btn:hover { transform: translateY(-1px); filter: brightness(1.1); }
    .tb-btn.primary { --btn-bg: var(--accent-2); border-color: transparent; }
    .tb-btn.paused  { --btn-bg: #4b5563; }
    .tb-btn.info    { --btn-bg: var(--accent); border-color: transparent; }
    .tb-btn.ghost   { --btn-bg: rgba(255,255,255,.12); }
    .tb-btn.off     { opacity: .5; }
    .counter {
      color: rgba(255,255,255,.82); font-size: .86rem; white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }
    .speed-wrap {
      display: flex; align-items: center; gap: 8px;
      color: rgba(255,255,255,.85); font-size: .82rem; white-space: nowrap;
    }
    input[type="range"] { width: 96px; accent-color: var(--accent); cursor: pointer; }
    #speed-label { min-width: 2.6em; font-variant-numeric: tabular-nums; }
"""

SS_STAGE_CSS = """
    .progress-bar {
      flex-shrink: 0; height: 4px; z-index: 5; background: rgba(255,255,255,.12);
    }
    .progress-fill {
      height: 100%; width: 0;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }
    .slide-area {
      position: relative; display: flex; align-items: center;
      justify-content: center; flex: 1; min-height: 0; overflow: hidden;
      background: #000000; touch-action: pan-y;
    }
    .slide {
      position: absolute; inset: 0; display: flex; align-items: center;
      justify-content: center; opacity: 0; visibility: hidden;
      transition: opacity var(--t-slow) var(--ease), visibility var(--t-slow);
    }
    .slide.active { opacity: 1; visibility: visible; }
    .slide img {
      max-width: 100%; max-height: 100%; object-fit: contain;
      background: rgba(128,128,128,.04);
      user-select: none; -webkit-user-select: none;
    }
    .slide.active img { animation: kenburns 14s var(--ease-out) both; }
    @keyframes kenburns {
      from { transform: scale(1) translate3d(0, 0, 0); }
      to   { transform: scale(1.07) translate3d(0, -1%, 0); }
    }
    .caption {
      position: absolute; left: 0; right: 0; bottom: 0;
      padding: 30px 16px 14px; color: #ffffff; font-size: .92rem;
      text-align: center; text-shadow: 0 1px 4px rgba(0,0,0,.9);
      background: linear-gradient(transparent, rgba(0,0,0,.78));
      transition: opacity var(--t-base) var(--ease);
    }
    body.no-caption .caption { opacity: 0; }
    .nav-arrow {
      position: absolute; top: 50%; z-index: 10; display: flex;
      align-items: center; justify-content: center; width: 56px; height: 56px;
      transform: translateY(-50%); border: 1px solid rgba(255,255,255,.16);
      border-radius: 50%; background: rgba(255,255,255,.12); color: #ffffff;
      font-size: 2rem; line-height: 1; cursor: pointer; opacity: .82;
      -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px);
      transition: background var(--t-fast) var(--ease),
        transform var(--t-fast) var(--ease), opacity var(--t-base) var(--ease);
    }
    .nav-arrow:hover {
      background: rgba(255,255,255,.28); opacity: 1;
      transform: translateY(-50%) scale(1.05);
    }
    #ss-prev { left: clamp(6px, 1.6vw, 20px); }
    #ss-next { right: clamp(6px, 1.6vw, 20px); }
    .hint {
      position: absolute; top: 12px; left: 50%; z-index: 8;
      transform: translateX(-50%); padding: 6px 13px;
      border-radius: var(--r-pill); background: rgba(0,0,0,.42);
      color: rgba(255,255,255,.78); font-size: .74rem; white-space: nowrap;
      -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
      transition: opacity var(--t-slow) var(--ease);
    }
    .hint.fade { opacity: 0; }
"""

SS_RESPONSIVE_CSS = """
    @media (max-width: 900px) {
      .ss-toolbar h1 { max-width: 100%; flex-basis: 100%; }
      .speed-wrap label { display: none; }
    }
    @media (max-width: 760px) {
      .ss-toolbar { gap: 6px; padding: 8px 12px; }
      .counter { font-size: .8rem; }
      .speed-wrap { display: none; }
      .nav-arrow { width: 48px; height: 48px; font-size: 1.5rem; }
      .hint { display: none; }
    }
    @media (max-height: 520px) and (orientation: landscape) {
      .ss-toolbar { display: none; }
      .progress-bar { height: 2px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .slide.active img { animation: none; }
      .slide { transition: opacity .001ms; }
      .ss-toolbar { transition: none; }
    }
"""

# ============================================================
# 11. SAMMANSATTNING
# ============================================================

INDEX_CSS = "\n".join((
    TOKENS_CSS, RESET_CSS, BASE_CSS, HEADER_CSS, ACTIONBAR_CSS, PREFS_CSS,
    VIDEO_CSS, GALLERY_CSS, LAYOUT_CSS, LIGHTBOX_CSS, EXTRA_CSS,
    RESPONSIVE_CSS,
))

SLIDESHOW_CSS = "\n".join((
    TOKENS_CSS, RESET_CSS, BASE_CSS, PREFS_CSS,
    SS_BASE_CSS, SS_STAGE_CSS, SS_RESPONSIVE_CSS,
))

# ============================================================
# 12. TEMAN (tokens + extras)
# ============================================================

#: Gangbara temaid (utdata fran normalize_theme)
THEME_IDS = ("dark", "light", "colorful", "auto")

#: Standardtema om indata ar tom/okand
DEFAULT_THEME = "dark"

#: "system" (skickas av ui_settings) mappas till detta tema.
#: "auto" = folj besokarens prefers-color-scheme (D2).
#: Satt till "dark" for exakt gammalt beteende.
SYSTEM_THEME_MODE = "auto"

THEME_TOKENS = {
    "dark": {
        "--theme-id": "dark",
        "--color-scheme": "dark",
        "--meta-theme-color": "#070B14",
        "--bg": "#070B14",
        "--bg-elev": "#101827",
        "--bg-sunken": "#05080F",
        "--page-bg": "radial-gradient(1200px 620px at 12% -8%,"
                     " rgba(74,158,255,.16), transparent 62%),"
                     " radial-gradient(900px 520px at 92% 8%,"
                     " rgba(34,197,94,.10), transparent 58%)",
        "--fg": "#F3F5FB",
        "--fg-muted": "#B8C0D4",
        "--fg-subtle": "#8791A8",
        "--card-bg": "#121A2C",
        "--border": "rgba(255,255,255,.08)",
        "--border-strong": "rgba(255,255,255,.18)",
        "--accent": "#4A9EFF",
        "--accent-fg": "#06101C",
        "--accent-soft": "rgba(74,158,255,.20)",
        "--accent-2": "#22C55E",
        "--ring": "#7CB8FF",
        "--shadow-1": "0 4px 18px rgba(0,0,0,.38)",
        "--shadow-2": "0 22px 50px rgba(0,0,0,.55),"
                      " 0 0 0 1px rgba(74,158,255,.16)",
        "--header-bg": "linear-gradient(180deg, #0C1B38 0%,"
                       " #070B14 72%)",
        "--overlay": "rgba(5,8,16,.58)",
        "--scrim": "rgba(3,5,10,.92)",
        "--grain": ".04",
    },
    "light": {
        "--theme-id": "light",
        "--color-scheme": "light",
        "--meta-theme-color": "#F4F0E8",
        "--bg": "#F4F0E8",
        "--bg-elev": "#FFFdf8",
        "--bg-sunken": "#E8E2D6",
        "--page-bg": "radial-gradient(1100px 540px at 18% -12%,"
                     " rgba(29,78,216,.10), transparent 64%),"
                     " radial-gradient(800px 480px at 90% 0%,"
                     " rgba(21,128,61,.07), transparent 60%)",
        "--fg": "#17150F",
        "--fg-muted": "#4A453A",
        "--fg-subtle": "#6F685C",
        "--card-bg": "#FFFFFF",
        "--border": "rgba(28,22,12,.10)",
        "--border-strong": "rgba(28,22,12,.18)",
        "--accent": "#1D4ED8",
        "--accent-fg": "#ffffff",
        "--accent-soft": "rgba(29,78,216,.14)",
        "--accent-2": "#15803D",
        "--ring": "#1D4ED8",
        "--shadow-1": "0 2px 8px rgba(40,28,8,.08),"
                      " 0 8px 22px rgba(40,28,8,.06)",
        "--shadow-2": "0 18px 44px rgba(40,28,8,.16)",
        "--header-bg": "linear-gradient(180deg, #FFFaf3 0%,"
                       " #F4F0E8 78%)",
        "--overlay": "rgba(20,16,8,.50)",
        "--scrim": "rgba(18,16,12,.88)",
        "--grain": ".025",
    },
    "colorful": {
        "--theme-id": "colorful",
        "--color-scheme": "dark",
        "--meta-theme-color": "#0C081C",
        "--bg": "#0C081C",
        "--bg-elev": "#16102E",
        "--bg-sunken": "#080514",
        "--page-bg": "radial-gradient(900px 520px at 8% -8%,"
                     " rgba(247,37,133,.26), transparent 62%),"
                     " radial-gradient(900px 520px at 96% 4%,"
                     " rgba(76,201,240,.20), transparent 58%)",
        "--fg": "#FFFFFF",
        "--fg-muted": "#D9CFFB",
        "--fg-subtle": "#A99BD6",
        "--card-bg": "rgba(255,255,255,.07)",
        "--border": "rgba(255,255,255,.12)",
        "--border-strong": "rgba(255,255,255,.26)",
        "--accent": "#F72585",
        "--accent-fg": "#ffffff",
        "--accent-soft": "rgba(247,37,133,.22)",
        "--accent-2": "#4CC9F0",
        "--ring": "#F72585",
        "--shadow-1": "0 8px 28px rgba(0,0,0,.42)",
        "--shadow-2": "0 20px 52px rgba(247,37,133,.32)",
        "--header-bg": "linear-gradient(160deg, #140C32 0%,"
                       " #0C081C 70%)",
        "--overlay": "rgba(0,0,0,.52)",
        "--scrim": "rgba(8,5,20,.94)",
        "--grain": ".05",
    },
}

#: Tema-specifika justeringar utover tokens.
#: {SCOPE} ersatts med "" (for :root) eller '[data-theme="x"]' (D15).
THEME_EXTRAS = {
    "dark": """
    {SCOPE} .card { background: var(--card-bg); }
""",
    "light": """
    {SCOPE} .card-num, {SCOPE} .card-fmt { background: rgba(22,16,8,.48); }
    {SCOPE} .card::after {
      background: linear-gradient(180deg, transparent 58%, rgba(20,14,6,.16));
    }
    {SCOPE} .lb-caption, {SCOPE} .lb-counter { color: #eef1f7; }
    {SCOPE} .site-title { letter-spacing: -.042em; }
""",
    "colorful": """
    {SCOPE} .site-title {
      background: linear-gradient(92deg, #f72585, #b5179e 42%, #4cc9f0);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    {SCOPE} .card {
      -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
    }
    {SCOPE} .nav-btn.nav-alt { background: #4cc9f0; color: #06263a; }
    {SCOPE} .kicker { color: #4cc9f0; }
""",
}

#: Alias -> gangbart temaid (K3)
THEME_ALIASES = {
    "":           DEFAULT_THEME,
    "none":       DEFAULT_THEME,
    "default":    DEFAULT_THEME,
    "dark":       "dark",
    "mork":       "dark",
    "mörk":       "dark",
    "morkt":      "dark",
    "mörkt":      "dark",
    "natt":       "dark",
    "light":      "light",
    "ljus":       "light",
    "ljust":      "light",
    "vit":        "light",
    "white":      "light",
    "colorful":   "colorful",
    "colourful":  "colorful",
    "fargglad":   "colorful",
    "färgglad":   "colorful",
    "farg":       "colorful",
    "color":      "colorful",
    "neon":       "colorful",
    "auto":       "auto",
    "adaptiv":    "auto",
    "adaptive":   "auto",
    "system":     SYSTEM_THEME_MODE,
    "systemet":   SYSTEM_THEME_MODE,
    "os":         SYSTEM_THEME_MODE,
}


def normalize_theme(theme) -> str:
    """
    Normalisera temanamn till ett av THEME_IDS.

    Accepterar None, skiftlage, mellanslag, bindestreck samt
    svenska/engelska alias (t.ex. "System", "Mörkt", "färgglad").
    Okant varde -> DEFAULT_THEME.

    Returnerar:
        "dark" | "light" | "colorful" | "auto"
    """
    if theme is None:
        return DEFAULT_THEME
    key = str(theme).strip().lower().replace("-", "_")
    if key in THEME_IDS:
        return key
    if key in THEME_ALIASES:
        return THEME_ALIASES[key]
    return DEFAULT_THEME


def theme_ids() -> tuple:
    """Returnera gangbara temaid (for validering/UI)."""
    return THEME_IDS


def _tokens_css(tokens: dict, indent: str = "    ",
                selector: str = ":root") -> str:
    """Rendera en token-dict till ett CSS-block (bevarar ordning)."""
    pad = indent + "  "
    lines = ["%s%s {" % (indent, selector)]
    for key, value in tokens.items():
        lines.append("%s%s: %s;" % (pad, key, value))
    lines.append("%s}" % indent)
    return "\n".join(lines)


def theme_block(name: str, indent: str = "    ", scope: str = "") -> str:
    """
    Rendera tokens + extras for ETT tema.

    scope="" ger ett :root-block (standard). scope='[data-theme="x"]'
    ger ett block som styr samma tokens via attribut (D13/D15).
    """
    tid = normalize_theme(name)
    if tid == "auto":
        tid = "dark"
    selector = scope.strip() or ":root"
    parts = [_tokens_css(THEME_TOKENS[tid], indent, selector)]
    extra = THEME_EXTRAS.get(tid, "")
    if extra:
        parts.append(extra.replace("{SCOPE}", scope).rstrip("\n"))
    return "\n".join(parts)


def switcher_css(base_theme: str, indent: str = "    ") -> str:
    """
    CSS-block som gor temat vaxlingsbart i sidan (D13).

    Skriver [data-theme="dark"] och [data-theme="light"] (samt
    [data-theme="colorful"] om det ar grundtemat). "auto" behover inget
    block - da galler :root + prefers-color-scheme.
    """
    base = normalize_theme(base_theme)
    names = ["dark", "light"]
    if base == "colorful":
        names.append("colorful")

    out = ["", "%s/* Besokaren kan vaxla tema (D13) */" % indent]
    for name in names:
        out.append(theme_block(
            name, indent, '[data-theme="%s"]' % name
        ))
    return "\n".join(out)


def render_theme_css(theme) -> str:
    """
    Returnera tema-CSS for valt tema (ersatter {{THEME_CSS}}).

    Innehaller:
      1. :root med det valda temats tokens (grundtema)
      2. for "auto"/"system": @media (prefers-color-scheme: light) (D2)
      3. [data-theme=...]-block sa besökaren kan vaxla tema (D13)

    OBS: Detta ar BAS-CSS. custom_css_editor lagger till extra CSS
    ovanpa ({{CUSTOM_CSS}} kommer sist i <style>).
    """
    tid = normalize_theme(theme)
    parts = [theme_block(tid if tid != "auto" else "dark")]

    if tid == "auto":
        media_indent = "      "
        light = _tokens_css(THEME_TOKENS["light"], media_indent)
        light_extra = THEME_EXTRAS.get("light", "").replace("{SCOPE}", "")
        light_extra = light_extra.rstrip("\n")
        if light_extra:
            light = light + "\n" + light_extra
        parts.extend([
            "",
            "    /* auto: folj besokarens systemtema (D2) */",
            "    @media (prefers-color-scheme: light) {",
            light,
            "    }",
        ])

    parts.append(switcher_css(tid))
    return "\n".join(parts)


#: Bakatkompatibilitet: tidigare namn pa samma funktion
get_theme_css = render_theme_css
