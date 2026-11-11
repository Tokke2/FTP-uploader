#!/usr/bin/env python3
# ============================================================
# Hjalpmodul (mixin) for plugins/html_generator.py
# ============================================================
# FIL:       plugins/html_generator_templates.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/html_generator_templates.py)
# Klass:     HtmlTemplatesMixin
# VERSION:   3.3.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
# Syfte:     HTML-skeletten for de genererade sidorna (index.html och
#            slideshow.html) + tema-API. Haller html_generator.py under
#            1800 rader (BUG-023).
#
#            HtmlGenerator arver fran denna mixin:
#                class HtmlGenerator(HtmlTemplatesMixin, BasePlugin)
#            OBS: INGEN PLUGIN_NAME har -> ignoreras av plugin-loadern.
#
# STRUCTUR v3.0.0 (tre hjalpmoduler - ingen nar 1200-gransen, KRAV 17):
#   plugins/html_generator.py            logik (replace + filskrivning)
#   plugins/html_generator_templates.py  HTML-skelett + mixin (DENNA FIL)
#   plugins/html_generator_css.py        design-tokens, komponent-CSS, teman
#   plugins/html_generator_js.py         galleri-/lightbox-/slideshow-JS
#
# ÄNDRINGAR v3.2.0 → v3.3.0: kicker i sidhuvud. v3.1→3.2 radjämn:
#   [L1]      RADJÄMNT (justified) galleri är nu standard: bilderna visas i
#             sina egna proportioner utan beskärning, i rader som fyller
#             bredden exakt (Flickr/Google Photos-stil). Ordningen är
#             oförändrad (till skillnad från CSS-columns-masonry).
#   [L2]      Layoutväxlare i sidan: Radjämnt ↔ Rutnät (sparas i
#             localStorage, precis som tema/densitet). Rutnät = gamla
#             beteendet med {{COLUMNS}} kolumner och 4:3-beskärning.
#   [L3]      data-columns="{{COLUMNS}}" på <main> → JS räknar radhöjd ur
#             användarens kolumninställning.
#   [L4]      Kortens proportion kommer från html_generator.py som
#             `style="--ar:1.5"` (PIL-huvudläsning + EXIF-orientation) →
#             layouten är klar före bilderna laddats (ingen reflow-flash).
#             Saknas --ar mäter JS naturalWidth/Height i efterhand.
#
# ÄNDRINGAR v3.0.0 → v3.1.0 (besökaren styr sidan + render-API):
#   [D13] Tema-växlare i sidan: auto -> mörk -> ljus -> färgglad (sparas i
#         localStorage, återställs före första paint).  [D14] Densitetsväxlare:
#         standard -> kompakt (1:1) -> bekväm (3:2).  [D17] Dela-knapp i
#         lightboxen (kopierar länk till aktuell bild).
#   [J14] Djuplänkar: #bild-7 / #video-2 öppnar lightboxen direkt och hashen
#         följer med vid bläddring (history.replaceState).
#   [K8]  render_template(which, values, log): mallrenderingen flyttad till
#         mixinen - dict istället för 20 kedjade .replace()-anrop. Saknade
#         värden loggas. Gamla replace()-anrop fungerar fortfarande.
#   [K9]  asset_warning()/self_check() upptäcker VERSIONSDRIFT mellan
#         templates/css/js.  [K10] Reservmallarna bantade (döljer avancerade
#         verktyg i reservläge så inga döda kontroller visas).
#
# ÄNDRINGAR v2.9.0 → v3.0.0 (sammandrag):
#   DESIGN: D1 tokens (legacy-namn bevarade) · D2 theme="system" → adaptivt
#   (följer besökarens OS, var tidigare alltid dark) · D3 a11y (skip-link,
#   fokusfälla, inert, AA-kontrast) · D4 sticky actionbar + sök/filter ·
#   D5 skeleton/intoning/content-visibility · D6 lightbox med filmstrip,
#   zoom, helskärm · D7 videokort · D8 slideshow (rAF, Ken Burns) ·
#   D9 clamp()+safe-area · D10 print · D11 reduced-motion · D12 ingen CDN.
#   KOD: K1 sektionerade mallar · K2 self_check() · K3 normalize_theme() ·
#   K4 reservmallar · K5 dokumenterade platthållarlistor · K6 typhintar ·
#   K7 inga f-strings/print.
#
# PLATSHALLARE: se INDEX_PLACEHOLDERS / SLIDESHOW_PLACEHOLDERS nedan
#   (exakt de som html_generator.py ersatter med str.replace).
# ============================================================

import re
from datetime import datetime
from typing import Optional, Sequence, Tuple

VERSION   = "3.3.0"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

# ============================================================
# 1. IMPORT AV CSS/JS-TILLGANGAR (K4: reserv om fil saknas)
# ============================================================

#: KOMPAKTA RESERVER (K4). Om html_generator_css.py / _js.py saknas pa
#: disken genereras fortfarande en fungerande sida - och felet loggas.
#: Reservsidan ar medvetet enkel: lightbox + slideshow + djuplankar fungerar,
#: medan avancerade verktyg (filter, tema/densitet, filmstrip, dela, till toppen)
#: dols med CSS sa att inga doda kontroller visas.
_MINI_INDEX_CSS = """
    :root {
      --bg: #101019; --bg-elev: #191926; --bg-sunken: #0b0b12; --fg: #eef0f7;
      --fg-muted: #b6bbc9; --fg-subtle: #8b91a3; --card-bg: #1a1a28;
      --border: rgba(255,255,255,.1); --accent: #5aa9ff; --accent-fg: #07131f;
      --overlay: rgba(0,0,0,.62); --scrim: rgba(6,7,12,.94);
      --shadow-1: 0 2px 8px rgba(0,0,0,.35); --r-lg: 16px; --r-pill: 999px;
      --pad: clamp(12px,3vw,28px); --shell: 1700px;
      --header-bg: linear-gradient(160deg,#171731,#101019 60%,#0c1420);
      --bg2: #191926; --fg2: #b6bbc9; --card-shadow: var(--shadow-1);
      --card-hover-shadow: 0 18px 40px rgba(0,0,0,.5);
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, "Segoe UI", sans-serif; line-height: 1.5;
      color: var(--fg); background: var(--bg); }
    body.lb-open { overflow: hidden; }
    .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
      clip: rect(0 0 0 0); }
    /* Avancerade verktyg dols i reservlage */
    .tools, .to-top, #lb-share, #lb-zoom, #lb-fullscreen, #lb-strip,
    #lb-spinner, #lb-error, .skip-link, #layout-toggle, #theme-toggle,
    #density-toggle { display: none !important; }
    .site-header { padding: 40px var(--pad) 24px; text-align: center;
      background: var(--header-bg); }
    .site-title { font-size: clamp(1.7rem,4vw,3rem); }
    .description, .meta { color: var(--fg-muted); margin-top: 10px; }
    .attachments { display: flex; gap: 10px; justify-content: center;
      flex-wrap: wrap; margin-top: 14px; }
    .attachment-link { padding: 7px 14px; border-radius: var(--r-pill);
      border: 1px solid var(--border); color: var(--fg); text-decoration: none; }
    .actionbar { display: flex; gap: 8px; justify-content: center;
      flex-wrap: wrap; padding: 12px var(--pad); background: var(--bg-elev);
      border-bottom: 1px solid var(--border); }
    .nav-btn { padding: 9px 18px; border-radius: var(--r-pill);
      background: var(--accent); color: var(--accent-fg); font-weight: 700;
      text-decoration: none; }
    .nav-btn.nav-alt { background: #22c55e; color: #fff; }
    .video-strip { max-width: var(--shell); margin: 0 auto;
      padding: 24px var(--pad) 0; }
    .video-grid { display: grid; gap: 14px;
      grid-template-columns: repeat(auto-fill,minmax(190px,1fr)); }
    .vcard { overflow: hidden; border-radius: var(--r-lg); cursor: pointer;
      border: 1px solid var(--border); background: var(--card-bg); }
    .vthumb { display: flex; align-items: center; justify-content: center;
      aspect-ratio: 16/9; color: #fff; background: var(--bg-sunken); }
    .vthumb .play { display: flex; align-items: center; justify-content: center;
      width: 52px; height: 52px; border-radius: 50%;
      border: 2px solid rgba(255,255,255,.7); background: rgba(255,255,255,.16); }
    .vname { display: block; padding: 9px 12px; font-size: .82rem;
      text-align: center; color: var(--fg-muted); white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; }
    .gallery { display: grid; gap: 16px; max-width: var(--shell);
      margin: 0 auto; padding: 24px var(--pad) 48px;
      grid-template-columns: repeat({{COLUMNS}}, minmax(0,1fr)); }
    .card { position: relative; overflow: hidden; cursor: pointer;
      border-radius: var(--r-lg); border: 1px solid var(--border);
      background: var(--card-bg); box-shadow: var(--card-shadow); }
    .card img { display: block; width: 100%; aspect-ratio: 4/3;
      object-fit: cover; }
    .card-overlay { position: absolute; left: 0; right: 0; bottom: 0;
      padding: 28px 12px 10px; color: #fff; font-size: .84rem; opacity: 0;
      background: linear-gradient(transparent, rgba(0,0,0,.78));
      transition: opacity .2s; white-space: nowrap; overflow: hidden;
      text-overflow: ellipsis; }
    .card:hover .card-overlay, .card:focus-visible .card-overlay { opacity: 1; }
    .card-num { position: absolute; top: 9px; left: 10px; padding: 3px 9px;
      border-radius: var(--r-pill); background: var(--overlay); color: #fff;
      font-size: .72rem; }
    .card-fmt { display: none; }
    .card.hidden-by-filter, .vcard.hidden-by-filter { display: none; }
    .empty-state { padding: 48px var(--pad); text-align: center;
      color: var(--fg-subtle); }
    #lightbox { position: fixed; inset: 0; z-index: 9999; display: flex;
      align-items: center; justify-content: center; padding: 12px;
      background: var(--scrim); opacity: 0; visibility: hidden; }
    #lightbox.active { opacity: 1; visibility: visible; }
    .lb-top { position: absolute; top: 12px; left: 12px; right: 12px;
      display: flex; align-items: center; gap: 8px; }
    .lb-counter { margin-right: auto; color: #d3d7e3; font-size: .88rem; }
    .lb-actions { display: flex; gap: 6px; }
    .lb-icon { display: inline-flex; align-items: center; justify-content: center;
      width: 44px; height: 44px; border-radius: 50%; cursor: pointer;
      border: 1px solid rgba(255,255,255,.18); color: #fff;
      background: rgba(255,255,255,.1); text-decoration: none; }
    .lb-icon svg, .lb-btn svg { display: block; }
    .lb-stage { display: flex; align-items: center; justify-content: center; }
    #lb-img, #lb-video { max-width: 92vw; max-height: 76vh;
      object-fit: contain; border-radius: 10px; }
    #lb-video { display: none; background: #000; }
    .lb-btn { position: absolute; top: 50%; transform: translateY(-50%);
      width: 52px; height: 52px; border-radius: 50%; cursor: pointer;
      border: 1px solid rgba(255,255,255,.16); color: #fff; display: flex;
      align-items: center; justify-content: center;
      background: rgba(255,255,255,.1); }
    #lb-prev { left: 8px; } #lb-next { right: 8px; }
    .lb-bottom { position: absolute; left: 0; right: 0; bottom: 14px;
      text-align: center; }
    .lb-caption { color: #e8eaf2; font-size: .95rem; }
    .site-footer { padding: 24px var(--pad); text-align: center;
      color: var(--fg-subtle); font-size: .8rem; }
    @media (max-width: 1300px) {
      .gallery { grid-template-columns: repeat({{COLUMNS_4}},minmax(0,1fr)); }
    }
    @media (max-width: 950px) {
      .gallery { grid-template-columns: repeat({{COLUMNS_3}},minmax(0,1fr)); }
    }
    @media (max-width: 700px) {
      .gallery { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; }
    }
    @media (max-width: 420px) {
      .gallery { grid-template-columns: minmax(0,1fr); }
    }
"""

_MINI_SLIDESHOW_CSS = """
    html, body { height: 100%; }
    body { display: flex; flex-direction: column; overflow: hidden;
      background: #000; color: #fff;
      font-family: system-ui, "Segoe UI", sans-serif; }
    .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
      clip: rect(0 0 0 0); }
    #ss-theme, #ss-caption-btn, #ss-full, .skip-link { display: none !important; }
    .ss-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
      padding: 10px 18px; background: rgba(0,0,0,.45); }
    .ss-toolbar h1 { margin-right: auto; font-size: 1rem; max-width: 38vw;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .attachments { display: flex; gap: 8px; flex-wrap: wrap; }
    .attachment-link { padding: 5px 11px; border-radius: 999px; color: #fff;
      text-decoration: none; font-size: .8rem;
      border: 1px solid rgba(255,255,255,.2); background: rgba(255,255,255,.08); }
    .tb-btn { min-height: 38px; padding: 8px 15px; border-radius: 999px;
      border: 1px solid rgba(255,255,255,.14); color: #fff; cursor: pointer;
      background: rgba(255,255,255,.12); font-weight: 700; font-size: .85rem;
      text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
    .tb-btn.paused { background: #4b5563; }
    .tb-btn.info { background: #5aa9ff; }
    .counter { font-size: .86rem; opacity: .85; }
    .speed-wrap { display: flex; align-items: center; gap: 8px; font-size: .82rem; }
    .progress-bar { height: 3px; background: rgba(255,255,255,.16); }
    .progress-fill { height: 100%; width: 0; background: #5aa9ff; }
    .slide-area { position: relative; flex: 1; min-height: 0; overflow: hidden;
      display: flex; align-items: center; justify-content: center; }
    .slide { position: absolute; inset: 0; display: flex; align-items: center;
      justify-content: center; opacity: 0; visibility: hidden;
      transition: opacity .4s; }
    .slide.active { opacity: 1; visibility: visible; }
    .slide img { max-width: 100%; max-height: 100%; object-fit: contain; }
    .caption { position: absolute; left: 0; right: 0; bottom: 0;
      padding: 30px 16px 14px; text-align: center;
      background: linear-gradient(transparent, rgba(0,0,0,.78)); }
    .nav-arrow { position: absolute; top: 50%; transform: translateY(-50%);
      width: 52px; height: 52px; border-radius: 50%; cursor: pointer;
      border: 1px solid rgba(255,255,255,.16); color: #fff; display: flex;
      align-items: center; justify-content: center;
      background: rgba(255,255,255,.12); }
    .nav-arrow svg { display: block; }
    #ss-prev { left: 10px; } #ss-next { right: 10px; }
    .hint { display: none; }
    @media (max-width: 760px) {
      .speed-wrap { display: none; }
      .ss-toolbar h1 { max-width: 100%; flex-basis: 100%; }
    }
"""

_MINI_INDEX_JS = """
  (function () {
    "use strict";
    var IMAGES = {{IMAGES_JS}};
    var VIDEOS = {{VIDEOS_JS}};
    function $(id) { return document.getElementById(id); }
    function wrap(i, len) { return len ? ((i % len) + len) % len : 0; }
    var lb = $("lightbox"), lbImg = $("lb-img"), lbVid = $("lb-video");
    var cap = $("lb-caption"), cnt = $("lb-counter");
    var LIST = IMAGES, current = 0;
    function videoMode() { return LIST === VIDEOS; }
    function stopVideo() {
      if (lbVid && lbVid.getAttribute("src")) {
        try { lbVid.pause(); } catch (e) {}
        lbVid.removeAttribute("src");
        try { lbVid.load(); } catch (e) {}
      }
    }
    function pushHash() {
      var t = lb && lb.classList.contains("active")
        ? "#" + (videoMode() ? "video-" : "bild-") + (current + 1)
        : window.location.pathname + window.location.search;
      try { window.history.replaceState(null, "", t); } catch (e) {}
    }
    function show() {
      var item = LIST[current];
      if (!item) { return; }
      if (cap) { cap.textContent = item.title || ""; }
      if (cnt) { cnt.textContent = (current + 1) + " / " + LIST.length; }
      var download = $("lb-download"), href = videoMode() ? "" : (item.download || "");
      if (download) {
        download.hidden = !href;
        download.style.display = href ? "inline-flex" : "none";
        if (href) { download.href = href; download.title = item.downloadLabel || "Ladda ned"; }
        else { download.removeAttribute("href"); }
      }
      if (videoMode()) {
        stopVideo();
        if (lbImg) { lbImg.style.display = "none"; }
        if (lbVid) {
          lbVid.style.display = "block";
          lbVid.src = item.src;
          var p = lbVid.play();
          if (p && p.catch) { p.catch(function () {}); }
        }
      } else {
        stopVideo();
        if (lbVid) { lbVid.style.display = "none"; }
        if (lbImg) {
          lbImg.style.display = "block";
          lbImg.sizes = "100vw";
          lbImg.srcset = item.srcset || "";
          lbImg.src = item.src;
          lbImg.alt = item.title || "";
        }
      }
      pushHash();
    }
    function open(list, i) {
      if (!lb || !list || !list.length) { return; }
      LIST = list; current = wrap(i, list.length); show();
      lb.classList.add("active");
      lb.setAttribute("aria-hidden", "false");
      document.body.classList.add("lb-open");
    }
    function close() {
      if (!lb) { return; }
      stopVideo();
      lb.classList.remove("active");
      lb.setAttribute("aria-hidden", "true");
      document.body.classList.remove("lb-open");
      pushHash();
    }
    function nav(d) {
      if (LIST.length) { current = wrap(current + d, LIST.length); show(); }
    }
    document.addEventListener("click", function (e) {
      var el = e.target;
      while (el && el !== document.body) {
        if (el.classList && el.hasAttribute) {
          if (el.classList.contains("card") &&
              el.hasAttribute("data-index")) {
            open(IMAGES, parseInt(el.getAttribute("data-index"), 10) || 0);
            return;
          }
          if (el.classList.contains("vcard") &&
              el.hasAttribute("data-video-index")) {
            open(VIDEOS, parseInt(el.getAttribute("data-video-index"), 10) || 0);
            return;
          }
        }
        el = el.parentNode;
      }
      if (e.target === lb || e.target === $("lb-stage")) { close(); }
    });
    var b1 = $("lb-close"), b2 = $("lb-prev"), b3 = $("lb-next");
    if (b1) { b1.addEventListener("click", close); }
    if (b2) { b2.addEventListener("click", function () { nav(-1); }); }
    if (b3) { b3.addEventListener("click", function () { nav(1); }); }
    document.addEventListener("keydown", function (e) {
      if (!lb || !lb.classList.contains("active")) { return; }
      if (e.key === "ArrowLeft") { nav(-1); }
      if (e.key === "ArrowRight") { nav(1); }
      if (e.key === "Escape") { close(); }
    });
    var cards = document.querySelectorAll(".card");
    for (var i = 0; i < cards.length; i++) {
      var img = cards[i].querySelector("img");
      if (img) {
        img.classList.add("loaded");
        cards[i].classList.add("done");
        cards[i].classList.add("in");
      }
    }
    var hm = /^#(bild|img|video)-([0-9]+)$/.exec(
      (window.location.hash || "").toLowerCase()
    );
    if (hm) {
      var n = parseInt(hm[2], 10) - 1;
      if (hm[1] === "video") { open(VIDEOS, n); } else { open(IMAGES, n); }
    }
    window.openImages = function (i) { open(IMAGES, i); };
    window.openVideo = function (i) { open(VIDEOS, i); };
    window.closeLightbox = close;
    window.navigate = nav;
  })();
"""

_MINI_SLIDESHOW_JS = """
  (function () {
    "use strict";
    function $(id) { return document.getElementById(id); }
    var slides = document.querySelectorAll(".slide");
    var counter = $("ss-counter"), progress = $("progress-fill");
    var playBtn = $("ss-play");
    var idx = 0, playing = true, speed = 4000, elapsed = 0, lastTs = 0;
    var total = slides.length;
    function show(i) {
      if (!total) { return; }
      idx = ((i % total) + total) % total;
      for (var n = 0; n < total; n++) {
        slides[n].classList.toggle("active", n === idx);
      }
      if (counter) { counter.textContent = (idx + 1) + " / " + total; }
      elapsed = 0;
      if (progress) { progress.style.width = "0%"; }
      try {
        window.history.replaceState(null, "", "#bild-" + (idx + 1));
      } catch (e) {}
    }
    function tick(ts) {
      if (!lastTs) { lastTs = ts; }
      var dt = ts - lastTs;
      lastTs = ts;
      if (dt > 500) { dt = 0; }
      if (playing && !document.hidden && total > 1) {
        elapsed += dt;
        if (progress) {
          progress.style.width = Math.min(100, elapsed / speed * 100) + "%";
        }
        if (elapsed >= speed) { show(idx + 1); }
      }
      window.requestAnimationFrame(tick);
    }
    function setPlaying(state) {
      playing = !!state;
      if (playBtn) {
        playBtn.innerHTML = playing ? "&#9208; Pausa" : "&#9654; Spela";
        playBtn.classList.toggle("paused", !playing);
      }
      elapsed = 0;
    }
    var btns = [["ss-prev", -1], ["ss-next", 1], ["ss-prev-btn", -1],
                ["ss-next-btn", 1]];
    for (var k = 0; k < btns.length; k++) {
      (function (id, d) {
        var b = $(id);
        if (b) { b.addEventListener("click", function () { show(idx + d); }); }
      })(btns[k][0], btns[k][1]);
    }
    if (playBtn) {
      playBtn.addEventListener("click", function () { setPlaying(!playing); });
    }
    var slider = $("speed-slider"), lbl = $("speed-label");
    if (slider) {
      slider.addEventListener("input", function () {
        speed = (parseInt(slider.value, 10) || 4) * 1000;
        if (lbl) { lbl.textContent = (speed / 1000) + " s"; }
        elapsed = 0;
      });
      speed = (parseInt(slider.value, 10) || 4) * 1000;
      if (lbl) { lbl.textContent = (speed / 1000) + " s"; }
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") { show(idx - 1); }
      if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") { show(idx + 1); }
      if (e.key === "Home") { show(0); }
      if (e.key === "End") { show(total - 1); }
      if (e.key === " ") { e.preventDefault(); setPlaying(!playing); }
      if (e.key === "Escape") { window.location.href = "index.html"; }
    });
    document.addEventListener("visibilitychange", function () { lastTs = 0; });
    var hm = /^#(bild|img)-([0-9]+)$/.exec(
      (window.location.hash || "").toLowerCase()
    );
    show(hm ? parseInt(hm[2], 10) - 1 : 0);
    setPlaying(true);
    window.requestAnimationFrame(tick);
  })();
"""

_MINI_BOOT_JS = """
    (function () {
      var d = document.documentElement;
      d.className = (d.className ? d.className + " " : "") + "js";
    })();
"""

_MINI_LIGHT_TOKENS = """
    :root {
      --bg: #f6f7fb; --bg-elev: #ffffff; --bg-sunken: #eceef5; --fg: #141722;
      --fg-muted: #4a5162; --fg-subtle: #6b7280; --card-bg: #ffffff;
      --border: rgba(16,20,32,.1); --accent: #2563eb; --accent-fg: #ffffff;
      --overlay: rgba(0,0,0,.55); --scrim: rgba(12,14,20,.9);
      --shadow-1: 0 1px 3px rgba(16,20,32,.1);
      --header-bg: linear-gradient(160deg,#ffffff,#f2f4fa 60%,#e8edf8);
      --bg2: #ffffff; --fg2: #4a5162; --card-shadow: var(--shadow-1);
      --card-hover-shadow: 0 10px 30px rgba(16,20,32,.18);
    }
"""

_MINI_COLORFUL_TOKENS = """
    :root {
      --bg: #0d0a24; --bg-elev: #171236; --bg-sunken: #08061a; --fg: #ffffff;
      --fg-muted: #d9cffb; --fg-subtle: #a99bd6;
      --card-bg: rgba(255,255,255,.07); --border: rgba(255,255,255,.14);
      --accent: #f72585; --accent-fg: #ffffff; --overlay: rgba(0,0,0,.55);
      --scrim: rgba(8,6,26,.94); --shadow-1: 0 6px 24px rgba(0,0,0,.4);
      --header-bg: linear-gradient(135deg,#0f0c29,#302b63 50%,#24243e);
      --bg2: #171236; --fg2: #d9cffb; --card-shadow: var(--shadow-1);
      --card-hover-shadow: 0 16px 44px rgba(247,37,133,.3);
    }
"""

_MINI_THEME_IDS = ("dark", "light", "colorful", "auto")


def _mini_render_theme_css(theme) -> str:
    """Reserv-tema-CSS (dark/light/colorful) om css-modulen saknas."""
    name = str(theme or "").strip().lower()
    if name in ("light", "ljus", "ljust", "vit", "white"):
        return _MINI_LIGHT_TOKENS
    if name in ("colorful", "färgglad", "fargglad", "neon", "farg"):
        return _MINI_COLORFUL_TOKENS
    return "    /* mini-reserv: dark (standard) */\n"


#: Sanna/False beroende pa om css/js-modulerna kunde importeras.
ASSETS_AVAILABLE = True
ASSET_ERROR = ""

try:
    from .html_generator_css import (  # noqa: F401
        DEFAULT_THEME,
        INDEX_CSS,
        THEME_ALIASES,
        VERSION as CSS_VERSION,
        SLIDESHOW_CSS,
        SYSTEM_THEME_MODE,
        THEME_IDS,
        THEME_TOKENS,
        normalize_theme,
        render_theme_css,
        theme_block,
        theme_ids,
    )
    from .html_generator_js import (  # noqa: F401
        BOOT_JS,
        INDEX_JS,
        SLIDESHOW_JS,
        VERSION as JS_VERSION,
    )
except Exception as _exc:                      # pragma: no cover
    ASSETS_AVAILABLE = False
    ASSET_ERROR = "%s: %s" % (type(_exc).__name__, _exc)
    CSS_VERSION      = "0"
    JS_VERSION       = "0"
    INDEX_CSS        = _MINI_INDEX_CSS
    SLIDESHOW_CSS    = _MINI_SLIDESHOW_CSS
    INDEX_JS         = _MINI_INDEX_JS
    SLIDESHOW_JS     = _MINI_SLIDESHOW_JS
    BOOT_JS          = _MINI_BOOT_JS
    THEME_IDS        = _MINI_THEME_IDS
    THEME_ALIASES    = {}
    DEFAULT_THEME    = "dark"
    SYSTEM_THEME_MODE = "dark"
    THEME_TOKENS     = {}

    def normalize_theme(theme):                # noqa: F811
        """Reserv: enkel normalisering utan css-modulen."""
        key = str(theme or "").strip().lower()
        if key in _MINI_THEME_IDS:
            return key
        if key in ("system", "auto", "os"):
            return SYSTEM_THEME_MODE
        if key in ("light", "ljus", "ljust"):
            return "light"
        if key in ("colorful", "färgglad", "fargglad"):
            return "colorful"
        return DEFAULT_THEME

    def render_theme_css(theme):               # noqa: F811
        """Reserv: tema-CSS utan css-modulen."""
        return _mini_render_theme_css(theme)

    def theme_block(name, indent="    "):      # noqa: F811
        return ""

    def theme_ids():                           # noqa: F811
        return THEME_IDS


# ============================================================
# 2. IKONER (inline SVG - ingen extern resurs, D12)
# ============================================================

_SVG_OPEN = (
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true" focusable="false">'
)

ICON_DOWNLOAD = _SVG_OPEN + (
    '<path d="M12 3v12"/><path d="M7 11l5 5 5-5"/><path d="M4 20h16"/>'
    "</svg>"
)
ICON_ZOOM = _SVG_OPEN + (
    '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/>'
    '<path d="M11 8.5v5M8.5 11h5"/>'
    "</svg>"
)
ICON_EXPAND = _SVG_OPEN + (
    '<path d="M4 9V4h5"/><path d="M20 9V4h-5"/>'
    '<path d="M4 15v5h5"/><path d="M20 15v5h-5"/>'
    "</svg>"
)
ICON_CLOSE = _SVG_OPEN + '<path d="M6 6l12 12M18 6L6 18"/>' + "</svg>"
ICON_PREV = _SVG_OPEN + '<path d="M14.5 5l-7 7 7 7"/>' + "</svg>"
ICON_NEXT = _SVG_OPEN + '<path d="M9.5 5l7 7-7 7"/>' + "</svg>"
ICON_UP = _SVG_OPEN + (
    '<path d="M12 20V5"/><path d="M5 12l7-7 7 7"/>'
    "</svg>"
)
ICON_SEARCH = _SVG_OPEN + (
    '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/>'
    "</svg>"
)
ICON_LAYOUT = _SVG_OPEN + (
    '<rect x="3" y="5" width="8.5" height="6" rx="1.4"/>'
    '<rect x="13.5" y="5" width="7.5" height="6" rx="1.4"/>'
    '<rect x="3" y="13" width="12.5" height="6" rx="1.4"/>'
    '<rect x="17.5" y="13" width="3.5" height="6" rx="1.4"/></svg>'
)
ICON_THEME = _SVG_OPEN + (
    '<circle cx="12" cy="12" r="8.5"/>'
    '<path d="M12 3.5a8.5 8.5 0 0 0 0 17z" fill="currentColor" stroke="none"/>'
    "</svg>"
)
ICON_DENSITY = _SVG_OPEN + (
    '<rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/>'
    '<rect x="13.5" y="3.5" width="7" height="7" rx="1.6"/>'
    '<rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/>'
    '<rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/>'
    "</svg>"
)
ICON_LINK = _SVG_OPEN + (
    '<path d="M10.5 13.5a4.5 4.5 0 0 0 6.4 0l2.1-2.1'
    'a4.5 4.5 0 0 0-6.4-6.4l-1 1"/>'
    '<path d="M13.5 10.5a4.5 4.5 0 0 0-6.4 0l-2.1 2.1'
    'a4.5 4.5 0 0 0 6.4 6.4l1-1"/>'
    "</svg>"
)
ICON_CAPTION = _SVG_OPEN + (
    '<rect x="3" y="5" width="18" height="14" rx="3"/>'
    '<path d="M7 15c0-2 1.2-3 2.6-3S12 13 12 15"/>'
    '<path d="M14 15c0-2 1.2-3 2.6-3S19 13 19 15"/>'
    "</svg>"
)


# ============================================================
# 3. INDEX.HTML - SKELETT
# ============================================================

_INDEX_HEAD = """<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="UTF-8">
  <link rel="icon" type="image/png" href="app-icon.png">
  <meta name="viewport"
        content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark light">
  <meta name="theme-color" id="meta-theme-color" content="#101019">
  <meta name="generator" content="FTP-Galleri v{{VERSION}}">
  <meta name="description" content="{{META_DESC}}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{{TITLE}}">
  <meta property="og:description" content="{{META_DESC}}">
  <meta property="og:site_name" content="FTP-Galleri">
  <meta name="twitter:card" content="summary_large_image">
  <title>{{TITLE}}</title>
  {{CUSTOM_HEAD}}
  <script>"""

_INDEX_STYLE_OPEN = """</script>
  <style>
    /* ==========================================================
       1. Design-tokens, layout och komponenter
          (plugins/html_generator_css.py)
       ========================================================== */
"""

_INDEX_STYLE_THEME = """
    /* ==========================================================
       2. Tema (render_theme_css - dark/light/colorful/auto)
       ========================================================== */
{{THEME_CSS}}
"""

_INDEX_STYLE_CUSTOM = """
    /* ==========================================================
       3. Custom CSS fran CSS-redigeraren (ligger sist = vinner)
       ========================================================== */
{{CUSTOM_CSS}}
  </style>
</head>
<body>
  <a class="skip-link" href="#gallery">Hoppa till galleriet</a>

  <header class="site-header">
    <div class="header-inner">
      <p class="kicker">Galleri</p>
      <h1 class="site-title">{{TITLE}}</h1>
      {{DESC_HTML}}
      {{ATTACHMENTS_HTML}}
      <p class="meta">
        {{IMG_COUNT}} bilder &middot; {{FOLDER}}
        &middot; Genererat {{NOW}}
      </p>
    </div>
  </header>

  <div class="actionbar" id="actionbar">
    <nav class="nav-bar" aria-label="Sidnavigering">
      <a class="nav-btn" href="index.html" aria-current="page">
        &#128444;&#65039; Galleri
      </a>
      <a class="nav-btn nav-alt" href="slideshow.html">
        &#9654; Slideshow
      </a>
    </nav>
    <div class="tools">
      <div class="search">
        <label class="sr-only" for="filter-input">Filtrera bilder</label>
        <span class="search-icon">""" + ICON_SEARCH + """</span>
        <input id="filter-input" type="search"
               placeholder="Filtrera bilder&#8230;"
               autocomplete="off" spellcheck="false">
        <button id="filter-clear" type="button"
                aria-label="Rensa filter">&#10005;</button>
      </div>
      <span class="count-pill" id="count-pill" role="status">
        {{IMG_COUNT}} bilder
      </span>
      <button class="tool-btn" id="layout-toggle" type="button"
              aria-pressed="false" title="Layout">""" + ICON_LAYOUT + """
        <span class="tool-label">Radjämnt</span>
      </button>
      <button class="tool-btn" id="theme-toggle" type="button"
              aria-pressed="false" title="Tema">""" + ICON_THEME + """
        <span class="tool-label">Auto</span>
      </button>
      <button class="tool-btn" id="density-toggle" type="button"
              aria-pressed="false" title="Densitet">""" + ICON_DENSITY + """
        <span class="tool-label">Standard</span>
      </button>
    </div>
  </div>

  <!-- Videor ligger fore bildgalleriet (v2.9.0) -->
  {{VIDEOS_HTML}}

  <main class="gallery" id="gallery" data-columns="{{COLUMNS}}"
        role="main" aria-label="Bildgalleri">
{{CARDS_HTML}}
  </main>

  <p class="empty-state" id="empty-state" hidden>
    Ingen bild matchar filtret.
  </p>

  <button class="to-top" id="to-top" type="button"
          aria-label="Tillbaka till toppen"
          title="Tillbaka till toppen">""" + ICON_UP + """</button>

  <!-- Lightbox (dialog) -->
  <div id="lightbox" role="dialog" aria-modal="true"
       aria-label="Bildvisning" aria-hidden="true">
    <div class="lb-top">
      <span class="lb-counter" id="lb-counter"></span>
      <div class="lb-actions">
        <button class="lb-icon" id="lb-share" type="button"
                aria-label="Kopiera lank till bilden"
                title="Kopiera lank">""" + ICON_LINK + """</button>
        <a class="lb-icon" id="lb-download" hidden style="display:none" download
           aria-label="Ladda ner filen"
           title="Ladda ner">""" + ICON_DOWNLOAD + """</a>
        <button class="lb-icon" id="lb-zoom" type="button"
                aria-label="Zooma" aria-pressed="false"
                title="Zooma (Z)">""" + ICON_ZOOM + """</button>
        <button class="lb-icon" id="lb-fullscreen" type="button"
                aria-label="Helskarm"
                title="Helskarm (F)">""" + ICON_EXPAND + """</button>
        <button class="lb-icon" id="lb-close" type="button"
                aria-label="Stang"
                title="Stang (Escape)">""" + ICON_CLOSE + """</button>
      </div>
    </div>

    <button class="lb-btn" id="lb-prev" type="button"
            aria-label="Foregaende"
            title="Foregaende (&#8592;)">""" + ICON_PREV + """</button>

    <div class="lb-stage" id="lb-stage">
      <div class="lb-spinner" id="lb-spinner" aria-hidden="true"></div>
      <p id="lb-error" role="alert">Kunde inte ladda filen</p>
      <img id="lb-img" src="" alt="">
      <video id="lb-video" controls playsinline preload="metadata"></video>
    </div>

    <button class="lb-btn" id="lb-next" type="button"
            aria-label="Nasta"
            title="Nasta (&#8594;)">""" + ICON_NEXT + """</button>

    <div class="lb-bottom">
      <p class="lb-caption" id="lb-caption" aria-live="polite"></p>
      <div class="lb-strip" id="lb-strip" aria-label="Miniatyrer"></div>
      <p class="lb-hint">
        &#8592; / &#8594; byter media &middot; Z zoom &middot;
        F helskarm &middot; Escape stanger &middot; svep pa mobil
      </p>
    </div>
  </div>

  <footer class="site-footer">
    FTP-Galleri &middot; {{NOW}}
  </footer>

  {{CUSTOM_FOOTER}}

  <script>"""

_INDEX_SCRIPT_CLOSE = """</script>
</body>
</html>"""


# ============================================================
# 4. SLIDESHOW.HTML - SKELETT
# ============================================================

_SLIDESHOW_HEAD = """<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="UTF-8">
  <link rel="icon" type="image/png" href="app-icon.png">
  <meta name="viewport"
        content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark light">
  <meta name="theme-color" id="meta-theme-color" content="#000000">
  <meta name="description" content="Slideshow">
  <title>{{TITLE}} - Slideshow</title>
  {{CUSTOM_HEAD}}
  <script>
</script>
  <style>
    /* ==========================================================
       1. Design-tokens + slideshow-komponenter
       ========================================================== */
"""

_SLIDESHOW_STYLE_THEME = """
    /* ==========================================================
       2. Tema
       ========================================================== */
{{THEME_CSS}}
"""

_SLIDESHOW_STYLE_CUSTOM = """
    /* ==========================================================
       3. Custom CSS (ligger sist = vinner)
       ========================================================== */
{{CUSTOM_CSS}}
  </style>
</head>
<body>
  <a class="skip-link" href="#slide-area">Hoppa till bildspelet</a>

  <div class="ss-toolbar" id="ss-toolbar">
    <h1>&#127916; {{TITLE}}</h1>
    {{ATTACHMENTS_HTML}}
    <span class="counter" id="ss-counter">1 / {{IMG_COUNT}}</span>
    <button class="tb-btn primary" id="ss-play" type="button"
            aria-pressed="false" title="Pausa/spela (Space)">
      &#9208; Pausa
    </button>
    <button class="tb-btn ghost" id="ss-prev-btn" type="button"
            title="Foregaende (&#8592;)">
      &#8249; Foregaende
    </button>
    <button class="tb-btn ghost" id="ss-next-btn" type="button"
            title="Nasta (&#8594;)">
      Nasta &#8250;
    </button>
    <button class="tb-btn ghost" id="ss-caption-btn" type="button"
            aria-pressed="true" title="Bildtext av/pa (C)">""" + ICON_CAPTION + """
      <span class="sr-only">Bildtext</span>
    </button>
    <button class="tb-btn ghost" id="ss-theme" type="button"
            aria-pressed="false" title="Tema">""" + ICON_THEME + """
      <span>Tema</span>
    </button>
    <button class="tb-btn ghost" id="ss-full" type="button"
            title="Helskarm (F)">""" + ICON_EXPAND + """
      <span class="sr-only">Helskarm</span>
    </button>
    <div class="speed-wrap">
      <label for="speed-slider">Hastighet</label>
      <input type="range" id="speed-slider"
             min="1" max="10" step="1" value="4">
      <span id="speed-label">4 s</span>
    </div>
    <a href="index.html" class="tb-btn info" title="Tillbaka till galleriet">
      &#127968; Galleri
    </a>
  </div>

  <div class="progress-bar" role="presentation">
    <div class="progress-fill" id="progress-fill"></div>
  </div>

  <main class="slide-area" id="slide-area" aria-label="Bildspel">
    <div class="hint">
      &#8592; / &#8594; byter bild &middot; Space pausar &middot;
      F helskarm &middot; C bildtext &middot;
      Escape tillbaka &middot; svep pa mobil
    </div>
{{SLIDES_HTML}}
    <button class="nav-arrow" id="ss-prev" type="button"
            aria-label="Foregaende bild">""" + ICON_PREV + """</button>
    <button class="nav-arrow" id="ss-next" type="button"
            aria-label="Nasta bild">""" + ICON_NEXT + """</button>
  </main>

  {{CUSTOM_FOOTER}}

  <script>"""

_SLIDESHOW_SCRIPT_CLOSE = """</script>
</body>
</html>"""


# ============================================================
# 5. PLATSHALLARE SOM html_generator.py ERSATTER (K5)
# ============================================================

INDEX_PLACEHOLDERS = (
    "{{VERSION}}", "{{META_DESC}}", "{{TITLE}}", "{{TITLE_RAW}}",
    "{{CUSTOM_HEAD}}", "{{THEME_CSS}}", "{{COLUMNS}}", "{{COLUMNS_4}}",
    "{{COLUMNS_3}}", "{{CUSTOM_CSS}}", "{{DESC_HTML}}",
    "{{ATTACHMENTS_HTML}}", "{{IMG_COUNT}}", "{{FOLDER}}", "{{NOW}}",
    "{{CARDS_HTML}}", "{{VIDEOS_HTML}}", "{{IMAGES_JS}}", "{{VIDEOS_JS}}",
    "{{CUSTOM_FOOTER}}",
)

SLIDESHOW_PLACEHOLDERS = (
    "{{TITLE}}", "{{CUSTOM_HEAD}}", "{{THEME_CSS}}", "{{CUSTOM_CSS}}",
    "{{ATTACHMENTS_HTML}}", "{{IMG_COUNT}}", "{{SLIDES_HTML}}",
    "{{CUSTOM_FOOTER}}",
)

#: Id som JavaScript-koden hamtar (maste finnas i respektive mall)
_REQUIRED_INDEX_IDS = (
    "gallery", "lightbox", "lb-img", "lb-video", "lb-caption",
    "lb-counter", "lb-strip", "lb-spinner", "lb-error", "lb-download",
    "lb-zoom", "lb-fullscreen", "lb-stage", "lb-close", "lb-prev",
    "lb-next", "filter-input", "filter-clear", "count-pill",
    "empty-state", "to-top", "meta-theme-color", "theme-toggle",
    "density-toggle", "layout-toggle", "lb-share",
)

# OBS: id="video-strip" skapas av {{VIDEOS_HTML}} (html_generator.py)
# och kan darfor inte kontrolleras mot den obearbetade mallen.

_REQUIRED_SLIDESHOW_IDS = (
    "slide-area", "ss-toolbar", "ss-counter", "progress-fill", "ss-play",
    "ss-caption-btn", "ss-full", "speed-slider", "speed-label",
    "ss-prev", "ss-next", "ss-prev-btn", "ss-next-btn",
    "meta-theme-color", "ss-theme",
)


# ============================================================
# 6. MIXIN
# ============================================================

class HtmlTemplatesMixin:
    """
    HTML/CSS-mallar och tema-API for HtmlGenerator (se filhuvud).

    Klassattribut:
        _INDEX_TEMPLATE      komplett index.html-mall ({{...}})
        _SLIDESHOW_TEMPLATE  komplett slideshow.html-mall ({{...}})

    Metoder:
        _get_theme_css(theme)   tema-CSS (anropas av html_generator.py)
        get_theme_css(theme)    publik alias
        normalize_theme(theme)  "System"/"Mörkt"/... -> temaid
        theme_names()           gangbara temaid
        is_valid_theme(theme)   True om temat känns igen
        self_check()            lista med problem (tom = OK)
    """

    VERSION   = VERSION
    AUTHOR    = AUTHOR
    COPYRIGHT = COPYRIGHT

    #: Gangbara temaid + standard (speglar html_generator_css)
    THEME_IDS         = THEME_IDS
    DEFAULT_THEME     = DEFAULT_THEME
    SYSTEM_THEME_MODE = SYSTEM_THEME_MODE

    #: True om css/js-modulerna fanns (K4) + deras versioner (K9)
    ASSETS_AVAILABLE = ASSETS_AVAILABLE
    ASSET_ERROR      = ASSET_ERROR
    CSS_VERSION      = CSS_VERSION
    JS_VERSION       = JS_VERSION

    # -- Mallar (sammansatta av sektioner, K1) -----------------
    _INDEX_TEMPLATE = (
        _INDEX_HEAD
        + BOOT_JS
        + _INDEX_STYLE_OPEN
        + INDEX_CSS
        + _INDEX_STYLE_THEME
        + _INDEX_STYLE_CUSTOM
        + INDEX_JS
        + _INDEX_SCRIPT_CLOSE
    )

    _SLIDESHOW_TEMPLATE = (
        _SLIDESHOW_HEAD
        + BOOT_JS
        + SLIDESHOW_CSS
        + _SLIDESHOW_STYLE_THEME
        + _SLIDESHOW_STYLE_CUSTOM
        + SLIDESHOW_JS
        + _SLIDESHOW_SCRIPT_CLOSE
    )

    # ==========================================================
    # TEMA-API
    # ==========================================================
    def normalize_theme(self, theme) -> str:
        """Normalisera temanamn till dark/light/colorful/auto."""
        return normalize_theme(theme)

    def theme_names(self) -> Tuple[str, ...]:
        """Returnera gangbara temaid."""
        return tuple(THEME_IDS)

    def is_valid_theme(self, theme) -> bool:
        """
        True om theme ar ett kant tema eller kant alias.

        Skillnad mot normalize_theme(): okanda varden (t.ex. "skrapa")
        ger False har, men faller annars tillbaka till DEFAULT_THEME.
        """
        key = "" if theme is None else str(theme).strip().lower()
        key = key.replace("-", "_")
        if not key:
            return False          # tomt/None = inget tema valt
        return key in tuple(THEME_IDS) or key in THEME_ALIASES

    def get_theme_css(self, theme: str) -> str:
        """
        Returnera bas-CSS for valt tema ({{THEME_CSS}}).

        "system"/"auto" ger ett adaptivt tema som foljer besokarens
        prefers-color-scheme (D2). Okant tema -> DEFAULT_THEME.
        """
        try:
            return render_theme_css(theme)
        except Exception:
            return _mini_render_theme_css(theme)

    # Bakatkompatibilitet: gamalt privat namn (anropas av html_generator.py)
    _get_theme_css = get_theme_css

    # ==========================================================
    # MALLRENDERING (K8)
    # ==========================================================
    def render_template(self, which: str, values: dict, log=None) -> str:
        """
        Rendera en mall: ersatt {{NYCKEL}} med values["NYCKEL"].

        which="index"|"slideshow", values=dict utan klamrar (t.ex. "TITLE"),
        log=valfri pipeline-loggfunktion. Platthallare som inte fick nagon
        ersatts med tom strang och loggas som varning.

        OBS: html_generator.py kan fortfarande gora egna str.replace()-anrop
        - bada vagarna ger identiskt resultat.
        """
        slide = str(which).lower().startswith("slide")
        template = self._SLIDESHOW_TEMPLATE if slide else self._INDEX_TEMPLATE
        allowed = SLIDESHOW_PLACEHOLDERS if slide else INDEX_PLACEHOLDERS

        html = template
        for key, value in (values or {}).items():
            html = html.replace(
                "{{%s}}" % str(key).upper(),
                "" if value is None else str(value),
            )

        missing = [ph for ph in allowed if ph in html]
        if missing:
            self._warn(
                log,
                "%s: platthallare utan varde: %s" % (which, ", ".join(missing)),
            )
            for ph in missing:
                html = html.replace(ph, "")
        return html

    def _warn(self, log, msg: str) -> None:
        """Logga en varning via pipeline-log() eller BasePlugin.log()."""
        try:
            if log:
                log("  [!] %s" % msg)
            else:
                self.log("VARNING", msg)
        except Exception:
            pass

    # ==========================================================
    # SJALVKONTROLL (K2)
    # ==========================================================
    def template_placeholders(self, which: str = "index") -> Tuple[str, ...]:
        """Returnera dokumenterade platshallare for 'index'|'slideshow'."""
        if str(which).lower().startswith("slide"):
            return SLIDESHOW_PLACEHOLDERS
        return INDEX_PLACEHOLDERS

    @staticmethod
    def _found_placeholders(text: str) -> Sequence[str]:
        """Hitta alla {{...}}-platshallare i en text."""
        return re.findall(r"\{\{[A-Z0-9_]+\}\}", text or "")

    def self_check(self) -> list:
        """
        Kontrollera mallarna mot html_generator.py:s kontrakt.

        Testar:
          1. Alla {{...}} i mallen ar kanda (annars blir de synliga i HTML)
          2. Alla id som JS hamtar finns i mallen
          3. Tematabellen ar komplett (tokens for varje tema)

        Returnerar:
            Lista med problemstrangar - tom lista betyder OK.
        """
        problems = []

        for name, template, allowed in (
            ("index", self._INDEX_TEMPLATE, INDEX_PLACEHOLDERS),
            ("slideshow", self._SLIDESHOW_TEMPLATE, SLIDESHOW_PLACEHOLDERS),
        ):
            for found in self._found_placeholders(template):
                if found not in allowed:
                    problems.append(
                        "%s: okand platshallare %s" % (name, found)
                    )

            required = (
                _REQUIRED_INDEX_IDS if name == "index"
                else _REQUIRED_SLIDESHOW_IDS
            )
            for ident in required:
                if ('id="%s"' % ident) not in template:
                    problems.append(
                        "%s: saknar id=\"%s\" (JS/CSS refererar)"
                        % (name, ident)
                    )

        if not ASSETS_AVAILABLE:
            problems.append(
                "reservmall aktiv (saknade moduler): %s" % ASSET_ERROR
            )
        else:
            for name, ver in self.asset_versions().items():
                if ver != VERSION:
                    problems.append(
                        "versionsdrift: %s ar v%s, mallarna ar v%s"
                        % (name, ver, VERSION)
                    )

        for tid in THEME_IDS:
            if tid == "auto":
                continue
            if THEME_TOKENS and tid not in THEME_TOKENS:
                problems.append("tema saknar tokens: %s" % tid)

        return problems

    def asset_versions(self) -> dict:
        """
        Versioner hos mall/CSS/JS (K9).

        Anvands for att upptacka ojamt kopierade filer: om t.ex.
        html_generator_css.py ligger kvar pa 3.0.0 medan mallarna ar 3.1.0
        sa loggas en varning vid generering.
        """
        return {
            "html_generator_templates.py": VERSION,
            "html_generator_css.py":       CSS_VERSION,
            "html_generator_js.py":        JS_VERSION,
        }

    def asset_warning(self, log=None) -> Optional[str]:
        """
        Logga (och returnera) varningar om hjalpmodulerna inte ar i synk.

        Tacker tva fall:
          1. css/js-modul saknas  -> reservmall anvands (K4)
          2. css/js har annan VERSION an mallarna -> versionsdrift (K9)

        Returnerar:
            Meddelandestrang eller None om allt ar OK.
        """
        msgs = []
        if not ASSETS_AVAILABLE:
            msgs.append(
                "html_generator_css/js saknas - reservmall anvands (%s)"
                % ASSET_ERROR
            )
        else:
            for name, ver in self.asset_versions().items():
                if ver != VERSION:
                    msgs.append(
                        "%s ar v%s men mallarna ar v%s - kopiera alla filer"
                        % (name, ver, VERSION)
                    )
        for msg in msgs:
            self._warn(log, msg)
        return "; ".join(msgs) if msgs else None
