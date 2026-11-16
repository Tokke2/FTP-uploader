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


def open_payment(service):
    """Only predefined recipient profiles; no URL from settings or input."""
    return webbrowser.open(PAYMENT_LINKS[service])


def show_donations(parent):
    import tkinter as tk
    previous = getattr(parent, '_donation_window', None)
    if previous is not None:
        try:
            if previous.winfo_exists():
                previous.deiconify()
                previous.lift()
                return
        except tk.TclError:
            pass
    window = tk.Toplevel(parent)
    parent._donation_window = window
    window.title('Stöd FTP Uploader')
    window.configure(bg='#090f26')
    window.geometry('520x650')
    window.minsize(380, 400)
    from app_icon import apply_tk_window_icon
    apply_tk_window_icon(window)
    canvas = tk.Canvas(window, bg='#090f26', highlightthickness=0)
    scrollbar = tk.Scrollbar(window, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    body = tk.Frame(canvas, bg='#090f26', padx=22, pady=22)
    item = canvas.create_window(0, 0, window=body, anchor='nw')
    body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
    labels = []

    def label(text, size=11, color='#c4cce1', bold=False):
        widget = tk.Label(body, text=text, bg='#090f26', fg=color,
                          font=('TkDefaultFont', size, 'bold' if bold else 'normal'),
                          wraplength=420, justify='center')
        widget.pack(fill='x', pady=6)
        labels.append(widget)
        return widget

    label('FRIVILLIGT STÖD · INGA LÅSTA FUNKTIONER', 9, '#26dce0', True)
    label('Stöd utvecklingen', 24, '#ffffff', True)
    label('Skanna med Swish', 17, '#c885ff', True)
    label('Öppna Swish och välj Skanna.\nVälj själv belopp i Swish-appen.')
    try:
        # Keep crisp square modules and quiet zone; never smooth or decorate QR.
        window._swish_qr = tk.PhotoImage(master=window, file=str(QR_FILE))
        tk.Label(body, image=window._swish_qr, bg='white', padx=10, pady=10).pack(pady=12)
    except (tk.TclError, OSError):
        label('QR-koden saknas eller kunde inte läsas.\nHämta hela releasepaketet igen.', 11, '#ffb4c6')
    label('Mottagarnummer: ' + SWISH_NUMBER, 12, '#ffffff', True)
    label('Kontrollera mottagarnamnet och beloppet i Swish innan du godkänner. '
          'Ingen betalning sker i appen och inga betaluppgifter samlas in.')
    label('Eller stöd direkt via', 11, '#c885ff', True)

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
        tk.Button(body, text=title, command=lambda key=service: payment(key),
                  bg=color, fg='white', activebackground='#314365', activeforeground='white',
                  relief='flat', font=('TkDefaultFont', 12, 'bold'), pady=10,
                  cursor='hand2').pack(fill='x', pady=5)
    label('Knapparna öppnar betalprofilen direkt i webbläsaren.\n'
          'Välj belopp och godkänn där – ingen egen stödsida.', 10)
    label('Gratis för privat och kommersiell användning.\n'
          'Donationer är helt frivilliga – tack för ditt stöd!', 10, '#26dce0')
    label('Copyright © 2026 Rickard Längkvist', 10)
    tk.Button(body, text='Stäng', command=window.destroy, bg='#263354', fg='white',
              relief='flat', padx=18, pady=8).pack(pady=10)

    def resize(event):
        canvas.itemconfigure(item, width=event.width)
        for widget in labels:
            widget.configure(wraplength=max(220, event.width - 60))
    canvas.bind('<Configure>', resize)


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
