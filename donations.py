# Copyright (c) 2026 Rickard Längkvist
"""Offline Swish QR and direct payment buttons, no intermediary support page."""
from pathlib import Path
from types import MappingProxyType
import webbrowser

SWISH_NUMBER = '0721817177'
SWISH_PAYEE = '46721817177'
# Swish C-format, no fixed amount/message; those remain editable (mask 6).
SWISH_PAYLOAD = 'C' + SWISH_PAYEE + ';;;6'
QR_FILE = Path(__file__).resolve().parent / 'icon' / 'swish-donation.png'

PAYMENT_LINKS = MappingProxyType({
    'paypal': 'https://paypal.me/Rickard3dPrint',
    'kofi': 'https://ko-fi.com/tokke2',
})

SUPPORT_TEXT = (
    'Har FTP Uploader gjort din vardag lite enklare?\n\n'
    'Appen är gratis att använda, både privat och i företag. Om du vill '
    'kan du lämna en frivillig gåva som ett tack och stöd till fortsatt '
    'utveckling, felsökning och underhåll.\n\n'
    'Du väljer själv belopp. Ingen donation krävs, inga funktioner låses upp '
    'och du kan fortsätta använda appen precis som vanligt utan att betala.\n\n'
    'Tack för att du använder FTP Uploader – ditt stöd uppskattas!\n'
    'Rickard Längkvist'
)


def open_payment(service):
    """Only predefined recipient profiles; no URL from settings or input."""
    return webbrowser.open(PAYMENT_LINKS[service])


def support_window_size(screen_width, screen_height):
    """Fit the usable screen instead of assuming a tall desktop."""
    return max(280, min(760, screen_width - 40)), max(240, min(780, screen_height - 80))


def show_donations(parent):
    import tkinter as tk
    previous = getattr(parent, '_donation_window', None)
    if previous is not None:
        try:
            if previous.winfo_exists():
                previous.deiconify()
                previous.lift()
                previous.focus_set()
                return
        except tk.TclError:
            pass
    window = tk.Toplevel(parent)
    parent._donation_window = window
    window.title('Donationer – Stöd FTP Uploader')
    bg, surface = '#101827', '#192538'
    window.configure(bg=bg)
    width, height = support_window_size(window.winfo_screenwidth(), window.winfo_screenheight())
    window.geometry('%dx%d' % (width, height))
    window.minsize(min(340, width), min(360, height))
    window.bind('<Escape>', lambda event: window.destroy())
    window.protocol('WM_DELETE_WINDOW', window.destroy)
    from app_icon import apply_tk_window_icon
    apply_tk_window_icon(window)
    # Fixed close row stays reachable; the support content scrolls independently.
    footer = tk.Frame(window, bg=bg, padx=12, pady=8)
    footer.pack(side='bottom', fill='x')
    tk.Button(footer, text='Stäng', command=window.destroy, bg='#334766', fg='white',
              activebackground='#435c80', activeforeground='white', relief='flat',
              padx=24, pady=9, cursor='hand2').pack(side='right')
    tk.Label(footer, text='Frivilligt stöd – inga låsta funktioner', bg=bg, fg='#67e8f9',
             font=('TkDefaultFont', 9), wraplength=230).pack(side='left', fill='x', expand=True)
    canvas = tk.Canvas(window, bg=bg, highlightthickness=0)
    scrollbar = tk.Scrollbar(window, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    body = tk.Frame(canvas, bg=bg, padx=16, pady=18)
    item = canvas.create_window(0, 0, window=body, anchor='nw')
    body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
    labels = []

    def label(text, size=11, color='#d2dbea', bold=False, host=None):
        host = host if host is not None else body
        widget = tk.Label(host, text=text, bg=host.cget('bg'), fg=color,
                          font=('TkDefaultFont', size, 'bold' if bold else 'normal'),
                          wraplength=420, justify='center')
        widget.pack(fill='x', pady=6)
        labels.append(widget)
        return widget

    label('FRIVILLIGT STÖD · INGA PRENUMERATIONSKRAV', 9, '#67e8f9', True)
    label('Gillar du FTP Uploader?', 23, '#ffffff', True)
    label(SUPPORT_TEXT)
    cards = tk.Frame(body, bg=bg)
    cards.pack(fill='x', pady=10)
    swish = tk.Frame(cards, bg=surface, padx=14, pady=16, highlightthickness=1, highlightbackground='#67e8f9')
    online = tk.Frame(cards, bg=surface, padx=14, pady=16, highlightthickness=1, highlightbackground='#c4b5fd')
    label('Swish', 19, '#67e8f9', True, swish)
    label('Skanna QR-koden i Swish.\nVälj själv belopp i Swish-appen.', host=swish)
    try:
        # Integer subsampling only: crisp black modules and white quiet zone.
        original = tk.PhotoImage(master=window, file=str(QR_FILE))
        factor = max(1, (original.width() + 239) // 240)
        window._swish_qr = original.subsample(factor, factor) if factor > 1 else original
        tk.Label(swish, image=window._swish_qr, bg='white', padx=8, pady=8).pack(pady=12)
    except (tk.TclError, OSError):
        label('QR-koden kunde inte visas.\nAnge mottagarnumret manuellt i Swish eller hämta hela releasepaketet igen.',
              color='#f9a8d4', host=swish)
    label('Mottagare: ' + SWISH_NUMBER, 12, '#ffffff', True, swish)
    label('Kontrollera mottagarnamn och belopp i Swish innan du godkänner.', 10, host=swish)

    label('Andra sätt att stödja', 17, '#c4b5fd', True, online)
    label('Öppna betalprofilen direkt i din vanliga webbläsare. Välj själv belopp och godkänn hos tjänsten.', host=online)

    def payment(service):
        from tkinter import messagebox
        try:
            if not open_payment(service):
                messagebox.showerror('Stöd FTP Uploader', 'Kunde inte öppna standardwebbläsaren.', parent=window)
        except Exception as exc:
            from event_log import exception
            exception('donation.browser.failed', type(exc), exc, exc.__traceback__)
            messagebox.showerror('Stöd FTP Uploader', 'Kunde inte öppna betaltjänsten.', parent=window)

    for service, title, color in (
            ('paypal', 'PayPal  →  Rickard3dPrint', '#176baf'),
            ('kofi', 'Ko-fi  →  tokke2', '#a83068')):
        tk.Button(online, text=title, command=lambda key=service: payment(key),
                  bg=color, fg='white', activebackground='#314365', activeforeground='white',
                  relief='flat', font=('TkDefaultFont', 11, 'bold'), pady=12,
                  cursor='hand2', wraplength=230).pack(fill='x', pady=7)
    label('Ingen egen betalningssida eller mellanhand i appen.', 10, '#67e8f9', host=online)
    label('Din gåva kan stödja', 15, '#f9a8d4', True)
    label('Fortsatt utveckling · felsökning · underhåll\nInga stödnivåer, inga belöningspaket och ingen betalvägg.')
    label('Om betalning och integritet', 14, '#c4b5fd', True)
    label('Dialogen hämtar inte QR-koden från någon onlinetjänst och skickar inga betaluppgifter. '
          'Swish-numret finns i QR-kodens innehåll – QR är inte kryptering. '
          'PayPal och Ko-fi har egna villkor och integritetspolicyer.', 10)
    label('Copyright © 2026 Rickard Längkvist', 10)
    layout = {'columns': None}

    def resize(event):
        canvas.itemconfigure(item, width=event.width)
        columns = 2 if event.width >= 660 else 1
        if layout['columns'] != columns:
            for card in (swish, online):
                card.grid_forget()
            swish.grid(row=0, column=0, sticky='nsew', padx=(0, 5) if columns == 2 else 0, pady=5)
            online.grid(row=0 if columns == 2 else 1, column=1 if columns == 2 else 0,
                        sticky='nsew', padx=(5, 0) if columns == 2 else 0, pady=5)
            cards.columnconfigure(0, weight=1, uniform='support')
            cards.columnconfigure(1, weight=1 if columns == 2 else 0, uniform='support' if columns == 2 else '')
            layout['columns'] = columns
        for widget in labels:
            # A label wraps within its own card, not the whole dialog.
            host_width = event.width - 62
            if widget.master in (swish, online):
                host_width = (event.width - 72) // columns - 30
            widget.configure(wraplength=max(160, host_width))
    canvas.bind('<Configure>', resize)

    def wheel(event):
        if getattr(event, 'num', None) in (4, 5):
            amount = -1 if event.num == 4 else 1
        else:
            delta = getattr(event, 'delta', 0)
            amount = -1 if delta > 0 else 1 if delta < 0 else 0
        canvas.yview_scroll(amount * 3, 'units')
        return 'break'
    # Toplevel bindtag receives wheel events only from this dialog's children.
    window.bind('<MouseWheel>', wheel)
    window.bind('<Button-4>', wheel)
    window.bind('<Button-5>', wheel)


def show_license(parent):
    import tkinter as tk
    from tkinter import messagebox
    from tkinter.scrolledtext import ScrolledText
    from pathlib import Path
    try:
        text = (Path(__file__).resolve().parent / 'LICENSE').read_text(encoding='utf-8')
    except OSError:
        messagebox.showerror('Licens', 'LICENSE saknas. Hämta hela releasepaketet.', parent=parent)
        return
    window = tk.Toplevel(parent)
    window.title('Licens – privat och kommersiell användning')
    window.geometry('740x550')
    from app_icon import apply_tk_window_icon
    apply_tk_window_icon(window)
    content = ScrolledText(window, wrap='word', padx=18, pady=18)
    content.pack(fill='both', expand=True)
    content.insert('1.0', text)
    content.configure(state='disabled')
