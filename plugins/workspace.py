# Copyright (c) 2026 Rickard Längkvist
"""Home and workflow navigation. Existing tools remain available in Advanced."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from app_paths import config_dir
from workspace_design import TOKENS, apply_styles, load_state, save_state, pane_orientation, palette, navigation_icon, navigation_columns, density_padding


class Workspace:
    PLUGIN_NAME = 'Arbetsyta'
    PRIORITY = 200

    def init(self, app):
        self.app = app
        self.manager = app.context.get('_tab_manager')
        if self.manager is None:
            return
        self.alive = True
        self.timer = None
        self.resize_timer = None
        self.state_path = config_dir() / 'workspace.json'
        self.state = load_state(self.state_path)
        self.advanced = tk.BooleanVar(app, value=bool(self.state.get('advanced', False)))
        apply_styles(app)
        self.home = self.manager.add_tab('workspace', 'Start')
        self.home.configure(bg=TOKENS['bg'])
        self.navigation = ttk.Frame(self.manager.main_container, style='Studio.TFrame', padding=6)
        self.navigation.pack(fill='x', before=self.manager.tab_bar_container)
        destinations = [('Start', 'workspace'), ('1 Projekt', 'settings'), ('2 Media', 'gallery'),
                        ('3 Utseende', 'designer'), ('4 Publicera', 'controls')]
        self.nav_buttons = []
        self.nav_icons = {}
        for label, key in destinations:
            self.nav_icons[key] = navigation_icon(app, key, palette(app)['cyan'])
            button = ttk.Button(self.navigation, image=self.nav_icons[key], compound='left', text=label, style='Studio.TButton', command=lambda k=key: self.navigate(k))
            self.nav_buttons.append(button)
        self.advanced_button = ttk.Checkbutton(self.navigation, text='Avancerat', variable=self.advanced, command=self.toggle_advanced)
        self.nav_buttons.append(self.advanced_button)
        self.density = tk.StringVar(app, value='Kompakt' if self.state.get('density') == 'compact' else 'Luftig')
        self.density_box = ttk.Combobox(self.home, textvariable=self.density, values=('Luftig', 'Kompakt'), state='readonly', width=12)
        self.density_box.pack(anchor='e', padx=12, pady=6)
        self.density_box.bind('<<ComboboxSelected>>', self.change_density)
        self.heading = ttk.Label(self.home, text='Din galleriarbetsyta', style='Studio.Title.TLabel', padding=12)
        self.heading.pack(fill='x')
        self.panes = tk.PanedWindow(self.home, orient='horizontal', bg=TOKENS['border'], sashwidth=9,
                                   sashrelief='flat', borderwidth=0)
        self.panes.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self.left_host = ttk.Frame(self.panes, style='Studio.Card.TFrame')
        self.action_canvas = tk.Canvas(self.left_host, bg=TOKENS['surface'], highlightthickness=0, width=280, height=200)
        action_scroll = ttk.Scrollbar(self.left_host, command=self.action_canvas.yview)
        action_scroll.pack(side='right', fill='y')
        self.action_canvas.configure(yscrollcommand=action_scroll.set)
        self.action_canvas.pack(side='left', fill='both', expand=True)
        self.left = ttk.Frame(self.action_canvas, style='Studio.Card.TFrame', padding=12)
        action_window = self.action_canvas.create_window(0, 0, anchor='nw', window=self.left)
        self.left.bind('<Configure>', lambda event: self.action_canvas.configure(scrollregion=self.action_canvas.bbox('all')))
        self.action_canvas.bind('<Configure>', lambda event: self.action_canvas.itemconfigure(action_window, width=event.width))
        self.right = ttk.Frame(self.panes, style='Studio.Card.TFrame', padding=12)
        self.panes.add(self.left_host, minsize=150, stretch='always')
        self.panes.add(self.right, minsize=100, stretch='always')
        ttk.Label(self.left, text='Skapa och publicera', style='Studio.TLabel', font=('TkDefaultFont', 14, 'bold')).pack(anchor='w')
        actions = [('Välj källmapp', lambda: self.call('_settings', 'browse_folder')),
                   ('Öppna media', lambda: self.navigate('gallery')),
                   ('Anpassa galleriets layout', self.designer),
                   ('Generera galleri', lambda: self.call('_controls', 'run_generate')),
                   ('Förhandsvisa senaste galleri', lambda: self.call('_controls', 'open_preview')),
                   ('Öppna exportmappen', lambda: self.call('_settings', 'open_output_folder'))]
        for label, callback in actions:
            ttk.Button(self.left, text=label, command=callback, style='Studio.TButton').pack(fill='x', pady=4)
        ttk.Label(self.left, text='Börja med en källmapp. Originalvideor konverteras vid behov under exporten.',
                  style='Studio.TLabel', wraplength=350).pack(fill='x', pady=8)
        ttk.Label(self.right, text='Projekt och driftstatus', style='Studio.TLabel', font=('TkDefaultFont', 14, 'bold')).pack(anchor='w')
        self.details = tk.Text(self.right, wrap='word', height=8, width=24, bg=TOKENS['surface'],
                               fg=TOKENS['fg'], relief='flat', padx=8, pady=8, state='disabled')
        scrollbar = ttk.Scrollbar(self.right, command=self.details.yview)
        scrollbar.pack(side='right', fill='y')
        self.details.configure(yscrollcommand=scrollbar.set)
        self.details.pack(fill='both', expand=True)
        self.orientation = 'horizontal'
        self.nav_width = 0
        self.home.bind('<Configure>', self.schedule_resize)
        self.navigation.bind('<Configure>', self.navigation_resize)
        self.panes.bind('<ButtonRelease-1>', self.remember_sash)
        self.refresh_theme()
        self.theme_binding = app.bind('<<ThemeChanged>>', lambda event: self.refresh_theme(), add='+')
        app.context['_workspace'] = self
        self.toggle_advanced(save=False)
        self.manager.select_tab('workspace')
        app.after_idle(self.resize)
        self.refresh()

    def change_density(self, event=None):
        self.state['density'] = 'compact' if self.density.get() == 'Kompakt' else 'comfortable'
        self.refresh_theme()
        self.save()
        self.schedule_resize(None)

    def refresh_theme(self):
        apply_styles(self.app)
        ttk.Style(self.app).configure('Studio.TButton', padding=density_padding(self.state.get('density')))
        colors = palette(self.app)
        self.home.configure(bg=colors['bg'])
        self.panes.configure(bg=colors['border'])
        self.action_canvas.configure(bg=colors['surface'])
        self.details.configure(bg=colors['surface'], fg=colors['fg'], insertbackground=colors['fg'])
        for button, key in zip(self.nav_buttons, self.nav_icons):
            self.nav_icons[key] = navigation_icon(self.app, key, colors['cyan'])
            button.configure(image=self.nav_icons[key])

    def call(self, key, method):
        if getattr(self.app, '_release_update_active', False):
            messagebox.showinfo('Uppdatering pågår', 'Vänta tills uppdateringen är klar.', parent=self.app)
            return
        owner = self.app.context.get(key)
        callback = getattr(owner, method, None)
        if not callable(callback):
            messagebox.showinfo('Verktyget saknas', 'Aktivera verktyget under Plugins och försök igen.', parent=self.app)
            return
        try:
            callback()
        except Exception as exc:
            messagebox.showerror('Åtgärden misslyckades', str(exc), parent=self.app)

    def designer(self):
        settings = self.app.context.get('_settings')
        if settings is None:
            self.call('_settings', 'browse_folder')
            return
        from layout_designer import open_designer
        open_designer(self.app, settings)

    def navigate(self, name):
        if name == 'designer':
            self.designer()
        elif name in self.manager.tabs:
            self.manager.select_tab(name)
        else:
            messagebox.showinfo('Verktyget saknas', 'Aktivera motsvarande plugin för att använda detta steg.', parent=self.app)

    def toggle_advanced(self, save=True):
        if self.advanced.get():
            self.manager.tab_bar_container.pack(fill='x', after=self.navigation)
        else:
            self.manager.tab_bar_container.pack_forget()
        if save:
            self.save()

    def navigation_resize(self, event):
        count = navigation_columns(event.width)
        if count == self.nav_width:
            return
        self.nav_width = count
        for index, button in enumerate(self.nav_buttons):
            button.grid(row=index // count, column=index % count, sticky='ew', padx=2, pady=2)
        for column in range(6):
            self.navigation.columnconfigure(column, weight=1 if column < count else 0)

    def schedule_resize(self, event):
        if self.resize_timer is not None:
            self.app.after_cancel(self.resize_timer)
        self.resize_timer = self.app.after(120, self.resize)

    def resize(self):
        self.resize_timer = None
        if not self.alive:
            return
        orientation = pane_orientation(self.home.winfo_width())
        if orientation != self.orientation:
            self.orientation = orientation
            self.panes.configure(orient=orientation)
        total = self.panes.winfo_width() if orientation == 'horizontal' else self.panes.winfo_height()
        try:
            ratio = float(self.state.get('ratio_' + orientation, 0.55))
            ratio = max(0.25, min(0.75, ratio))
        except (ValueError, TypeError):
            ratio = 0.55
        self.panes.sash_place(0, int(total * ratio) if orientation == 'horizontal' else 0,
                               int(total * ratio) if orientation == 'vertical' else 0)

    def remember_sash(self, event=None):
        x, y = self.panes.sash_coord(0)
        total = self.panes.winfo_width() if self.orientation == 'horizontal' else self.panes.winfo_height()
        if total > 0:
            self.state['ratio_' + self.orientation] = max(0.25, min(0.75, (x if self.orientation == 'horizontal' else y) / total))
            self.save()

    def save(self):
        self.state['advanced'] = self.advanced.get()
        try:
            save_state(self.state_path, self.state)
        except OSError as exc:
            self.app._log_error('Arbetsytans layout kunde inte sparas: ' + str(exc))

    def refresh(self):
        if not self.alive:
            return
        from auto_update import installation_info
        from restart_safety import active_job_reasons
        settings = self.app.context.get('_settings')
        folder = settings.folder_var.get() if settings else ''
        output = settings.get_output_path() if settings else None
        jobs = active_job_reasons(self.app)
        latest = self.app.context.get('html_output')
        latest = str(latest) if latest and Path(latest).is_file() else 'Inget galleri genererat under denna körning'
        text = ('Källmapp\n%s\n\nVald exportmapp\n%s\n\nSenaste genererade galleri\n%s\n\nArbete\n%s\n\nUppdatering\n%s\n\n%s') % (
            folder or 'Ingen mapp vald', output or 'Ingen export vald', latest, '\n'.join(jobs) or 'Redo',
            'Pågår – nya jobb är spärrade' if getattr(self.app, '_release_update_active', False) else 'Ingen installation pågår',
            installation_info(Path(__file__).resolve().parents[1]))
        report_path = self.app.context.get('image_quality_report_path')
        if report_path:
            text += '\n\nBildstorlek och uppskalningsrisk\n' + str(report_path)
        if text != getattr(self, '_last_details', None):
            position = self.details.yview()[0]
            self.details.configure(state='normal')
            self.details.delete('1.0', 'end')
            self.details.insert('1.0', text)
            self.details.configure(state='disabled')
            self.details.yview_moveto(position)
            self._last_details = text
        try:
            hidden = self.app.state() in ('withdrawn', 'iconic')
        except Exception:
            hidden = False
        self.timer = self.app.after(10000 if hidden else 2500, self.refresh)

    def cleanup(self):
        if not hasattr(self, 'alive'):
            return
        self.alive = False
        self.save()
        for timer in (self.timer, self.resize_timer):
            if timer is not None:
                self.app.after_cancel(timer)
        if self.theme_binding:
            self.app.unbind('<<ThemeChanged>>', self.theme_binding)
        self.manager.tab_bar_container.pack(fill='x', before=self.manager.content)
        self.navigation.destroy()
