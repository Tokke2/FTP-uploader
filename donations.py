# Copyright (c) 2026 Rickard Längkvist
"""Voluntary support. Recipient destinations never come from user settings."""
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
import webbrowser

DESTINATIONS = MappingProxyType({
    'paypal': 'https://paypal.me/Rickard3dPrint',
    'kofi': 'https://ko-fi.com/tokke2',
    'swish': 'https://tokke2.github.io/recept/stod.html',
})


def parse_amount(text):
    text = str(text).strip().replace(',', '.')
    if not text:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError('Ange ett belopp mellan 1 och 99 999 kr.') from None
    if not amount.is_finite() or not Decimal('1') <= amount <= Decimal('99999'):
        raise ValueError('Ange ett belopp mellan 1 och 99 999 kr.')
    if amount != amount.quantize(Decimal('0.01')):
        raise ValueError('Ange högst två decimaler.')
    return format(amount.quantize(Decimal('0.01')), 'f')


def payment_url(service, amount=''):
    destination = DESTINATIONS[service]
    value = parse_amount(amount)
    # Ko-fi and the external Swish page let the donor choose on that page.
    if service == 'paypal' and value is not None:
        return destination + '/' + value + 'SEK'
    return destination


def show_donations(parent):
    import tkinter as tk
    from tkinter import messagebox
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
    window.geometry('620x660')
    window.minsize(400, 400)
    from app_icon import apply_tk_window_icon
    apply_tk_window_icon(window)
    # Scrollable for smaller screens and high-DPI desktops.
    canvas = tk.Canvas(window, bg='#090f26', highlightthickness=0)
    scrollbar = tk.Scrollbar(window, orient='vertical', command=canvas.yview)
    scrollbar.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    body = tk.Frame(canvas, bg='#090f26', padx=26, pady=22)
    item = canvas.create_window(0, 0, window=body, anchor='nw')
    body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
    labels = []

    def label(text, size=11, color='#c4cce1', bold=False, master=body):
        widget = tk.Label(master, text=text, bg=master.cget('bg'), fg=color,
                          font=('TkDefaultFont', size, 'bold' if bold else 'normal'),
                          wraplength=500, justify='left', anchor='w')
        widget.pack(fill='x', pady=5)
        labels.append(widget)
        return widget

    try:
        from app_icon import load_app_icon
        from PIL import ImageTk
        image, _ = load_app_icon(64)
        window._support_icon = ImageTk.PhotoImage(image, master=window)
        tk.Label(body, image=window._support_icon, bg='#090f26').pack(anchor='w', pady=(0, 8))
    except Exception:
        pass
    label('BYGGT MED OMSORG · STÖDS FRIVILLIGT', 9, '#26dce0', True)
    label('Gillar du FTP Uploader?', 24, '#ffffff', True)
    label('Ge utvecklingen lite extra kraft.', 16, '#c885ff', True)
    label('Gratis att använda – både privat och kommersiellt.\n'
          'Din frivilliga gåva kan stödja fortsatt utveckling och underhåll. '
          'Inga nivåer, inga låsta funktioner och inget krav på betalning.')
    card = tk.Frame(body, bg='#151e39', padx=18, pady=14)
    card.pack(fill='x', pady=14)
    label('VALFRITT BELOPP', 10, '#26dce0', True, card)
    amount = tk.StringVar(value='50')
    choices = tk.Frame(card, bg='#151e39')
    choices.pack(fill='x', pady=8)
    for value in ('25', '50', '100', '200'):
        tk.Button(choices, text=value + ' kr', command=lambda v=value: amount.set(v),
                  bg='#263354', fg='white', relief='flat', padx=10, pady=8).pack(side='left', padx=(0, 5))
    entry_row = tk.Frame(card, bg='#151e39')
    entry_row.pack(fill='x')
    tk.Label(entry_row, text='Eget belopp (SEK): ', bg='#151e39', fg='white').pack(side='left')
    tk.Entry(entry_row, textvariable=amount, width=12, font=('TkDefaultFont', 12)).pack(side='left')
    label('Beloppet skickas till PayPal. Välj belopp på respektive sida för Ko-fi och Swish. '
          'Lämna tomt för att välja hos betaltjänsten.', 10, master=card)

    def open_payment(service):
        try:
            url = payment_url(service, amount.get())
            if not webbrowser.open(url):
                messagebox.showerror('Stöd FTP Uploader', 'Webbläsaren kunde inte öppnas. Försök med din standardwebbläsare.', parent=window)
        except ValueError as exc:
            messagebox.showwarning('Belopp', str(exc), parent=window)
        except Exception as exc:
            from event_log import exception
            exception('donation.browser.failed', type(exc), exc, exc.__traceback__)
            messagebox.showerror('Stöd FTP Uploader', 'Kunde inte öppna betaltjänsten.', parent=window)

    for service, text, color in (
            ('paypal', 'PayPal  →  Rickard3dPrint', '#176baf'),
            ('kofi', 'Ko-fi  →  tokke2', '#a83068'),
            ('swish', 'Swish  →  öppna befintlig stödsida', '#19775f')):
        tk.Button(body, text=text, command=lambda s=service: open_payment(s),
                  bg=color, fg='white', activebackground='#314365', activeforeground='white',
                  font=('TkDefaultFont', 12, 'bold'), relief='flat', pady=11, cursor='hand2').pack(fill='x', pady=5)
    label('Swish öppnar din webbläsare till Mitt Maskinköks stödsida. '
          'Den sidan har egen information och beloppsväljare. Kontrollera alltid mottagare och belopp innan du godkänner.', 10)
    label('Fasta mottagarlänkar · Inga betaluppgifter hanteras i appen\n'
          'Betalning sker först när du själv godkänner hos betaltjänsten.', 10, '#26dce0')
    label('Copyright © 2026 Rickard Längkvist', 10)
    tk.Button(body, text='Stäng', command=window.destroy, bg='#263354', fg='white',
              relief='flat', padx=18, pady=8).pack(anchor='e', pady=8)

    def resize(event):
        for widget in labels:
            widget.configure(wraplength=max(220, event.width - 100))
    canvas.bind('<Configure>', resize, add='+')


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
