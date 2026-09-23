"""
Módulo de Produtividade Interna
Código original do controle_produtividade_app.py adaptado para o ERP unificado
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkcalendar import DateEntry
import pandas as pd
from datetime import datetime, timedelta
import json
import logging
import os
import shutil
from pathlib import Path

from config.cores import TemaPraia
from core.database_manager import DatabaseManager
from core.database_local import DatabaseLocal
from widgets.scrollable_frame import ScrollableFrame

# ============================================================
# CONSTANTES
# ============================================================

CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)

from core.utils import get_config_dir

MESES_FILE = get_config_dir() / "meses_cadastrados.json"

# ============================================================
# DIÁLOGO DE FALTA/ATESTADO - IGUAL AO ORIGINAL
# ============================================================

class DialogoFaltaAtestado:
    """Diálogo para registrar falta ou atestado - IGUAL AO ORIGINAL"""
    
    def __init__(self, parent, colaborador, data):
        self.resultado = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("📋 Registrar Falta/Atestado")
        self.dialog.geometry("400x300")
        self.dialog.configure(bg='#F0F8FF')
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centralizar
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        cores = TemaPraia()
        
        # Título
        tk.Label(
            self.dialog,
            text="📋 REGISTRAR AUSÊNCIA",
            font=('Arial', 14, 'bold'),
            bg='#F0F8FF',
            fg='#006994'
        ).pack(pady=15)
        
        # Informações do colaborador
        tk.Label(
            self.dialog,
            text=f"Colaborador: {colaborador}",
            font=('Arial', 12),
            bg='#F0F8FF',
            fg='#006994'
        ).pack(pady=5)
        
        tk.Label(
            self.dialog,
            text=f"Data: {data.strftime('%d/%m/%Y')}",
            font=('Arial', 12),
            bg='#F0F8FF',
            fg='#006994'
        ).pack(pady=5)
        
        tk.Label(self.dialog, text="", bg='#F0F8FF').pack(pady=5)
        
        # Botões de seleção
        btn_frame = tk.Frame(self.dialog, bg='#F0F8FF')
        btn_frame.pack(pady=15)
        
        # Botão Falta
        btn_falta = tk.Button(
            btn_frame,
            text="❌ Falta",
            font=('Arial', 12, 'bold'),
            bg='#FF6B6B',
            fg='white',
            width=15,
            height=2,
            relief=tk.RAISED,
            bd=3,
            command=lambda: self.definir_resultado('falta')
        )
        btn_falta.pack(side=tk.LEFT, padx=10)
        
        # Botão Atestado
        btn_atestado = tk.Button(
            btn_frame,
            text="📄 Atestado",
            font=('Arial', 12, 'bold'),
            bg='#4ECDC4',
            fg='white',
            width=15,
            height=2,
            relief=tk.RAISED,
            bd=3,
            command=lambda: self.definir_resultado('atestado')
        )
        btn_atestado.pack(side=tk.LEFT, padx=10)
        
        # Botão Cancelar
        tk.Button(
            self.dialog,
            text="❌ Cancelar",
            font=('Arial', 10),
            bg='#95A5A6',
            fg='white',
            width=12,
            command=self.cancelar
        ).pack(pady=15)
        
        # Observação
        tk.Label(
            self.dialog,
            text="💡 A falta/atestado será registrado para este dia",
            font=('Arial', 9, 'italic'),
            bg='#F0F8FF',
            fg='#7F8C8D'
        ).pack(pady=5)
    
    def definir_resultado(self, tipo):
        self.resultado = tipo
        self.dialog.destroy()
    
    def cancelar(self):
        self.resultado = None
        self.dialog.destroy()


# ============================================================
# MÓDULO PRINCIPAL
# ============================================================

class ModuloProdutividade:
    """Módulo de Produtividade Interna - IGUAL AO ORIGINAL"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.cores = TemaPraia()
        self.db = DatabaseManager()
        self.db_local = DatabaseLocal()
        
        # Dados - IGUAL AO ORIGINAL
        self.monthly_data = {
            'biquini': [],
            'roupa': [],
            'acabamento': []
        }
        self.colaboradores = self.db_local.carregar_colaboradores()
        self.metas = self.db_local.carregar_metas()
        self.periodo_atual = None
        self.arquivo_atual = None
        self.mes_atual_info = None
        self.feriados = []
        
        # Dicionários para controle - IGUAL AO ORIGINAL
        self.qty_entries_dict = {}
        self.qty_frames = {}
        self.qty_label = {}
        self.last_selection = {}
        self.product_data = {}
        self.product_listboxes = {}
        self.treeviews = {}
        self.date_entries = {}
        self.cycle_entries = {}
        self.order_entries = {}
        self.stats_labels = {}
        
        # Carregar meses cadastrados
        self.meses_cadastrados = self.carregar_meses_cadastrados()
        
        # Interface
        self._criar_interface()
        
        # Carregar colaboradores
        self.atualizar_combo_colaboradores()
    
    # ============================================================
    # CARREGAR ARQUIVOS DE CONFIGURAÇÃO - CORRIGIDO
    # ============================================================
    
    def carregar_meses_cadastrados(self):
        """Carrega meses cadastrados do arquivo JSON - CORRIGIDO"""
        try:
            if MESES_FILE.exists():
                with open(MESES_FILE, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    logging.info(f"Meses carregados: {len(dados)}")
                    return dados
        except Exception as e:
            logging.error(f"Erro ao carregar meses: {e}")
        return {}
    
    def salvar_meses_cadastrados(self):
        """Salva meses cadastrados no arquivo JSON - CORRIGIDO"""
        try:
            with open(MESES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.meses_cadastrados, f, ensure_ascii=False, indent=2)
            logging.info(f"Meses salvos: {len(self.meses_cadastrados)}")
        except Exception as e:
            logging.error(f"Erro ao salvar meses: {e}")
            messagebox.showerror("Erro", f"Erro ao salvar meses: {str(e)}")
    
    def carregar_metas(self):
        """Carrega metas de produção - IGUAL AO ORIGINAL"""
        return self.db_local.carregar_metas()
    
    def salvar_metas(self):
        """Salva metas de produção - IGUAL AO ORIGINAL"""
        for grupo, meta in self.metas.items():
            self.db_local.salvar_meta(
                grupo,
                meta.get('num_funcionarios', 1),
                meta.get('meta_diaria_por_funcionario', 15)
            )
    
    # ============================================================
    # MÉTODOS DE CÁLCULO - IGUAIS AO ORIGINAL
    # ============================================================
    
    def calcular_meta_mensal(self, grupo):
        """Calcula meta mensal para um grupo - IGUAL AO ORIGINAL"""
        if grupo not in self.metas:
            return 0
        meta_info = self.metas[grupo]
        num_funcionarios = meta_info.get('num_funcionarios', 1)
        meta_diaria_por_func = meta_info.get('meta_diaria_por_funcionario', 15)
        if self.periodo_atual:
            dias_uteis = self.calcular_dias_uteis(self.periodo_atual[0], self.periodo_atual[1])
        else:
            dias_uteis = 22
        return num_funcionarios * meta_diaria_por_func * dias_uteis
    
    def calcular_dias_uteis(self, inicio, fim):
        """Calcula dias úteis entre duas datas - IGUAL AO ORIGINAL"""
        dias = 0
        data_atual = inicio
        while data_atual <= fim:
            if self.eh_dia_util(data_atual):
                dias += 1
            data_atual += timedelta(days=1)
        return dias
    
    def eh_dia_util(self, data):
        """Verifica se uma data é dia útil - IGUAL AO ORIGINAL"""
        if data.weekday() >= 5:
            return False
        data_str = data.strftime('%Y-%m-%d')
        if data_str in [f['data'] for f in self.feriados]:
            return False
        return True
    
    def dias_restantes(self):
        """Calcula dias úteis restantes no mês - IGUAL AO ORIGINAL"""
        if not self.periodo_atual:
            return 0
        
        hoje = datetime.now()
        if hoje < self.periodo_atual[0]:
            hoje = self.periodo_atual[0]
        
        dias = 0
        data_atual = hoje
        while data_atual <= self.periodo_atual[1]:
            if self.eh_dia_util(data_atual):
                dias += 1
            data_atual += timedelta(days=1)
        
        return dias
    
    def avaliar_expressao_matematica(self, expressao):
        """Avalia expressão matemática simples em string - IGUAL AO ORIGINAL"""
        if not expressao or not expressao.strip():
            return 0
        
        expressao = expressao.strip()
        
        try:
            return int(expressao)
        except ValueError:
            pass
        
        try:
            if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expressao):
                resultado = eval(expressao)
                if isinstance(resultado, (int, float)):
                    return int(resultado)
        except:
            pass
        
        return None
    
    # ============================================================
    # GESTÃO DE MESES - CORRIGIDO
    # ============================================================
    
    def cadastrar_novo_mes(self):
        """Cadastra um novo mês de trabalho - IGUAL AO ORIGINAL"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("🏖️ Cadastrar Novo Mês")
        dialog.geometry("550x600")
        dialog.configure(bg=self.cores.CINZA_CLARO)
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(
            main_frame,
            text="📅 CADASTRAR NOVO MÊS",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)
        
        frame_mes = ttk.Frame(main_frame)
        frame_mes.pack(fill='x', pady=10)
        ttk.Label(frame_mes, text="Mês de Referência:", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        mes_combo = ttk.Combobox(frame_mes, values=meses_nomes, state='readonly', width=15)
        mes_combo.pack(side=tk.LEFT, padx=5)
        mes_combo.current(datetime.now().month - 1)
        
        ttk.Label(frame_mes, text="Ano:", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        ano_entry = ttk.Entry(frame_mes, width=8)
        ano_entry.pack(side=tk.LEFT, padx=5)
        ano_entry.insert(0, str(datetime.now().year))
        
        frame_datas = ttk.LabelFrame(main_frame, text="📆 Período do Mês", padding="10")
        frame_datas.pack(fill='x', pady=10)
        
        ttk.Label(frame_datas, text="Data de Início:", font=('Arial', 11)).grid(
            row=0, column=0, padx=5, pady=5, sticky='e'
        )
        data_inicio = DateEntry(
            frame_datas,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy'
        )
        data_inicio.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame_datas, text="Data de Término:", font=('Arial', 11)).grid(
            row=1, column=0, padx=5, pady=5, sticky='e'
        )
        data_fim = DateEntry(
            frame_datas,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yyyy'
        )
        data_fim.grid(row=1, column=1, padx=5, pady=5)
        
        frame_feriados = ttk.LabelFrame(main_frame, text="🏖️ Feriados do Mês", padding="10")
        frame_feriados.pack(fill='both', expand=True, pady=10)
        
        feriados_listbox = tk.Listbox(
            frame_feriados,
            height=5,
            bg='white',
            fg=self.cores.AZUL_MAR,
            selectbackground=self.cores.CORAL
        )
        feriados_listbox.pack(fill='both', expand=True, pady=5)
        
        feriados_temp = []
        
        def adicionar_feriado():
            sub_dialog = tk.Toplevel(dialog)
            sub_dialog.title("🏖️ Adicionar Feriado")
            sub_dialog.geometry("350x200")
            sub_dialog.configure(bg=self.cores.CINZA_CLARO)
            sub_dialog.transient(dialog)
            sub_dialog.grab_set()
            
            ttk.Label(sub_dialog, text="Data do Feriado:", font=('Arial', 11)).pack(pady=10)
            data_feriado = DateEntry(
                sub_dialog,
                width=15,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy'
            )
            data_feriado.pack(pady=5)
            
            ttk.Label(sub_dialog, text="Descrição:", font=('Arial', 11)).pack(pady=5)
            desc_entry = ttk.Entry(sub_dialog, width=30)
            desc_entry.pack(pady=5)
            
            def salvar_feriado():
                data = data_feriado.get_date().strftime("%Y-%m-%d")
                desc = desc_entry.get().strip()
                if data and desc:
                    feriados_temp.append({'data': data, 'descricao': desc})
                    feriados_listbox.insert(tk.END, f"🏖️ {data} - {desc}")
                    sub_dialog.destroy()
                else:
                    messagebox.showwarning("Aviso", "Preencha todos os campos!")
            
            ttk.Button(sub_dialog, text="Adicionar", command=salvar_feriado).pack(pady=10)
        
        def remover_feriado():
            selecao = feriados_listbox.curselection()
            if selecao:
                indice = selecao[0]
                feriados_listbox.delete(indice)
                del feriados_temp[indice]
        
        btn_frame = ttk.Frame(frame_feriados)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="➕ Adicionar Feriado", command=adicionar_feriado).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="➖ Remover Selecionado", command=remover_feriado).pack(side=tk.LEFT, padx=5)
        
        def salvar_mes():
            mes_nome = mes_combo.get()
            ano = ano_entry.get().strip()
            
            if not mes_nome or not ano:
                messagebox.showwarning("Aviso", "Selecione o mês e informe o ano!")
                return
            
            try:
                ano = int(ano)
            except ValueError:
                messagebox.showerror("Erro", "Ano inválido!")
                return
            
            inicio = data_inicio.get_date()
            fim = data_fim.get_date()
            
            if inicio > fim:
                messagebox.showerror("Erro", "Data de início deve ser anterior à data de término!")
                return
            
            mes_key = f"{mes_nome}_{ano}"
            
            if mes_key in self.meses_cadastrados:
                messagebox.showerror("Erro", f"O mês {mes_nome} de {ano} já está cadastrado!")
                return
            
            self.meses_cadastrados[mes_key] = {
                'nome': mes_nome,
                'ano': ano,
                'inicio': inicio.strftime('%Y-%m-%d'),
                'fim': fim.strftime('%Y-%m-%d'),
                'feriados': feriados_temp
            }
            
            self.salvar_meses_cadastrados()
            messagebox.showinfo("Sucesso", f"✅ Mês {mes_nome} de {ano} cadastrado com sucesso!")
            dialog.destroy()
            
            if messagebox.askyesno("📅 Abrir Mês", "Deseja abrir este mês agora?"):
                self.carregar_mes(mes_key)
        
        ttk.Button(main_frame, text="💾 Salvar Mês", command=salvar_mes).pack(pady=10)
    
    def editar_mes(self):
        """Edita um mês cadastrado - CORRIGIDO"""
        if not self.meses_cadastrados:
            messagebox.showinfo("Aviso", "Não há meses cadastrados!")
            return
        
        # Recarregar meses para garantir dados atualizados
        self.meses_cadastrados = self.carregar_meses_cadastrados()
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("✏️ Editar Mês")
        dialog.geometry("550x650")
        dialog.configure(bg=self.cores.CINZA_CLARO)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        ttk.Label(dialog, text="✏️ EDITAR MÊS", font=('Arial', 14, 'bold')).pack(pady=10)
        
        frame_selecao = ttk.Frame(dialog)
        frame_selecao.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(frame_selecao, text="Selecione o mês:").pack(side=tk.LEFT, padx=5)
        meses_lista = [f"{info['nome']} {info['ano']}" for info in self.meses_cadastrados.values()]
        mes_combo = ttk.Combobox(frame_selecao, values=sorted(meses_lista), state='readonly', width=20)
        mes_combo.pack(side=tk.LEFT, padx=5)
        
        frame_edicao = ttk.Frame(dialog)
        frame_edicao.pack(fill='both', expand=True, padx=20, pady=10)
        
        mes_key_atual = [None]
        feriados_temp = []
        
        def carregar_dados_mes():
            selecionado = mes_combo.get()
            if not selecionado:
                return
            
            mes_key = None
            for key, info in self.meses_cadastrados.items():
                if f"{info['nome']} {info['ano']}" == selecionado:
                    mes_key = key
                    break
            
            if not mes_key:
                return
            
            mes_key_atual[0] = mes_key
            info = self.meses_cadastrados[mes_key]
            
            for widget in frame_edicao.winfo_children():
                widget.destroy()
            
            frame_datas = ttk.LabelFrame(frame_edicao, text="📆 Período do Mês", padding="10")
            frame_datas.pack(fill='x', pady=10)
            
            ttk.Label(frame_datas, text="Data de Início:", font=('Arial', 11)).grid(
                row=0, column=0, padx=5, pady=5, sticky='e'
            )
            data_inicio_edit = DateEntry(
                frame_datas,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy'
            )
            data_inicio_edit.set_date(datetime.strptime(info['inicio'], '%Y-%m-%d'))
            data_inicio_edit.grid(row=0, column=1, padx=5, pady=5)
            
            ttk.Label(frame_datas, text="Data de Término:", font=('Arial', 11)).grid(
                row=1, column=0, padx=5, pady=5, sticky='e'
            )
            data_fim_edit = DateEntry(
                frame_datas,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy'
            )
            data_fim_edit.set_date(datetime.strptime(info['fim'], '%Y-%m-%d'))
            data_fim_edit.grid(row=1, column=1, padx=5, pady=5)
            
            frame_feriados = ttk.LabelFrame(frame_edicao, text="🏖️ Feriados do Mês", padding="10")
            frame_feriados.pack(fill='both', expand=True, pady=10)
            
            feriados_listbox = tk.Listbox(
                frame_feriados,
                height=6,
                bg='white',
                fg=self.cores.AZUL_MAR,
                selectbackground=self.cores.CORAL
            )
            feriados_listbox.pack(fill='both', expand=True, pady=5)
            
            feriados_temp.clear()
            feriados_temp.extend(info.get('feriados', []))
            
            for feriado in feriados_temp:
                feriados_listbox.insert(tk.END, f"🏖️ {feriado['data']} - {feriado['descricao']}")
            
            def adicionar_feriado_edit():
                sub_dialog = tk.Toplevel(dialog)
                sub_dialog.title("🏖️ Adicionar Feriado")
                sub_dialog.geometry("350x200")
                sub_dialog.configure(bg=self.cores.CINZA_CLARO)
                sub_dialog.transient(dialog)
                sub_dialog.grab_set()
                
                ttk.Label(sub_dialog, text="Data do Feriado:", font=('Arial', 11)).pack(pady=10)
                data_feriado = DateEntry(
                    sub_dialog,
                    width=15,
                    background='darkblue',
                    foreground='white',
                    borderwidth=2,
                    date_pattern='dd/mm/yyyy'
                )
                data_feriado.pack(pady=5)
                
                ttk.Label(sub_dialog, text="Descrição:", font=('Arial', 11)).pack(pady=5)
                desc_entry = ttk.Entry(sub_dialog, width=30)
                desc_entry.pack(pady=5)
                
                def salvar_feriado_edit():
                    data = data_feriado.get_date().strftime("%Y-%m-%d")
                    desc = desc_entry.get().strip()
                    
                    if not data or not desc:
                        messagebox.showwarning("Aviso", "Preencha todos os campos!")
                        return
                    
                    if any(f['data'] == data for f in feriados_temp):
                        messagebox.showwarning("Aviso", "Já existe um feriado cadastrado nesta data!")
                        return
                    
                    feriados_temp.append({'data': data, 'descricao': desc})
                    feriados_listbox.insert(tk.END, f"🏖️ {data} - {desc}")
                    sub_dialog.destroy()
                
                ttk.Button(sub_dialog, text="Adicionar", command=salvar_feriado_edit).pack(pady=10)
            
            def remover_feriado_edit():
                selecao = feriados_listbox.curselection()
                if selecao:
                    indice = selecao[0]
                    if messagebox.askyesno("Confirmar", "Remover este feriado?"):
                        feriados_listbox.delete(indice)
                        del feriados_temp[indice]
                else:
                    messagebox.showwarning("Aviso", "Selecione um feriado para remover!")
            
            def editar_feriado_edit():
                selecao = feriados_listbox.curselection()
                if not selecao:
                    messagebox.showwarning("Aviso", "Selecione um feriado para editar!")
                    return
                
                indice = selecao[0]
                feriado = feriados_temp[indice]
                
                sub_dialog = tk.Toplevel(dialog)
                sub_dialog.title("✏️ Editar Feriado")
                sub_dialog.geometry("350x200")
                sub_dialog.configure(bg=self.cores.CINZA_CLARO)
                sub_dialog.transient(dialog)
                sub_dialog.grab_set()
                
                ttk.Label(sub_dialog, text="Data do Feriado:", font=('Arial', 11)).pack(pady=10)
                data_feriado = DateEntry(
                    sub_dialog,
                    width=15,
                    background='darkblue',
                    foreground='white',
                    borderwidth=2,
                    date_pattern='dd/mm/yyyy'
                )
                data_feriado.set_date(datetime.strptime(feriado['data'], '%Y-%m-%d'))
                data_feriado.pack(pady=5)
                
                ttk.Label(sub_dialog, text="Descrição:", font=('Arial', 11)).pack(pady=5)
                desc_entry = ttk.Entry(sub_dialog, width=30)
                desc_entry.insert(0, feriado['descricao'])
                desc_entry.pack(pady=5)
                
                def salvar_edicao_feriado():
                    nova_data = data_feriado.get_date().strftime("%Y-%m-%d")
                    nova_desc = desc_entry.get().strip()
                    
                    if not nova_data or not nova_desc:
                        messagebox.showwarning("Aviso", "Preencha todos os campos!")
                        return
                    
                    if any(f['data'] == nova_data for i, f in enumerate(feriados_temp) if i != indice):
                        messagebox.showwarning("Aviso", "Já existe um feriado cadastrado nesta data!")
                        return
                    
                    feriados_temp[indice] = {'data': nova_data, 'descricao': nova_desc}
                    feriados_listbox.delete(indice)
                    feriados_listbox.insert(indice, f"🏖️ {nova_data} - {nova_desc}")
                    sub_dialog.destroy()
                
                ttk.Button(sub_dialog, text="Salvar", command=salvar_edicao_feriado).pack(pady=10)
            
            btn_frame_feriados = ttk.Frame(frame_feriados)
            btn_frame_feriados.pack(fill='x', pady=5)
            
            ttk.Button(btn_frame_feriados, text="➕ Adicionar",
                      command=adicionar_feriado_edit).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame_feriados, text="✏️ Editar",
                      command=editar_feriado_edit).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame_feriados, text="➖ Remover",
                      command=remover_feriado_edit).pack(side=tk.LEFT, padx=5)
            
            def salvar_edicao():
                novo_inicio = data_inicio_edit.get_date()
                novo_fim = data_fim_edit.get_date()
                
                if novo_inicio > novo_fim:
                    messagebox.showerror("Erro", "Data de início deve ser anterior à data de término!")
                    return
                
                self.meses_cadastrados[mes_key]['inicio'] = novo_inicio.strftime('%Y-%m-%d')
                self.meses_cadastrados[mes_key]['fim'] = novo_fim.strftime('%Y-%m-%d')
                self.meses_cadastrados[mes_key]['feriados'] = feriados_temp.copy()
                
                self.salvar_meses_cadastrados()
                
                if self.mes_atual_info and self.mes_atual_info == mes_key:
                    self.carregar_mes(mes_key)
                
                messagebox.showinfo("Sucesso", "✅ Mês atualizado com sucesso!")
                dialog.destroy()
            
            ttk.Button(frame_edicao, text="💾 Salvar Alterações", command=salvar_edicao).pack(pady=20)
        
        ttk.Button(frame_selecao, text="📂 Carregar", command=carregar_dados_mes).pack(side=tk.LEFT, padx=10)
        ttk.Button(frame_selecao, text="🗑️ Excluir Mês", command=lambda: self.excluir_mes(dialog, mes_combo)).pack(side=tk.LEFT, padx=10)
    
    def excluir_mes(self, dialog, mes_combo):
        """Exclui um mês cadastrado - CORRIGIDO"""
        selecionado = mes_combo.get()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um mês para excluir!")
            return
        
        if not messagebox.askyesno("Confirmar Exclusão", 
            f"Tem certeza que deseja excluir o mês '{selecionado}'?\n"
            "Esta ação não pode ser desfeita!"):
            return
        
        mes_key = None
        for key, info in self.meses_cadastrados.items():
            if f"{info['nome']} {info['ano']}" == selecionado:
                mes_key = key
                break
        
        if not mes_key:
            return
        
        # Remover do dicionário
        del self.meses_cadastrados[mes_key]
        
        # Salvar arquivo
        self.salvar_meses_cadastrados()
        
        # Se o mês atual for o excluído, limpar
        if self.mes_atual_info == mes_key:
            self.mes_atual_info = None
            self.periodo_atual = None
            self.arquivo_atual = None
            self.feriados = []
            for key in self.monthly_data:
                self.monthly_data[key] = []
            for tree in self.treeviews.values():
                for item in tree.get_children():
                    tree.delete(item)
            self.status_bar.config(text="🏖️ Mês excluído - Nenhum mês carregado")
            messagebox.showinfo("Sucesso", f"✅ Mês '{selecionado}' excluído com sucesso!")
        
        dialog.destroy()
        messagebox.showinfo("Sucesso", f"✅ Mês '{selecionado}' excluído com sucesso!")
        
        # Atualizar lista de meses
        self.meses_cadastrados = self.carregar_meses_cadastrados()
    
    def selecionar_mes(self):
        """Seleciona um mês cadastrado para abrir - CORRIGIDO"""
        # Recarregar meses para garantir dados atualizados
        self.meses_cadastrados = self.carregar_meses_cadastrados()
        
        if not self.meses_cadastrados:
            messagebox.showinfo("Aviso", "Não há meses cadastrados!\nCadastre um novo mês primeiro.")
            return
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("📅 Selecionar Mês")
        dialog.geometry("600x450")
        dialog.configure(bg=self.cores.CINZA_CLARO)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        ttk.Label(dialog, text="📅 SELECIONAR MÊS", font=('Arial', 14, 'bold')).pack(pady=10)
        
        frame_lista = ttk.Frame(dialog)
        frame_lista.pack(fill='both', expand=True, padx=20, pady=10)
        
        columns = ('Mês', 'Ano', 'Início', 'Fim', 'Feriados')
        tree = ttk.Treeview(frame_lista, columns=columns, show='headings', height=10)
        
        tree.heading('Mês', text='📅 Mês')
        tree.heading('Ano', text='📆 Ano')
        tree.heading('Início', text='▶️ Início')
        tree.heading('Fim', text='⏹️ Fim')
        tree.heading('Feriados', text='🏖️ Feriados')
        
        tree.column('Mês', width=120)
        tree.column('Ano', width=70)
        tree.column('Início', width=120)
        tree.column('Fim', width=120)
        tree.column('Feriados', width=80)
        
        for key, info in sorted(self.meses_cadastrados.items()):
            tree.insert('', 'end', values=(
                info['nome'],
                info['ano'],
                datetime.strptime(info['inicio'], '%Y-%m-%d').strftime('%d/%m/%Y'),
                datetime.strptime(info['fim'], '%Y-%m-%d').strftime('%d/%m/%Y'),
                f"{len(info.get('feriados', []))} 🏖️"
            ))
        
        scrollbar = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(btn_frame, text="📂 Abrir Mês", 
                  command=lambda: self._abrir_mes_selecionado(tree, dialog)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="✏️ Editar Mês", 
                  command=lambda: self._editar_mes_selecionado(tree, dialog)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🗑️ Excluir Mês", 
                  command=lambda: self._excluir_mes_selecionado(tree, dialog)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="❌ Fechar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        tree.bind("<Double-1>", lambda event: self._abrir_mes_selecionado(tree, dialog))
    
    def _abrir_mes_selecionado(self, tree, dialog):
        """Abre o mês selecionado - CORRIGIDO"""
        selecao = tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um mês!")
            return
        
        valores = tree.item(selecao[0])['values']
        mes_key = f"{valores[0]}_{valores[1]}"
        self.carregar_mes(mes_key)
        dialog.destroy()
    
    def _editar_mes_selecionado(self, tree, dialog):
        """Edita o mês selecionado - CORRIGIDO"""
        selecao = tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um mês!")
            return
        
        dialog.destroy()
        self.editar_mes()
    
    def _excluir_mes_selecionado(self, tree, dialog):
        """Exclui o mês selecionado - CORRIGIDO"""
        selecao = tree.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um mês!")
            return
        
        valores = tree.item(selecao[0])['values']
        mes_key = f"{valores[0]}_{valores[1]}"
        
        if not messagebox.askyesno("Confirmar Exclusão", 
            f"Tem certeza que deseja excluir o mês '{valores[0]} {valores[1]}'?\n"
            "Esta ação não pode ser desfeita!"):
            return
        
        if mes_key in self.meses_cadastrados:
            del self.meses_cadastrados[mes_key]
            self.salvar_meses_cadastrados()
            
            # Se o mês atual for o excluído, limpar
            if self.mes_atual_info == mes_key:
                self.mes_atual_info = None
                self.periodo_atual = None
                self.arquivo_atual = None
                self.feriados = []
                for key in self.monthly_data:
                    self.monthly_data[key] = []
                for treeview in self.treeviews.values():
                    for item in treeview.get_children():
                        treeview.delete(item)
                self.status_bar.config(text="🏖️ Mês excluído - Nenhum mês carregado")
            
            messagebox.showinfo("Sucesso", f"✅ Mês '{valores[0]} {valores[1]}' excluído com sucesso!")
            dialog.destroy()
            
            # Recarregar lista
            self.selecionar_mes()
    
    def carregar_mes(self, mes_key):
        """Carrega os dados de um mês específico - IGUAL AO ORIGINAL"""
        if mes_key not in self.meses_cadastrados:
            messagebox.showerror("Erro", "Mês não encontrado!")
            return
        
        info = self.meses_cadastrados[mes_key]
        self.mes_atual_info = mes_key
        
        inicio_mes = datetime.strptime(info['inicio'], '%Y-%m-%d')
        fim_mes = datetime.strptime(info['fim'], '%Y-%m-%d')
        self.periodo_atual = (inicio_mes, fim_mes)
        
        self.feriados = info.get('feriados', [])
        
        self.arquivo_atual = f"producao_{info['nome']}_{info['ano']}.xlsx"
        
        # Limpar dados
        for key in self.monthly_data:
            self.monthly_data[key] = []
        
        for tree in self.treeviews.values():
            for item in tree.get_children():
                tree.delete(item)
        
        # Carregar do arquivo se existir
        if os.path.exists(self.arquivo_atual):
            try:
                for tipo in ['biquini', 'roupa']:
                    try:
                        df = pd.read_excel(self.arquivo_atual, sheet_name=tipo, engine='openpyxl')
                        if not df.empty:
                            if 'data' in df.columns:
                                df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
                                mask = (df['data'] >= inicio_mes.strftime('%Y-%m-%d')) & \
                                    (df['data'] <= fim_mes.strftime('%Y-%m-%d'))
                                df_periodo = df[mask]
                            else:
                                df_periodo = df
                            
                            self.monthly_data[tipo] = df_periodo.to_dict('records')
                            self.ordenar_dados_por_data(tipo)
                            self.recarregar_treeview(tipo)
                    except Exception as e:
                        print(f"Erro ao carregar {tipo}: {e}")
                
                try:
                    df = pd.read_excel(self.arquivo_atual, sheet_name='acabamento', engine='openpyxl')
                    if not df.empty:
                        if 'data' in df.columns:
                            df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
                            mask = (df['data'] >= inicio_mes.strftime('%Y-%m-%d')) & \
                                (df['data'] <= fim_mes.strftime('%Y-%m-%d'))
                            df_periodo = df[mask]
                        else:
                            df_periodo = df
                        
                        self.monthly_data['acabamento'] = df_periodo.to_dict('records')
                        self.ordenar_dados_por_data('acabamento')
                        self.recarregar_treeview('acabamento')
                except Exception as e:
                    print(f"Erro ao carregar acabamento: {e}")
                    
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar arquivo: {str(e)}")
        
        self.atualizar_todas_estatisticas()
        self.atualizar_sugestao_datas()
        
        self.status_bar.config(
            text=f"🏖️ Mês atual: {info['nome']} {info['ano']} "
                 f"(Período: {inicio_mes.strftime('%d/%m/%Y')} a {fim_mes.strftime('%d/%m/%Y')})"
        )
        
        total_registros = sum(len(v) for v in self.monthly_data.values())
        messagebox.showinfo(
            "📅 Mês Carregado",
            f"✅ Mês: {info['nome']} de {info['ano']}\n"
            f"📆 Período: {inicio_mes.strftime('%d/%m/%Y')} a {fim_mes.strftime('%d/%m/%Y')}\n"
            f"🏖️ Feriados: {len(self.feriados)}\n"
            f"📊 Registros carregados: {total_registros}"
        )
    
    # ============================================================
    # INTERFACE - IGUAL AO ORIGINAL
    # ============================================================
    
    def _criar_interface(self):
        """Cria a interface do módulo de produtividade - IGUAL AO ORIGINAL"""
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Barra de ferramentas - IGUAL AO ORIGINAL
        toolbar = tk.Frame(main_frame, bg=self.cores.AZUL_MAR, height=50)
        toolbar.pack(fill='x', pady=(0, 10))
        toolbar.pack_propagate(False)
        
        botoes = [
            ("📅 Selecionar Mês", self.selecionar_mes),
            ("➕ Cadastrar Mês", self.cadastrar_novo_mes),
            ("✏️ Editar Mês", self.editar_mes),
            ("❓ Ajuda", self.mostrar_ajuda),
            ("💾 Salvar", self.salvar_producao)
        ]
        
        for texto, comando in botoes:
            btn = tk.Button(
                toolbar,
                text=texto,
                command=comando,
                font=('Arial', 10, 'bold'),
                bg=self.cores.AREIA,
                fg=self.cores.AZUL_MAR_ESCURO,
                relief='flat',
                bd=0,
                padx=15,
                pady=5,
                cursor='hand2'
            )       
        
            btn.pack(side=tk.LEFT, padx=5, pady=5)

            # Efeitos hover
            def on_enter(e, b=btn):
                b.config(bg=self.cores.AREIA_ESCURA)
            def on_leave(e, b=btn):
                b.config(bg=self.cores.AREIA)
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
        
        # Barra de status - IGUAL AO ORIGINAL
        self.status_bar = tk.Label(
            main_frame,
            text="🏖️ Pronto - Nenhum mês carregado",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg='#E6F3FF',
            fg='#006994',
            font=('Arial', 10)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Notebook interno - IGUAL AO ORIGINAL
        self.notebook_prod = ttk.Notebook(main_frame)
        self.notebook_prod.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Aba Biquíni - IGUAL AO ORIGINAL
        self.aba_biquini = ttk.Frame(self.notebook_prod)
        self.notebook_prod.add(self.aba_biquini, text='👙 Costura Biquíni')
        self.configurar_aba_costura(self.aba_biquini, 'biquini')
        
        # Aba Roupa - IGUAL AO ORIGINAL
        self.aba_roupa = ttk.Frame(self.notebook_prod)
        self.notebook_prod.add(self.aba_roupa, text='👗 Costura Roupa')
        self.configurar_aba_costura(self.aba_roupa, 'roupa')
        
        # Aba Acabamento - IGUAL AO ORIGINAL
        self.aba_acabamento = ttk.Frame(self.notebook_prod)
        self.notebook_prod.add(self.aba_acabamento, text='✨ Acabamento')
        self.configurar_aba_acabamento()
        
        # Aba Metas - IGUAL AO ORIGINAL
        self.aba_metas = ttk.Frame(self.notebook_prod)
        self.notebook_prod.add(self.aba_metas, text='🎯 Metas')
        self.configurar_aba_metas()
    
    # ============================================================
    # CONFIGURAR ABA COSTURA - IGUAL AO ORIGINAL
    # ============================================================
    
    def configurar_aba_costura(self, aba, tipo):
        """Configura a aba de costura com seleção múltipla de produtos - IGUAL AO ORIGINAL"""
        main_frame = ttk.Frame(aba)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # GRID PRINCIPAL - Duas colunas
        main_frame.grid_columnconfigure(0, weight=1, uniform="colunas")
        main_frame.grid_columnconfigure(1, weight=1, uniform="colunas")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=3)
        
        # ============================================================
        # COLUNA ESQUERDA - REGISTRO DE PRODUÇÃO
        # ============================================================
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=(0, 5))
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)
        
        entry_frame = ttk.LabelFrame(
            left_frame,
            text=f" Registro de Produção - {tipo.capitalize()} ",
            padding="10"
        )
        entry_frame.grid(row=0, column=0, sticky='nsew')
        
        # Data
        ttk.Label(entry_frame, text="Data:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        date_entry = DateEntry(
            entry_frame,
            width=12,
            background='darkblue',
            foreground='white',
            date_pattern='dd/mm/yyyy'
        )
        date_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.date_entries[tipo] = date_entry
        
        # Ciclo
        ttk.Label(entry_frame, text="Ciclo:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        cycle_entry = ttk.Entry(entry_frame, width=20)
        cycle_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.cycle_entries[tipo] = cycle_entry
        
        # Ordem
        ttk.Label(entry_frame, text="Ordem:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        order_entry = ttk.Entry(entry_frame, width=20)
        order_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.order_entries[tipo] = order_entry
        
        ttk.Button(
            entry_frame,
            text="🔍 Buscar Produtos",
            command=lambda: self.buscar_produtos_multi(tipo)
        ).grid(row=2, column=2, padx=5)
        
        # Frame para lista de produtos
        ttk.Label(entry_frame, text="Produtos (selecione um ou mais):").grid(
            row=3, column=0, padx=5, pady=5, sticky='ne'
        )
        
        # Frame para o Listbox com scrollbar
        listbox_frame = ttk.Frame(entry_frame)
        listbox_frame.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky='ew')
        
        # Criar Listbox com seleção múltipla
        product_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.MULTIPLE,
            height=5,
            width=45,
            bg='white',
            fg=self.cores.AZUL_MAR,
            selectbackground=self.cores.CORAL,
            selectforeground='white'
        )
        product_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        self.product_listboxes[tipo] = product_listbox
        
        # Vincular evento de seleção
        product_listbox.bind('<<ListboxSelect>>', lambda event, t=tipo: self.atualizar_quantidades_selecionados(t))
        
        # Scrollbar para o Listbox
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=product_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        product_listbox.config(yscrollcommand=scrollbar.set)
        
        # Botões para seleção
        btn_select_frame = ttk.Frame(entry_frame)
        btn_select_frame.grid(row=4, column=1, columnspan=2, pady=5)
        
        ttk.Button(
            btn_select_frame,
            text="✅ Selecionar Todos",
            command=lambda: self.selecionar_todos_produtos(tipo)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_select_frame,
            text="❌ Desmarcar Todos",
            command=lambda: self.deselecionar_todos_produtos(tipo)
        ).pack(side=tk.LEFT, padx=5)
        
        # Frame para quantidades por produto selecionado
        ttk.Label(entry_frame, text="Quantidades por Produto:").grid(
            row=5, column=0, padx=5, pady=5, sticky='ne'
        )
        
        # Frame para as entradas de quantidade
        qty_frame = ttk.Frame(entry_frame)
        qty_frame.grid(row=5, column=1, columnspan=2, padx=5, pady=5, sticky='ew')
        self.qty_frames[tipo] = qty_frame
        
        # Label de instruções
        label_instrucao = ttk.Label(
            qty_frame,
            text="🔹 Selecione produtos na lista acima",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        label_instrucao.pack(pady=10)
        self.qty_label[tipo] = label_instrucao
        
        # Botões de ação
        btn_frame = ttk.Frame(entry_frame)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        ttk.Button(
            btn_frame,
            text="➕ Adicionar Todos Selecionados",
            command=lambda: self.adicionar_producao_multipla(tipo)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="🧹 Limpar",
            command=lambda: self.limpar_campos_costura(tipo)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="🗑️ Remover",
            command=lambda: self.remover_registro(tipo)
        ).pack(side=tk.LEFT, padx=5)
        
        # ============================================================
        # COLUNA DIREITA - ESTATÍSTICAS
        # ============================================================
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0), pady=(0, 5))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        
        stats_frame = ttk.LabelFrame(right_frame, text="📊 Estatísticas do Período", padding="10")
        stats_frame.grid(row=0, column=0, sticky='nsew')
        
        tipo_stats = {}
        
        # Total de peças
        ttk.Label(stats_frame, text="Total de Peças:").grid(row=0, column=0, padx=5, pady=3, sticky='e')
        lbl_total = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_total.grid(row=0, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['total'] = lbl_total
        
        # Média diária
        ttk.Label(stats_frame, text="Média Diária:").grid(row=1, column=0, padx=5, pady=3, sticky='e')
        lbl_media = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_media.grid(row=1, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['media'] = lbl_media
        
        # Dias com produção
        ttk.Label(stats_frame, text="Dias com Produção:").grid(row=2, column=0, padx=5, pady=3, sticky='e')
        lbl_dias = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_dias.grid(row=2, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['dias'] = lbl_dias
        
        # Dias úteis
        ttk.Label(stats_frame, text="Dias Úteis no Período:").grid(row=3, column=0, padx=5, pady=3, sticky='e')
        lbl_dias_uteis = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_dias_uteis.grid(row=3, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['dias_uteis'] = lbl_dias_uteis
        
        # Melhor dia
        ttk.Label(stats_frame, text="Melhor Dia:").grid(row=4, column=0, padx=5, pady=3, sticky='e')
        lbl_melhor_dia = ttk.Label(stats_frame, text="-", font=('Arial', 10))
        lbl_melhor_dia.grid(row=4, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['melhor_dia'] = lbl_melhor_dia
        
        # Top produto
        ttk.Label(stats_frame, text="Top Produto:").grid(row=5, column=0, padx=5, pady=3, sticky='e')
        lbl_top_produto = ttk.Label(stats_frame, text="-", font=('Arial', 10))
        lbl_top_produto.grid(row=5, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['top_produto'] = lbl_top_produto
        
        # Meta mensal
        ttk.Label(stats_frame, text="Meta Mensal:").grid(row=6, column=0, padx=5, pady=3, sticky='e')
        lbl_meta = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_meta.grid(row=6, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['meta'] = lbl_meta
        
        # Progresso
        ttk.Label(stats_frame, text="Progresso:").grid(row=7, column=0, padx=5, pady=3, sticky='e')
        lbl_progresso = ttk.Label(stats_frame, text="0%", font=('Arial', 12, 'bold'))
        lbl_progresso.grid(row=7, column=1, padx=5, pady=3, sticky='w')
        tipo_stats['progresso'] = lbl_progresso
        
        self.stats_labels[tipo] = tipo_stats
        
        # ============================================================
        # QUADRO INFERIOR - PRODUÇÃO REGISTRADA
        # ============================================================
        tree_frame = ttk.LabelFrame(
            main_frame,
            text=f" Produção Registrada - {tipo.capitalize()} ",
            padding="10"
        )
        tree_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
        
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill='both', expand=True)
        
        columns = ('Data', 'Ciclo', 'Ordem', 'Produto', 'Referência', 'Quantidade')
        tree = ttk.Treeview(tree_container, columns=columns, show='headings', selectmode='extended')
        self.treeviews[tipo] = tree
        
        col_widths = {'Data': 100, 'Ciclo': 80, 'Ordem': 120,
                    'Produto': 250, 'Referência': 120, 'Quantidade': 100}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), minwidth=50)
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
    
    # ============================================================
    # MÉTODOS DE COSTURA - IGUAIS AO ORIGINAL
    # ============================================================
    
    def buscar_produtos_multi(self, tipo):
        """Busca produtos no banco de dados - IGUAL AO ORIGINAL"""
        cycle = self.cycle_entries[tipo].get().strip()
        order = self.order_entries[tipo].get().strip()
        
        if not cycle or not order:
            messagebox.showwarning("Aviso", "Preencha Ciclo e Ordem de Produção!")
            return
        
        try:
            self.status_bar.config(text="🔍 Buscando produtos...")
            self.parent.update()
            
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            db_config = {
                'host': 'caboose.proxy.rlwy.net',
                'port': 45649,
                'database': 'railway',
                'user': 'postgres',
                'password': 'UWKjEVQAzWDEOcGTOGvqrYChNuyFgrpY'
            }
            
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT DISTINCT 
                    location_product_code, 
                    product_name, 
                    reference_code
                FROM production_items 
                WHERE cycle_code = %s 
                AND order_code = %s
                ORDER BY product_name
                LIMIT 200
            """
            
            cursor.execute(query, (cycle, order))
            results = cursor.fetchall()
            
            product_listbox = self.product_listboxes[tipo]
            product_listbox.delete(0, tk.END)
            
            if tipo in self.last_selection:
                self.last_selection[tipo] = None
            
            if tipo in self.qty_entries_dict:
                self.qty_entries_dict[tipo] = {}
            
            self.product_data[tipo] = {}
            
            if results:
                for row in results:
                    desc = f"{row['product_name']} - Ref: {row['reference_code']}"
                    product_listbox.insert(tk.END, desc)
                    self.product_data[tipo][desc] = {
                        'location_product_code': row['location_product_code'],
                        'product_name': row['product_name'],
                        'reference_code': row['reference_code']
                    }
                
                self.status_bar.config(text=f"✅ Encontrados {len(results)} produtos")
                self.limpar_frame_quantidades(tipo)
            else:
                messagebox.showinfo("Informação", "Nenhum produto encontrado para este ciclo/ordem")
                self.status_bar.config(text="❌ Nenhum produto encontrado")
                self.limpar_frame_quantidades(tipo)
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao conectar ao banco de dados: {str(e)}")
            self.status_bar.config(text="❌ Erro na conexão com o banco de dados")
    
    def criar_widgets_quantidades(self, tipo):
        """Cria widgets de quantidade para cada produto selecionado - IGUAL AO ORIGINAL"""
        self.limpar_frame_quantidades(tipo)
        
        if tipo not in self.product_listboxes:
            return
        
        product_listbox = self.product_listboxes[tipo]
        
        if tipo in self.last_selection and self.last_selection[tipo]:
            selected_indices = self.last_selection[tipo]
        else:
            selected_indices = product_listbox.curselection()
            if selected_indices:
                self.last_selection[tipo] = selected_indices
        
        if not selected_indices:
            label = ttk.Label(
                self.qty_frames[tipo],
                text="🔹 Selecione produtos na lista acima",
                font=('Arial', 9, 'italic'),
                foreground='gray'
            )
            label.pack(pady=10)
            self.qty_label[tipo] = label
            return
        
        if tipo not in self.qty_entries_dict:
            self.qty_entries_dict[tipo] = {}
        
        for idx in selected_indices:
            produto_desc = product_listbox.get(idx)
            
            row_frame = ttk.Frame(self.qty_frames[tipo])
            row_frame.pack(fill='x', pady=2)
            
            nome_curto = produto_desc[:40] + "..." if len(produto_desc) > 40 else produto_desc
            ttk.Label(
                row_frame,
                text=nome_curto,
                font=('Arial', 9),
                width=40,
                anchor='w'
            ).pack(side=tk.LEFT, padx=5)
            
            qty_container = ttk.Frame(row_frame)
            qty_container.pack(side=tk.RIGHT, padx=5)
            
            qty_entry = ttk.Entry(qty_container, width=10)
            qty_entry.pack(side=tk.LEFT, padx=2)
            qty_entry.insert(0, "0")
            
            qty_entry.bind('<Button-1>', lambda e, entry=qty_entry: entry.focus_set())
            qty_entry.bind('<FocusIn>', lambda e, entry=qty_entry: entry.select_range(0, tk.END))
            
            ttk.Button(
                qty_container,
                text="0",
                width=2,
                command=lambda e=qty_entry: self.zerar_quantidade_sem_foco(e)
            ).pack(side=tk.LEFT, padx=2)
            
            ttk.Button(
                qty_container,
                text="+",
                width=2,
                command=lambda e=qty_entry: self.incrementar_quantidade_sem_foco(e)
            ).pack(side=tk.LEFT, padx=2)
            
            self.qty_entries_dict[tipo][produto_desc] = qty_entry
    
    def zerar_quantidade_sem_foco(self, entry):
        """Zera o campo de quantidade sem perder a seleção - IGUAL AO ORIGINAL"""
        entry.delete(0, tk.END)
        entry.insert(0, "0")
    
    def incrementar_quantidade_sem_foco(self, entry):
        """Incrementa a quantidade em 1 sem perder a seleção - IGUAL AO ORIGINAL"""
        try:
            valor = int(entry.get().strip() or "0")
            entry.delete(0, tk.END)
            entry.insert(0, str(valor + 1))
        except ValueError:
            entry.delete(0, tk.END)
            entry.insert(0, "1")
    
    def limpar_frame_quantidades(self, tipo):
        """Limpa o frame de quantidades - IGUAL AO ORIGINAL"""
        for widget in self.qty_frames[tipo].winfo_children():
            widget.destroy()
        
        if tipo in self.qty_entries_dict:
            self.qty_entries_dict[tipo] = {}
    
    def selecionar_todos_produtos(self, tipo):
        """Seleciona todos os produtos no listbox - IGUAL AO ORIGINAL"""
        product_listbox = self.product_listboxes[tipo]
        product_listbox.selection_set(0, tk.END)
        self.last_selection[tipo] = product_listbox.curselection()
        self.criar_widgets_quantidades(tipo)
    
    def deselecionar_todos_produtos(self, tipo):
        """Desmarca todos os produtos no listbox - IGUAL AO ORIGINAL"""
        product_listbox = self.product_listboxes[tipo]
        product_listbox.selection_clear(0, tk.END)
        if tipo in self.last_selection:
            self.last_selection[tipo] = ()
        self.limpar_frame_quantidades(tipo)
        label = ttk.Label(
            self.qty_frames[tipo],
            text="🔹 Selecione produtos na lista acima",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        label.pack(pady=10)
        self.qty_label[tipo] = label
    
    def atualizar_quantidades_selecionados(self, tipo):
        """Atualiza os widgets de quantidade quando a seleção muda - IGUAL AO ORIGINAL"""
        if tipo not in self.product_listboxes:
            return
        
        product_listbox = self.product_listboxes[tipo]
        current_selection = product_listbox.curselection()
        
        if not current_selection and tipo in self.last_selection and self.last_selection[tipo]:
            focus_widget = self.parent.focus_get()
            if focus_widget:
                parent = focus_widget
                while parent:
                    if parent == self.qty_frames[tipo]:
                        return
                    parent = parent.master
        
        if tipo in self.last_selection and self.last_selection[tipo] == current_selection:
            return
        
        self.last_selection[tipo] = current_selection
        self.criar_widgets_quantidades(tipo)
    
    def adicionar_producao_multipla(self, tipo):
        """Adiciona produção para múltiplos produtos selecionados - IGUAL AO ORIGINAL"""
        if tipo not in self.last_selection or not self.last_selection[tipo]:
            product_listbox = self.product_listboxes[tipo]
            selected_indices = product_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("Aviso", "Selecione pelo menos um produto!")
                return
        else:
            selected_indices = self.last_selection[tipo]
            product_listbox = self.product_listboxes[tipo]
        
        if tipo not in self.qty_entries_dict or not self.qty_entries_dict[tipo]:
            messagebox.showwarning("Aviso", "Defina as quantidades para cada produto!")
            return
        
        data_producao = self.date_entries[tipo].get_date().strftime("%Y-%m-%d")
        ciclo = self.cycle_entries[tipo].get()
        ordem = self.order_entries[tipo].get()
        
        if not ciclo or not ordem:
            messagebox.showwarning("Aviso", "Preencha Ciclo e Ordem de Produção!")
            return
        
        if self.periodo_atual:
            data_dt = datetime.strptime(data_producao, "%Y-%m-%d")
            if data_dt < self.periodo_atual[0] or data_dt > self.periodo_atual[1]:
                messagebox.showwarning(
                    "Aviso",
                    f"Data {data_producao} está fora do período atual!\n"
                    f"Período: {self.periodo_atual[0].strftime('%d/%m/%Y')} a {self.periodo_atual[1].strftime('%d/%m/%Y')}"
                )
                return
        
        qty_entries = self.qty_entries_dict[tipo]
        registros_adicionados = 0
        produtos_com_quantidade = []
        
        for idx in selected_indices:
            produto_desc = product_listbox.get(idx)
            if produto_desc in qty_entries:
                try:
                    quantidade_str = qty_entries[produto_desc].get().strip() or "0"
                    quantidade = int(quantidade_str)
                    if quantidade > 0:
                        produto_info = self.product_data[tipo].get(produto_desc, {})
                        
                        registro = {
                            'data': data_producao,
                            'ciclo': ciclo,
                            'ordem': ordem,
                            'produto': produto_info.get('product_name', produto_desc),
                            'referencia': produto_info.get('reference_code', ''),
                            'codigo': produto_info.get('location_product_code', ''),
                            'quantidade': quantidade,
                            'tipo': tipo
                        }
                        
                        self.monthly_data[tipo].append(registro)
                        registros_adicionados += 1
                        produtos_com_quantidade.append(produto_desc)
                except ValueError:
                    continue
        
        if registros_adicionados == 0:
            messagebox.showwarning("Aviso", "Nenhuma quantidade válida informada!\nInforme valores maiores que 0.")
            return
        
        self.ordenar_dados_por_data(tipo)
        self.recarregar_treeview(tipo)
        
        self.status_bar.config(
            text=f"✅ {registros_adicionados} produtos adicionados - {tipo.capitalize()} em {data_producao}"
        )
        
        self.atualizar_todas_estatisticas()
        self.salvar_producao()
        
        # Avançar para próxima data
        if self.periodo_atual:
            data_atual = datetime.strptime(data_producao, "%Y-%m-%d")
            proxima_data = self.encontrar_proximo_dia_util(data_atual + timedelta(days=1), self.periodo_atual[1])
            if proxima_data:
                self.date_entries[tipo].set_date(proxima_data)
        
        # LIMPAR CAMPOS E FOCAR NO CICLO - IGUAL AO ORIGINAL
        for produto_desc in produtos_com_quantidade:
            if produto_desc in qty_entries:
                qty_entries[produto_desc].delete(0, tk.END)
                qty_entries[produto_desc].insert(0, "0")
        
        self.cycle_entries[tipo].delete(0, tk.END)
        self.order_entries[tipo].delete(0, tk.END)
        
        try:
            product_listbox.selection_clear(0, tk.END)
            self.last_selection[tipo] = ()
        except:
            pass
        
        self.limpar_frame_quantidades(tipo)
        
        label = ttk.Label(
            self.qty_frames[tipo],
            text="🔹 Selecione produtos na lista acima",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        label.pack(pady=10)
        self.qty_label[tipo] = label
        
        self.cycle_entries[tipo].focus_set()
    
    def limpar_campos_costura(self, tipo):
        """Limpa os campos da aba de costura - IGUAL AO ORIGINAL"""
        self.cycle_entries[tipo].delete(0, tk.END)
        self.order_entries[tipo].delete(0, tk.END)
        
        product_listbox = self.product_listboxes[tipo]
        product_listbox.delete(0, tk.END)
        
        self.limpar_frame_quantidades(tipo)
        
        if tipo in self.product_data:
            self.product_data[tipo] = {}
    
    # ============================================================
    # CONFIGURAR ABA ACABAMENTO - IGUAL AO ORIGINAL
    # ============================================================
    
    def configurar_aba_acabamento(self):
        """Configura a aba de acabamento com estatísticas individuais por colaborador - IGUAL AO ORIGINAL"""
        main_frame = ttk.Frame(self.aba_acabamento)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        main_frame.grid_columnconfigure(0, weight=1, uniform="colunas")
        main_frame.grid_columnconfigure(1, weight=1, uniform="colunas")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=3)
        
        # ============================================================
        # COLUNA ESQUERDA - COLABORADORES E REGISTRO
        # ============================================================
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, rowspan=2, sticky='nsew', padx=(0, 5))
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=3)
        
        # Frame de colaboradores
        collab_frame = ttk.LabelFrame(left_frame, text=" 👥 Gerenciar Colaboradores ", padding="10")
        collab_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        ttk.Button(collab_frame, text="➕ Adicionar", command=self.adicionar_colaborador).pack(side=tk.LEFT, padx=5)
        ttk.Button(collab_frame, text="➖ Remover", command=self.remover_colaborador).pack(side=tk.LEFT, padx=5)
        
        # Frame de registro
        registro_frame = ttk.LabelFrame(left_frame, text=" ✨ Registro de Produção - Acabamento ", padding="10")
        registro_frame.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        
        # Data
        ttk.Label(registro_frame, text="Data:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.date_acabamento = DateEntry(
            registro_frame,
            width=12,
            background='darkblue',
            foreground='white',
            date_pattern='dd/mm/yyyy'
        )
        self.date_acabamento.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Colaborador
        ttk.Label(registro_frame, text="Colaborador:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.colab_combobox = ttk.Combobox(registro_frame, width=30, state='readonly')
        self.colab_combobox.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='w')
        self.colab_combobox.bind('<<ComboboxSelected>>', self.on_colaborador_selected)
        
        # Quantidade de Biquíni
        ttk.Label(registro_frame, text="Qtd. Biquíni:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.qty_biquini = ttk.Entry(registro_frame, width=15)
        self.qty_biquini.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.qty_biquini.insert(0, "")
        
        # Quantidade de Roupa
        ttk.Label(registro_frame, text="Qtd. Roupa:").grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.qty_roupa = ttk.Entry(registro_frame, width=15)
        self.qty_roupa.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        self.qty_roupa.insert(0, "")
        
        # Quantidade de Acessórios
        ttk.Label(registro_frame, text="Qtd. Acessórios:").grid(row=4, column=0, padx=5, pady=5, sticky='e')
        self.qty_acessorios = ttk.Entry(registro_frame, width=15)
        self.qty_acessorios.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        self.qty_acessorios.insert(0, "")
        
        # Botões
        btn_frame = ttk.Frame(registro_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="✨ Registrar", command=self.registrar_acabamento).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 Falta/Atestado", command=self.registrar_falta_atestado).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🧹 Limpar", command=self.limpar_campos_acabamento).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Remover", command=lambda: self.remover_registro('acabamento')).pack(side=tk.LEFT, padx=5)
        
        # ============================================================
        # COLUNA DIREITA - ESTATÍSTICAS
        # ============================================================
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, rowspan=2, sticky='nsew', padx=(5, 0))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # Estatísticas gerais
        stats_frame = ttk.LabelFrame(right_frame, text="📊 Estatísticas Gerais", padding="5")
        stats_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        
        self.stats_labels['acabamento'] = {}
        
        ttk.Label(stats_frame, text="Total de Peças:").grid(row=0, column=0, padx=5, pady=3, sticky='e')
        lbl_total = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_total.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['acabamento']['total'] = lbl_total
        
        ttk.Label(stats_frame, text="Média Diária:").grid(row=1, column=0, padx=5, pady=3, sticky='e')
        lbl_media = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_media.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['acabamento']['media'] = lbl_media
        
        ttk.Label(stats_frame, text="Dias com Produção:").grid(row=2, column=0, padx=5, pady=3, sticky='e')
        lbl_dias = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_dias.grid(row=2, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['acabamento']['dias'] = lbl_dias
        
        ttk.Label(stats_frame, text="Meta Mensal:").grid(row=3, column=0, padx=5, pady=3, sticky='e')
        lbl_meta = ttk.Label(stats_frame, text="0", font=('Arial', 12, 'bold'))
        lbl_meta.grid(row=3, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['acabamento']['meta'] = lbl_meta
        
        ttk.Label(stats_frame, text="Progresso:").grid(row=4, column=0, padx=5, pady=3, sticky='e')
        lbl_progresso = ttk.Label(stats_frame, text="0%", font=('Arial', 12, 'bold'))
        lbl_progresso.grid(row=4, column=1, padx=5, pady=2, sticky='w')
        self.stats_labels['acabamento']['progresso'] = lbl_progresso
        
        # Estatísticas por colaborador
        colab_stats_frame = ttk.LabelFrame(right_frame, text="📊 Estatísticas por Colaborador", padding="5")
        colab_stats_frame.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        
        stats_container = ttk.Frame(colab_stats_frame)
        stats_container.pack(fill='both', expand=True)
        
        col_columns = ('Colaborador', 'Total', 'Biquíni', 'Roupa', 'Acessórios',
                      'Média/Dia', 'Dias Trab.', 'Faltas', 'Atestados', 'Presença')
        self.colab_stats_tree = ttk.Treeview(stats_container, columns=col_columns,
                                            show='headings', height=3)
        
        col_widths = {'Colaborador': 120, 'Total': 80, 'Biquíni': 80, 'Roupa': 80,
                     'Acessórios': 80, 'Média/Dia': 80, 'Dias Trab.': 80,
                     'Faltas': 70, 'Atestados': 80, 'Presença': 80}
        for col in col_columns:
            self.colab_stats_tree.heading(col, text=col)
            self.colab_stats_tree.column(col, width=col_widths.get(col, 80))
        
        scrollbar_stats = ttk.Scrollbar(stats_container, orient=tk.VERTICAL,
                                       command=self.colab_stats_tree.yview)
        self.colab_stats_tree.configure(yscrollcommand=scrollbar_stats.set)
        
        self.colab_stats_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_stats.grid(row=0, column=1, sticky='ns')
        stats_container.grid_rowconfigure(0, weight=1)
        stats_container.grid_columnconfigure(0, weight=1)
        
        # ============================================================
        # QUADRO INFERIOR - REGISTROS DE ACABAMENTO
        # ============================================================
        tree_frame = ttk.LabelFrame(main_frame, text=" 📋 Registros de Acabamento ", padding="10")
        tree_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
        
        registros_container = ttk.Frame(tree_frame)
        registros_container.pack(fill='both', expand=True)
        
        columns = ('Data', 'Colaborador', 'Qtd. Biquíni', 'Qtd. Roupa',
                  'Qtd. Acessórios', 'Total', 'Justificativa')
        tree = ttk.Treeview(registros_container, columns=columns, show='headings', selectmode='extended')
        
        col_widths = {'Data': 100, 'Colaborador': 180, 'Qtd. Biquíni': 110,
                     'Qtd. Roupa': 100, 'Qtd. Acessórios': 110, 'Total': 80, 'Justificativa': 120}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), minwidth=50)
        
        scrollbar_y = ttk.Scrollbar(registros_container, orient=tk.VERTICAL, command=tree.yview)
        scrollbar_x = ttk.Scrollbar(registros_container, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        registros_container.grid_rowconfigure(0, weight=1)
        registros_container.grid_columnconfigure(0, weight=1)
        
        self.treeviews['acabamento'] = tree        
        # Atualizar colaboradores
        self.atualizar_combo_colaboradores()
    
    # ============================================================
    # MÉTODOS DE ACABAMENTO - IGUAIS AO ORIGINAL
    # ============================================================
    
    def registrar_acabamento(self):
        """Registra produção de acabamento - IGUAL AO ORIGINAL"""
        colaborador = self.colab_combobox.get()
        
        if not colaborador:
            messagebox.showwarning("Aviso", "Selecione um colaborador!")
            return
        
        qtd_biquini = self.avaliar_expressao_matematica(self.qty_biquini.get())
        qtd_roupa = self.avaliar_expressao_matematica(self.qty_roupa.get())
        qtd_acessorios = self.avaliar_expressao_matematica(self.qty_acessorios.get())
        
        if qtd_biquini is None or qtd_roupa is None or qtd_acessorios is None:
            messagebox.showwarning("Aviso", "Expressão matemática inválida!")
            return
        
        if qtd_biquini < 0 or qtd_roupa < 0 or qtd_acessorios < 0:
            messagebox.showwarning("Aviso", "Quantidades não podem ser negativas!")
            return
        
        if qtd_biquini == 0 and qtd_roupa == 0 and qtd_acessorios == 0:
            messagebox.showwarning("Aviso", "Informe pelo menos uma quantidade!")
            return
        
        data_producao = self.date_acabamento.get_date().strftime("%Y-%m-%d")
        
        if self.periodo_atual:
            data_dt = datetime.strptime(data_producao, "%Y-%m-%d")
            if data_dt < self.periodo_atual[0] or data_dt > self.periodo_atual[1]:
                messagebox.showwarning(
                    "Aviso",
                    f"Data {data_producao} está fora do período atual!\n"
                    f"Período: {self.periodo_atual[0].strftime('%d/%m/%Y')} a {self.periodo_atual[1].strftime('%d/%m/%Y')}"
                )
                return
        
        # Verificar se já existe registro
        for registro in self.monthly_data['acabamento']:
            if registro.get('colaborador') == colaborador and registro.get('data') == data_producao:
                messagebox.showwarning(
                    "Aviso",
                    f"Colaborador {colaborador} já possui registro na data {data_producao}!"
                )
                return
        
        total = qtd_biquini + qtd_roupa + qtd_acessorios
        
        registro = {
            'data': data_producao,
            'colaborador': colaborador,
            'qtd_biquini': qtd_biquini,
            'qtd_roupa': qtd_roupa,
            'qtd_acessorios': qtd_acessorios,
            'total': total,
            'ausencia': None,
            'justificativa': ''
        }
        
        self.monthly_data['acabamento'].append(registro)
        self.ordenar_dados_por_data('acabamento')
        self.recarregar_treeview('acabamento')
        
        self.limpar_campos_acabamento()
        
        if self.periodo_atual:
            data_atual = datetime.strptime(data_producao, "%Y-%m-%d")
            proxima_data = self.encontrar_proximo_dia_util(data_atual + timedelta(days=1), self.periodo_atual[1])
            if proxima_data:
                self.date_acabamento.set_date(proxima_data)
        
        if colaborador in self.colaboradores:
            self.colab_combobox.set(colaborador)
        
        self.qty_biquini.focus_set()
        self.qty_biquini.select_range(0, tk.END)
        
        self.status_bar.config(
            text=f"✅ Produção registrada - {colaborador}: Total {total} peças em {data_producao}"
        )
        
        self.atualizar_todas_estatisticas()
        self.on_colaborador_selected(None)
        self.salvar_producao()
    
    def registrar_falta_atestado(self):
        """Registra falta ou atestado para um colaborador - IGUAL AO ORIGINAL"""
        colaborador = self.colab_combobox.get()
        
        if not colaborador:
            messagebox.showwarning("Aviso", "Selecione um colaborador!")
            return
        
        data_producao = self.date_acabamento.get_date()
        data_str = data_producao.strftime("%Y-%m-%d")
        
        # Verificar se já existe registro
        for registro in self.monthly_data['acabamento']:
            if registro.get('colaborador') == colaborador and registro.get('data') == data_str:
                messagebox.showwarning(
                    "Aviso",
                    f"Colaborador {colaborador} já possui registro na data {data_str}!"
                )
                return
        
        # Verificar se é dia útil
        if not self.eh_dia_util(data_producao):
            messagebox.showwarning(
                "Aviso",
                "Não é possível registrar falta/atestado em feriados ou fins de semana!"
            )
            return
        
        # Abrir diálogo para escolher o tipo
        dialog = DialogoFaltaAtestado(self.parent, colaborador, data_producao)
        self.parent.wait_window(dialog.dialog)
        tipo = dialog.resultado
        
        if not tipo:
            return
        
        # Criar registro de ausência
        registro = {
            'data': data_str,
            'colaborador': colaborador,
            'qtd_biquini': 0,
            'qtd_roupa': 0,
            'qtd_acessorios': 0,
            'total': 0,
            'ausencia': tipo,
            'justificativa': 'Falta' if tipo == 'falta' else 'Atestado'
        }
        
        self.monthly_data['acabamento'].append(registro)
        self.ordenar_dados_por_data('acabamento')
        self.recarregar_treeview('acabamento')
        
        if self.periodo_atual:
            proxima_data = self.encontrar_proximo_dia_util(
                data_producao + timedelta(days=1),
                self.periodo_atual[1]
            )
            if proxima_data:
                self.date_acabamento.set_date(proxima_data)
        
        if colaborador in self.colaboradores:
            self.colab_combobox.set(colaborador)
        
        self.qty_biquini.focus_set()
        self.qty_biquini.select_range(0, tk.END)
        
        status_text = f"✅ {tipo.capitalize()} registrada para {colaborador} em {data_producao.strftime('%d/%m/%Y')}"
        self.status_bar.config(text=status_text)
        
        self.atualizar_todas_estatisticas()
        self.salvar_producao()
    
    def limpar_campos_acabamento(self):
        """Limpa os campos da aba de acabamento - IGUAL AO ORIGINAL"""
        self.qty_biquini.delete(0, tk.END)
        self.qty_biquini.insert(0, "")
        self.qty_roupa.delete(0, tk.END)
        self.qty_roupa.insert(0, "")
        self.qty_acessorios.delete(0, tk.END)
        self.qty_acessorios.insert(0, "")
    
    def atualizar_combo_colaboradores(self):
        """Atualiza a combobox de colaboradores - IGUAL AO ORIGINAL"""
        self.colab_combobox['values'] = sorted(self.colaboradores)
        if self.colaboradores:
            self.colab_combobox.set(sorted(self.colaboradores)[0])
    
    def adicionar_colaborador(self):
        """Adiciona um novo colaborador - IGUAL AO ORIGINAL"""
        nome = simpledialog.askstring("Adicionar Colaborador", "Nome do colaborador:")
        if nome and nome.strip():
            nome = nome.strip()
            if nome not in self.colaboradores:
                self.colaboradores.append(nome)
                self.db_local.salvar_colaborador(nome)
                self.atualizar_combo_colaboradores()
                self.status_bar.config(text=f"✅ Colaborador {nome} adicionado")
            else:
                messagebox.showwarning("Aviso", "Colaborador já existe!")
    
    def remover_colaborador(self):
        """Remove um colaborador - IGUAL AO ORIGINAL"""
        selecionado = self.colab_combobox.get()
        if selecionado and selecionado in self.colaboradores:
            if messagebox.askyesno("Confirmar", f"Remover {selecionado}?"):
                self.colaboradores.remove(selecionado)
                self.db_local.remover_colaborador(selecionado)
                self.atualizar_combo_colaboradores()
    
    def on_colaborador_selected(self, event):
        """Evento quando um colaborador é selecionado - IGUAL AO ORIGINAL"""
        colaborador = self.colab_combobox.get()
        if colaborador and self.periodo_atual:
            inicio_mes, fim_mes = self.periodo_atual
            
            ultima_data = None
            for registro in self.monthly_data['acabamento']:
                if registro['colaborador'] == colaborador:
                    data_reg = datetime.strptime(registro['data'], '%Y-%m-%d')
                    if ultima_data is None or data_reg > ultima_data:
                        ultima_data = data_reg
            
            if ultima_data:
                proxima_data = ultima_data + timedelta(days=1)
                while proxima_data <= fim_mes:
                    if self.eh_dia_util(proxima_data):
                        self.date_acabamento.set_date(proxima_data)
                        break
                    proxima_data += timedelta(days=1)
                else:
                    self.date_acabamento.set_date(ultima_data)
            else:
                data_atual = inicio_mes
                while data_atual <= fim_mes:
                    if self.eh_dia_util(data_atual):
                        self.date_acabamento.set_date(data_atual)
                        break
                    data_atual += timedelta(days=1)
                else:
                    self.date_acabamento.set_date(inicio_mes)
    
    # ============================================================
    # MÉTODOS DE MANIPULAÇÃO DE DADOS - IGUAIS AO ORIGINAL
    # ============================================================
    
    def ordenar_dados_por_data(self, tipo):
        """Ordena dados por data - IGUAL AO ORIGINAL"""
        if self.monthly_data[tipo]:
            self.monthly_data[tipo] = sorted(
                self.monthly_data[tipo],
                key=lambda x: x.get('data', '')
            )
    
    def recarregar_treeview(self, tipo):
        """Recarrega a treeview com os dados atuais - IGUAL AO ORIGINAL"""
        tree = self.treeviews[tipo]
        
        for item in tree.get_children():
            tree.delete(item)
        
        for record in self.monthly_data[tipo]:
            if tipo == 'acabamento':
                ausencia = record.get('ausencia')
                is_ausencia = ausencia is not None and str(ausencia).lower() not in ['none', 'nan', '']
                
                nome_colaborador = record.get('colaborador', '')
                if is_ausencia and str(ausencia).lower() == 'falta':
                    nome_colaborador = f"❌ {nome_colaborador}"
                elif is_ausencia and str(ausencia).lower() == 'atestado':
                    nome_colaborador = f"📄 {nome_colaborador}"
                
                justificativa = ''
                if is_ausencia:
                    justificativa = record.get('justificativa', '')
                    if not justificativa:
                        justificativa = 'Falta' if str(ausencia).lower() == 'falta' else 'Atestado'
                
                tree.insert('', 'end', values=(
                    record.get('data', ''),
                    nome_colaborador,
                    record.get('qtd_biquini', 0),
                    record.get('qtd_roupa', 0),
                    record.get('qtd_acessorios', 0),
                    record.get('total', 0),
                    justificativa
                ))
            else:
                tree.insert('', 'end', values=(
                    record.get('data', ''),
                    record.get('ciclo', ''),
                    record.get('ordem', ''),
                    record.get('produto', ''),
                    record.get('referencia', ''),
                    record.get('quantidade', 0)
                ))
        
        self.atualizar_estatisticas_grupo(tipo)
        
        if tipo == 'acabamento':
            self.atualizar_estatisticas_colaboradores()
    
    def remover_registro(self, tipo):
        """Remove registros selecionados - IGUAL AO ORIGINAL"""
        tree = self.treeviews[tipo]
        selected_items = tree.selection()
        
        if not selected_items:
            messagebox.showwarning("Aviso", "Selecione um ou mais registros para remover!")
            return
        
        if not messagebox.askyesno("Confirmar", f"Remover {len(selected_items)} registro(s)?"):
            return
        
        indices_remover = []
        
        for item in selected_items:
            valores = tree.item(item)['values']
            
            if tipo == 'acabamento':
                data = valores[0]
                nome_com_icone = valores[1]
                nome_limpo = self.limpar_icone_colaborador(nome_com_icone)
                qtd_biquini = valores[2]
                qtd_roupa = valores[3]
                qtd_acessorios = valores[4]
                total = valores[5]
                justificativa = valores[6] if len(valores) > 6 else ''
                
                for i, registro in enumerate(self.monthly_data[tipo]):
                    if (registro.get('data', '') == data and
                        registro.get('colaborador', '') == nome_limpo and
                        registro.get('qtd_biquini', 0) == qtd_biquini and
                        registro.get('qtd_roupa', 0) == qtd_roupa and
                        registro.get('qtd_acessorios', 0) == qtd_acessorios and
                        registro.get('total', 0) == total):
                        
                        if justificativa:
                            ausencia = registro.get('ausencia', '')
                            if ausencia == 'falta' and justificativa == 'Falta':
                                indices_remover.append(i)
                                break
                            elif ausencia == 'atestado' and justificativa == 'Atestado':
                                indices_remover.append(i)
                                break
                        else:
                            if not registro.get('ausencia'):
                                indices_remover.append(i)
                                break
            
            else:
                data = valores[0]
                ciclo = valores[1]
                ordem = valores[2]
                produto = valores[3]
                referencia = valores[4]
                quantidade = valores[5]
                
                for i, registro in enumerate(self.monthly_data[tipo]):
                    if (registro.get('data', '') == data and
                        registro.get('ciclo', '') == ciclo and
                        registro.get('ordem', '') == ordem and
                        registro.get('produto', '') == produto and
                        registro.get('referencia', '') == referencia and
                        registro.get('quantidade', 0) == quantidade):
                        indices_remover.append(i)
                        break
        
        for i in sorted(indices_remover, reverse=True):
            del self.monthly_data[tipo][i]
        
        self.ordenar_dados_por_data(tipo)
        self.recarregar_treeview(tipo)
        
        self.status_bar.config(text=f"🗑️ {len(selected_items)} registro(s) removido(s)")
        
        self.atualizar_todas_estatisticas()
        self.atualizar_sugestao_datas()
        self.salvar_producao()
    
    def limpar_icone_colaborador(self, texto):
        """Remove ícones do nome do colaborador - IGUAL AO ORIGINAL"""
        if not texto:
            return texto
        
        icones = ['❌ ', '📄 ', '❌', '📄']
        for icone in icones:
            if texto.startswith(icone):
                return texto[len(icone):].strip()
        
        return texto.strip()
    
    # ============================================================
    # MÉTODOS DE ATUALIZAÇÃO DE DATAS - IGUAIS AO ORIGINAL
    # ============================================================
    
    def atualizar_sugestao_datas(self):
        """Atualiza as datas sugeridas nas abas - IGUAL AO ORIGINAL"""
        if not self.periodo_atual:
            return
        
        inicio_mes, fim_mes = self.periodo_atual
        
        for tipo in ['biquini', 'roupa']:
            if tipo in self.date_entries:
                ultima_data = self.obter_ultima_data_grupo(tipo)
                if ultima_data:
                    proxima_data = self.encontrar_proximo_dia_util(ultima_data + timedelta(days=1), fim_mes)
                    if proxima_data:
                        self.date_entries[tipo].set_date(proxima_data)
                    else:
                        self.date_entries[tipo].set_date(fim_mes)
                else:
                    data_atual = inicio_mes
                    while data_atual <= fim_mes:
                        if self.eh_dia_util(data_atual):
                            self.date_entries[tipo].set_date(data_atual)
                            break
                        data_atual += timedelta(days=1)
        
        if hasattr(self, 'date_acabamento') and self.colaboradores:
            self.colab_combobox.set(self.colaboradores[0])
            self.on_colaborador_selected(None)
        elif hasattr(self, 'date_acabamento'):
            data_atual = inicio_mes
            while data_atual <= fim_mes:
                if self.eh_dia_util(data_atual):
                    self.date_acabamento.set_date(data_atual)
                    break
                data_atual += timedelta(days=1)
    
    def obter_ultima_data_grupo(self, tipo):
        """Obtém a última data de produção de um grupo - IGUAL AO ORIGINAL"""
        if not self.monthly_data[tipo]:
            return None
        
        ultima_data = None
        for registro in self.monthly_data[tipo]:
            data_reg = datetime.strptime(registro['data'], '%Y-%m-%d')
            if ultima_data is None or data_reg > ultima_data:
                ultima_data = data_reg
        
        return ultima_data
    
    def encontrar_proximo_dia_util(self, data_inicio, data_fim):
        """Encontra o próximo dia útil a partir de uma data - IGUAL AO ORIGINAL"""
        data_atual = data_inicio
        while data_atual <= data_fim:
            if self.eh_dia_util(data_atual):
                return data_atual
            data_atual += timedelta(days=1)
        return None
    
    # ============================================================
    # MÉTODOS DE ESTATÍSTICAS - IGUAIS AO ORIGINAL
    # ============================================================
    
    def atualizar_todas_estatisticas(self):
        """Atualiza todas as estatísticas - IGUAL AO ORIGINAL"""
        for grupo in ['biquini', 'roupa', 'acabamento']:
            self.atualizar_estatisticas_grupo(grupo)
        
        if hasattr(self, 'colab_stats_tree'):
            self.atualizar_estatisticas_colaboradores()
        
        self.parent.update_idletasks()
    
    def atualizar_estatisticas_grupo(self, tipo):
        """Atualiza as estatísticas de um grupo específico - IGUAL AO ORIGINAL"""
        if tipo not in self.stats_labels:
            return
        
        stats = self.stats_labels[tipo]
        dados = self.monthly_data[tipo]
        
        if tipo == 'acabamento':
            total = 0
            dias_producao = set()
            
            for registro in dados:
                ausencia = registro.get('ausencia')
                if ausencia is not None and str(ausencia).lower() not in ['none', 'nan', '']:
                    continue
                else:
                    total += registro.get('total', 0)
                    data = registro.get('data', '')
                    if data:
                        dias_producao.add(data)
            
            dias_prod = len(dias_producao)
        else:
            total = sum(r.get('quantidade', 0) for r in dados)
            dias_producao = set()
            for r in dados:
                data = r.get('data', '')
                if data:
                    dias_producao.add(data)
            dias_prod = len(dias_producao)
        
        if 'total' in stats:
            stats['total'].config(text=str(total))
        
        if 'media' in stats:
            if dias_prod > 0:
                media = total / dias_prod
                stats['media'].config(text=f"{media:.1f}")
            else:
                stats['media'].config(text="0")
        
        if 'dias' in stats:
            stats['dias'].config(text=str(dias_prod))
        
        if 'dias_uteis' in stats:
            if self.periodo_atual:
                dias_uteis = self.calcular_dias_uteis(self.periodo_atual[0], self.periodo_atual[1])
                stats['dias_uteis'].config(text=str(dias_uteis))
            else:
                stats['dias_uteis'].config(text="0")
        
        if 'melhor_dia' in stats:
            producao_por_dia = {}
            if tipo == 'acabamento':
                for registro in dados:
                    ausencia = registro.get('ausencia')
                    if ausencia is not None and str(ausencia).lower() not in ['none', 'nan', '']:
                        continue
                    data = registro.get('data', '')
                    total_dia = registro.get('total', 0)
                    if data:
                        producao_por_dia[data] = producao_por_dia.get(data, 0) + total_dia
            else:
                for r in dados:
                    data = r.get('data', '')
                    qtd = r.get('quantidade', 0)
                    if data:
                        producao_por_dia[data] = producao_por_dia.get(data, 0) + qtd
            
            if producao_por_dia:
                melhor_dia = max(producao_por_dia.items(), key=lambda x: x[1])
                stats['melhor_dia'].config(text=f"{melhor_dia[0]} ({melhor_dia[1]} peças)")
            else:
                stats['melhor_dia'].config(text="-")
        
        if 'top_produto' in stats:
            if tipo == 'acabamento':
                colab_total = {}
                for registro in dados:
                    ausencia = registro.get('ausencia')
                    if ausencia is not None and str(ausencia).lower() not in ['none', 'nan', '']:
                        continue
                    colaborador = registro.get('colaborador', '')
                    total_dia = registro.get('total', 0)
                    if colaborador:
                        colab_total[colaborador] = colab_total.get(colaborador, 0) + total_dia
                
                if colab_total:
                    top_colab = max(colab_total.items(), key=lambda x: x[1])
                    stats['top_produto'].config(text=f"{top_colab[0]} ({top_colab[1]} peças)")
                else:
                    stats['top_produto'].config(text="-")
            else:
                produto_quantidade = {}
                for r in dados:
                    produto = r.get('produto', '')
                    qtd = r.get('quantidade', 0)
                    if produto:
                        produto_quantidade[produto] = produto_quantidade.get(produto, 0) + qtd
                
                if produto_quantidade:
                    top_produto = max(produto_quantidade.items(), key=lambda x: x[1])
                    nome = top_produto[0]
                    if len(nome) > 30:
                        nome = nome[:27] + "..."
                    stats['top_produto'].config(text=f"{nome} ({top_produto[1]} peças)")
                else:
                    stats['top_produto'].config(text="-")
        
        if 'meta' in stats:
            meta = self.calcular_meta_mensal(tipo)
            stats['meta'].config(text=str(meta))
        
        if 'progresso' in stats:
            meta = self.calcular_meta_mensal(tipo)
            if meta > 0:
                progresso = (total / meta) * 100
                stats['progresso'].config(text=f"{progresso:.1f}%")
                if progresso >= 100:
                    stats['progresso'].config(foreground='green')
                elif progresso >= 75:
                    stats['progresso'].config(foreground='orange')
                else:
                    stats['progresso'].config(foreground='red')
            else:
                stats['progresso'].config(text="0%")
    
    def atualizar_estatisticas_colaboradores(self):
        """Atualiza a treeview de estatísticas por colaborador do acabamento - IGUAL AO ORIGINAL"""
        if not hasattr(self, 'colab_stats_tree'):
            return
        
        for item in self.colab_stats_tree.get_children():
            self.colab_stats_tree.delete(item)
        
        dados = self.monthly_data['acabamento']
        
        if not dados:
            return
        
        if self.periodo_atual:
            dias_uteis_total = self.calcular_dias_uteis(self.periodo_atual[0], self.periodo_atual[1])
        else:
            dias_uteis_total = 22
        
        stats_colab = {}
        
        for registro in dados:
            colaborador = registro.get('colaborador', '')
            if not colaborador:
                continue
            
            if colaborador not in stats_colab:
                stats_colab[colaborador] = {
                    'total_pecas': 0,
                    'biquini': 0,
                    'roupa': 0,
                    'acessorios': 0,
                    'dias_producao': 0,
                    'faltas': 0,
                    'atestados': 0,
                    'dias_ausencia': 0
                }
            
            ausencia = registro.get('ausencia')
            if ausencia is not None and str(ausencia).lower() not in ['none', 'nan', '']:
                if str(ausencia).lower() == 'falta':
                    stats_colab[colaborador]['faltas'] += 1
                elif str(ausencia).lower() == 'atestado':
                    stats_colab[colaborador]['atestados'] += 1
                stats_colab[colaborador]['dias_ausencia'] += 1
            else:
                qtd_biquini = registro.get('qtd_biquini', 0)
                qtd_roupa = registro.get('qtd_roupa', 0)
                qtd_acessorios = registro.get('qtd_acessorios', 0)
                total = registro.get('total', 0)
                
                stats_colab[colaborador]['total_pecas'] += total
                stats_colab[colaborador]['biquini'] += qtd_biquini
                stats_colab[colaborador]['roupa'] += qtd_roupa
                stats_colab[colaborador]['acessorios'] += qtd_acessorios
                stats_colab[colaborador]['dias_producao'] += 1
        
        for colaborador, stats in stats_colab.items():
            total_pecas = stats['total_pecas']
            dias_producao = stats['dias_producao']
            
            media = total_pecas / dias_producao if dias_producao > 0 else 0
            dias_trabalhados = dias_producao
            presenca = (dias_trabalhados / dias_uteis_total * 100) if dias_uteis_total > 0 else 0
            
            self.colab_stats_tree.insert('', 'end', values=(
                colaborador,
                total_pecas,
                stats['biquini'],
                stats['roupa'],
                stats['acessorios'],
                f"{media:.1f}",
                dias_trabalhados,
                stats['faltas'],
                stats['atestados'],
                f"{presenca:.0f}%"
            ))
    
    # ============================================================
    # CONFIGURAR ABA METAS - IGUAL AO ORIGINAL
    # ============================================================
    
    def configurar_aba_metas(self):
        """Configura a aba de metas - IGUAL AO ORIGINAL"""
        frame = ttk.Frame(self.aba_metas)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(
            frame,
            text="🎯 Metas de Produção",
            font=('Arial', 18, 'bold'),
            fg=self.cores.AZUL_MAR_ESCURO,
            bg=self.cores.BRANCO_NEVE
        ).pack(pady=10)
        
        grupos = ['biquini', 'roupa', 'acabamento']
        nomes = ['👙 Costura Biquíni', '👗 Costura Roupa', '✨ Acabamento']
        self.meta_entries = {}
        
        for i, (grupo, nome) in enumerate(zip(grupos, nomes)):
            sub_frame = ttk.LabelFrame(frame, text=nome, padding="10")
            sub_frame.pack(fill='x', pady=10)
            
            meta = self.metas.get(grupo, {'num_funcionarios': 1, 'meta_diaria_por_funcionario': 15})
            
            ttk.Label(sub_frame, text="Nº de Funcionários:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
            entry_func = ttk.Entry(sub_frame, width=10)
            entry_func.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            entry_func.insert(0, str(meta.get('num_funcionarios', 1)))
            
            ttk.Label(sub_frame, text="Meta Diária por Funcionário:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
            entry_meta = ttk.Entry(sub_frame, width=10)
            entry_meta.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            entry_meta.insert(0, str(meta.get('meta_diaria_por_funcionario', 15)))
            
            self.meta_entries[grupo] = {'func': entry_func, 'meta': entry_meta}
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="💾 Salvar Metas", command=self._salvar_metas).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 Visualizar Metas", command=self._visualizar_metas).pack(side=tk.LEFT, padx=5)
    
    def _salvar_metas(self):
        """Salva as metas - IGUAL AO ORIGINAL"""
        try:
            for grupo, entries in self.meta_entries.items():
                num_func = int(entries['func'].get())
                meta_diaria = int(entries['meta'].get())
                
                if num_func <= 0 or meta_diaria <= 0:
                    messagebox.showwarning("Aviso", "Os valores devem ser maiores que zero!")
                    return
                
                self.metas[grupo] = {
                    'num_funcionarios': num_func,
                    'meta_diaria_por_funcionario': meta_diaria
                }
            
            self.salvar_metas()
            self.atualizar_todas_estatisticas()
            messagebox.showinfo("Sucesso", "✅ Metas atualizadas com sucesso!")
            self.salvar_producao()
            
        except ValueError:
            messagebox.showerror("Erro", "Digite apenas números inteiros!")
    
    def _visualizar_metas(self):
        """Visualiza as metas atuais - IGUAL AO ORIGINAL"""
        if self.periodo_atual:
            dias_uteis = self.calcular_dias_uteis(self.periodo_atual[0], self.periodo_atual[1])
        else:
            dias_uteis = 22
        
        meta_mensal_biquini = self.calcular_meta_mensal('biquini')
        meta_mensal_roupa = self.calcular_meta_mensal('roupa')
        meta_mensal_acab = self.calcular_meta_mensal('acabamento')
        
        metas_texto = f"""
METAS DE PRODUÇÃO ATUAIS
(Baseado em {dias_uteis} dias úteis no mês)

👙 COSTURA BIQUÍNI:
• Funcionários: {self.metas['biquini']['num_funcionarios']}
• Meta por Funcionário: {self.metas['biquini']['meta_diaria_por_funcionario']} peças/dia
• Meta Mensal: {meta_mensal_biquini} peças/mês

👗 COSTURA ROUPA:
• Funcionários: {self.metas['roupa']['num_funcionarios']}
• Meta por Funcionário: {self.metas['roupa']['meta_diaria_por_funcionario']} peças/dia
• Meta Mensal: {meta_mensal_roupa} peças/mês

✨ ACABAMENTO:
• Funcionários: {self.metas['acabamento']['num_funcionarios']}
• Meta por Funcionário: {self.metas['acabamento']['meta_diaria_por_funcionario']} peças/dia
• Meta Mensal Geral: {meta_mensal_acab} peças/mês
"""
        
        messagebox.showinfo("Metas de Produção", metas_texto)
    
    # ============================================================
    # SALVAR E RELATÓRIOS - IGUAIS AO ORIGINAL
    # ============================================================
    
    def salvar_producao(self):
        """Salva os dados de produção em arquivo Excel - IGUAL AO ORIGINAL"""
        if not self.arquivo_atual:
            messagebox.showwarning("Aviso", "Nenhum mês carregado!")
            return
        
        try:
            dados_para_salvar = {}
            
            for tipo in ['biquini', 'roupa', 'acabamento']:
                if self.monthly_data[tipo]:
                    df_atual = pd.DataFrame(self.monthly_data[tipo])
                    dados_para_salvar[tipo] = df_atual
            
            metadata = pd.DataFrame({
                'Informação': ['Feriados', 'Colaboradores', 'Periodo_Inicio', 'Periodo_Fim', 'Mes_Key'],
                'Dados': [
                    json.dumps(self.feriados),
                    json.dumps(self.colaboradores),
                    self.periodo_atual[0].strftime('%Y-%m-%d') if self.periodo_atual else '',
                    self.periodo_atual[1].strftime('%Y-%m-%d') if self.periodo_atual else '',
                    self.mes_atual_info if self.mes_atual_info else ''
                ]
            })
            dados_para_salvar['Metadata'] = metadata
            
            with pd.ExcelWriter(self.arquivo_atual, engine='openpyxl') as writer:
                for sheet_name, df in dados_para_salvar.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            self.status_bar.config(text="💾 Dados salvos com sucesso")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar arquivo: {str(e)}")
    
    def gerar_relatorio_mensal(self):
        """Gera relatório mensal - IGUAL AO ORIGINAL"""
        if not self.periodo_atual:
            messagebox.showwarning("Aviso", "Carregue um mês primeiro!")
            return
        
        inicio_mes, fim_mes = self.periodo_atual
        
        if any(self.monthly_data.values()):
            resposta = messagebox.askyesno(
                "Gerar Relatório",
                "Usar dados atuais em memória?\n"
                "Sim: Usa dados não salvos\n"
                "Não: Carrega do arquivo"
            )
        else:
            resposta = False
        
        try:
            nome_resumo = f"resumo_{self.arquivo_atual.replace('.xlsx', '')}.xlsx" if self.arquivo_atual else "resumo.xlsx"
            
            with pd.ExcelWriter(nome_resumo, engine='openpyxl') as writer:
                if resposta and any(self.monthly_data.values()):
                    for tipo in ['biquini', 'roupa']:
                        if self.monthly_data[tipo]:
                            df = pd.DataFrame(self.monthly_data[tipo])
                            if not df.empty:
                                resumo = df.groupby(['produto', 'referencia'])['quantidade'].sum().reset_index()
                                resumo = resumo.sort_values('quantidade', ascending=False)
                                resumo.to_excel(writer, sheet_name=f'Resumo_{tipo.capitalize()}', index=False)
                    
                    if self.monthly_data['acabamento']:
                        df_acab = pd.DataFrame(self.monthly_data['acabamento'])
                        if not df_acab.empty:
                            resumo_colab = df_acab.groupby('colaborador').agg({
                                'qtd_biquini': 'sum',
                                'qtd_roupa': 'sum',
                                'qtd_acessorios': 'sum',
                                'total': 'sum'
                            }).reset_index()
                            resumo_colab.to_excel(writer, sheet_name='Resumo_Colaborador', index=False)
                
                elif self.arquivo_atual and os.path.exists(self.arquivo_atual):
                    for tipo in ['biquini', 'roupa']:
                        try:
                            df = pd.read_excel(self.arquivo_atual, sheet_name=tipo, engine='openpyxl')
                            if not df.empty:
                                df['data'] = pd.to_datetime(df['data'])
                                df_periodo = df[(df['data'] >= inicio_mes) & (df['data'] <= fim_mes)]
                                
                                if not df_periodo.empty:
                                    resumo = df_periodo.groupby(['produto', 'referencia'])['quantidade'].sum().reset_index()
                                    resumo = resumo.sort_values('quantidade', ascending=False)
                                    resumo.to_excel(writer, sheet_name=f'Resumo_{tipo.capitalize()}', index=False)
                        except Exception as e:
                            print(f"Erro ao processar {tipo}: {e}")
                    
                    try:
                        df_acab = pd.read_excel(self.arquivo_atual, sheet_name='acabamento', engine='openpyxl')
                        if not df_acab.empty:
                            df_acab['data'] = pd.to_datetime(df_acab['data'])
                            df_periodo = df_acab[(df_acab['data'] >= inicio_mes) & (df_acab['data'] <= fim_mes)]
                            
                            if not df_periodo.empty:
                                resumo_colab = df_periodo.groupby('colaborador').agg({
                                    'qtd_biquini': 'sum',
                                    'qtd_roupa': 'sum',
                                    'qtd_acessorios': 'sum',
                                    'total': 'sum'
                                }).reset_index()
                                resumo_colab.to_excel(writer, sheet_name='Resumo_Colaborador', index=False)
                    except Exception as e:
                        print(f"Erro ao processar acabamento: {e}")
                
                info_periodo = pd.DataFrame({
                    'Informação': ['Início do Período', 'Fim do Período', 'Dias Úteis', 'Dias Totais'],
                    'Valor': [
                        inicio_mes.strftime('%d/%m/%Y'),
                        fim_mes.strftime('%d/%m/%Y'),
                        self.calcular_dias_uteis(inicio_mes, fim_mes),
                        (fim_mes - inicio_mes).days + 1
                    ]
                })
                info_periodo.to_excel(writer, sheet_name='Informações', index=False)
            
            messagebox.showinfo("Sucesso", f"📊 Relatório gerado: {nome_resumo}")
            self.status_bar.config(text="📊 Relatório mensal gerado com sucesso")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {str(e)}")
    
    def editar_metas(self):
        """Abre a aba de metas - IGUAL AO ORIGINAL"""
        self.notebook_prod.select(self.aba_metas)

    def mostrar_ajuda(self):
            """Mostra ajuda com estilo praia - IGUAL AO ORIGINAL"""
            messagebox.showinfo(
                "🏖️ Ajuda - Borana Controle de Produção",
                "🌊 Bem-vindo ao Sistema de Controle de Produção!\n\n"
                "📌 Funcionalidades:\n"
                "• Visualização de produção por facção\n"
                "• Edição de quantidades enviadas e recebidas\n"
                "• Relatórios e gráficos interativos\n"
                "• Pesquisa rápida por OP, referência e ciclo\n"
                "• Filtros por data e status\n\n"
                "🔄 Importar TOTVS:\n"
                "• Busca ordens ativas no TOTVS\n"
                "• Adiciona novas ordens automaticamente\n"
                "• Atualiza quantidades de ordens existentes\n"
                "• Preserva dados locais (chegou, status, etc.)\n"
                "• Dados organizados automaticamente\n\n"
                "📏 Tamanhos:\n"
                "• Todos os tamanhos: PP, P, M, G, GG, U\n\n"
                "💾 Dados Locais:\n"
                "• Todos os dados são salvos localmente em CSV\n"
                "• Faça backups regularmente"
            )