#!/usr/bin/env python3
# ============================================================
# Hjalpmodul (JavaScript) for plugins/html_generator_templates.py
# ============================================================
# FIL:       plugins/html_generator_js.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/html_generator_js.py)
# VERSION:   3.4.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
# Syfte:     All JavaScript for de GENERERADE sidorna.
#
#            OBS: Denna fil definierar INGEN PLUGIN_NAME och ignoreras
#            darfor av plugin-loadern (laddas bara som import).
#
# ÄNDRINGAR v3.3.0 → v3.4.0:
#   Radjamnt: malhojd ~140 px (densitet/viewport), inte W/kolumner.
#   Bryter rader sa hojden halls inom ~20 % – thumbnails lika stora.
#
# ÄNDRINGAR v3.1.0 → v3.2.0:
#   [L1]      RADJÄMNT galleri: layoutJustified() räknar ut rader som fyller
#             bredden exakt ur varje bilds proportion (--ar från generatorn,
#             annars naturalWidth/Height) och sätter --w/--h per kort.
#             Ingen beskärning, ordningen bevarad.
#   [L2]      Layoutväxlare Radjämnt ↔ Rutnät (data-layout på <html>,
#             sparas i localStorage, återställd av BOOT_JS före paint).
#   [L5]      Omräkning vid: init, resize (debounce), filter, bildladdning
#             (okänd proportion), densitetsbyte, layoutbyte.
#
# ÄNDRINGAR v3.0.0 → v3.1.0:
#   [J12] BOOT_JS återställer tema/densitet före första paint (ingen FOUC).
#   [J13] Tema-/densitetsväxlare (applyThemeMeta skriver inte data-theme).
#   [J14] Djuplänkar #bild-7/#video-2 + dela-knapp (clipboard/prompt).
#   [J15] Slideshow: temaväxlare + start från hash.
#
# ÄNDRINGAR v2.9.0 → v3.0.0 (sammandrag):
#   [J1] IIFE + "use strict", publikt API + gamla globaler bevarade.
#   [J2] Event-delegation (EN lyssnare for alla kort).  [J3] .loaded/.done/
#   .failed styr skeleton+intoning.  [J4] IntersectionObserver-intoning.
#   [J5] Sok/filter med debounce.  [J6] Lightbox: filmstrip, spinner,
#   felmeddelande, nerladdning, zoom+drag-pan, helskarm, fokusfalla+inert.
#   [J7] Svep via Pointer Events.  [J8] Preload av grannar.
#   [J9] theme-color ur CSS-tokens.  [J10] Slideshow: EN rAF-loop + paus
#   vid flikbyte + auto-hide.  [J11] Null-sakrade elementhamtningar.
#
# TEKNISK DETALJ:
#   Vanliga strangar (INTE f-strings). {{IMAGES_JS}} / {{VIDEOS_JS}}
#   ersatts med str.replace() i html_generator.py. Ingen ES6-syntax
#   (var/function) for maximal browserkompatibilitet pa publika sidor.
# ============================================================

from datetime import datetime

VERSION   = "3.4.0"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

# ============================================================
# BOOT (liten, ligger i <head> fore CSS:en)
# ============================================================

BOOT_JS = """
    /* Satt .js pa <html> sa CSS kan skilja JS/ingen-JS (J4, D4) och
       aterstall besokarens sparade tema/densitet FORE forsta paint
       (J12 - ingen FOUC). Utan JS ar alla kort direkt synliga. */
    (function () {
      var d = document.documentElement;
      d.className = (d.className ? d.className + " " : "") + "js";
      try {
        var t = window.localStorage.getItem("gu-theme");
        if (t === "dark" || t === "light" || t === "colorful") {
          d.setAttribute("data-theme", t);
        }
        var g = window.localStorage.getItem("gu-density");
        if (g === "compact" || g === "comfortable") {
          d.setAttribute("data-density", g);
        }
        /* Bara "grid" behover attribut - radjamnt ar standard (L2). */
        if (window.localStorage.getItem("gu-layout") === "grid") {
          d.setAttribute("data-layout", "grid");
        }
      } catch (e) {}
    })();
"""

# ============================================================
# INDEX.JS  (galleri + lightbox)
# ============================================================

INDEX_JS = """
  (function () {
    "use strict";

    /* ---- Data fran generatorn ---- */
    var IMAGES = {{IMAGES_JS}};
    var VIDEOS = {{VIDEOS_JS}};

    /* ---- Sma hjalpare ---- */
    function $(id) { return document.getElementById(id); }
    function on(el, ev, fn, opt) {
      if (el) { el.addEventListener(ev, fn, opt || false); }
    }
    function wrap(i, len) { return len ? ((i % len) + len) % len : 0; }
    function esc(s) {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }
    var reduceMotion = false;
    try {
      reduceMotion = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) { reduceMotion = false; }

    var root = document.documentElement, body = document.body;
    var gallery = $("gallery");
    var cards = gallery ? gallery.querySelectorAll(".card") : [];

    /* ==========================================================
       J9 - tema-meta (theme-color, color-scheme, data-theme)
       ========================================================== */
    function applyThemeMeta() {
      var cs = window.getComputedStyle(root);
      function tok(name) {
        return (cs.getPropertyValue(name) || "").replace(/^\\s+|\\s+$/g, "");
      }
      /* OBS: skriver INTE data-theme - det skulle lasa fast temat och
         stanga av prefers-color-scheme (J13). */
      var color  = tok("--meta-theme-color");
      var scheme = tok("--color-scheme");
      if (color) {
        var m = $("meta-theme-color");
        if (m) { m.setAttribute("content", color); }
      }
      if (scheme) {
        var c = document.querySelector('meta[name="color-scheme"]');
        if (c) { c.setAttribute("content", scheme); }
      }
    }
    applyThemeMeta();
    try {
      var mq = window.matchMedia("(prefers-color-scheme: light)");
      if (mq && mq.addEventListener) {
        mq.addEventListener("change", applyThemeMeta);
      }
    } catch (e) {}

    /* ==========================================================
       J3 - bildladdning: skeleton -> intoning / fel
       ========================================================== */
    function markLoaded(img) {
      img.classList.add("loaded");
      var c = img.parentNode;
      if (c && c.classList) { c.classList.add("done"); }
      /* L5: utan --ar från generatorn mäts proportionen först nu */
      if (c && !c.getAttribute("style")) { layoutSoon(); }
    }
    function markFailed(img) {
      img.classList.add("loaded");
      img.classList.add("failed");
      var c = img.parentNode;
      if (c && c.classList) { c.classList.add("done"); }
    }
    for (var ci = 0; ci < cards.length; ci++) {
      (function (img) {
        if (!img) { return; }
        if (img.complete && img.naturalWidth) {
          markLoaded(img);
          return;
        }
        on(img, "load", function () { markLoaded(img); });
        on(img, "error", function () { markFailed(img); });
      })(cards[ci].querySelector("img"));
    }

    /* ==========================================================
       J4 - intoning av kort (IntersectionObserver)
       ========================================================== */
    function revealAll() {
      for (var i = 0; i < cards.length; i++) { cards[i].classList.add("in"); }
    }
    if ("IntersectionObserver" in window && cards.length) {
      var io = new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (!entries[i].isIntersecting) { continue; }
          entries[i].target.classList.add("in");
          io.unobserve(entries[i].target);
        }
      }, { rootMargin: "200px 0px", threshold: 0.01 });
      for (var oi = 0; oi < cards.length; oi++) { io.observe(cards[oi]); }
    } else {
      revealAll();
    }

    /* ==========================================================
       J5 - sok/filter (bilder + videor)
       ========================================================== */
    var filterInput = $("filter-input"), filterClear = $("filter-clear");
    var countPill = $("count-pill"), emptyState = $("empty-state");
    var searchBox = filterInput ? filterInput.parentNode : null;
    var vStrip = $("video-strip");
    var vCards = vStrip ? vStrip.querySelectorAll(".vcard") : [];
    var totalCards = cards.length;

    function textOf(card, sel) {
      var label = card.getAttribute("aria-label") || "";
      var extra = card.querySelector(sel);
      return (label + " " + (extra ? extra.textContent : "")).toLowerCase();
    }
    var cardTexts = [];
    for (var ti = 0; ti < cards.length; ti++) {
      cardTexts.push(textOf(cards[ti], ".card-overlay"));
    }
    var vCardTexts = [];
    for (var vi = 0; vi < vCards.length; vi++) {
      vCardTexts.push(textOf(vCards[vi], ".vname"));
    }

    function applyFilter() {
      var q = filterInput ? (filterInput.value || "").toLowerCase() : "";
      q = q.replace(/^\\s+|\\s+$/g, "");
      var shown = 0;
      for (var i = 0; i < cards.length; i++) {
        var hit = !q || cardTexts[i].indexOf(q) !== -1;
        if (hit) { shown++; }
        cards[i].classList.toggle("hidden-by-filter", !hit);
      }
      var vShown = 0;
      for (var j = 0; j < vCards.length; j++) {
        var vHit = !q || vCardTexts[j].indexOf(q) !== -1;
        if (vHit) { vShown++; }
        vCards[j].classList.toggle("hidden-by-filter", !vHit);
      }
      if (countPill) {
        countPill.textContent = q
          ? shown + " / " + totalCards + " bilder"
          : shown + (shown === 1 ? " bild" : " bilder");
        countPill.classList.toggle("filtered", !!q);
      }
      if (searchBox) { searchBox.classList.toggle("filled", !!q); }
      if (emptyState) {
        emptyState.hidden = (shown !== 0 || vShown !== 0 || !q);
      }
      layoutSoon();     /* L5: radjämnt måste räknas om efter filtrering */
    }

    var filterTimer = null;
    function filterSoon() {
      if (filterTimer) { clearTimeout(filterTimer); }
      filterTimer = setTimeout(applyFilter, 110);
    }
    on(filterInput, "input", filterSoon);
    on(filterInput, "keydown", function (e) {
      if (e.key === "Escape") {
        filterInput.value = "";
        applyFilter();
        e.stopPropagation();
      }
    });
    on(filterClear, "click", function () {
      if (!filterInput) { return; }
      filterInput.value = "";
      applyFilter();
      filterInput.focus();
    });
    if (filterInput) { applyFilter(); }

    /* ==========================================================
       Tillbaka-till-topp
       ========================================================== */
    var toTop = $("to-top");
    var scrollTick = false;
    function onScroll() {
      if (scrollTick) { return; }
      scrollTick = true;
      window.requestAnimationFrame(function () {
        if (toTop) {
          toTop.classList.toggle("show", window.pageYOffset > 600);
        }
        scrollTick = false;
      });
    }
    on(window, "scroll", onScroll, { passive: true });
    on(toTop, "click", function () {
      try {
        window.scrollTo({
          top: 0,
          behavior: reduceMotion ? "auto" : "smooth"
        });
      } catch (e) { window.scrollTo(0, 0); }
    });

    /* ==========================================================
       J6/J7/J8 - LIGHTBOX
       ========================================================== */
    var lb = $("lightbox"), lbImg = $("lb-img"), lbVid = $("lb-video");
    var lbCap = $("lb-caption"), lbCount = $("lb-counter");
    var lbStrip = $("lb-strip"), lbSpinner = $("lb-spinner");
    var lbError = $("lb-error"), lbDown = $("lb-download");
    var lbZoomBtn = $("lb-zoom"), lbFull = $("lb-fullscreen");
    var lbStage = $("lb-stage");

    var LIST = IMAGES, current = 0, lastFocus = null, zoomed = false;
    var panX = 0, panY = 0, stripKey = "", suppressClick = false;

    function videoMode() { return LIST === VIDEOS; }

    function spinner(showIt) {
      if (lbSpinner) { lbSpinner.classList.toggle("show", !!showIt); }
    }
    function showError(showIt) {
      if (lbError) { lbError.classList.toggle("show", !!showIt); }
    }
    function stopVideo() {
      if (lbVid && lbVid.getAttribute("src")) {
        try { lbVid.pause(); } catch (e) {}
        lbVid.removeAttribute("src");
        try { lbVid.load(); } catch (e) {}
      }
    }
    function setZoom(state) {
      zoomed = !!state && !videoMode();
      if (lbImg) {
        lbImg.classList.toggle("zoomed", zoomed);
        lbImg.classList.remove("dragging");
      }
      if (!zoomed) {
        panX = 0; panY = 0;
        if (lbImg) {
          lbImg.style.setProperty("--tx", "0px");
          lbImg.style.setProperty("--ty", "0px");
        }
      }
      if (lbZoomBtn) {
        lbZoomBtn.setAttribute("aria-pressed", zoomed ? "true" : "false");
      }
    }

    /* ---- filmstrip (J6) ---- */
    function buildStrip() {
      if (!lbStrip) { return; }
      var key = (videoMode() ? "v" : "i") + LIST.length;
      if (stripKey === key) { syncStrip(); return; }
      stripKey = key;
      var out = [];
      for (var i = 0; i < LIST.length; i++) {
        var item = LIST[i] || {};
        var label = esc(item.title
          || ((videoMode() ? "Video " : "Bild ") + (i + 1)));
        var inner = videoMode() ? "<span>&#9654;</span>"
          : '<img src="' + esc(item.thumb || item.src || "")
            + '" alt="" loading="lazy" decoding="async">';
        out.push('<button type="button" class="strip-item'
          + (videoMode() ? " video" : "") + '" data-i="' + i
          + '" aria-label="' + label + '" title="' + label + '">'
          + inner + "</button>");
      }
      lbStrip.innerHTML = out.join("");
      lbStrip.classList.toggle("hidden", LIST.length < 2);
      syncStrip();
    }
    function syncStrip() {
      if (!lbStrip) { return; }
      var kids = lbStrip.children;
      for (var i = 0; i < kids.length; i++) {
        var act = (i === current);
        kids[i].classList.toggle("active", act);
        if (act) { kids[i].setAttribute("aria-current", "true"); }
        else { kids[i].removeAttribute("aria-current"); }
        if (act && kids[i].scrollIntoView) {
          try {
            kids[i].scrollIntoView({ block: "nearest", inline: "center" });
          } catch (e) {
            kids[i].scrollIntoView(false);
          }
        }
      }
    }

    function preloadAround(idx) {
      if (videoMode()) { return; }
      var len = IMAGES.length;
      if (len < 2) { return; }
      var offs = [1, -1, 2];
      for (var i = 0; i < offs.length; i++) {
        var it = IMAGES[wrap(idx + offs[i], len)];
        if (it && it.src) {
          var nearby = new Image();
          nearby.sizes = "100vw";
          nearby.srcset = it.srcset || "";
          nearby.src = it.src;
        }
      }
    }

    function showItem() {
      var item = LIST[current];
      if (!item) { return; }
      var title = item.title || "";
      if (lbCap)   { lbCap.textContent = title; }
      if (lbCount) {
        lbCount.textContent = (current + 1) + " / " + LIST.length;
      }
      showError(false);
      setZoom(false);
      if (lbDown) {
        var download = videoMode() ? "" : (item.download || "");
        lbDown.hidden = !download;
        lbDown.style.display = download ? "inline-flex" : "none";
        if (download) {
          lbDown.setAttribute("href", download);
          lbDown.setAttribute("aria-label", item.downloadLabel || "Ladda ned bilden");
          lbDown.setAttribute("title", item.downloadLabel || "Ladda ned bilden");
        } else {
          lbDown.removeAttribute("href");
        }
      }

      stopVideo();
      if (videoMode()) {
        if (lbImg) {
          lbImg.style.display = "none";
          lbImg.removeAttribute("srcset");
          lbImg.removeAttribute("src");
        }
        if (lbVid) {
          lbVid.style.display = "block";
          lbVid.src = item.src;
          var p = lbVid.play();
          if (p && p.catch) { p.catch(function () {}); }
        }
        spinner(false);
      } else {
        if (lbVid) { lbVid.style.display = "none"; }
        if (lbImg) {
          lbImg.style.display = "block";
          spinner(true);
          lbImg.onload = function () { spinner(false); };
          lbImg.onerror = function () { spinner(false); showError(true); };
          lbImg.sizes = "100vw";
          lbImg.srcset = item.srcset || "";
          lbImg.src = item.src;
          lbImg.alt = title;
          if (lbImg.complete) { spinner(false); }
        }
        preloadAround(current);
      }
      syncStrip();
      pushHash();
    }

    function setBackgroundInert(state) {
      try {
        if (!("inert" in HTMLElement.prototype)) { return; }
        var kids = body.children;
        for (var i = 0; i < kids.length; i++) {
          if (kids[i] !== lb && kids[i].nodeType === 1) { kids[i].inert = state; }
        }
      } catch (e) {}
    }

    function openList(list, idx, trigger) {
      if (!lb || !list || !list.length) { return; }
      LIST = list;
      current = wrap(idx, list.length);
      stripKey = "";
      buildStrip();
      showItem();
      lastFocus = trigger || document.activeElement;
      lb.classList.add("active");
      lb.setAttribute("aria-hidden", "false");
      body.classList.add("lb-open");
      setBackgroundInert(true);
      var closeBtn = $("lb-close");
      if (closeBtn && closeBtn.focus) {
        try { closeBtn.focus(); } catch (e) {}
      }
    }
    function openImages(idx, trigger) { openList(IMAGES, idx, trigger); }
    function openVideo(idx, trigger)  { openList(VIDEOS, idx, trigger); }

    function closeLightbox() {
      if (!lb) { return; }
      stopVideo();
      setZoom(false);
      lb.classList.remove("active");
      lb.setAttribute("aria-hidden", "true");
      body.classList.remove("lb-open");
      setBackgroundInert(false);
      pushHash();
      if (lastFocus && lastFocus.focus) {
        try { lastFocus.focus(); } catch (e) {}
      }
    }

    function goTo(idx) {
      if (!LIST.length) { return; }
      current = wrap(idx, LIST.length);
      showItem();
    }
    function navigate(delta) {
      if (!LIST.length) { return; }
      goTo(current + delta);
    }

    function toggleFullscreen() {
      try {
        var fs = document.fullscreenElement || document.webkitFullscreenElement;
        if (!fs) {
          if (root.requestFullscreen) { root.requestFullscreen(); }
          else if (root.webkitRequestFullscreen) { root.webkitRequestFullscreen(); }
        } else if (document.exitFullscreen) { document.exitFullscreen(); }
        else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); }
      } catch (e) {}
    }

    /* ---- J2: delegation for bildkort ---- */
    function closestCard(target, limit, cls, attr) {
      var el = target;
      while (el && el !== limit) {
        if (el.nodeType === 1 && el.classList &&
            el.classList.contains(cls) && el.hasAttribute(attr)) { return el; }
        el = el.parentNode;
      }
      return null;
    }
    function bindCards(zone, cls, attr, opener) {
      function handle(e, isKey) {
        if (isKey && e.key !== "Enter" && e.key !== " " &&
            e.key !== "Spacebar") { return; }
        var card = closestCard(e.target, zone, cls, attr);
        if (!card) { return; }
        if (isKey) { e.preventDefault(); }
        opener(parseInt(card.getAttribute(attr), 10) || 0, card);
      }
      on(zone, "click", function (e) { handle(e, false); });
      on(zone, "keydown", function (e) { handle(e, true); });
    }
    bindCards(gallery, "card", "data-index", openImages);
    bindCards(vStrip, "vcard", "data-video-index", openVideo);

    /* ---- knappar ---- */
    on($("lb-close"), "click", closeLightbox);
    on($("lb-prev"), "click", function () { navigate(-1); });
    on($("lb-next"), "click", function () { navigate(1); });
    on(lbZoomBtn, "click", function () { setZoom(!zoomed); });
    on(lbFull, "click", toggleFullscreen);
    on(lbStrip, "click", function (e) {
      var el = e.target;
      while (el && el !== lbStrip) {
        if (el.nodeType === 1 && el.classList &&
            el.classList.contains("strip-item")) {
          goTo(parseInt(el.getAttribute("data-i"), 10) || 0);
          return;
        }
        el = el.parentNode;
      }
    });
    on(lb, "click", function (e) {
      if (e.target === lb || (lbStage && e.target === lbStage)) {
        closeLightbox();
      }
    });

    /* ---- zoom + drag-pan ---- */
    on(lbImg, "click", function (e) {
      if (videoMode() || suppressClick) { return; }
      e.stopPropagation();
      setZoom(!zoomed);
    });
    var dragging = false, dragStartX = 0, dragStartY = 0;
    var dragBaseX = 0, dragBaseY = 0;
    on(lbImg, "pointerdown", function (e) {
      if (!zoomed) { return; }
      dragging = true;
      suppressClick = false;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      dragBaseX = panX;
      dragBaseY = panY;
      lbImg.classList.add("dragging");
      if (lbImg.setPointerCapture) {
        try { lbImg.setPointerCapture(e.pointerId); } catch (err) {}
      }
      e.preventDefault();
    });
    on(lbImg, "pointermove", function (e) {
      if (!dragging) { return; }
      var dx = e.clientX - dragStartX;
      var dy = e.clientY - dragStartY;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) { suppressClick = true; }
      panX = dragBaseX + dx;
      panY = dragBaseY + dy;
      lbImg.style.setProperty("--tx", panX + "px");
      lbImg.style.setProperty("--ty", panY + "px");
    });
    function endDrag() {
      dragging = false;
      if (lbImg) { lbImg.classList.remove("dragging"); }
      setTimeout(function () { suppressClick = false; }, 0);
    }
    on(lbImg, "pointerup", endDrag);
    on(lbImg, "pointercancel", endDrag);

    /* ---- J7: svep (Pointer Events) ---- */
    var swipeOn = false, swipeX = 0, swipeY = 0, swipeT = 0;
    var swipeMoved = 0;
    on(lbStage, "pointerdown", function (e) {
      if (zoomed || e.pointerType === "mouse") { return; }
      swipeOn = true;
      swipeMoved = 0;
      swipeX = e.clientX;
      swipeY = e.clientY;
      swipeT = Date.now();
    });
    on(lbStage, "pointermove", function (e) {
      if (!swipeOn) { return; }
      swipeMoved = Math.max(
        swipeMoved, Math.abs(e.clientX - swipeX)
      );
    });
    on(lbStage, "pointerup", function (e) {
      if (!swipeOn) { return; }
      swipeOn = false;
      var dx = e.clientX - swipeX;
      var dy = e.clientY - swipeY;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) &&
          (Date.now() - swipeT) < 1000) {
        navigate(dx < 0 ? 1 : -1);
      }
    });
    on(lbStage, "pointercancel", function () { swipeOn = false; });

    /* ---- tangentbord + fokusfalla (J6) ---- */
    on(document, "keydown", function (e) {
      if (!lb || !lb.classList.contains("active")) { return; }
      var k = e.key;
      if (k === "ArrowLeft" || k === "a" || k === "A") {
        e.preventDefault();
        navigate(-1);
      } else if (k === "ArrowRight" || k === "d" || k === "D") {
        e.preventDefault();
        navigate(1);
      } else if (k === "Home") {
        e.preventDefault();
        goTo(0);
      } else if (k === "End") {
        e.preventDefault();
        goTo(LIST.length - 1);
      } else if (k === "Escape") {
        closeLightbox();
      } else if (k === "f" || k === "F") {
        toggleFullscreen();
      } else if (k === "z" || k === "Z") {
        setZoom(!zoomed);
      } else if (k === "Tab") {
        var nodes = lb.querySelectorAll(
          'a[href], button:not([disabled]), video, [tabindex="0"]');
        var list = [];
        for (var i = 0; i < nodes.length; i++) {
          if (nodes[i].offsetParent !== null ||
              nodes[i] === document.activeElement) { list.push(nodes[i]); }
        }
        if (!list.length) { return; }
        var first = list[0], last = list[list.length - 1];
        var act = document.activeElement;
        if (e.shiftKey && act === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && act === last) { e.preventDefault(); first.focus(); }
      }
    });

    /* ==========================================================
       J13 - tema/densitet: besokaren styr sidan (sparas lokalt)
       ========================================================== */
    var THEME_KEY = "gu-theme", DENSITY_KEY = "gu-density";
    var THEME_ORDER = ["auto", "dark", "light", "colorful"];
    var DENSITY_ORDER = ["standard", "compact", "comfortable"];
    var THEME_LABEL = {
      auto: "Auto", dark: "M\u00f6rk", light: "Ljus",
      colorful: "F\u00e4rgglad"
    };
    var DENSITY_LABEL = {
      standard: "Standard", compact: "Kompakt", comfortable: "Bekv\u00e4m"
    };
    var themeBtn = $("theme-toggle"), densityBtn = $("density-toggle");

    function store(key, value) {
      try { window.localStorage.setItem(key, value); } catch (e) {}
    }
    function currentTheme() {
      var a = root.getAttribute("data-theme");
      return (a === "dark" || a === "light" || a === "colorful") ? a : "auto";
    }
    function currentDensity() {
      var a = root.getAttribute("data-density");
      return (a === "compact" || a === "comfortable") ? a : "standard";
    }
    function setTheme(name, persist) {
      if (name === "auto") { root.removeAttribute("data-theme"); }
      else { root.setAttribute("data-theme", name); }
      if (persist !== false) { store(THEME_KEY, name); }
      applyThemeMeta();
      syncTools();
    }
    function setDensity(name, persist) {
      if (name === "standard") { root.removeAttribute("data-density"); }
      else { root.setAttribute("data-density", name); }
      if (persist !== false) { store(DENSITY_KEY, name); }
      syncTools();
      layoutSoon();     /* L5: radhöjd beror på densitet */
    }
    function labelOf(btn, text) {
      if (!btn) { return; }
      var el = btn.querySelector(".tool-label");
      if (el) { el.textContent = text; }
    }
    function syncTools() {
      var specs = [
        [themeBtn, THEME_LABEL, currentTheme(), "auto", "Tema"],
        [densityBtn, DENSITY_LABEL, currentDensity(), "standard", "Densitet"],
        [layoutBtn, LAYOUT_LABEL, currentLayout(), "justified", "Layout"]
      ];
      for (var i = 0; i < specs.length; i++) {
        var sp = specs[i], v = sp[2], txt = sp[1][v] || v;
        labelOf(sp[0], txt);
        if (!sp[0]) { continue; }
        sp[0].setAttribute("aria-pressed", v === sp[3] ? "false" : "true");
        sp[0].setAttribute("title", sp[4] + ": " + txt
          + " \u2013 klicka f\u00f6r att v\u00e4xla");
      }
    }
    on(themeBtn, "click", function () {
      var i = THEME_ORDER.indexOf(currentTheme());
      setTheme(THEME_ORDER[(i + 1) % THEME_ORDER.length]);
    });
    on(densityBtn, "click", function () {
      var i = DENSITY_ORDER.indexOf(currentDensity());
      setDensity(DENSITY_ORDER[(i + 1) % DENSITY_ORDER.length]);
    });
    syncTools();

    /* ==========================================================
       L1/L2 - radjamn layout (justified rows) + layoutvaxlare
       ========================================================== */
    var LAYOUT_KEY = "gu-layout";
    var LAYOUT_ORDER = ["justified", "grid"];
    var LAYOUT_LABEL = { justified: "Radj\u00e4mnt", grid: "Rutn\u00e4t" };
    var layoutBtn = $("layout-toggle");
    var layoutTimer = null;

    function currentLayout() {
      return root.getAttribute("data-layout") === "grid" ? "grid" : "justified";
    }
    function ratioOf(card) {
      var v = parseFloat(card.style.getPropertyValue("--ar"));
      if (v > 0.2 && v < 12) { return v; }
      var img = card.querySelector("img");
      if (img && img.naturalWidth && img.naturalHeight) {
        return img.naturalWidth / img.naturalHeight;
      }
      return 4 / 3;
    }
    function densityFactor() {
      var d = currentDensity();
      return d === "compact" ? 0.74 : (d === "comfortable" ? 1.22 : 1);
    }
    function clearRowSizes() {
      for (var i = 0; i < cards.length; i++) {
        cards[i].style.removeProperty("--w");
        cards[i].style.removeProperty("--h");
      }
    }
    function layoutJustified() {
      if (!gallery || currentLayout() !== "justified") { return; }
      var items = [];
      for (var i = 0; i < cards.length; i++) {
        if (!cards[i].classList.contains("hidden-by-filter")) {
          items.push(cards[i]);
        }
      }
      if (!items.length) { return; }

      var cs = window.getComputedStyle(gallery);
      var gap = parseFloat(cs.columnGap || cs.gap) || 8;
      var W = gallery.clientWidth;
      if (!W) { return; }

      /* Malhojd i px – samma storlek oavsett kolumn-installning.
         Antal per rad blir dynamiskt utifran varje bilds --ar. */
      var base = W < 520 ? 114 : (W < 900 ? 130 : 144);
      var target = Math.round(base * densityFactor());
      if (target < 96) { target = 96; }
      if (target > 176) { target = 176; }
      var minH = Math.round(target * 0.8);
      var maxH = Math.round(target * 1.16);

      function rowH(n, s) {
        return (W - gap * Math.max(0, n - 1)) / (s || 1);
      }
      function emit(row, sum, isLast) {
        var n = row.length, avail = W - gap * (n - 1), ws = [], tot = 0, k;
        var h = isLast ? target : rowH(n, sum);
        if (isLast) {
          var fillH = rowH(n, sum);
          if (fillH >= minH && fillH <= maxH) { h = fillH; }
        }
        if (h > maxH) { h = maxH; }
        if (h < 64) { h = 64; }
        var need = h * sum;
        var sc = 1;
        if (need > 0 && (!isLast || need > avail)) {
          sc = Math.min(1, (avail * 0.998) / need);
        }
        for (k = 0; k < n; k++) {
          ws[k] = Math.max(40, Math.floor(h * ratioOf(row[k]) * sc));
          tot += ws[k];
        }
        if (tot > avail) {
          for (k = 0; k < n; k++) {
            ws[k] = Math.max(1, Math.floor(ws[k] * avail / tot));
          }
        }
        for (k = 0; k < n; k++) {
          row[k].style.setProperty("--h", Math.round(h) + "px");
          row[k].style.setProperty("--w", ws[k] + "px");
        }
      }

      var row = [], sum = 0, j, ar, hNow, hNext, nowOk, nextBetter;
      for (j = 0; j < items.length; j++) {
        ar = ratioOf(items[j]);
        if (!row.length) {
          row.push(items[j]);
          sum = ar;
          continue;
        }
        hNow = rowH(row.length, sum);
        hNext = rowH(row.length + 1, sum + ar);
        nowOk = hNow <= maxH;
        nextBetter = Math.abs(hNext - target) < Math.abs(hNow - target);
        if (nowOk && (!nextBetter || hNext < minH)) {
          emit(row, sum, false);
          row = [items[j]];
          sum = ar;
        } else {
          row.push(items[j]);
          sum += ar;
        }
      }
      if (row.length) { emit(row, sum, true); }
    }
    function setLayout(name, persist) {
      if (name === "grid") { root.setAttribute("data-layout", "grid"); }
      else { root.removeAttribute("data-layout"); }
      if (persist !== false) { store(LAYOUT_KEY, name); }
      if (name === "grid") { clearRowSizes(); } else { layoutJustified(); }
      syncTools();
    }
    function layoutSoon() {
      if (layoutTimer) { clearTimeout(layoutTimer); }
      layoutTimer = setTimeout(function () {
        layoutTimer = null;
        layoutJustified();
      }, 70);
    }
    on(window, "resize", layoutSoon);
    on(layoutBtn, "click", function () {
      var i = LAYOUT_ORDER.indexOf(currentLayout());
      setLayout(LAYOUT_ORDER[(i + 1) % LAYOUT_ORDER.length]);
    });
    setLayout(currentLayout(), false);

    /* ==========================================================
       J14 - delbara djuplankar (#bild-7 / #video-2) + kopiera lank
       ========================================================== */
    var lbShare = $("lb-share");

    function pushHash() {
      if (!lb) { return; }
      var target;
      if (lb.classList.contains("active")) {
        target = "#" + (videoMode() ? "video-" : "bild-") + (current + 1);
      } else {
        target = window.location.pathname + window.location.search;
      }
      try { window.history.replaceState(null, "", target); } catch (e) {}
    }

    function openFromHash() {
      var m = /^#(bild|img|video)-([0-9]+)$/.exec(
        (window.location.hash || "").toLowerCase()
      );
      if (!m) { return; }
      var n = parseInt(m[2], 10) - 1;
      if (m[1] === "video") {
        if (VIDEOS.length) { openVideo(n); }
      } else if (IMAGES.length) {
        openImages(n);
      }
    }

    function shareLink() {
      var url = window.location.href;
      function done() {
        if (!lbShare) { return; }
        lbShare.classList.add("ok");
        setTimeout(function () { lbShare.classList.remove("ok"); }, 1200);
      }
      function fallback() {
        try { window.prompt("Kopiera l\u00e4nken:", url); } catch (e) {}
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(done, fallback);
      } else {
        fallback();
      }
    }
    on(lbShare, "click", shareLink);

    /* Oppna direkt om l\u00e4nken har en hash (J14) */
    openFromHash();

    /* ==========================================================
       J1 - publik API (+ bakatkompatibla globaler)
       ========================================================== */
    var api = {
      version: "{{VERSION}}",
      images: IMAGES,
      videos: VIDEOS,
      openImage: openImages,
      openVideo: openVideo,
      close: closeLightbox,
      next: function () { navigate(1); },
      prev: function () { navigate(-1); },
      goTo: goTo,
      toggleFullscreen: toggleFullscreen,
      setTheme: setTheme,
      setDensity: setDensity,
      setLayout: setLayout,
      layout: currentLayout,
      theme: currentTheme,
      density: currentDensity,
      shareLink: shareLink,
      filter: function (q) {
        if (!filterInput) { return; }
        filterInput.value = q == null ? "" : String(q);
        applyFilter();
      }
    };
    window.Gallery = api;
    window.openImages = openImages;
    window.openVideo = openVideo;
    window.closeLightbox = closeLightbox;
    window.navigate = navigate;
  })();
"""

# ============================================================
# SLIDESHOW.JS
# ============================================================

SLIDESHOW_JS = """
  (function () {
    "use strict";

    function $(id) { return document.getElementById(id); }
    function on(el, ev, fn, opt) {
      if (el) { el.addEventListener(ev, fn, opt || false); }
    }
    function wrap(i, len) { return len ? ((i % len) + len) % len : 0; }

    var slides = document.querySelectorAll(".slide");
    var area = $("slide-area"), toolbar = $("ss-toolbar");
    var counter = $("ss-counter"), progress = $("progress-fill");
    var playBtn = $("ss-play"), capBtn = $("ss-caption-btn");
    var fullBtn = $("ss-full"), slider = $("speed-slider");
    var speedLbl = $("speed-label"), root = document.documentElement;
    var hint = document.querySelector(".hint");

    var reduceMotion = false;
    try {
      reduceMotion = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) { reduceMotion = false; }

    var idx = 0, playing = true, speed = 4000;
    var elapsed = 0, lastTs = 0, total = slides.length;

    /* ---- tema-meta ur CSS-tokens ---- */
    function applyThemeMeta() {
      var cs = window.getComputedStyle(root);
      function tok(name) {
        return (cs.getPropertyValue(name) || "").replace(/^\\s+|\\s+$/g, "");
      }
      var color = tok("--meta-theme-color");
      var m = $("meta-theme-color");
      if (color && m) { m.setAttribute("content", color); }
    }
    applyThemeMeta();

    function preloadNeighbours(i) {
      if (total < 2) { return; }
      var offs = [1, -1, 2];
      for (var n = 0; n < offs.length; n++) {
        var s = slides[wrap(i + offs[n], total)];
        var img = s ? s.querySelector("img") : null;
        if (img && img.src) {
          var pre = new Image();
          pre.sizes = img.sizes || "100vw";
          pre.srcset = img.srcset || "";
          pre.src = img.src;
        }
      }
    }

    function show(i) {
      if (!total) { return; }
      idx = wrap(i, total);
      for (var n = 0; n < total; n++) {
        slides[n].classList.toggle("active", n === idx);
      }
      var active = slides[idx];
      if (active && !reduceMotion) {
        /* Starta om Ken Burns-animationen */
        var img = active.querySelector("img");
        if (img) {
          img.style.animation = "none";
          /* tvinga reflow */
          void img.offsetWidth;
          img.style.animation = "";
        }
      }
      if (counter) {
        counter.textContent = (idx + 1) + " / " + total;
      }
      try {
        window.history.replaceState(null, "", "#bild-" + (idx + 1));
      } catch (e) {}
      elapsed = 0;
      if (progress) { progress.style.width = "0%"; }
      preloadNeighbours(idx);
    }

    /* ---- J10: EN rAF-loop driver progress + auto-advance ---- */
    function tick(ts) {
      if (!lastTs) { lastTs = ts; }
      var dt = ts - lastTs;
      lastTs = ts;
      if (dt > 500) { dt = 0; }   /* hopp efter vila/flikbyte */

      if (playing && !document.hidden && total > 1) {
        elapsed += dt;
        if (progress) {
          var pct = Math.min(100, (elapsed / speed) * 100);
          progress.style.width = pct + "%";
        }
        if (elapsed >= speed) { show(idx + 1); }
      }
      window.requestAnimationFrame(tick);
    }

    function setPlaying(state) {
      playing = !!state;
      if (playBtn) {
        playBtn.innerHTML = playing ? "&#9208; Pausa" : "&#9654; Spela";
        playBtn.setAttribute("aria-pressed", playing ? "false" : "true");
        playBtn.classList.toggle("primary", playing);
        playBtn.classList.toggle("paused", !playing);
      }
      elapsed = 0;
      if (progress && !playing) { progress.style.width = "0%"; }
    }
    function togglePlay() { setPlaying(!playing); wake(); }

    function next() { show(idx + 1); wake(); }
    function prev() { show(idx - 1); wake(); }

    function setSpeed(sec) {
      speed = Math.max(1, Math.min(10, parseInt(sec, 10) || 4)) * 1000;
      if (speedLbl) { speedLbl.textContent = (speed / 1000) + " s"; }
      elapsed = 0;
    }

    function toggleFullscreen() {
      try {
        var fs = document.fullscreenElement || document.webkitFullscreenElement;
        if (!fs) {
          if (root.requestFullscreen) { root.requestFullscreen(); }
          else if (root.webkitRequestFullscreen) { root.webkitRequestFullscreen(); }
        } else if (document.exitFullscreen) { document.exitFullscreen(); }
        else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); }
      } catch (e) {}
    }

    function toggleCaption() {
      var off = document.body.classList.toggle("no-caption");
      if (capBtn) {
        capBtn.classList.toggle("off", !!off);
        capBtn.setAttribute("aria-pressed", off ? "false" : "true");
      }
    }

    /* ---- verktygsfalt tonar bort vid inaktivitet ---- */
    var idleTimer = null;
    function wake() {
      if (toolbar) { toolbar.classList.remove("idle"); }
      if (hint) { hint.classList.remove("fade"); }
      if (idleTimer) { clearTimeout(idleTimer); }
      idleTimer = setTimeout(function () {
        if (!playing) { return; }
        if (toolbar) { toolbar.classList.add("idle"); }
        if (hint) { hint.classList.add("fade"); }
      }, 2800);
    }
    on(document, "pointermove", wake, { passive: true });
    on(toolbar, "pointerenter", function () {
      if (idleTimer) { clearTimeout(idleTimer); }
      if (toolbar) { toolbar.classList.remove("idle"); }
    });

    /* ---- kontroller ---- */
    on($("ss-prev"), "click", prev);
    on($("ss-next"), "click", next);
    on($("ss-prev-btn"), "click", prev);
    on($("ss-next-btn"), "click", next);
    on(playBtn, "click", togglePlay);
    on(capBtn, "click", toggleCaption);
    on(fullBtn, "click", toggleFullscreen);
    on(slider, "input", function () {
      setSpeed(slider.value);
      wake();
    });

    /* ---- tangentbord ---- */
    on(document, "keydown", function (e) {
      var k = e.key;
      if (k === "ArrowLeft" || k === "a" || k === "A") {
        e.preventDefault();
        prev();
      } else if (k === "ArrowRight" || k === "d" || k === "D") {
        e.preventDefault();
        next();
      } else if (k === "Home") {
        e.preventDefault();
        show(0);
        wake();
      } else if (k === "End") {
        e.preventDefault();
        show(total - 1);
        wake();
      } else if (k === " " || k === "Spacebar") {
        e.preventDefault();
        togglePlay();
      } else if (k === "f" || k === "F") {
        toggleFullscreen();
      } else if (k === "c" || k === "C") {
        toggleCaption();
      } else if (k === "Escape") {
        window.location.href = "index.html";
      }
    });

    /* ---- svep (Pointer Events) ---- */
    var swipeOn = false, swipeX = 0, swipeY = 0;
    on(area, "pointerdown", function (e) {
      if (e.pointerType === "mouse") { return; }
      swipeOn = true;
      swipeX = e.clientX;
      swipeY = e.clientY;
    });
    on(area, "pointerup", function (e) {
      if (!swipeOn) { return; }
      swipeOn = false;
      var dx = e.clientX - swipeX;
      var dy = e.clientY - swipeY;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy)) {
        if (dx < 0) { next(); } else { prev(); }
      }
    });
    on(area, "pointercancel", function () { swipeOn = false; });

    /* ---- flikbyte: nollstall klockan sa inget hopp sker ---- */
    on(document, "visibilitychange", function () {
      lastTs = 0;
      // Preserve elapsed time and the user's manual play/pause choice.
    });

    /* ---- J13: temavaxlare (samma val som i galleriet) ---- */
    var THEME_ORDER = ["auto", "dark", "light", "colorful"];
    var themeBtn = $("ss-theme");
    function store(key, value) {
      try { window.localStorage.setItem(key, value); } catch (e) {}
    }
    function currentTheme() {
      var a = root.getAttribute("data-theme");
      return (a === "dark" || a === "light" || a === "colorful") ? a : "auto";
    }
    function setTheme(name) {
      if (name === "auto") { root.removeAttribute("data-theme"); }
      else { root.setAttribute("data-theme", name); }
      store("gu-theme", name);
      applyThemeMeta();
      if (themeBtn) {
        themeBtn.setAttribute("aria-pressed",
          name === "auto" ? "false" : "true");
        themeBtn.setAttribute("title", "Tema: " + name);
      }
    }
    on(themeBtn, "click", function () {
      var i = THEME_ORDER.indexOf(currentTheme());
      setTheme(THEME_ORDER[(i + 1) % THEME_ORDER.length]);
    });
    if (themeBtn) {
      themeBtn.setAttribute("aria-pressed",
        currentTheme() === "auto" ? "false" : "true");
    }

    /* ---- start (J15: oppna pa bild fran hash om den finns) ---- */
    if (slider) { setSpeed(slider.value); }
    for (var s = 0; s < Math.min(3, total); s++) {
      var early = slides[s].querySelector("img");
      if (early) { early.setAttribute("loading", "eager"); }
    }
    var startIdx = 0;
    var hashMatch = /^#(bild|img)-([0-9]+)$/.exec(
      (window.location.hash || "").toLowerCase()
    );
    if (hashMatch) { startIdx = parseInt(hashMatch[2], 10) - 1; }
    show(startIdx);
    setPlaying(true);
    wake();
    window.requestAnimationFrame(tick);

    window.Slideshow = {
      next: next,
      prev: prev,
      show: show,
      togglePlay: togglePlay,
      setSpeed: setSpeed,
      toggleFullscreen: toggleFullscreen,
      toggleCaption: toggleCaption,
      setTheme: setTheme,
      theme: currentTheme
    };
  })();
"""
