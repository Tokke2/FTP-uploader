# Copyright (c) 2026 Rickard Längkvist
"""Shared progressive enhancements for both rich and fallback gallery scripts."""
TOOLS_HTML = '''
<style>
#visitor-help{max-width:min(90vw,620px);padding:24px;border-radius:12px;background:#101827;color:#fff;border:1px solid #8791a8}
#visitor-help::backdrop{background:#000b}
#visitor-help button,.visitor-tool{font:inherit;padding:10px 14px;border:1px solid #8791a8;border-radius:8px;cursor:pointer;background:#182840;color:white}
#visitor-help dt{font-weight:bold;margin-top:12px}#visitor-help dd{margin-left:0}
html.visitor-hidden .slide img{animation-play-state:paused!important}
#visitor-tool-status{font:14px system-ui}
</style>
<dialog id="visitor-help" aria-labelledby="visitor-help-title">
<h2 id="visitor-help-title">Tangentbordshjälp</h2>
<p>Tab flyttar fokus. Enter aktiverar vald knapp eller länk. Kortkommandon gäller inte när du skriver i ett fält.</p>
<dl><dt>Galleri</dt><dd>Öppna ett bildkort med Enter. F: helskärm. ?: hjälp.</dd>
<dt>Öppen bild / bildspel</dt><dd>← / → eller A / D: föregående/nästa. Home / End: första/sista. F: helskärm.</dd>
<dt>Lightbox</dt><dd>Z: zoom (om tillgängligt). Escape: stäng bilden.</dd>
<dt>Bildspel</dt><dd>Mellanslag: pausa/spela. C: visa/dölj bildtext (om tillgängligt). Escape: tillbaka till galleriet.</dd>
<dt>Hjälp och helskärm</dt><dd>Escape stänger först hjälpen. Webbläsaren använder Escape för att lämna helskärm.</dd></dl>
<button id="visitor-help-close" type="button">Stäng hjälpen</button></dialog>
'''
TOOLS_JS = r'''
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var help = doc.getElementById("visitor-help"), previous = null;
  var host = doc.querySelector(".nav-bar") || doc.getElementById("ss-toolbar") || doc.body;
  var helpButton = doc.createElement("button");
  helpButton.type = "button"; helpButton.className = "visitor-tool";
  helpButton.textContent = "Tangentbordshjälp (?)";
  helpButton.setAttribute("aria-controls", "visitor-help"); host.appendChild(helpButton);
  var status = doc.createElement("span"); status.id = "visitor-tool-status";
  status.setAttribute("role", "status"); host.appendChild(status);
  function isOpen() { return help && help.open; }
  function closeHelp() {
    if (help && help.close) { help.close(); }
    if (previous && previous.focus) { previous.focus(); }
  }
  function openHelp() {
    previous = doc.activeElement;
    if (help && help.showModal) { help.inert = false; help.showModal(); }
    else { window.alert(help ? help.textContent : "Tangentbordshjälp saknas."); }
  }
  helpButton.addEventListener("click", openHelp);
  doc.getElementById("visitor-help-close").addEventListener("click", closeHelp);
  if (help) { help.addEventListener("close", function () { if (previous && previous.focus) { previous.focus(); } }); }
  var full = doc.getElementById("ss-full");
  if (!full) {
    full = doc.createElement("button"); full.type = "button"; full.className = "visitor-tool";
    full.textContent = "Helskärm (F)"; host.appendChild(full);
  }
  var supported = !!(root.requestFullscreen || root.webkitRequestFullscreen);
  full.hidden = !supported;
  if (!supported) { full.style.display = "none"; }
  full.setAttribute("aria-pressed", "false");
  function fullscreen() {
    try {
      var active = doc.fullscreenElement || doc.webkitFullscreenElement, result;
      if (active) {
        if (doc.exitFullscreen) { result = doc.exitFullscreen(); }
        else if (doc.webkitExitFullscreen) { result = doc.webkitExitFullscreen(); }
      } else if (root.requestFullscreen) { result = root.requestFullscreen(); }
      else if (root.webkitRequestFullscreen) { result = root.webkitRequestFullscreen(); }
      if (result && result.catch) { result.catch(function () { status.textContent = "Webbläsaren tillät inte helskärm."; }); }
    } catch (error) { status.textContent = "Helskärm är inte tillgängligt här."; }
  }
  full.addEventListener("click", function (event) { event.stopImmediatePropagation(); fullscreen(); }, true);
  var wasFull = false, lastFullExit = 0;
  function syncFull() {
    var active = !!(doc.fullscreenElement || doc.webkitFullscreenElement);
    if (wasFull && !active) { lastFullExit = Date.now(); }
    wasFull = active;
    full.setAttribute("aria-pressed", String(active));
    full.setAttribute("aria-label", active ? "Lämna helskärm" : "Visa helskärm");
  }
  doc.addEventListener("fullscreenchange", syncFull);
  doc.addEventListener("webkitfullscreenchange", syncFull);
  doc.addEventListener("keydown", function (event) {
    var target = event.target, key = event.key;
    if (event.ctrlKey || event.altKey || event.metaKey) { return; }
    if (isOpen()) {
      if (key === "Escape") { event.preventDefault(); closeHelp(); }
      // Let native dialog Tab focus handling run, but block slideshow shortcuts.
      event.stopImmediatePropagation(); return;
    }
    if (key === "Escape" && (doc.fullscreenElement || doc.webkitFullscreenElement ||
        (lastFullExit && Date.now() - lastFullExit < 300))) {
      event.stopImmediatePropagation(); return;
    }
    if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) {
      event.stopImmediatePropagation(); return;
    }
    if (target && target.tagName === "BUTTON" && (key === " " || key === "Enter")) {
      event.stopImmediatePropagation(); return;
    }
    if (key === "?") { event.preventDefault(); event.stopImmediatePropagation(); openHelp(); }
    else if ((key === "f" || key === "F") && supported) {
      event.preventDefault(); event.stopImmediatePropagation(); fullscreen();
    }
  }, true);
  function visibility() { root.classList.toggle("visitor-hidden", doc.hidden); }
  doc.addEventListener("visibilitychange", visibility); visibility();
})();
'''
