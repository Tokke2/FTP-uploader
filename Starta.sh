#!/bin/sh
# Copyright (c) 2026 Rickard Längkvist
# No runtime upgrade and no installation prompt when Python already exists.
set -u
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
launch() {
    if "$1" -I -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
        if [ ! -f "$BASE/start.pyw" ]; then
            printf '%s\n' 'start.pyw saknas. Packa upp hela releasepaketet.' >&2
            exit 1
        fi
        cd "$BASE" || exit 1
        interpreter=$1
        shift
        exec "$interpreter" "$BASE/start.pyw" "$@"
    fi
}
# Probe executability only. Missing Tk/old Python is reported by the Python
# launcher, not interpreted as permission to install another interpreter.
for name in python3 python; do
    candidate=$(command -v "$name" 2>/dev/null || :)
    if [ -n "$candidate" ]; then launch "$candidate" "$@"; fi
done
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 /Library/Frameworks/Python.framework/Versions/*/bin/python3 "$HOME"/.local/bin/python3 /opt/python*/bin/python3; do
    if [ -x "$candidate" ]; then launch "$candidate" "$@"; fi
done
printf '%s\n' 'Python saknas. Ingen installation sker utan ditt godkännande.'
if [ ! -t 0 ]; then
    printf '%s\n' 'Kör sh Starta.sh i en terminal för installationserbjudandet.' >&2
    exit 1
fi
printf '%s' 'Vill du öppna installationssidan/instruktionen? [j/N] '
read -r answer
case "$answer" in j|J|ja|Ja|y|Y|yes) ;; *) exit 0 ;; esac
case "$(uname -s)" in
    Darwin)
        printf '%s\n' 'Installera senaste stabila macOS-Python med Tcl/Tk. Kör sedan startaren igen.'
        open 'https://www.python.org/downloads/macos/'
        ;;
    Linux)
        printf '%s\n' 'Använd distributionens senaste stödda Python, inte en manuell ersättning av system-Python.'
        if command -v apt-get >/dev/null 2>&1; then
            printf '%s\n' 'Installationskommando: sudo apt-get update && sudo apt-get install python3 python3-tk'
        elif command -v dnf >/dev/null 2>&1; then
            printf '%s\n' 'Installationskommando: sudo dnf install python3 python3-tkinter'
        elif command -v pacman >/dev/null 2>&1; then
            printf '%s\n' 'Installationskommando: sudo pacman -Syu python tk'
        else
            printf '%s\n' 'Installera Python 3 och Tk via din distributions pakethanterare.'
        fi
        printf '%s\n' 'Kör kommandot själv och starta sedan sh Starta.sh igen.'
        ;;
    *) printf '%s\n' 'Operativsystemet saknar installationsguide i denna startare.' >&2; exit 1 ;;
esac
