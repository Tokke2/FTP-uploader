#!/usr/bin/env python3
# ============================================================
# Gallery Uploader - Plugin-paket
# ============================================================
# FIL:       plugins/__init__.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/__init__.py)
# Syfte:     Gor plugins/ till ett Python-paket.
#            Minimal kod - main.py hanterar all plugin-logik.
# VERSION:   1.0.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# DESIGN-BESLUT:
#   All plugin-discovery, laddning och hantering sker i main.py.
#   Denna fil ar avsiktligt minimal for att undvika:
#     - Cirkulara importer
#     - Dubblerad logik
#     - Onodig komplexitet
#
# main.py ansvarar for:
#   - pkgutil.iter_modules()  - hitta plugins
#   - importlib.import_module - ladda plugins
#   - PRIORITY-sortering      - korordning
#   - app.context             - delad data
#   - plugin.init(app)        - initiering
#   - plugin.execute(ctx)     - pipeline
#
# IMPORTER: Inga (avsiktligt minimal, B3-konstanter endast)
# ============================================================

from datetime import datetime

VERSION   = "1.0.0"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, AUTHOR)

__all__ = ["VERSION", "AUTHOR", "COPYRIGHT"]
