"""Native, offline catalog interface built with the Python standard library."""
import queue
import sqlite3
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .catalog import import_json
from .unified import search_resources as search, list_resources as list_records
import webbrowser
from urllib.parse import urlparse


class CatalogApp:
    def __init__(self, root, db=None):
        self.root = root
        root.title('Personal Knowledge Management System')
        root.geometry('1100x720')
        root.minsize(800, 540)
        self.db = tk.StringVar(value=str(Path(db).resolve()) if db else '')
        self.source = tk.StringVar(value='zotero')
        self.query = tk.StringVar()
        self.status = tk.StringVar(value='Selecciona o crea un catálogo para empezar.')
        self.jobs = queue.Queue()
        self.busy = False
        self.rows = {}
        style = ttk.Style(root)
        style.configure('Title.TLabel', font=('Helvetica', 22, 'bold'))
        style.configure('Status.TLabel', padding=8)
        outer = ttk.Frame(root, padding=24)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Tu conocimiento, en un solo lugar', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Catálogo bibliográfico local · Python + SQLite · Sin conexión a la nube').pack(anchor='w', pady=(6, 18))
        catalog = ttk.LabelFrame(outer, text='1. Catálogo local', padding=12)
        catalog.pack(fill='x')
        ttk.Entry(catalog, textvariable=self.db, state='readonly').pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.controls = []
        self.button(catalog, 'Abrir catálogo', self.open_db).pack(side='left', padx=4)
        self.button(catalog, 'Crear catálogo', self.new_db).pack(side='left')
        importer = ttk.LabelFrame(outer, text='2. Importar referencias', padding=12)
        importer.pack(fill='x', pady=12)
        ttk.Label(importer, text='Biblioteca de origen:').pack(side='left')
        self.source_entry = ttk.Entry(importer, textvariable=self.source, width=26)
        self.source_entry.pack(side='left', padx=8)
        self.controls.append(self.source_entry)
        self.button(importer, 'Importar JSON…', self.import_file).pack(side='left', padx=4)
        self.button(importer, 'Cargar ejemplo sintético', self.demo).pack(side='left', padx=4)
        ttk.Label(outer, text='Usa un origen distinto por biblioteca. Reimportar la misma clave actualiza el registro sin duplicarlo.').pack(anchor='w')
        finder = ttk.Frame(outer)
        finder.pack(fill='x', pady=(18, 10))
        self.query_entry = ttk.Entry(finder, textvariable=self.query)
        self.query_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.query_entry.bind('<Return>', lambda event: self.find())
        self.controls.append(self.query_entry)
        self.button(finder, 'Buscar', self.find).pack(side='left', padx=4)
        self.button(finder, 'Ver catálogo', self.browse).pack(side='left')
        self.button(finder, 'Abrir fuente', self.open_source).pack(side='left', padx=4)
        ttk.Label(outer, text='Busca títulos, creadores e índices de Drive · Hasta 200 resultados por consulta').pack(anchor='w', pady=(0, 6))
        table_frame = ttk.Frame(outer)
        table_frame.pack(fill='both', expand=True)
        self.table = ttk.Treeview(table_frame, columns=('title', 'authors', 'date', 'source'), show='headings', selectmode='browse')
        for name, label, width in [('title', 'Título', 400), ('authors', 'Creadores', 230), ('date', 'Fecha', 90), ('source', 'Origen', 120)]:
            self.table.heading(name, text=label)
            self.table.column(name, width=width, minwidth=60)
        scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.table.bind('<<TreeviewSelect>>', self.details)
        self.detail = tk.Text(outer, height=5, wrap='word', state='disabled', font=('Helvetica', 12))
        self.detail.pack(fill='x', pady=(10, 0))
        ttk.Label(outer, textvariable=self.status, style='Status.TLabel', wraplength=1000).pack(fill='x')
        root.after(100, self.poll)
        if db:
            self.browse()

    def button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        self.controls.append(button)
        return button

    def run(self, task, success):
        if self.busy:
            return
        self.busy = True
        self.status.set('Procesando…')
        for control in self.controls:
            control.configure(state='disabled')
        def worker():
            try:
                self.jobs.put((success, task(), None))
            except Exception as error:
                self.jobs.put((success, None, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            callback, result, error = self.jobs.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            for control in self.controls:
                control.configure(state='normal')
            if error:
                self.status.set('No se completó la operación. Revisa el mensaje antes de continuar.')
                messagebox.showerror('Revisa el archivo o catálogo', error, parent=self.root)
            else:
                callback(result)
        self.root.after(100, self.poll)

    def open_db(self):
        path = filedialog.askopenfilename(parent=self.root, title='Abrir un catálogo PKM', filetypes=[('Catálogo SQLite', '*.sqlite *.db'), ('Todos los archivos', '*')])
        if path:
            self.load_path(path)

    def load_path(self, path):
        def success(rows):
            self.db.set(str(Path(path).resolve()))
            self.show(rows)
        self.run(lambda: list_records(path), success)

    def new_db(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='Crear catálogo PKM', defaultextension='.sqlite', filetypes=[('Catálogo SQLite', '*.sqlite')])
        if not path:
            return
        if Path(path).exists():
            messagebox.showinfo('El archivo ya existe', 'Usa Abrir catálogo o elige un nombre nuevo.', parent=self.root)
            return
        self.db.set(path)
        self.show([])
        self.status.set('Destino preparado. El catálogo se creará al importar referencias.')

    def import_file(self):
        if not self.ready():
            return
        path = filedialog.askopenfilename(parent=self.root, title='Importar referencias JSON', filetypes=[('JSON', '*.json')])
        if path:
            self.import_path(path, self.source.get().strip())

    def ready(self):
        if not self.db.get():
            messagebox.showinfo('Selecciona un catálogo', 'Crea un catálogo nuevo o abre uno existente.', parent=self.root)
            return False
        return True

    def import_path(self, path, source):
        db = self.db.get()
        def task():
            if Path(db).exists():
                list_records(db)  # Reject unrelated SQLite databases before writing.
            stats = import_json(db, path, source)
            return stats, list_records(db)
        def success(result):
            stats, rows = result
            self.show(rows)
            self.status.set(f"Importación completada: {stats['inserted']} nuevas · {stats['updated']} actualizadas · {stats['unchanged']} sin cambios.")
        self.run(task, success)

    def demo(self):
        if not self.ready():
            return
        # Embedded fictional records; independent of a developer checkout path.
        import json
        import tempfile
        db = self.db.get()
        def task():
            if Path(db).exists():
                list_records(db)
            with tempfile.TemporaryDirectory(prefix='pkm-gui-demo-') as folder:
                path = Path(folder) / 'synthetic.json'
                path.write_text(json.dumps([{'key': f'DEMO{i:04}', 'title': f'Aprendizaje sintético volumen {i}', 'creators': [{'firstName': 'Ana', 'lastName': 'Ejemplo'}], 'date': '2026', 'itemType': 'book'} for i in range(1, 11)]), encoding='utf-8')
                stats = import_json(db, path, 'synthetic-demo')
            return stats, list_records(db)
        def success(result):
            stats, rows = result
            self.show(rows)
            self.status.set(f"Ejemplo ficticio: {stats['inserted']} nuevas · {stats['unchanged']} sin cambios. Busca «aprendizaje» o «ejemplo».")
        self.run(task, success)

    def find(self):
        if self.busy or not self.ready():
            return
        db, query = self.db.get(), self.query.get()
        self.run(lambda: search(db, query, 200), self.show)

    def browse(self):
        if self.busy or not self.ready():
            return
        db = self.db.get()
        self.run(lambda: list_records(db), self.show)

    def show(self, rows):
        self.table.delete(*self.table.get_children())
        self.rows = {}
        for row in rows:
            iid = self.table.insert('', 'end', values=tuple(row[k] for k in ('title', 'authors', 'date', 'source')))
            self.rows[iid] = row
        self.set_detail('Selecciona una referencia para ver su clave y DOI.')
        self.status.set(f'{len(rows)} referencias mostradas (máximo 200).')

    def details(self, event=None):
        selected = self.table.selection()
        if selected and selected[0] in self.rows:
            row = self.rows[selected[0]]
            self.set_detail(f"{row['title']}\nClave: {row['source_key']} · Origen: {row['source']} · DOI: {row['doi'] or 'No disponible'}\n{row.get('metadata_status', '')}\n{row.get('url', '')}")

    def open_source(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo('Selecciona un resultado', 'Selecciona primero una referencia o un archivo.', parent=self.root)
            return
        url = self.rows.get(selected[0], {}).get('url', '')
        parsed = urlparse(url)
        allowed = (parsed.scheme == 'https' and parsed.hostname == 'drive.google.com') or (parsed.scheme == 'zotero' and parsed.netloc == 'select')
        if not allowed:
            messagebox.showinfo('Sin enlace de apertura', 'Este registro no tiene un enlace de Drive o Zotero válido.', parent=self.root)
            return
        webbrowser.open(url)

    def set_detail(self, text):
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        self.detail.insert('1.0', text)
        self.detail.configure(state='disabled')


def launch(db=None):
    root = tk.Tk()
    CatalogApp(root, db)
    root.mainloop()
