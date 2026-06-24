#!/usr/bin/env python3
"""
Organizador de Fotos por Data com Detecção de Duplicatas
Acessa HD externo, organiza por data (EXIF ou data do arquivo) e remove duplicatas com confirmação.
"""

import os
import sys
import shutil
import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("Tkinter não encontrado. Instalando dependências...")
    os.system(f"{sys.executable} -m pip install tk")
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

EXTENSOES_FOTO = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
                  '.heic', '.heif', '.webp', '.raw', '.cr2', '.nef', '.arw',
                  '.dng', '.orf', '.rw2', '.pef', '.srw'}
EXTENSOES_VIDEO = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.wmv',
                   '.flv', '.mts', '.m2ts', '.mpg', '.mpeg'}

def get_exif_date(filepath):
    """Tenta obter data EXIF da imagem."""
    if not PILLOW_OK:
        return None
    try:
        with Image.open(filepath) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ('DateTimeOriginal', 'DateTime', 'DateTimeDigitized'):
                        dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        return dt
    except Exception:
        pass
    return None

def get_file_date(filepath):
    """Obtém data do arquivo (modificação ou criação)."""
    try:
        stat = os.stat(filepath)
        ts = min(stat.st_mtime, stat.st_ctime if stat.st_ctime > 0 else stat.st_mtime)
        return datetime.fromtimestamp(ts)
    except Exception:
        return datetime.now()

def get_best_date(filepath):
    """Retorna a melhor data disponível para o arquivo."""
    ext = Path(filepath).suffix.lower()
    if ext in EXTENSOES_FOTO:
        exif_date = get_exif_date(filepath)
        if exif_date:
            return exif_date, "EXIF"
    return get_file_date(filepath), "Arquivo"

def calcular_hash(filepath, chunk_size=8192):
    """Calcula MD5 hash do arquivo para detectar duplicatas."""
    h = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def listar_arquivos(pasta, incluir_videos=True):
    """Lista todos os arquivos de mídia recursivamente."""
    extensoes = EXTENSOES_FOTO.copy()
    if incluir_videos:
        extensoes |= EXTENSOES_VIDEO
    arquivos = []
    for root, dirs, files in os.walk(pasta):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if Path(f).suffix.lower() in extensoes:
                arquivos.append(os.path.join(root, f))
    return arquivos


class OrganizadorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📸 Organizador de Fotos — HD Externo")
        self.root.geometry("900x700")
        self.root.configure(bg="#1a1a2e")
        self.root.minsize(800, 600)

        self.pasta_origem = tk.StringVar()
        self.pasta_destino = tk.StringVar()
        self.incluir_videos = tk.BooleanVar(value=True)
        self.mover_arquivos = tk.BooleanVar(value=False)
        self.formato_pasta = tk.StringVar(value="YYYY/MM - Nome do Mês")

        self.arquivos_lista = []
        self.duplicatas = {}
        self.operacao_ativa = False

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Card.TFrame', background='#16213e', relief='flat')
        style.configure('Title.TLabel', background='#1a1a2e', foreground='#e2e8f0',
                        font=('Segoe UI', 11, 'bold'))
        style.configure('Sub.TLabel', background='#16213e', foreground='#94a3b8',
                        font=('Segoe UI', 9))
        style.configure('Val.TLabel', background='#16213e', foreground='#e2e8f0',
                        font=('Segoe UI', 9))
        style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'),
                        padding=(16, 8))
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'),
                        padding=(16, 8), background='#4f46e5', foreground='white')

        header = tk.Frame(self.root, bg='#0f3460', pady=14)
        header.pack(fill='x')
        tk.Label(header, text="📸  Organizador de Fotos", font=('Segoe UI', 16, 'bold'),
                 bg='#0f3460', fg='#e2e8f0').pack()
        tk.Label(header, text="Organize por data • Detecte e remova duplicatas",
                 font=('Segoe UI', 9), bg='#0f3460', fg='#94a3b8').pack()

        main = tk.Frame(self.root, bg='#1a1a2e', padx=20, pady=12)
        main.pack(fill='both', expand=True)

        left = tk.Frame(main, bg='#1a1a2e')
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        right = tk.Frame(main, bg='#1a1a2e', width=270)
        right.pack(side='right', fill='y')
        right.pack_propagate(False)

        self._card_pastas(left)
        self._card_opcoes(left)
        self._card_progresso(left)
        self._card_botoes(left)
        self._card_stats(right)
        self._card_log(right)

    def _card(self, parent, title):
        outer = tk.Frame(parent, bg='#1a1a2e', pady=4)
        outer.pack(fill='x')
        tk.Label(outer, text=title, font=('Segoe UI', 10, 'bold'),
                 bg='#1a1a2e', fg='#818cf8').pack(anchor='w', pady=(0, 4))
        card = tk.Frame(outer, bg='#16213e', padx=14, pady=12,
                        highlightbackground='#334155', highlightthickness=1)
        card.pack(fill='x')
        return card

    def _pasta_row(self, parent, label, var, comando):
        row = tk.Frame(parent, bg='#16213e')
        row.pack(fill='x', pady=3)
        tk.Label(row, text=label, width=10, anchor='w',
                 bg='#16213e', fg='#94a3b8', font=('Segoe UI', 9)).pack(side='left')
        entry = tk.Entry(row, textvariable=var, bg='#0f3460', fg='#e2e8f0',
                         insertbackground='white', relief='flat',
                         font=('Segoe UI', 9), highlightthickness=1,
                         highlightbackground='#334155', highlightcolor='#818cf8')
        entry.pack(side='left', fill='x', expand=True, padx=(4, 6), ipady=5)
        tk.Button(row, text='📂', command=comando, bg='#334155', fg='#e2e8f0',
                  relief='flat', padx=8, cursor='hand2',
                  activebackground='#4f46e5', activeforeground='white').pack(side='right')

    def _card_pastas(self, parent):
        card = self._card(parent, "📁  Pastas")
        self._pasta_row(card, "Origem:", self.pasta_origem, self._escolher_origem)
        tk.Label(card, text="↑ HD externo ou pasta com as fotos",
                 bg='#16213e', fg='#64748b', font=('Segoe UI', 8)).pack(anchor='w', padx=2)
        self._pasta_row(card, "Destino:", self.pasta_destino, self._escolher_destino)
        tk.Label(card, text="↑ Onde salvar organizado (pode ser a mesma pasta)",
                 bg='#16213e', fg='#64748b', font=('Segoe UI', 8)).pack(anchor='w', padx=2)

    def _card_opcoes(self, parent):
        card = self._card(parent, "⚙️  Opções")
        row1 = tk.Frame(card, bg='#16213e')
        row1.pack(fill='x', pady=3)
        self._check(row1, "Incluir vídeos", self.incluir_videos)
        self._check(row1, "Mover (apagar da origem)", self.mover_arquivos)

        row2 = tk.Frame(card, bg='#16213e')
        row2.pack(fill='x', pady=(6, 0))
        tk.Label(row2, text="Estrutura de pasta:", bg='#16213e', fg='#94a3b8',
                 font=('Segoe UI', 9)).pack(side='left')
        cb = ttk.Combobox(row2, textvariable=self.formato_pasta, width=28,
                          values=["YYYY/MM - Nome do Mês", "YYYY/MM", "YYYY/MM/DD", "YYYY"],
                          state='readonly', font=('Segoe UI', 9))
        cb.pack(side='left', padx=(8, 0))

    def _check(self, parent, text, var):
        tk.Checkbutton(parent, text=text, variable=var,
                       bg='#16213e', fg='#e2e8f0', selectcolor='#0f3460',
                       activebackground='#16213e', activeforeground='#818cf8',
                       font=('Segoe UI', 9), cursor='hand2').pack(side='left', padx=(0, 20))

    def _card_progresso(self, parent):
        card = self._card(parent, "📊  Progresso")
        self.lbl_status = tk.Label(card, text="Aguardando...", bg='#16213e',
                                   fg='#94a3b8', font=('Segoe UI', 9))
        self.lbl_status.pack(anchor='w')
        self.progressbar = ttk.Progressbar(card, mode='determinate', length=400)
        self.progressbar.pack(fill='x', pady=(6, 0))
        style = ttk.Style()
        style.configure('TProgressbar', troughcolor='#0f3460', background='#818cf8',
                        bordercolor='#334155', lightcolor='#818cf8', darkcolor='#4f46e5')

    def _card_botoes(self, parent):
        frame = tk.Frame(parent, bg='#1a1a2e', pady=8)
        frame.pack(fill='x')
        btns = [
            ("🔍  Escanear", '#334155', self._escanear),
            ("📅  Organizar", '#065f46', self._organizar),
            ("🗑️  Duplicatas", '#7f1d1d', self._mostrar_duplicatas),
        ]
        for text, color, cmd in btns:
            tk.Button(frame, text=text, bg=color, fg='#e2e8f0', relief='flat',
                      padx=14, pady=7, font=('Segoe UI', 9, 'bold'), cursor='hand2',
                      activebackground='#818cf8', activeforeground='white',
                      command=cmd).pack(side='left', padx=(0, 8))

    def _card_stats(self, parent):
        outer = tk.Frame(parent, bg='#1a1a2e', pady=4)
        outer.pack(fill='x')
        tk.Label(outer, text="📈  Estatísticas", font=('Segoe UI', 10, 'bold'),
                 bg='#1a1a2e', fg='#818cf8').pack(anchor='w', pady=(0, 4))
        card = tk.Frame(outer, bg='#16213e', padx=14, pady=12,
                        highlightbackground='#334155', highlightthickness=1)
        card.pack(fill='x')

        labels = [("Total de arquivos", 'stat_total'),
                  ("Fotos", 'stat_fotos'),
                  ("Vídeos", 'stat_videos'),
                  ("Grupos duplicados", 'stat_dups'),
                  ("Espaço duplicatas", 'stat_espaco')]
        self.stats = {}
        for label, key in labels:
            row = tk.Frame(card, bg='#16213e')
            row.pack(fill='x', pady=2)
            tk.Label(row, text=label, bg='#16213e', fg='#64748b',
                     font=('Segoe UI', 8)).pack(side='left')
            lbl = tk.Label(row, text="—", bg='#16213e', fg='#e2e8f0',
                           font=('Segoe UI', 8, 'bold'))
            lbl.pack(side='right')
            self.stats[key] = lbl

    def _card_log(self, parent):
        outer = tk.Frame(parent, bg='#1a1a2e', pady=4)
        outer.pack(fill='both', expand=True)
        tk.Label(outer, text="📋  Log", font=('Segoe UI', 10, 'bold'),
                 bg='#1a1a2e', fg='#818cf8').pack(anchor='w', pady=(0, 4))
        self.log_text = tk.Text(outer, bg='#0f172a', fg='#94a3b8', wrap='word',
                                font=('Courier New', 8), relief='flat',
                                highlightthickness=1, highlightbackground='#334155',
                                state='disabled')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_config('ok', foreground='#4ade80')
        self.log_text.tag_config('warn', foreground='#fbbf24')
        self.log_text.tag_config('err', foreground='#f87171')
        self.log_text.tag_config('info', foreground='#818cf8')

    def _log(self, msg, tag=''):
        self.log_text.config(state='normal')
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert('end', f"[{ts}] {msg}\n", tag)
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _escolher_origem(self):
        p = filedialog.askdirectory(title="Selecionar pasta de origem (HD Externo)")
        if p:
            self.pasta_origem.set(p)
            self._log(f"Origem: {p}", 'info')

    def _escolher_destino(self):
        p = filedialog.askdirectory(title="Selecionar pasta de destino")
        if p:
            self.pasta_destino.set(p)
            self._log(f"Destino: {p}", 'info')

    def _set_status(self, msg):
        self.lbl_status.config(text=msg)
        self.root.update_idletasks()

    def _escanear(self):
        origem = self.pasta_origem.get().strip()
        if not origem or not os.path.isdir(origem):
            messagebox.showerror("Erro", "Selecione uma pasta de origem válida!")
            return
        if self.operacao_ativa:
            return
        threading.Thread(target=self._escanear_thread, args=(origem,), daemon=True).start()

    def _escanear_thread(self, origem):
        self.operacao_ativa = True
        self._log("Escaneando arquivos...", 'info')
        self._set_status("Escaneando...")
        self.progressbar.config(mode='indeterminate')
        self.progressbar.start(10)

        try:
            self.arquivos_lista = listar_arquivos(origem, self.incluir_videos.get())
            total = len(self.arquivos_lista)
            fotos = sum(1 for f in self.arquivos_lista if Path(f).suffix.lower() in EXTENSOES_FOTO)
            videos = total - fotos

            self.progressbar.stop()
            self.progressbar.config(mode='determinate', value=0)

            self._log(f"✓ {total} arquivos encontrados ({fotos} fotos, {videos} vídeos)", 'ok')
            self.stats['stat_total'].config(text=str(total))
            self.stats['stat_fotos'].config(text=str(fotos))
            self.stats['stat_videos'].config(text=str(videos))

            self._log("Calculando hashes para detectar duplicatas...", 'info')
            self._set_status("Detectando duplicatas...")
            self.progressbar.config(maximum=total)

            hash_map = defaultdict(list)
            for i, fp in enumerate(self.arquivos_lista):
                h = calcular_hash(fp)
                if h:
                    hash_map[h].append(fp)
                self.progressbar['value'] = i + 1
                if i % 50 == 0:
                    self.root.update_idletasks()

            self.duplicatas = {h: files for h, files in hash_map.items() if len(files) > 1}
            n_grupos = len(self.duplicatas)
            n_dup = sum(len(v) - 1 for v in self.duplicatas.values())
            espaco = sum(os.path.getsize(f) for g in self.duplicatas.values() for f in g[1:])
            espaco_mb = espaco / (1024 * 1024)

            self.stats['stat_dups'].config(text=f"{n_grupos} grupos")
            self.stats['stat_espaco'].config(text=f"{espaco_mb:.1f} MB")
            self._log(f"✓ {n_grupos} grupos duplicados ({n_dup} arquivos, {espaco_mb:.1f} MB)", 'warn')
            self._set_status(f"Pronto — {total} arquivos, {n_grupos} grupos duplicados")
        except Exception as e:
            self._log(f"Erro: {e}", 'err')
            self._set_status("Erro durante escaneamento")
        finally:
            self.operacao_ativa = False

    def _pasta_destino_nome(self, dt):
        fmt = self.formato_pasta.get()
        meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                 'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        y = str(dt.year)
        m = f"{dt.month:02d}"
        d = f"{dt.day:02d}"
        nome_mes = meses[dt.month - 1]
        if fmt == "YYYY/MM - Nome do Mês":
            return os.path.join(y, f"{m} - {nome_mes}")
        elif fmt == "YYYY/MM":
            return os.path.join(y, m)
        elif fmt == "YYYY/MM/DD":
            return os.path.join(y, m, d)
        else:
            return y

    def _organizar(self):
        origem = self.pasta_origem.get().strip()
        destino = self.pasta_destino.get().strip()
        if not origem or not os.path.isdir(origem):
            messagebox.showerror("Erro", "Selecione uma pasta de origem válida!")
            return
        if not destino:
            messagebox.showerror("Erro", "Selecione a pasta de destino!")
            return
        if not self.arquivos_lista:
            messagebox.showinfo("Atenção", "Clique em 'Escanear' primeiro!")
            return

        acao = "mover" if self.mover_arquivos.get() else "copiar"
        if not messagebox.askyesno("Confirmar", f"Deseja {acao} {len(self.arquivos_lista)} arquivos para:\n{destino}\n\nOrganizando por data..."):
            return

        threading.Thread(target=self._organizar_thread, args=(destino,), daemon=True).start()

    def _organizar_thread(self, destino):
        self.operacao_ativa = True
        total = len(self.arquivos_lista)
        self.progressbar.config(maximum=total, value=0)
        copiados = erros = 0

        for i, fp in enumerate(self.arquivos_lista):
            try:
                dt, fonte = get_best_date(fp)
                subpasta = self._pasta_destino_nome(dt)
                pasta_final = os.path.join(destino, subpasta)
                os.makedirs(pasta_final, exist_ok=True)

                nome = os.path.basename(fp)
                destino_arquivo = os.path.join(pasta_final, nome)

                contador = 1
                base, ext = os.path.splitext(nome)
                while os.path.exists(destino_arquivo):
                    destino_arquivo = os.path.join(pasta_final, f"{base}_{contador}{ext}")
                    contador += 1

                if self.mover_arquivos.get():
                    shutil.move(fp, destino_arquivo)
                else:
                    shutil.copy2(fp, destino_arquivo)

                copiados += 1
                if i % 20 == 0:
                    self._log(f"{'→' if self.mover_arquivos.get() else '↦'} {nome} → {subpasta}", 'ok')
            except Exception as e:
                erros += 1
                self._log(f"Erro em {os.path.basename(fp)}: {e}", 'err')

            self.progressbar['value'] = i + 1
            self._set_status(f"Processando {i+1}/{total}...")
            if i % 10 == 0:
                self.root.update_idletasks()

        self._log(f"✓ Concluído! {copiados} arquivos, {erros} erros.", 'ok')
        self._set_status(f"Organização concluída — {copiados} arquivos")
        messagebox.showinfo("Concluído", f"✅ {copiados} arquivos organizados com sucesso!\n{erros} erros.")
        self.operacao_ativa = False

    def _mostrar_duplicatas(self):
        if not self.duplicatas:
            if not self.arquivos_lista:
                messagebox.showinfo("Atenção", "Clique em 'Escanear' primeiro!")
            else:
                messagebox.showinfo("Sem Duplicatas", "✅ Nenhuma duplicata encontrada!")
            return

        win = tk.Toplevel(self.root)
        win.title("🗑️ Gerenciar Duplicatas")
        win.geometry("820x560")
        win.configure(bg='#1a1a2e')
        win.grab_set()

        tk.Label(win, text="Arquivos Duplicados", font=('Segoe UI', 13, 'bold'),
                 bg='#1a1a2e', fg='#f87171').pack(pady=(14, 0))

        n_grupos = len(self.duplicatas)
        n_dup = sum(len(v) - 1 for v in self.duplicatas.values())
        espaco = sum(os.path.getsize(f) for g in self.duplicatas.values() for f in g[1:])
        tk.Label(win, text=f"{n_grupos} grupos · {n_dup} arquivos redundantes · {espaco/(1024*1024):.1f} MB",
                 font=('Segoe UI', 9), bg='#1a1a2e', fg='#94a3b8').pack(pady=(2, 10))

        frame_tree = tk.Frame(win, bg='#1a1a2e')
        frame_tree.pack(fill='both', expand=True, padx=16)

        cols = ("Manter (original)", "Duplicata a remover", "Tamanho")
        tree = ttk.Treeview(frame_tree, columns=cols, show='headings', selectmode='extended')
        for col in cols:
            tree.heading(col, text=col)
        tree.column("Manter (original)", width=280)
        tree.column("Duplicata a remover", width=280)
        tree.column("Tamanho", width=90, anchor='center')

        scrollbar = ttk.Scrollbar(frame_tree, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        tree_data = {}
        for h, files in self.duplicatas.items():
            original = files[0]
            for dup in files[1:]:
                try:
                    size = os.path.getsize(dup)
                    size_str = f"{size/1024:.1f} KB" if size < 1e6 else f"{size/1e6:.1f} MB"
                except Exception:
                    size_str = "?"
                iid = tree.insert('', 'end', values=(
                    os.path.basename(original),
                    os.path.basename(dup),
                    size_str
                ))
                tree_data[iid] = dup

        tree.tag_configure('oddrow', background='#0f172a')
        for i, iid in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(iid, tags='oddrow')

        btn_frame = tk.Frame(win, bg='#1a1a2e', pady=12)
        btn_frame.pack()

        def excluir_selecionados():
            selecionados = tree.selection()
            if not selecionados:
                messagebox.showinfo("Atenção", "Selecione arquivos na lista!")
                return
            nomes = "\n".join(f"• {os.path.basename(tree_data[i])}" for i in selecionados[:10])
            if len(selecionados) > 10:
                nomes += f"\n... e mais {len(selecionados)-10} arquivos"
            if not messagebox.askyesno("⚠️ Confirmar Exclusão",
                f"Tem certeza que deseja EXCLUIR PERMANENTEMENTE {len(selecionados)} arquivo(s)?\n\n{nomes}\n\n⚠️ Esta ação NÃO pode ser desfeita!"):
                return
            excluidos = erros = 0
            for iid in selecionados:
                fp = tree_data.get(iid, '')
                try:
                    if os.path.exists(fp):
                        os.remove(fp)
                        excluidos += 1
                        self._log(f"🗑️ Excluído: {os.path.basename(fp)}", 'warn')
                    tree.delete(iid)
                except Exception as e:
                    erros += 1
                    self._log(f"Erro ao excluir {os.path.basename(fp)}: {e}", 'err')
            messagebox.showinfo("Concluído", f"✅ {excluidos} arquivo(s) excluído(s).\n{erros} erro(s).")

        def excluir_todos():
            todos = list(tree.get_children())
            if not todos:
                return
            espaco_total = sum(
                os.path.getsize(tree_data[i]) for i in todos
                if os.path.exists(tree_data.get(i, ''))
            )
            if not messagebox.askyesno("⚠️ ATENÇÃO — Excluir TODOS",
                f"Deseja excluir TODOS os {len(todos)} arquivos duplicados?\n\n"
                f"Liberará aprox. {espaco_total/(1024*1024):.1f} MB\n\n"
                "⚠️ Esta ação é IRREVERSÍVEL!\n\nOs arquivos originais serão mantidos."):
                return
            excluidos = erros = 0
            for iid in todos:
                fp = tree_data.get(iid, '')
                try:
                    if fp and os.path.exists(fp):
                        os.remove(fp)
                        excluidos += 1
                except Exception:
                    erros += 1
                tree.delete(iid)
            self._log(f"🗑️ Todos excluídos: {excluidos} arquivos, {erros} erros", 'warn')
            messagebox.showinfo("Concluído", f"✅ {excluidos} duplicatas removidas!\n{erros} erro(s).\nOriginais mantidos.")

        for text, color, cmd in [
            ("✅ Excluir Selecionados", '#7f1d1d', excluir_selecionados),
            ("🗑️ Excluir TODOS os Duplicados", '#450a0a', excluir_todos),
            ("Fechar", '#1e293b', win.destroy),
        ]:
            tk.Button(btn_frame, text=text, bg=color, fg='#e2e8f0', relief='flat',
                      padx=14, pady=7, font=('Segoe UI', 9, 'bold'), cursor='hand2',
                      activebackground='#818cf8', command=cmd).pack(side='left', padx=6)


def verificar_pillow():
    global PILLOW_OK
    if not PILLOW_OK:
        try:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow', '-q'])
            from PIL import Image
            from PIL.ExifTags import TAGS
            PILLOW_OK = True
        except Exception:
            pass


if __name__ == "__main__":
    verificar_pillow()
    root = tk.Tk()
    app = OrganizadorApp(root)
    if not PILLOW_OK:
        app._log("Pillow não instalado — datas EXIF indisponíveis (usando data do arquivo)", 'warn')
    else:
        app._log("✓ Pillow disponível — leitura de EXIF ativada", 'ok')
    app._log("Selecione a pasta de origem e clique em 'Escanear'", 'info')
    root.mainloop()