#!/usr/bin/env python3
# ============================================================
# Gallery Uploader – App-ikoner (icon/)
# ============================================================
# FIL:       app_icon.py
# PLATS:     projektrot (ftp_gallery_uploader/)
# VERSION:   1.0.0
# AUTHOR:    Rickard Längkvist
# Syfte:     Kanonisk ikonkalla. Alla ytor (fonster, aktivitetsfalt,
#            systray) laser harifran. Haller helpers.py under 1800.
#
# MAPPAR / FILER (icon/):
#   icon.ico        Windows: fonster + aktivitetsfalt + Alt-Tab
#   icon.png        Standard-PNG (Linux/Mac fonster, fallback)
#   icon_16.png     Titelrad / liten systray
#   icon_32.png     Aktivitetsfalt
#   icon_64.png     Systray (foretrad)
#   icon_256.png    Hog DPI / Alt-Tab
#   ikon_oversikt.png   Oversikt (anvands inte runtime)
#
# SOKORDNING: icon/  ->  assets/  ->  generate_app_icon() fallback
#
# REGLER: inga f-strings, ingen print().
# ============================================================

import sys
from pathlib import Path

VERSION = "1.0.0"

_ICON_SIZE_FILES = {
    16:  "icon_16.png",
    32:  "icon_32.png",
    64:  "icon_64.png",
    256: "icon_256.png",
}


def _base() -> Path:
    """Projektrot (samma logik som helpers.get_base_path)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()


def get_icon_path() -> Path:
    """
    Returnera icon/-mappens Path (kanonisk ikonkalla).

    Skapar mappen om den saknas.
    """
    p = _base() / "icon"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def resolve_icon_file(*names):
    """
    Forsta existerande ikonfil.

    Soker icon/ forst, sedan assets/ (bakatkompatibilitet).
    Returnerar Path eller None.
    """
    roots = [get_icon_path(), _base() / "assets"]
    for root in roots:
        for name in names:
            try:
                cand = root / name
                if cand.is_file():
                    return cand
            except Exception:
                continue
    return None


def load_app_icon(prefer_size=64):
    """
    Ladda appens ikon som PIL.Image (RGBA) for systray m.m.

    prefer_size: 16, 32, 64 eller 256 - narmaste PNG valjs,
    sedan icon.png, sedan icon.ico, sedan genererad fallback.

    Returnerar (image, kalla_str) t.ex. ("icon/icon_64.png",).
    """
    from PIL import Image
    try:
        size = int(prefer_size)
    except Exception:
        size = 64
    order = []
    if size in _ICON_SIZE_FILES:
        order.append(_ICON_SIZE_FILES[size])
    for s in (64, 32, 256, 16):
        n = _ICON_SIZE_FILES[s]
        if n not in order:
            order.append(n)
    order.extend(["icon.png", "icon.ico"])
    path = resolve_icon_file(*tuple(order))
    if path is not None:
        try:
            img = Image.open(path)
            img = img.convert("RGBA")
            try:
                rel = str(path.relative_to(_base())).replace("\\", "/")
            except Exception:
                rel = "icon/%s" % path.name
            return img, rel
        except Exception:
            pass
    from helpers import generate_app_icon
    return generate_app_icon((size, size)), "genererad fallback"


def apply_tk_window_icon(window) -> str:
    """
    Satt fonster- och aktivitetsfalts-ikon fran icon/.

    Windows: icon.ico via iconbitmap (aktivitetsfalt / Alt-Tab).
    Alla OS: PNG-storlekar via iconphoto (16/32/64/256 + icon.png).
    Referenser halls pa window._icon_photos sa GC inte slar.

    Returnerar kallbeskrivning for loggning.
    """
    photos = []
    source = "ingen"
    ico = resolve_icon_file("icon.ico")
    if ico is not None:
        try:
            window.iconbitmap(str(ico))
            try:
                rel = str(ico.relative_to(_base())).replace("\\", "/")
            except Exception:
                rel = "icon/%s" % ico.name
            source = rel
        except Exception:
            pass

    try:
        from PIL import Image, ImageTk
    except ImportError:
        try:
            window._icon_photos = photos
        except Exception:
            pass
        return source

    png_names = (
        "icon_16.png", "icon_32.png", "icon_64.png",
        "icon_256.png", "icon.png",
    )
    for name in png_names:
        pth = resolve_icon_file(name)
        if pth is None:
            continue
        try:
            img = Image.open(pth)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            photos.append(ImageTk.PhotoImage(img))
        except Exception:
            continue

    if photos:
        try:
            window.iconphoto(True, *tuple(photos))
            if source == "ingen":
                source = "icon/*.png"
            else:
                source = "%s + PNG" % source
        except Exception:
            try:
                window.iconphoto(True, photos[0])
            except Exception:
                pass

    if source == "ingen" and not photos:
        try:
            from helpers import generate_app_icon
            gen = generate_app_icon((64, 64))
            if gen is not None:
                ph = ImageTk.PhotoImage(gen)
                photos.append(ph)
                window.iconphoto(True, ph)
                source = "genererad fallback"
        except Exception:
            pass

    try:
        window._icon_photos = photos
        if photos:
            window._icon_photo = photos[0]
    except Exception:
        pass
    return source
