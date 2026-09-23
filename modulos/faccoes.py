"""
Módulo de Gestão de Facções (terceirizados)
- Chave de edição compartilhada: Ciclo + OP
- Campos não editáveis definem unicidade de linha
- Preserva histórico de OPs que passaram por cada facção
- Ordenação por "OP Criada em" (mais recente primeiro)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os
from datetime import datetime
import numpy as np
import warnings
import re
import threading
import psycopg2
from psycopg2 import sql
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from pathlib import Path

from config.cores import TemaPraia
from core.database_manager import DatabaseManager
from core.database_local import DatabaseLocal

warnings.filterwarnings('ignore')


class ModuloFaccoes:
    """Módulo de Gestão de Facções"""
    
    # Campos que NÃO podem ser editados (chave de unicidade de linha)
    CAMPOS_NAO_EDITAVEIS = [
        'Referencia', 'Ciclo', 'OP', 'OP Criada em', 
        'Data Entrada', 'Faccao', 'Descricao'
    ]
    
    # Campos editáveis COMPARTILHADOS entre linhas de mesmo Ciclo+OP
    CAMPOS_COMPARTILHADOS = ['Cortou em', 'Valor', 'Observacoes']
    
    # Campos editáveis INDIVIDUAIS (por linha)
    CAMPOS_INDIVIDUAIS = [
        'Data Chegada', 'Status',
        'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
        'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
        'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
    ]
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.cores = TemaPraia
        
        self.db = DatabaseManager()
        self.db_local = DatabaseLocal()
        
        # Configurações do PostgreSQL
        self.db_config = {
            'host': 'caboose.proxy.rlwy.net',
            'port': 45649,
            'dbname': 'railway',
            'user': 'postgres',
            'password': 'UWKjEVQAzWDEOcGTOGvqrYChNuyFgrpY'
        }

        # Mapeamento de status para emojis
        self.status_emojis = {
            'EM ANDAMENTO': '⏳',
            'FINALIZADO': '✅',
            'CANCELADO': '❌'
        }
        
        self.emoji_status = {
            '⏳': 'EM ANDAMENTO',
            '✅': 'FINALIZADO',
            '❌': 'CANCELADO'
        }

        self.cidades_conhecidas = [
            'SAO GABRIEL DA PALHA', 'SAO MATEUS', 'NOVA VENECIA',
            'VILA VELHA', 'MARILANDIA', 'LINHARES', 'COLATINA',
            'FRIBURGO', 'MANTENA', 'GURIRI', 'SERRA', 'SGP'
        ]
        
        self.palavras_remover = ['FACCAO', 'ESTAMPARIA', 'OFICINA', 'FACCÃO']
        self.padrao_numero_hifen = r'^\d{3,4}-'
        
        from core.utils import get_app_dir

        CAMINHO_REDE = Path(r"Z:\15 - Produção\BRUNA\OFICINA\Banco de Dados - Sistema")

        if CAMINHO_REDE.exists():
            pasta_dados = CAMINHO_REDE
        else:
            pasta_dados = get_app_dir() / "dados_faccoes"
            pasta_dados.mkdir(exist_ok=True)

        self.caminho_banco = str(pasta_dados / "BANCODEDADOS_FACCAO.csv")
        self.caminho_backup = str(pasta_dados / "backups")
        self.caminho_historico = str(pasta_dados / "BANCODEDADOS_HISTORICO.csv")

        print(f"📂 Facções — pasta de dados: {pasta_dados}")
        
        # Dados
        self.df_banco = None
        self.df_filtrado = None
        self.df_historico = None
        self.fornecedores = []
        self.locais_faccao = []
        
        # Paginação do histórico
        self.hist_pagina_atual = 1
        self.hist_por_pagina = 100
        self.hist_total_paginas = 1
        self.hist_dados_filtrados = None
        
        # Interface
        self._criar_interface()
        
        # Carregar dados locais primeiro
        self.carregar_dados_locais()
        
        # Verificar se os dados já estão organizados e organizar se necessário
        self.verificar_e_organizar_dados()
        
        # Atualizar a interface com os dados existentes
        self.atualizar_abas_fornecedores()
        
        # Atualizar página inicial após carregar dados
        self.atualizar_pagina_inicial()
        
        # Tentar carregar dados do banco em background se não houver dados locais
        if self.df_banco is None or self.df_banco.empty:
            self.carregar_dados_banco_async()
        else:
            self.atualizar_status(f"🏝️ Dados carregados: {len(self.df_banco)} registros")
    
    def _criar_interface(self):
        """Cria a interface do módulo de facções"""
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        self.criar_menu_superior()
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.frame_inicial = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_inicial, text="🏠 Menu")
        self.criar_pagina_inicial()
        
        self.frame_faccoes = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_faccoes, text="🏭 Facções")
        self.criar_abas_faccoes()

        self.frame_relatorios = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_relatorios, text="📊 Relatórios")
        self.criar_pagina_relatorios()

        self.frame_historico = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_historico, text="📜 Histórico")
        self.criar_pagina_historico()
        
        self.criar_barra_status()
    
    def criar_menu_superior(self):
        menu_frame = tk.Frame(self.main_frame, bg=self.cores.AZUL_MAR, height=50)
        menu_frame.pack(fill='x', pady=(0, 0))
        menu_frame.pack_propagate(False)
        
        botoes = [
            ("🏄 Importar TOTVS", self.importar_ordens_banco),
            ("➕ Nova OP", self.adicionar_produto),
            ("❓ Ajuda", self.mostrar_ajuda)
        ]
        
        for texto, comando in botoes:
            btn = tk.Button(
                menu_frame, text=texto, command=comando,
                font=('Arial', 10, 'bold'),
                bg=self.cores.AREIA, fg=self.cores.AZUL_MAR_ESCURO,
                bd=0, padx=15, pady=5, relief='flat', cursor='hand2'
            )
            btn.pack(side='left', padx=5, pady=5)
            
            def on_enter(e, b=btn): b.config(bg=self.cores.AREIA_ESCURA)
            def on_leave(e, b=btn): b.config(bg=self.cores.AREIA)
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
        
        pesquisa_frame = tk.Frame(menu_frame, bg=self.cores.AZUL_MAR)
        pesquisa_frame.pack(side='right', padx=15)
        
        tk.Label(pesquisa_frame, text="Pesquisar por Facção: ", 
                bg=self.cores.AZUL_MAR, fg='white', 
                font=('Arial', 10)).pack(side='left')
        
        self.entry_pesquisa_faccao = tk.Entry(pesquisa_frame, 
                                             font=('Arial', 10), width=25,
                                             relief='flat', bd=2)
        self.entry_pesquisa_faccao.pack(side='left', padx=5, pady=5)
        self.entry_pesquisa_faccao.bind('<Return>', lambda e: self.pesquisar_e_ir_para_aba())
        
        btn_pesquisar = tk.Button(pesquisa_frame, text="🔍", 
                                 command=self.pesquisar_e_ir_para_aba,
                                 font=('Arial', 10, 'bold'),
                                 bg=self.cores.CORAL, fg='white', 
                                 bd=0, padx=12, pady=5,
                                 relief='flat', cursor='hand2')
        btn_pesquisar.pack(side='left', padx=5)
    
    def criar_barra_status(self):
        self.status_bar = tk.Label(self.main_frame, 
                                   text="🏝️ Pronto para navegar!", 
                                   relief=tk.FLAT, anchor=tk.W,
                                   bg=self.cores.AREIA, fg=self.cores.CINZA_ESCURO,
                                   font=('Arial', 10), padx=15, pady=8)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def atualizar_status(self, mensagem):
        self.status_bar.config(text=f"🏝️ {mensagem}")
        self.main_frame.update_idletasks()
    
    # ===== PÁGINA INICIAL =====
    
    def criar_pagina_inicial(self):
        for widget in self.frame_inicial.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self.frame_inicial)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.main_frame_inicial = main_frame
        
        self.frame_metricas = ttk.Frame(main_frame)
        self.frame_metricas.pack(fill='x', pady=15)
        
        self.atualizar_metricas()
        
        frame_pesquisa = ttk.LabelFrame(main_frame, text="🔍 Pesquisa Rápida", padding=15)
        frame_pesquisa.pack(fill='x', pady=10)
        
        grid_frame = ttk.Frame(frame_pesquisa)
        grid_frame.pack(fill='x')
        
        campos = [
            ("Referência:", 'entry_pesquisa_ref'),
            ("Ciclo:", 'entry_pesquisa_ciclo'),
            ("OP:", 'entry_pesquisa_op'),
            ("Facção:", 'entry_pesquisa_faccao_rapida')
        ]
        
        for i, (label, attr) in enumerate(campos):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(grid_frame, text=label, font=('Arial', 10)).grid(
                row=row, column=col, sticky='e', padx=(10, 5), pady=5
            )
            entry = ttk.Entry(grid_frame, font=('Arial', 10), width=25)
            entry.grid(row=row, column=col+1, sticky='w', padx=(0, 20), pady=5)
            setattr(self, attr, entry)
        
        btn_pesquisar = ttk.Button(frame_pesquisa, text="🔍 Pesquisar", 
                                  command=self.pesquisar_rapida)
        btn_pesquisar.pack(pady=10)
    
    def atualizar_metricas(self):
        for widget in self.frame_metricas.winfo_children():
            widget.destroy()
        
        if self.df_banco is not None and not self.df_banco.empty:
            total_produtos = len(self.df_banco)
            fornecedores = self.df_banco['Faccao'].nunique() if 'Faccao' in self.df_banco.columns else 0
            finalizados = len(self.df_banco[self.df_banco['Status'] == 'FINALIZADO']) if 'Status' in self.df_banco.columns else 0
            em_andamento = len(self.df_banco[self.df_banco['Status'] == 'EM ANDAMENTO']) if 'Status' in self.df_banco.columns else 0
            total_historico = len(self.df_historico) if hasattr(self, 'df_historico') and self.df_historico is not None and not self.df_historico.empty else 0
            
            cards = [
                ("📦 Total Produtos", total_produtos, self.cores.AZUL_MAR),
                ("🏭 Facções", fornecedores, self.cores.AZUL_CEU),
                ("✅ Finalizados", finalizados, self.cores.VERDE_COQUEIRO),
                ("⏳ Em Andamento", em_andamento, self.cores.AREIA),
                ("📜 Histórico", total_historico, self.cores.CORAL)
            ]
            
            for titulo, valor, cor in cards:
                card = tk.Frame(self.frame_metricas, bg=self.cores.BRANCO, 
                               relief='flat', bd=0, highlightthickness=2,
                               highlightbackground=cor)
                card.pack(side='left', padx=5, expand=True, fill='x')
                
                tk.Label(card, text=titulo, font=('Arial', 10),
                        bg=self.cores.BRANCO, fg=self.cores.CINZA_ESCURO).pack(pady=(10, 0))
                tk.Label(card, text=str(valor), font=('Arial', 16, 'bold'),
                        bg=self.cores.BRANCO, fg=cor).pack(pady=(0, 10))
        else:
            card = tk.Frame(self.frame_metricas, bg=self.cores.BRANCO, 
                           relief='flat', bd=0, highlightthickness=2,
                           highlightbackground=self.cores.AREIA)
            card.pack(fill='x', padx=10)
            
            tk.Label(card, text="🏝️ Nenhum dado carregado", 
                    font=('Arial', 14),
                    bg=self.cores.BRANCO, fg=self.cores.CINZA_ESCURO).pack(pady=10)
            tk.Label(card, text="Clique em 'Importar TOTVS' para começar", 
                    font=('Arial', 11),
                    bg=self.cores.BRANCO, fg=self.cores.CINZA_MEDIO).pack(pady=(0, 10))
    
    def atualizar_pagina_inicial(self):
        if hasattr(self, 'frame_metricas'):
            self.atualizar_metricas()
    
    # ===== ORGANIZAÇÃO DE DADOS =====
    
    def verificar_e_organizar_dados(self):
        if self.df_banco is None or self.df_banco.empty:
            return
        
        precisa_organizar = False
        
        if 'Cidade' in self.df_banco.columns:
            cidades_vazias = self.df_banco[self.df_banco['Cidade'] == '']
            if not cidades_vazias.empty:
                precisa_organizar = True
            
            if not precisa_organizar:
                for palavra in self.palavras_remover:
                    if self.df_banco['Faccao'].str.contains(palavra, case=False, na=False).any():
                        precisa_organizar = True
                        break
            
            if not precisa_organizar:
                if self.df_banco['Faccao'].str.match(self.padrao_numero_hifen, na=False).any():
                    precisa_organizar = True
        else:
            precisa_organizar = True
        
        if precisa_organizar:
            try:
                self.organizar_dados_silencioso()
            except Exception as e:
                print(f"Erro ao organizar dados automaticamente: {e}")
    
    def organizar_dados_silencioso(self, df=None):
        if df is None:
            df = self.df_banco
            
        if df is None or df.empty:
            return df
        
        try:
            df_processado = df.copy()
            
            for idx, row in df_processado.iterrows():
                if 'Faccao_Original' in row and pd.notna(row['Faccao_Original']) and row['Faccao_Original']:
                    nome_original = str(row['Faccao_Original'])
                else:
                    nome_original = str(row['Faccao']) if pd.notna(row['Faccao']) else ''
                
                cidade_encontrada = ''
                nome_limpo = nome_original
                
                cidade_encontrada = self.extrair_cidade(nome_original)
                if cidade_encontrada:
                    nome_limpo = nome_limpo.replace(cidade_encontrada, '').strip()
                
                nome_limpo = re.sub(self.padrao_numero_hifen, '', nome_limpo).strip()
                
                for palavra in self.palavras_remover:
                    nome_limpo = nome_limpo.replace(palavra, '').strip()
                    if 'Ç' in palavra:
                        nome_limpo = nome_limpo.replace(palavra.replace('Ç', 'C'), '').strip()
                
                nome_limpo = ' '.join(nome_limpo.split())
                
                if not nome_limpo:
                    nome_limpo = nome_original.replace(cidade_encontrada, '').strip() if cidade_encontrada else nome_original
                    for palavra in self.palavras_remover:
                        nome_limpo = nome_limpo.replace(palavra, '').strip()
                    nome_limpo = ' '.join(nome_limpo.split())
                
                df_processado.at[idx, 'Faccao'] = nome_limpo
                if 'Faccao_Original' not in df_processado.columns:
                    df_processado['Faccao_Original'] = ''
                if not df_processado.at[idx, 'Faccao_Original']:
                    df_processado.at[idx, 'Faccao_Original'] = nome_original
                
                if cidade_encontrada:
                    df_processado.at[idx, 'Cidade'] = cidade_encontrada.title()
            
            self.df_banco = df_processado
            return df_processado
            
        except Exception as e:
            print(f"Erro ao organizar dados silenciosamente: {e}")
            return df
    
    def extrair_cidade(self, nome):
        if not nome:
            return ''
        
        nome_upper = nome.upper()
        
        for cidade in self.cidades_conhecidas:
            cidade_upper = cidade.upper()
            if cidade_upper in nome_upper:
                return cidade
        
        if 'FRIBURGO' in nome_upper:
            return 'FRIBURGO'
        
        if 'SGP' in nome_upper:
            return 'SGP'
        
        return ''
    
    # ===== DADOS LOCAIS =====
    
    def carregar_dados_locais(self):
        try:
            if os.path.exists(self.caminho_banco):
                try:
                    self.df_banco = pd.read_csv(self.caminho_banco, sep=';', dtype=str)
                except UnicodeDecodeError:
                    self.df_banco = pd.read_csv(self.caminho_banco, sep=';', dtype=str, encoding='latin-1')
                
                if not self.df_banco.empty:
                    colunas_necessarias = [
                        'Faccao', 'Faccao_Original', 'Cidade', 'Referencia', 'Ciclo', 'OP',
                        'OP Criada em', 'Cortou em',
                        'Descricao', 'Data Entrada', 'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
                        'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
                        'Data Chegada', 'Status', 'Valor', 'Prazo Retorno', 'Observacoes',
                        'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
                        'Quantity', 'Location_Quantity'
                    ]
                    
                    for col in colunas_necessarias:
                        if col not in self.df_banco.columns:
                            self.df_banco[col] = ''
                    
                    colunas_numericas = ['PP', 'P', 'M', 'G', 'GG', 'U', 'Total', 
                                        'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 
                                        'Ret U', 'Ret Total', 'Valor',
                                        'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 
                                        'Def U', 'Def Total']
                    for col in colunas_numericas:
                        if col in self.df_banco.columns:
                            self.df_banco[col] = pd.to_numeric(
                                self.df_banco[col].astype(str).str.replace(',', '.'), 
                                errors='coerce'
                            ).fillna(0)
                    
                    print(f"🌴 Dados locais (ativas) carregados: {len(self.df_banco)} registros")
                else:
                    print("🏝️ Banco local de ativas vazio")
            else:
                colunas = [
                    'Faccao', 'Faccao_Original', 'Cidade', 'Referencia', 'Ciclo', 'OP',
                    'OP Criada em', 'Cortou em',
                    'Descricao', 'Data Entrada', 'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
                    'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
                    'Data Chegada', 'Status', 'Valor', 'Prazo Retorno', 'Observacoes',
                    'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
                    'Quantity', 'Location_Quantity'
                ]
                self.df_banco = pd.DataFrame(columns=colunas)
                self.salvar_banco()
            
            self.carregar_dados_historico()
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar dados locais: {str(e)}")
            self.df_banco = pd.DataFrame()
    
    def carregar_dados_historico(self):
        try:
            if os.path.exists(self.caminho_historico):
                try:
                    self.df_historico = pd.read_csv(self.caminho_historico, sep=';', dtype=str)
                except UnicodeDecodeError:
                    self.df_historico = pd.read_csv(self.caminho_historico, sep=';', dtype=str, encoding='latin-1')
                
                if not self.df_historico.empty:
                    colunas_necessarias = [
                        'Faccao', 'Referencia', 'Ciclo', 'OP',
                        'OP Criada em', 'Cortou em', 'Data Entrada', 'Data Chegada',
                        'Descricao', 'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
                        'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
                        'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
                        'Status', 'Observacoes'
                    ]
                    
                    for col in colunas_necessarias:
                        if col not in self.df_historico.columns:
                            self.df_historico[col] = ''
                    
                    colunas_numericas = ['PP', 'P', 'M', 'G', 'GG', 'U', 'Total', 
                                        'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 
                                        'Ret U', 'Ret Total',
                                        'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 
                                        'Def U', 'Def Total']
                    for col in colunas_numericas:
                        if col in self.df_historico.columns:
                            self.df_historico[col] = pd.to_numeric(
                                self.df_historico[col].astype(str).str.replace(',', '.'), 
                                errors='coerce'
                            ).fillna(0)
                    
                    print(f"📜 Histórico carregado: {len(self.df_historico)} registros")
                else:
                    self.df_historico = pd.DataFrame()
            else:
                self.df_historico = pd.DataFrame()
        except Exception as e:
            print(f"Erro ao carregar histórico: {e}")
            self.df_historico = pd.DataFrame()
    
    def salvar_historico(self):
        try:
            if hasattr(self, 'df_historico') and self.df_historico is not None and not self.df_historico.empty:
                os.makedirs(os.path.dirname(self.caminho_historico), exist_ok=True)
                self.df_historico.to_csv(self.caminho_historico, sep=';', index=False, encoding='utf-8')
                return True
        except Exception as e:
            print(f"Erro ao salvar histórico: {e}")
            return False
    
    def salvar_banco(self):
        try:
            if self.df_banco is not None and not self.df_banco.empty:
                os.makedirs(os.path.dirname(self.caminho_banco), exist_ok=True)
                self.df_banco.to_csv(self.caminho_banco, sep=';', index=False, encoding='utf-8')
                self.atualizar_status("💾 Dados salvos localmente")
                self.atualizar_pagina_inicial()
                return True
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {str(e)}")
            return False
    
    def fazer_backup(self):
        try:
            if self.df_banco is None or self.df_banco.empty:
                messagebox.showwarning("Aviso", "Não há dados para fazer backup")
                return
            
            data = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(self.caminho_backup, exist_ok=True)
            
            backup_path = os.path.join(self.caminho_backup, f"backup_{data}.csv")
            self.df_banco.to_csv(backup_path, sep=';', index=False)
            
            messagebox.showinfo("Backup", f"🏖️ Backup criado com sucesso!\n{backup_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar backup: {str(e)}")
    
    # ===== PESQUISA =====
    
    def pesquisar_rapida(self):
        op = self.entry_pesquisa_op.get().strip()
        referencia = self.entry_pesquisa_ref.get().strip()
        ciclo = self.entry_pesquisa_ciclo.get().strip()
        faccao = self.entry_pesquisa_faccao_rapida.get().strip()
        
        if self.df_banco is None or self.df_banco.empty:
            messagebox.showwarning("Aviso", "Nenhum dado carregado")
            return
        
        if not op and not referencia and not ciclo and not faccao:
            messagebox.showwarning("Aviso", "Digite pelo menos um critério de pesquisa")
            return
        
        df_base = self.df_filtrado if self.df_filtrado is not None else self.df_banco
        df_resultado = df_base.copy()
        
        filtros_aplicados = []
        
        if referencia:
            df_resultado = df_resultado[
                df_resultado['Referencia'].astype(str).str.upper().str.contains(
                    referencia.upper(), na=False, regex=False
                )
            ]
            filtros_aplicados.append(f"Referência: '{referencia}'")
        
        if ciclo:
            df_resultado = df_resultado[
                df_resultado['Ciclo'].astype(str).str.upper().str.contains(
                    ciclo.upper(), na=False, regex=False
                )
            ]
            filtros_aplicados.append(f"Ciclo: '{ciclo}'")
        
        if op:
            df_resultado = df_resultado[
                df_resultado['OP'].astype(str).str.upper().str.contains(
                    op.upper(), na=False, regex=False
                )
            ]
            filtros_aplicados.append(f"OP: '{op}'")
        
        if faccao:
            df_resultado = df_resultado[
                df_resultado['Faccao'].astype(str).str.upper().str.contains(
                    faccao.upper(), na=False, regex=False
                )
            ]
            filtros_aplicados.append(f"Facção: '{faccao}'")
        
        if df_resultado.empty:
            messagebox.showinfo(
                "Resultado",
                f"Nenhum registro encontrado.\n\n"
                f"Filtros aplicados:\n" + "\n".join(f"• {f}" for f in filtros_aplicados)
            )
            return
        
        self.mostrar_resultados_pesquisa(df_resultado, filtros_aplicados)
    
    def mostrar_resultados_pesquisa(self, df_resultados, filtros_aplicados=None):
        janela = tk.Toplevel(self.parent)
        janela.title(f"🏖️ Resultados da Pesquisa ({len(df_resultados)} encontrados)")
        janela.geometry("1400x650")
        janela.transient(self.parent)
        janela.grab_set()
        janela.configure(bg=self.cores.BRANCO_NEVE)
        
        main_frame = ttk.Frame(janela, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        header = tk.Frame(main_frame, bg=self.cores.AZUL_MAR, height=50)
        header.pack(fill='x', pady=(0, 10))
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text=f"🏄 {len(df_resultados)} registro(s) encontrado(s)",
            font=('Arial', 13, 'bold'),
            bg=self.cores.AZUL_MAR, fg='white', padx=15
        ).pack(side='left', pady=10)
        
        tk.Button(
            header, text="❌ Fechar", command=janela.destroy,
            font=('Arial', 10, 'bold'),
            bg=self.cores.CORAL, fg='white',
            relief='flat', padx=15, pady=5, cursor='hand2'
        ).pack(side='right', padx=10, pady=8)
        
        if filtros_aplicados:
            frame_filtros = tk.Frame(main_frame, bg=self.cores.AZUL_AGUA)
            frame_filtros.pack(fill='x', pady=(0, 10))
            
            tk.Label(
                frame_filtros,
                text="🔍 Filtros aplicados: " + " | ".join(filtros_aplicados),
                font=('Arial', 10, 'italic'),
                bg=self.cores.AZUL_AGUA,
                fg=self.cores.AZUL_MAR_ESCURO,
                padx=10, pady=5
            ).pack(side='left')
        
        frame_resumo = ttk.LabelFrame(main_frame, text="📍 Resumo por Localização (Facção)", padding=8)
        frame_resumo.pack(fill='x', pady=(0, 10))
        
        resumo_faccao = df_resultados.groupby('Faccao').agg({
            'OP': 'count',
            'Total': 'sum'
        }).reset_index()
        resumo_faccao.columns = ['Faccao', 'Qtd OPs', 'Total Peças']
        resumo_faccao = resumo_faccao.sort_values('Qtd OPs', ascending=False)
        
        resumo_canvas = tk.Canvas(frame_resumo, bg=self.cores.BRANCO_NEVE, height=50, highlightthickness=0)
        resumo_scrollbar = ttk.Scrollbar(frame_resumo, orient='horizontal', command=resumo_canvas.xview)
        resumo_canvas.configure(xscrollcommand=resumo_scrollbar.set)
        
        resumo_inner = tk.Frame(resumo_canvas, bg=self.cores.BRANCO_NEVE)
        resumo_canvas.create_window((0, 0), window=resumo_inner, anchor='nw')
        
        resumo_canvas.pack(fill='x')
        resumo_scrollbar.pack(fill='x')
        
        for _, row in resumo_faccao.iterrows():
            badge = tk.Frame(resumo_inner, bg=self.cores.AZUL_MAR, relief='flat', padx=10, pady=4)
            badge.pack(side='left', padx=4, pady=4)
            
            tk.Label(
                badge,
                text=f"{row['Faccao']} • {row['Qtd OPs']} OPs • {int(row['Total Peças'])} pçs",
                font=('Arial', 9, 'bold'),
                bg=self.cores.AZUL_MAR, fg='white'
            ).pack()
        
        resumo_inner.update_idletasks()
        resumo_canvas.configure(scrollregion=resumo_canvas.bbox('all'))
        
        tabela_frame = ttk.Frame(main_frame)
        tabela_frame.pack(fill='both', expand=True)
        
        columns = [
            'Localização', 'Status',
            'Faccao', 'Referencia', 'Ciclo', 'OP',
            'OP Criada em', 'Data Entrada',
            'Descricao',
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
            'Observacoes'
        ]
        
        tree = ttk.Treeview(tabela_frame, columns=columns, show='headings', height=20)
        
        widths = {
            'Localização': 140, 'Status': 100,
            'Faccao': 140, 'Referencia': 100, 'Ciclo': 60, 'OP': 70,
            'OP Criada em': 95, 'Data Entrada': 95,
            'Descricao': 180,
            'PP': 45, 'P': 45, 'M': 45, 'G': 45, 'GG': 45, 'U': 45, 'Total': 60,
            'Ret PP': 55, 'Ret P': 45, 'Ret M': 45, 'Ret G': 45, 
            'Ret GG': 55, 'Ret U': 45, 'Ret Total': 65,
            'Def PP': 50, 'Def P': 45, 'Def M': 45, 'Def G': 45, 
            'Def GG': 50, 'Def U': 45, 'Def Total': 60,
            'Observacoes': 150
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 80), anchor='center', stretch=False)
        
        tree.tag_configure('finalizado', background='#d4edda')
        tree.tag_configure('andamento', background='#fff3cd')
        tree.tag_configure('cancelado', background='#f8d7da')
        
        for _, row in df_resultados.iterrows():
            localizacao = str(row.get('Faccao', '')).strip() or 'SEM LOCALIZAÇÃO'
            status_raw = str(row.get('Status', '')).upper()
            status_emoji = self.status_emojis.get(status_raw, status_raw)
            
            values = []
            for col in columns:
                if col == 'Localização':
                    values.append(localizacao)
                elif col == 'Status':
                    values.append(status_emoji)
                else:
                    valor = row[col] if col in row else ''
                    if pd.isna(valor):
                        values.append('')
                    elif isinstance(valor, (int, float)):
                        values.append(f"{int(valor)}" if valor == int(valor) else f"{valor:.1f}")
                    else:
                        values.append(str(valor))
            
            item = tree.insert('', 'end', values=values)
            
            if status_raw == 'FINALIZADO':
                tree.item(item, tags=('finalizado',))
            elif status_raw == 'EM ANDAMENTO':
                tree.item(item, tags=('andamento',))
            elif status_raw == 'CANCELADO':
                tree.item(item, tags=('cancelado',))
        
        vsb = ttk.Scrollbar(tabela_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tabela_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tabela_frame.grid_rowconfigure(0, weight=1)
        tabela_frame.grid_columnconfigure(0, weight=1)
        
        frame_totais = tk.Frame(main_frame, bg=self.cores.AZUL_AGUA)
        frame_totais.pack(fill='x', pady=(10, 0))
        
        total_ops = len(df_resultados)
        total_enviado = int(pd.to_numeric(df_resultados['Total'], errors='coerce').fillna(0).sum()) if 'Total' in df_resultados.columns else 0
        total_retornado = int(pd.to_numeric(df_resultados['Ret Total'], errors='coerce').fillna(0).sum()) if 'Ret Total' in df_resultados.columns else 0
        total_defeitos = int(pd.to_numeric(df_resultados['Def Total'], errors='coerce').fillna(0).sum()) if 'Def Total' in df_resultados.columns else 0
        
        tk.Label(
            frame_totais,
            text=f"📦 OPs: {total_ops}  |  "
                 f"👕 Enviadas: {total_enviado}  |  "
                 f"✅ Retornadas: {total_retornado}  |  "
                 f"⚠️ Defeitos: {total_defeitos}",
            font=('Arial', 11, 'bold'),
            bg=self.cores.AZUL_AGUA,
            fg=self.cores.AZUL_MAR_ESCURO,
            padx=10, pady=8
        ).pack(fill='x')
        
        def on_double_click(event):
            selection = tree.selection()
            if not selection:
                return
            values = tree.item(selection[0], 'values')
            referencia = values[3]
            ciclo = values[4]
            op = values[5]
            
            mask = (self.df_banco['OP'].astype(str) == str(op)) & \
                   (self.df_banco['Referencia'].astype(str) == str(referencia)) & \
                   (self.df_banco['Ciclo'].astype(str) == str(ciclo))
            
            if mask.any():
                idx = self.df_banco[mask].index[0]
                self.abrir_janela_edicao(idx)
        
        tree.bind('<Double-1>', on_double_click)
    
    # ===== ABAS DAS FACÇÕES =====
    
    def criar_abas_faccoes(self):
        for widget in self.frame_faccoes.winfo_children():
            widget.destroy()
        
        main_container = ttk.Frame(self.frame_faccoes)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 5))
        
        canvas_frame = tk.Frame(header_frame, bg=self.cores.BRANCO_NEVE, height=50)
        canvas_frame.pack(fill='x', pady=2)
        canvas_frame.pack_propagate(False)
        
        canvas = tk.Canvas(canvas_frame, bg=self.cores.BRANCO_NEVE, 
                          highlightthickness=0, height=45)
        
        scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
        
        tab_frame = tk.Frame(canvas, bg=self.cores.BRANCO_NEVE)
        self.tab_canvas_window = canvas.create_window((0, 0), window=tab_frame, anchor='nw')
        canvas.configure(xscrollcommand=scrollbar.set)
        
        canvas.pack(side='top', fill='both', expand=True)
        scrollbar.pack(side='bottom', fill='x', padx=5)
        
        self.content_frame = ttk.Frame(main_container)
        self.content_frame.pack(fill='both', expand=True, pady=5)
        
        self.tab_canvas = canvas
        self.tab_frame = tab_frame
        self.scrollbar = scrollbar
        self.tab_buttons = {}
        self.current_aba = None
        
        def on_mousewheel(event):
            if event.num == 4:
                canvas.xview_scroll(-1, 'units')
            elif event.num == 5:
                canvas.xview_scroll(1, 'units')
            else:
                canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')
        
        canvas.bind('<MouseWheel>', on_mousewheel)
        canvas.bind('<Button-4>', on_mousewheel)
        canvas.bind('<Button-5>', on_mousewheel)
        canvas.bind('<Enter>', lambda e: canvas.focus_set())
        canvas.bind('<Left>', lambda e: canvas.xview_scroll(-1, 'units'))
        canvas.bind('<Right>', lambda e: canvas.xview_scroll(1, 'units'))
        
        self.atualizar_botoes_abas()
    
    def atualizar_botoes_abas(self):
        if self.df_banco is None or self.df_banco.empty:
            return
        
        for widget in self.tab_frame.winfo_children():
            widget.destroy()
        self.tab_buttons.clear()
        
        if 'Faccao' in self.df_banco.columns:
            fornecedores = sorted(self.df_banco['Faccao'].dropna().unique())
            
            for fornecedor in fornecedores:
                tab_item = tk.Frame(self.tab_frame, bg=self.cores.BRANCO_NEVE)
                tab_item.pack(side='left', padx=2, pady=2)
                
                btn = tk.Button(tab_item, 
                               text=fornecedor,
                               font=('Arial', 10),
                               bg=self.cores.CINZA_CLARO,
                               fg=self.cores.CINZA_ESCURO,
                               relief='flat', padx=15, pady=8,
                               cursor='hand2', width=20, anchor='w',
                               command=lambda f=fornecedor: self.selecionar_aba(f))
                
                def on_enter_btn(e, b=btn):
                    if b.cget('bg') != self.cores.CORAL:
                        b.config(bg=self.cores.AZUL_AGUA)
                def on_leave_btn(e, b=btn):
                    if b.cget('bg') != self.cores.CORAL:
                        b.config(bg=self.cores.CINZA_CLARO)
                
                btn.bind('<Enter>', on_enter_btn)
                btn.bind('<Leave>', on_leave_btn)
                
                btn.pack(fill='both', expand=True)
                self.tab_buttons[fornecedor] = btn
        
        self.tab_frame.update_idletasks()
        self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox('all'))
        
        if fornecedores:
            self.selecionar_aba(fornecedores[0])
    
    def selecionar_aba(self, fornecedor):
        for faccao, btn in self.tab_buttons.items():
            if faccao == fornecedor:
                btn.config(bg=self.cores.CORAL, fg='white')
                btn.config(relief='sunken', bd=1)
            else:
                btn.config(bg=self.cores.CINZA_CLARO, fg=self.cores.CINZA_ESCURO)
                btn.config(relief='flat', bd=0)
        
        self.mostrar_conteudo_aba(fornecedor)
    
    def mostrar_conteudo_aba(self, fornecedor):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.df_banco is not None and not self.df_banco.empty:
            df_fornecedor = self.df_banco[self.df_banco['Faccao'] == fornecedor]
            if not df_fornecedor.empty:
                self.criar_tabela_fornecedor(self.content_frame, fornecedor, df_fornecedor)
            else:
                ttk.Label(self.content_frame, 
                         text=f"🏝️ Nenhum registro encontrado para {fornecedor}",
                         font=('Arial', 11),
                         background=self.cores.BRANCO_NEVE).pack(pady=20)
    
    def atualizar_abas_fornecedores(self):
        self.atualizar_botoes_abas()
        if hasattr(self, 'tree_historico'):
            self.atualizar_historico()
        if hasattr(self, 'frame_metricas'):
            self.atualizar_metricas()
    
    def atualizar_abas_fornecedores_filtrado(self):
        if self.df_filtrado is None or self.df_filtrado.empty:
            return
        
        for widget in self.tab_frame.winfo_children():
            widget.destroy()
        self.tab_buttons.clear()
        
        if 'Faccao' in self.df_filtrado.columns:
            fornecedores = sorted(self.df_filtrado['Faccao'].dropna().unique())
            
            for fornecedor in fornecedores:
                tab_item = tk.Frame(self.tab_frame, bg=self.cores.BRANCO_NEVE)
                tab_item.pack(side='left', padx=2, pady=2)
                
                btn = tk.Button(tab_item, 
                               text=f"{fornecedor} 🔍",
                               font=('Arial', 10),
                               bg=self.cores.CINZA_CLARO,
                               fg=self.cores.CINZA_ESCURO,
                               relief='flat', padx=15, pady=8,
                               cursor='hand2', width=20, anchor='w',
                               command=lambda f=fornecedor: self.selecionar_aba_filtrada(f))
                
                btn.pack(fill='both', expand=True)
                self.tab_buttons[fornecedor] = btn
        
        self.tab_frame.update_idletasks()
        self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox('all'))
        
        if fornecedores:
            self.selecionar_aba_filtrada(fornecedores[0])
    
    def selecionar_aba_filtrada(self, fornecedor):
        for faccao, btn in self.tab_buttons.items():
            if faccao == fornecedor:
                btn.config(bg=self.cores.CORAL, fg='white')
                btn.config(relief='sunken', bd=1)
            else:
                btn.config(bg=self.cores.CINZA_CLARO, fg=self.cores.CINZA_ESCURO)
                btn.config(relief='flat', bd=0)
        
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.df_filtrado is not None and not self.df_filtrado.empty:
            df_fornecedor = self.df_filtrado[self.df_filtrado['Faccao'] == fornecedor]
            if not df_fornecedor.empty:
                self.criar_tabela_fornecedor(self.content_frame, fornecedor, df_fornecedor)
    
    # ===== TABELA POR FORNECEDOR =====
    
    def criar_tabela_fornecedor(self, parent, fornecedor, df_fornecedor):
        """Cria tabela para fornecedor ORDENADA por OP Criada em (mais recente primeiro)"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill='both', expand=True)
        
        # ============================================================
        # ORDENAR POR "OP Criada em" (mais recente primeiro)
        # ============================================================
        df_fornecedor = df_fornecedor.copy()
        df_fornecedor['_data_ordenacao'] = pd.to_datetime(
            df_fornecedor['OP Criada em'], dayfirst=True, errors='coerce'
        )
        df_fornecedor = df_fornecedor.sort_values(
            '_data_ordenacao', ascending=False, na_position='last'
        )
        df_fornecedor = df_fornecedor.drop('_data_ordenacao', axis=1)
        
        # Cabeçalho
        header_frame = tk.Frame(main_frame, bg=self.cores.AZUL_MAR, height=50)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        cidade = df_fornecedor['Cidade'].iloc[0] if not df_fornecedor.empty and 'Cidade' in df_fornecedor.columns else 'N/A'
        
        tk.Label(header_frame, 
                text=f"🏖️ {fornecedor} | Cidade: {cidade} | 📦 {len(df_fornecedor)} registros",
                font=('Arial', 11),
                bg=self.cores.AZUL_MAR, fg='white').pack(side='left', padx=15, pady=10)
        
        btn_frame = tk.Frame(header_frame, bg=self.cores.AZUL_MAR)
        btn_frame.pack(side='right', padx=10)
        
        def criar_botao(texto, comando, cor):
            btn = tk.Button(btn_frame, text=texto, command=comando,
                        font=('Arial', 10),
                        bg=cor, fg=self.cores.AZUL_MAR_ESCURO,
                        relief='flat', padx=12, pady=5, cursor='hand2')
            btn.pack(side='left', padx=3)
            return btn
        
        tree = None
        
        def exportar():
            self.exportar_fornecedor(fornecedor, df_fornecedor)
        
        criar_botao("📥 Exportar", exportar, self.cores.AREIA)
        criar_botao("🔄 Recalc Retornos", self.recalcular_retornos_rapido, self.cores.AREIA)
        
        # Tabela
        tabela_frame = ttk.Frame(main_frame)
        tabela_frame.pack(fill='both', expand=True, pady=10)
        
        columns = ['Referencia', 'Ciclo', 'OP', 
                   'OP Criada em', 'Cortou em', 'Data Entrada',
                   'Descricao',
                   'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
                   'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 
                   'Ret Total', 'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
                   'Status', 'Observacoes']
        
        tree = ttk.Treeview(tabela_frame, columns=columns, show='headings', 
                        height=18, selectmode='extended')
        
        col_widths = {
            'Referencia': 100, 'Ciclo': 60, 'OP': 60, 
            'OP Criada em': 100, 'Cortou em': 100, 'Data Entrada': 100,
            'Descricao': 180,
            'PP': 50, 'P': 50, 'M': 50, 'G': 50, 'GG': 50, 'U': 50, 'Total': 75,
            'Ret PP': 70, 'Ret P': 60, 'Ret M': 60, 'Ret G': 60, 
            'Ret GG': 70, 'Ret U': 60, 'Ret Total': 85,
            'Def PP': 60, 'Def P': 60, 'Def M': 60, 'Def G': 60, 
            'Def GG': 60, 'Def U': 60, 'Def Total': 75,
            'Status': 70, 'Observacoes': 150
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), anchor='center')
        
        # Guardar índices originais para edição
        for idx, row in df_fornecedor.iterrows():
            values = []
            for col in columns:
                valor = row[col] if col in row else ''
                if pd.isna(valor):
                    values.append('')
                elif col == 'Status':
                    status_text = str(valor).upper()
                    values.append(self.status_emojis.get(status_text, status_text))
                elif isinstance(valor, (int, float)):
                    if col in ['PP', 'P', 'M', 'G', 'GG', 'U', 'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U',
                            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U']:
                        values.append(f"{int(valor)}" if valor == int(valor) else f"{valor}")
                    elif col in ['Total', 'Ret Total', 'Def Total']:
                        values.append(f"{int(valor)}" if valor == int(valor) else f"{valor:.1f}")
                    else:
                        values.append(str(valor))
                else:
                    values.append(str(valor))
            
            item = tree.insert('', 'end', values=values)
            tree.item(item, tags=(str(idx),))
            
            status = str(row.get('Status', '')).upper()
            if status == 'FINALIZADO':
                tree.tag_configure('finalizado', background='#d4edda')
                tree.item(item, tags=(str(idx), 'finalizado'))
            elif status == 'EM ANDAMENTO':
                tree.tag_configure('andamento', background='#fff3cd')
                tree.item(item, tags=(str(idx), 'andamento'))
        
        vsb = ttk.Scrollbar(tabela_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tabela_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tabela_frame.grid_rowconfigure(0, weight=1)
        tabela_frame.grid_columnconfigure(0, weight=1)
        
        tree.bind('<Double-1>', lambda e: self.editar_registro_por_tree(tree, fornecedor))
    
    def recalcular_retornos_rapido(self):
        """Recalcula retornos agrupando por Ciclo+OP (compartilhado)"""
        if self.df_banco is None or self.df_banco.empty:
            messagebox.showwarning("Aviso", "Não há dados para recalcular")
            return
        
        if 'Quantity' not in self.df_banco.columns or 'Location_Quantity' not in self.df_banco.columns:
            messagebox.showwarning("Aviso", 
                "As colunas 'Quantity' e 'Location_Quantity' não foram encontradas.")
            return
        
        resposta = messagebox.askyesno(
            "🔄 Recalcular Retornos",
            "Recalcular os campos de 'Ret' baseados em:\n\n"
            "• Quantity (Quantidade Total enviada)\n"
            "• Location_Quantity (Quantidade ainda com a facção)\n\n"
            "⚠️ Será aplicado por Ciclo+OP (compartilhado entre locais)\n\n"
            "Deseja continuar?"
        )
        
        if not resposta:
            return
        
        try:
            df_processado = self.df_banco.copy()
            atualizados = 0
            
            # Agrupar por (Ciclo, OP) - chave compartilhada
            for (ciclo, op), group_idx in df_processado.groupby(['Ciclo', 'OP']).groups.items():
                # Calcular retorno total do grupo (soma de todos os locais)
                idx_list = list(group_idx)
                
                quantity_total_grupo = 0
                location_quantity_total_grupo = 0
                
                for idx in idx_list:
                    quantity_total_grupo += int(df_processado.at[idx, 'Quantity']) if pd.notna(df_processado.at[idx, 'Quantity']) else 0
                    location_quantity_total_grupo += int(df_processado.at[idx, 'Location_Quantity']) if pd.notna(df_processado.at[idx, 'Location_Quantity']) else 0
                
                if quantity_total_grupo == 0:
                    continue
                
                ret_total_grupo = max(0, quantity_total_grupo - location_quantity_total_grupo)
                
                # Distribuir proporcionalmente entre os tamanhos
                tamanhos = ['PP', 'P', 'M', 'G', 'GG', 'U']
                total_original_grupo = 0
                for idx in idx_list:
                    for tam in tamanhos:
                        total_original_grupo += int(df_processado.at[idx, tam]) if pd.notna(df_processado.at[idx, tam]) else 0
                
                if total_original_grupo > 0:
                    for idx in idx_list:
                        for tam in tamanhos:
                            qt_original = int(df_processado.at[idx, tam]) if pd.notna(df_processado.at[idx, tam]) else 0
                            if qt_original > 0:
                                proporcao = qt_original / total_original_grupo
                                ret_calculado = int(round(ret_total_grupo * proporcao))
                                ret_calculado = min(ret_calculado, qt_original)
                                df_processado.at[idx, f'Ret {tam}'] = ret_calculado
                            else:
                                df_processado.at[idx, f'Ret {tam}'] = 0
                        
                        ret_total_linha = sum([int(df_processado.at[idx, f'Ret {tam}']) for tam in tamanhos])
                        df_processado.at[idx, 'Ret Total'] = ret_total_linha
                        
                        if ret_total_linha >= int(df_processado.at[idx, 'Quantity']):
                            df_processado.at[idx, 'Status'] = 'FINALIZADO'
                        elif ret_total_linha > 0:
                            df_processado.at[idx, 'Status'] = 'EM ANDAMENTO'
                        
                        atualizados += 1
            
            self.df_banco = df_processado
            self.salvar_banco()
            self.atualizar_abas_fornecedores()
            
            messagebox.showinfo("Sucesso", 
                f"✅ Retornos recalculados para {atualizados} registros!\n\n"
                f"• Aplicado por Ciclo+OP (compartilhado entre locais)")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao recalcular: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # ===== EDIÇÃO =====
    
    def editar_registro_por_tree(self, tree, fornecedor):
        selecionados = tree.selection()
        
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione um registro para editar")
            return
        
        item = selecionados[0]
        tags = tree.item(item, 'tags')
        
        if tags and tags[0].isdigit():
            idx = int(tags[0])
            self.abrir_janela_edicao(idx)
    
    def abrir_janela_edicao(self, idx):
        """Abre janela de edição - campos readonly com background cinza"""
        registro = self.df_banco.loc[idx]
        
        ciclo_atual = str(registro.get('Ciclo', '')).strip()
        op_atual = str(registro.get('OP', '')).strip()
        
        mask_compartilhado = (
            (self.df_banco['Ciclo'].astype(str).str.strip() == ciclo_atual) &
            (self.df_banco['OP'].astype(str).str.strip() == op_atual)
        )
        qtd_compartilhado = mask_compartilhado.sum()
        
        janela = tk.Toplevel(self.parent)
        janela.title(f"🏖️ Editar Ciclo {ciclo_atual} - OP {op_atual}")
        janela.geometry("1050x620")
        janela.minsize(700, 500)
        janela.transient(self.parent)
        janela.grab_set()
        janela.configure(bg=self.cores.BRANCO_NEVE)
        
        # Cores para campos readonly
        COR_READONLY_BG = '#E8E8E8'  # Cinza claro
        COR_READONLY_FG = '#666666'  # Cinza escuro para o texto
        
        outer_frame = ttk.Frame(janela)
        outer_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        canvas = tk.Canvas(outer_frame, bg=self.cores.BRANCO_NEVE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        main_frame = ttk.Frame(canvas, padding=15)
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor='nw')
        
        def configurar_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        def redimensionar_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        main_frame.bind('<Configure>', configurar_scroll)
        canvas.bind('<Configure>', redimensionar_canvas)
        
        def scroll_mouse(event):
            if event.num == 4:
                canvas.yview_scroll(-1, 'units')
            elif event.num == 5:
                canvas.yview_scroll(1, 'units')
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        
        canvas.bind('<MouseWheel>', scroll_mouse)
        canvas.bind('<Button-4>', scroll_mouse)
        canvas.bind('<Button-5>', scroll_mouse)
        
        campos = {}
        
        # Função auxiliar para criar Entry readonly com cor
        def criar_entry_readonly(parent, valor, width=18):
            entry = tk.Entry(
                parent,
                font=('Arial', 9),
                width=width,
                bg=COR_READONLY_BG,
                fg=COR_READONLY_FG,
                readonlybackground=COR_READONLY_BG,
                relief='solid',
                bd=1
            )
            entry.insert(0, str(valor))
            entry.config(state='readonly')
            return entry
        
        # AVISO
        if qtd_compartilhado > 1:
            frame_aviso = tk.Frame(main_frame, bg=self.cores.AREIA, relief='flat', padx=10, pady=8)
            frame_aviso.pack(fill='x', pady=(0, 10))
            
            tk.Label(
                frame_aviso,
                text=f"⚠️ Esta OP (Ciclo {ciclo_atual} - OP {op_atual}) está em {qtd_compartilhado} localizações.\n"
                     f"Os campos 'Cortou em', 'Valor' e 'Observações' são compartilhados entre todas elas.",
                font=('Arial', 10, 'bold'),
                bg=self.cores.AREIA, fg=self.cores.AZUL_MAR_ESCURO,
                justify='left'
            ).pack(anchor='w')
        
        # ============================================================
        # INFORMAÇÕES PRINCIPAIS (NÃO EDITÁVEIS - FUNDO CINZA)
        # ============================================================
        frame_principal = ttk.LabelFrame(main_frame, text="📋 Informações Principais (Não Editáveis)", padding=10)
        frame_principal.pack(fill='x', pady=5)
        
        frame_principal.grid_columnconfigure(0, weight=1)
        frame_principal.grid_columnconfigure(2, weight=1)
        frame_principal.grid_columnconfigure(4, weight=1)
        
        # Referência
        ttk.Label(frame_principal, text="Referência:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky='e', padx=(5, 2), pady=3)
        campos['Referencia'] = criar_entry_readonly(frame_principal, registro.get('Referencia', ''), width=18)
        campos['Referencia'].grid(row=0, column=1, sticky='w', padx=2, pady=3)
        
        # Ciclo
        ttk.Label(frame_principal, text="Ciclo:", font=('Arial', 9, 'bold')).grid(
            row=0, column=2, sticky='e', padx=(10, 2), pady=3)
        campos['Ciclo'] = criar_entry_readonly(frame_principal, registro.get('Ciclo', ''), width=12)
        campos['Ciclo'].grid(row=0, column=3, sticky='w', padx=2, pady=3)
        
        # OP
        ttk.Label(frame_principal, text="OP:", font=('Arial', 9, 'bold')).grid(
            row=0, column=4, sticky='e', padx=(10, 2), pady=3)
        campos['OP'] = criar_entry_readonly(frame_principal, registro.get('OP', ''), width=12)
        campos['OP'].grid(row=0, column=5, sticky='w', padx=2, pady=3)
        
        # OP Criada em
        ttk.Label(frame_principal, text="OP Criada em:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky='e', padx=(5, 2), pady=3)
        campos['OP Criada em'] = criar_entry_readonly(frame_principal, registro.get('OP Criada em', ''), width=18)
        campos['OP Criada em'].grid(row=1, column=1, sticky='w', padx=2, pady=3)
        
        # Data Entrada
        ttk.Label(frame_principal, text="Data Entrada:", font=('Arial', 9, 'bold')).grid(
            row=1, column=2, sticky='e', padx=(10, 2), pady=3)
        campos['Data Entrada'] = criar_entry_readonly(frame_principal, registro.get('Data Entrada', ''), width=12)
        campos['Data Entrada'].grid(row=1, column=3, sticky='w', padx=2, pady=3)
        
        # Facção
        ttk.Label(frame_principal, text="Facção:", font=('Arial', 9, 'bold')).grid(
            row=1, column=4, sticky='e', padx=(10, 2), pady=3)
        campos['Faccao'] = criar_entry_readonly(frame_principal, registro.get('Faccao', ''), width=20)
        campos['Faccao'].grid(row=1, column=5, sticky='w', padx=2, pady=3)
        
        # Descrição
        ttk.Label(frame_principal, text="Descrição:", font=('Arial', 9, 'bold')).grid(
            row=2, column=0, sticky='e', padx=(5, 2), pady=3)
        campos['Descricao'] = criar_entry_readonly(frame_principal, registro.get('Descricao', ''), width=70)
        campos['Descricao'].grid(row=2, column=1, columnspan=5, sticky='w', padx=2, pady=3)
        
        # ============================================================
        # CAMPOS COMPARTILHADOS (EDITÁVEIS)
        # ============================================================
        frame_compart = ttk.LabelFrame(
            main_frame, 
            text=f"🔗 Campos Compartilhados (aplicam a TODAS as {qtd_compartilhado} linhas)", 
            padding=10
        )
        frame_compart.pack(fill='x', pady=5)
        
        frame_compart.grid_columnconfigure(0, weight=1)
        frame_compart.grid_columnconfigure(2, weight=1)
        
        ttk.Label(frame_compart, text="Cortou em:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky='e', padx=(5, 2), pady=3)
        campos['Cortou em'] = ttk.Entry(frame_compart, font=('Arial', 9), width=20)
        campos['Cortou em'].insert(0, str(registro.get('Cortou em', '')))
        campos['Cortou em'].grid(row=0, column=1, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_compart, text="Valor (R$):", font=('Arial', 9, 'bold')).grid(
            row=0, column=2, sticky='e', padx=(10, 2), pady=3)
        campos['Valor'] = ttk.Entry(frame_compart, font=('Arial', 9), width=18)
        campos['Valor'].insert(0, str(registro.get('Valor', '')))
        campos['Valor'].grid(row=0, column=3, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_compart, text="Observações:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky='ne', padx=(5, 2), pady=3)
        campos['Observacoes'] = tk.Text(frame_compart, font=('Arial', 9), height=3, width=60, wrap=tk.WORD)
        campos['Observacoes'].insert('1.0', str(registro.get('Observacoes', '')))
        campos['Observacoes'].grid(row=1, column=1, columnspan=3, sticky='w', padx=2, pady=3)
        
        # ============================================================
        # TAMANHOS (EDITÁVEIS)
        # ============================================================
        frame_tamanhos = ttk.Frame(main_frame)
        frame_tamanhos.pack(fill='x', pady=5)
        
        frame_env = ttk.LabelFrame(frame_tamanhos, text="📦 Enviados (desta linha)", padding=8)
        frame_env.pack(side='left', fill='x', expand=True, padx=(0, 3))
        
        tamanhos = ['PP', 'P', 'M', 'G', 'GG', 'U']
        for i, tam in enumerate(tamanhos):
            ttk.Label(frame_env, text=f"{tam}:", font=('Arial', 9)).grid(
                row=0, column=i*2, padx=3, pady=2, sticky='e')
            campos[tam] = ttk.Entry(frame_env, width=6, font=('Arial', 9))
            valor = registro.get(tam, '0')
            try:
                if float(valor) == int(float(valor)):
                    campos[tam].insert(0, str(int(float(valor))))
                else:
                    campos[tam].insert(0, str(valor))
            except:
                campos[tam].insert(0, '0')
            campos[tam].grid(row=0, column=i*2+1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_env, text="Total:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, padx=3, pady=3, sticky='e')
        campos['Total'] = ttk.Entry(frame_env, width=10, font=('Arial', 9, 'bold'))
        try:
            qt_total = float(registro.get('Total', '0'))
            campos['Total'].insert(0, str(int(qt_total)) if qt_total == int(qt_total) else str(qt_total))
        except:
            campos['Total'].insert(0, '0')
        campos['Total'].grid(row=1, column=1, columnspan=5, padx=3, pady=3, sticky='w')
        
        frame_ret = ttk.LabelFrame(frame_tamanhos, text="✅ Retornados (desta linha)", padding=8)
        frame_ret.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        completos = ['Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U']
        for i, ctam in enumerate(completos):
            tamanho = ctam.split()[1]
            ttk.Label(frame_ret, text=f"{tamanho}:", font=('Arial', 9)).grid(
                row=0, column=i*2, padx=3, pady=2, sticky='e')
            campos[ctam] = ttk.Entry(frame_ret, width=6, font=('Arial', 9))
            valor = registro.get(ctam, '0')
            try:
                if float(valor) == int(float(valor)):
                    campos[ctam].insert(0, str(int(float(valor))))
                else:
                    campos[ctam].insert(0, str(valor))
            except:
                campos[ctam].insert(0, '0')
            campos[ctam].grid(row=0, column=i*2+1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_ret, text="Total:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, padx=3, pady=3, sticky='e')
        campos['Ret Total'] = ttk.Entry(frame_ret, width=10, font=('Arial', 9, 'bold'))
        try:
            ctotal = float(registro.get('Ret Total', '0'))
            campos['Ret Total'].insert(0, str(int(ctotal)) if ctotal == int(ctotal) else str(ctotal))
        except:
            campos['Ret Total'].insert(0, '0')
        campos['Ret Total'].grid(row=1, column=1, columnspan=5, padx=3, pady=3, sticky='w')
        
        # ============================================================
        # DEFEITOS E STATUS
        # ============================================================
        frame_inferior = ttk.Frame(main_frame)
        frame_inferior.pack(fill='x', pady=5)
        
        frame_def = ttk.LabelFrame(frame_inferior, text="⚠️ Defeitos (desta linha)", padding=8)
        frame_def.pack(side='left', fill='x', expand=True, padx=(0, 3))
        
        defs = ['Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U']
        for i, dtam in enumerate(defs):
            tamanho = dtam.split()[1]
            ttk.Label(frame_def, text=f"{tamanho}:", font=('Arial', 9)).grid(
                row=0, column=i*2, padx=3, pady=2, sticky='e')
            campos[dtam] = ttk.Entry(frame_def, width=6, font=('Arial', 9))
            valor = registro.get(dtam, '0')
            try:
                if float(valor) == int(float(valor)):
                    campos[dtam].insert(0, str(int(float(valor))))
                else:
                    campos[dtam].insert(0, str(valor))
            except:
                campos[dtam].insert(0, '0')
            campos[dtam].grid(row=0, column=i*2+1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_def, text="Total:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, padx=3, pady=3, sticky='e')
        campos['Def Total'] = ttk.Entry(frame_def, width=10, font=('Arial', 9, 'bold'))
        try:
            dtotal = float(registro.get('Def Total', '0'))
            campos['Def Total'].insert(0, str(int(dtotal)) if dtotal == int(dtotal) else str(dtotal))
        except:
            campos['Def Total'].insert(0, '0')
        campos['Def Total'].grid(row=1, column=1, columnspan=5, padx=3, pady=3, sticky='w')
        
        frame_status = ttk.LabelFrame(frame_inferior, text="📋 Status (desta linha)", padding=8)
        frame_status.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        ttk.Label(frame_status, text="Data Chegada:", font=('Arial', 9)).grid(
            row=0, column=0, sticky='e', padx=3, pady=2)
        campos['Data Chegada'] = ttk.Entry(frame_status, font=('Arial', 9), width=15)
        campos['Data Chegada'].insert(0, str(registro.get('Data Chegada', '')))
        campos['Data Chegada'].grid(row=0, column=1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_status, text="Status:", font=('Arial', 9)).grid(
            row=1, column=0, sticky='e', padx=3, pady=2)
        status_options = ['EM ANDAMENTO', 'FINALIZADO', 'CANCELADO']
        campos['Status'] = ttk.Combobox(frame_status, 
                                    values=status_options,
                                    width=13, state="readonly")
        status_atual = str(registro.get('Status', 'EM ANDAMENTO')).upper()
        campos['Status'].set(status_atual)
        campos['Status'].grid(row=1, column=1, padx=3, pady=2, sticky='w')
        
        # ============================================================
        # BOTÕES
        # ============================================================
        frame_botoes = ttk.Frame(main_frame)
        frame_botoes.pack(fill='x', pady=15)
        
        btn_chegou = ttk.Button(
            frame_botoes, text="✅ Chegou tudo", 
            command=lambda: self.preencher_chegou_tudo(campos)
        )
        btn_chegou.pack(side='left', padx=5)
        
        btn_excluir = ttk.Button(
            frame_botoes, text="🗑️ Excluir Linha", 
            command=lambda: self.excluir_registro(idx, janela)
        )
        btn_excluir.pack(side='left', padx=5)
        
        btn_salvar = ttk.Button(
            frame_botoes, text="💾 Salvar", 
            command=lambda: self.salvar_edicao(idx, campos, janela)
        )
        btn_salvar.pack(side='right', padx=5)
        
        btn_fechar = ttk.Button(
            frame_botoes, text="❌ Fechar", 
            command=janela.destroy
        )
        btn_fechar.pack(side='right', padx=5)
        
        # Binds
        for tam in tamanhos:
            campos[tam].bind('<KeyRelease>', lambda e, c=campos: self.calcular_total_edicao(c))
        for ctam in completos:
            campos[ctam].bind('<KeyRelease>', lambda e, c=campos: self.calcular_ctotal_edicao(c))
        for dtam in defs:
            campos[dtam].bind('<KeyRelease>', lambda e, c=campos: self.calcular_dtotal_edicao(c))
        
        campos['Cortou em'].focus_set()
    
    def calcular_dtotal_edicao(self, campos):
        try:
            total = 0
            for dtam in ['Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U']:
                valor = campos[dtam].get().strip()
                if valor:
                    total += float(valor.replace(',', '.'))
            campos['Def Total'].delete(0, tk.END)
            campos['Def Total'].insert(0, str(int(total)) if total == int(total) else f"{total:.1f}")
        except:
            pass
    
    def calcular_total_edicao(self, campos):
        try:
            total = 0
            for tam in ['PP', 'P', 'M', 'G', 'GG', 'U']:
                valor = campos[tam].get().strip()
                if valor:
                    total += float(valor.replace(',', '.'))
            campos['Total'].delete(0, tk.END)
            campos['Total'].insert(0, str(int(total)) if total == int(total) else f"{total:.1f}")
        except:
            pass
    
    def calcular_ctotal_edicao(self, campos):
        try:
            total = 0
            for ctam in ['Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U']:
                valor = campos[ctam].get().strip()
                if valor:
                    total += float(valor.replace(',', '.'))
            campos['Ret Total'].delete(0, tk.END)
            campos['Ret Total'].insert(0, str(int(total)) if total == int(total) else f"{total:.1f}")
        except:
            pass
    
    def preencher_chegou_tudo(self, campos):
        try:
            tamanhos = ['PP', 'P', 'M', 'G', 'GG', 'U']
            completos = ['Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U']
            
            for i, tam in enumerate(tamanhos):
                valor_enviado = campos[tam].get().strip()
                if valor_enviado:
                    try:
                        valor_num = float(valor_enviado.replace(',', '.'))
                        valor_texto = str(int(valor_num)) if valor_num == int(valor_num) else valor_enviado
                    except:
                        valor_texto = valor_enviado
                    campos[completos[i]].delete(0, tk.END)
                    campos[completos[i]].insert(0, valor_texto)
                else:
                    campos[completos[i]].delete(0, tk.END)
                    campos[completos[i]].insert(0, '0')
            
            self.calcular_ctotal_edicao(campos)
            
            data_atual = datetime.now().strftime('%d/%m/%Y')
            campos['Data Chegada'].delete(0, tk.END)
            campos['Data Chegada'].insert(0, data_atual)
            campos['Status'].set('FINALIZADO')
            
            messagebox.showinfo("Sucesso", 
                f"✅ Todos os tamanhos marcados como recebidos!\n"
                f"📅 Data: {data_atual}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro: {str(e)}")
    
    def salvar_edicao(self, idx, campos, janela):
        """
        Salva edições aplicando:
        - Campos compartilhados (Cortou em, Valor, Observações) para todas as linhas com mesmo Ciclo+OP
        - Campos individuais apenas para esta linha
        """
        registro = self.df_banco.loc[idx]
        ciclo_atual = str(registro.get('Ciclo', '')).strip()
        op_atual = str(registro.get('OP', '')).strip()
        
        # Coletar dados dos campos
        dados = {}
        for key, widget in campos.items():
            if key == 'Observacoes':
                dados[key] = widget.get('1.0', tk.END).strip()
            elif isinstance(widget, ttk.Combobox):
                dados[key] = widget.get().strip()
            else:
                dados[key] = widget.get().strip()
        
        # Validar campos não editáveis não foram alterados (segurança)
        for campo in self.CAMPOS_NAO_EDITAVEIS:
            if campo in dados and campo in registro:
                if str(dados[campo]).strip() != str(registro[campo]).strip():
                    messagebox.showerror("Erro", 
                        f"Campo '{campo}' não pode ser alterado (chave de unicidade).")
                    return
        
        try:
            # Converter numéricos
            for tam in ['PP', 'P', 'M', 'G', 'GG', 'U']:
                valor = dados.get(tam, '0').replace(',', '.')
                dados[tam] = float(valor) if valor else 0.0
            
            qt_total = float(dados.get('Total', '0').replace(',', '.'))
            dados['Total'] = int(qt_total) if qt_total == int(qt_total) else qt_total
            
            for ctam in ['Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U']:
                valor = dados.get(ctam, '0').replace(',', '.')
                dados[ctam] = float(valor) if valor else 0.0
            
            ctotal = float(dados.get('Ret Total', '0').replace(',', '.'))
            dados['Ret Total'] = int(ctotal) if ctotal == int(ctotal) else ctotal
            
            for dtam in ['Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U']:
                valor = dados.get(dtam, '0').replace(',', '.')
                dados[dtam] = float(valor) if valor else 0.0
            
            dtotal = float(dados.get('Def Total', '0').replace(',', '.'))
            dados['Def Total'] = int(dtotal) if dtotal == int(dtotal) else dtotal
            
            if dados.get('Valor'):
                valor = dados['Valor'].replace(',', '.')
                dados['Valor'] = float(valor) if valor else 0.0
            else:
                dados['Valor'] = 0.0
        except Exception as e:
            messagebox.showerror("Erro", f"Erro em valores numéricos: {str(e)}")
            return
        
        # ============================================================
        # APLICAR CAMPOS INDIVIDUAIS APENAS NESTA LINHA
        # ============================================================
        campos_individuais_edicao = [
            'Data Chegada', 'Status',
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total'
        ]
        
        for col in campos_individuais_edicao:
            if col in dados:
                self.df_banco.at[idx, col] = dados[col]
        
        # ============================================================
        # APLICAR CAMPOS COMPARTILHADOS PARA TODAS AS LINHAS COM MESMO Ciclo+OP
        # ============================================================
        mask_compartilhado = (
            (self.df_banco['Ciclo'].astype(str).str.strip() == ciclo_atual) &
            (self.df_banco['OP'].astype(str).str.strip() == op_atual)
        )
        
        for col in self.CAMPOS_COMPARTILHADOS:
            if col in dados:
                self.df_banco.loc[mask_compartilhado, col] = dados[col]
        
        self.salvar_banco()
        self.atualizar_abas_fornecedores()
        
        messagebox.showinfo("Sucesso", "🏖️ Registro atualizado com sucesso!")
        janela.destroy()
    
    def excluir_registro(self, idx, janela):
        resposta = messagebox.askyesno("Confirmar Exclusão", 
                                      "Tem certeza que deseja excluir esta linha?\n"
                                      "(Apenas esta linha, não a OP completa)")
        
        if resposta:
            self.df_banco = self.df_banco.drop(idx).reset_index(drop=True)
            self.salvar_banco()
            self.atualizar_abas_fornecedores()
            messagebox.showinfo("Excluído", "🗑️ Linha excluída!")
            janela.destroy()
    
    def exportar_fornecedor(self, fornecedor, df_fornecedor):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"{fornecedor}_dados.xlsx"
            )
            
            if file_path:
                df_fornecedor.to_excel(file_path, index=False)
                messagebox.showinfo("Exportar", f"🏖️ Dados de {fornecedor} exportados!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    # ===== IMPORTAÇÃO =====
    
    def importar_ordens_banco(self):
        resposta = messagebox.askyesno(
            "🏄 Importar TOTVS - OPs Ativas",
            "Deseja importar as OPs ativas do TOTVS?\n\n"
            "• Apenas OPs com localização\n"
            "• Novas OPs serão adicionadas\n"
            "• OPs existentes serão atualizadas (preservando edições)\n"
            "• OPs que saíram de uma facção continuarão visíveis lá (histórico)\n"
            "• Dados editados (Cortou em, Valor, Obs., Status, etc.) são preservados"
        )
        
        if not resposta:
            return
        
        progress = tk.Toplevel(self.parent)
        progress.title("🏄 Importando...")
        progress.geometry("400x120")
        progress.transient(self.parent)
        progress.grab_set()
        progress.configure(bg=self.cores.BRANCO_NEVE)
        
        ttk.Label(progress, text="🏄 Buscando OPs ATIVAS no TOTVS...", 
                 font=('Arial', 11),
                 background=self.cores.BRANCO_NEVE).pack(pady=15)
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate', length=300)
        progress_bar.pack(pady=10)
        progress_bar.start(10)
        
        def import_thread():
            try:
                sucesso = self.carregar_ordens_ativas_banco()
                progress.destroy()
                if sucesso:
                    self.atualizar_abas_fornecedores()
                    messagebox.showinfo("Sucesso", 
                        "🏄 OPs ATIVAS importadas com sucesso!\n\n"
                        "• Novas ordens adicionadas\n"
                        "• OPs existentes atualizadas\n"
                        "• Dados editados preservados\n"
                        "• Ordens antigas mantidas nas facções (histórico)")
                else:
                    messagebox.showwarning("Aviso", 
                        "🏝️ Nenhuma OP ativa encontrada no TOTVS.")
            except Exception as e:
                progress.destroy()
                messagebox.showerror("Erro", f"Erro na importação: {str(e)}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=import_thread, daemon=True).start()
    
    def carregar_ordens_ativas_banco(self):
        try:
            self.atualizar_status("🏄 Carregando OPs ativas do TOTVS...")
            
            conn = self.conectar_banco()
            if not conn:
                return False
            
            self.locais_faccao = self.get_locais_faccao()
            
            if not self.locais_faccao:
                self.atualizar_status("🏝️ Nenhuma facção encontrada no TOTVS")
                conn.close()
                return False
            
            placeholders = ','.join(['%s'] * len(self.locais_faccao))
            query_ativas = f"""
                SELECT 
                    location_name as faccao,
                    reference_code as referencia,
                    reference_name as descricao,
                    cycle_code as ciclo,
                    order_code as op,
                    size_name as tamanho,
                    quantity as quantidade_total,
                    location_quantity as quantidade_faccao,
                    entry_date as data_entrada,
                    create_date as op_criada_em,
                    last_change_date as data_envio,
                    estimated_delivery_date as prazo_retorno
                FROM public.production_items 
                WHERE location_name IN ({placeholders})
                AND location_quantity > 0
                ORDER BY location_name, reference_code, cycle_code
            """
            
            df_novo = pd.read_sql_query(query_ativas, conn, params=self.locais_faccao)
            conn.close()
            
            if df_novo.empty:
                self.atualizar_status("🏝️ Nenhuma OP ativa encontrada")
                return False
            
            num_faccoes = df_novo['faccao'].nunique()
            num_ops = df_novo['op'].nunique()
            print(f"📊 OPs ATIVAS: {len(df_novo)} registros ({num_faccoes} facções, {num_ops} OPs)")
            self.atualizar_status(f"🏄 Encontradas {num_faccoes} facções com {num_ops} OPs ativas")
            
            df_processado = self.processar_dados_banco(df_novo)
            
            if df_processado.empty:
                return False
            
            df_processado = self.organizar_dados_silencioso(df_processado)
            
            resultado = self.integrar_dados_banco(df_processado)
            
            return resultado
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar ordens: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def importar_historico_banco(self):
        resposta = messagebox.askyesno(
            "📜 Importar Histórico TOTVS",
            "Deseja importar o HISTÓRICO do TOTVS?\n\n"
            "⚠️ Mais de 16.000 registros!\n\n"
            "• Apenas OPs SEM localização\n"
            "• OPs já concluídas/expedidas\n"
            "• Salvas em arquivo separado"
        )
        
        if not resposta:
            return
        
        progress = tk.Toplevel(self.parent)
        progress.title("📜 Importando Histórico...")
        progress.geometry("450x150")
        progress.transient(self.parent)
        progress.grab_set()
        progress.configure(bg=self.cores.BRANCO_NEVE)
        
        ttk.Label(progress, text="📜 Buscando HISTÓRICO...", 
                 font=('Arial', 11),
                 background=self.cores.BRANCO_NEVE).pack(pady=15)
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate', length=350)
        progress_bar.pack(pady=10)
        progress_bar.start(10)
        
        def import_thread():
            try:
                sucesso = self.carregar_historico_banco()
                progress.destroy()
                if sucesso:
                    self.atualizar_historico()
                    total = len(self.df_historico) if self.df_historico is not None else 0
                    messagebox.showinfo("Sucesso", 
                        f"📜 HISTÓRICO importado!\n\n"
                        f"• Total: {total} OPs")
                else:
                    messagebox.showwarning("Aviso", "Nenhuma OP encontrada no histórico.")
            except Exception as e:
                progress.destroy()
                messagebox.showerror("Erro", f"Erro: {str(e)}")
        
        threading.Thread(target=import_thread, daemon=True).start()
    
    def carregar_historico_banco(self):
        try:
            self.atualizar_status("📜 Carregando histórico...")
            
            conn = self.conectar_banco()
            if not conn:
                return False
            
            query_historico = """
                SELECT 
                    COALESCE(location_name, '') as faccao,
                    reference_code as referencia,
                    reference_name as descricao,
                    cycle_code as ciclo,
                    order_code as op,
                    size_name as tamanho,
                    quantity as quantidade_total,
                    location_quantity as quantidade_faccao,
                    entry_date as data_entrada,
                    create_date as op_criada_em,
                    last_change_date as data_envio,
                    estimated_delivery_date as prazo_retorno
                FROM public.production_items 
                WHERE (location_name IS NULL OR TRIM(location_name) = '')
                AND quantity > 0
                ORDER BY reference_code, cycle_code
            """
            
            df_historico_novo = pd.read_sql_query(query_historico, conn)
            conn.close()
            
            if df_historico_novo.empty:
                return False
            
            self.atualizar_status(f"📜 Processando {len(df_historico_novo)} registros...")
            
            df_hist_processado = self.processar_dados_historico(df_historico_novo)
            
            if df_hist_processado.empty:
                return False
            
            return self.integrar_dados_historico(df_hist_processado)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro: {str(e)}")
            return False
    
    def carregar_dados_banco_async(self):
        def thread_func():
            try:
                self.carregar_ordens_ativas_banco()
                self.parent.after(0, self.atualizar_abas_fornecedores)
            except Exception as e:
                print(f"Erro: {e}")
        
        threading.Thread(target=thread_func, daemon=True).start()
    
    def conectar_banco(self):
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = True
            return conn
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return None
    
    def get_locais_faccao(self):
        conn = self.conectar_banco()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT location_name 
                    FROM public.production_items 
                    WHERE location_name IS NOT NULL 
                    AND location_name != ''
                    ORDER BY location_name
                """)
                todos_locais = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                return todos_locais
                
        except Exception as e:
            print(f"Erro: {e}")
            if conn:
                conn.close()
            return []
    
    def processar_dados_banco(self, df):
        """
        Processa dados do banco (ativas)
        
        IMPORTANTE:
        - 'quantity' = quantidade TOTAL da OP (repetida por tamanho) → usar como Total Geral
        - 'location_quantity' = quantidade POR TAMANHO naquela facção → usar para PP, P, M, G, GG, U
        """
        if df.empty:
            return pd.DataFrame()
        
        print(f"📊 Processando {len(df)} registros do TOTVS...")
        
        tamanhos_padrao = ['PP', 'P', 'M', 'G', 'GG', 'U']
        
        # ============================================================
        # NORMALIZAR
        # ============================================================
        df = df.copy()
        df['tamanho'] = df['tamanho'].fillna('').astype(str).str.strip().str.upper()
        df['quantidade_total'] = pd.to_numeric(df['quantidade_total'], errors='coerce').fillna(0).astype(int)  # quantity
        df['location_quantity'] = pd.to_numeric(df['quantidade_faccao'], errors='coerce').fillna(0).astype(int)  # location_quantity
        
        # ============================================================
        # AGRUPAMENTO MANUAL
        # Chave: (faccao, referencia, ciclo, op, descricao, datas)
        # - Por chave: somamos location_quantity POR TAMANHO
        # - 'quantity' pegamos o valor máximo (é o total da OP, repetido)
        # ============================================================
        agrupado = {}
        
        for _, row in df.iterrows():
            faccao = str(row.get('faccao', '') or '').strip()
            referencia = str(row.get('referencia', '') or '').strip()
            ciclo = str(row.get('ciclo', '') or '').strip()
            op = str(row.get('op', '') or '').strip()
            descricao = str(row.get('descricao', '') or '').strip()
            tamanho = row.get('tamanho', '').strip().upper()
            qtd_total_op = int(row.get('quantidade_total', 0) or 0)  # quantity (total da OP)
            qtd_location = int(row.get('location_quantity', 0) or 0)  # location_quantity (por tamanho)
            data_entrada = row.get('data_entrada')
            op_criada_em = row.get('op_criada_em')
            data_envio = row.get('data_envio')
            prazo_retorno = row.get('prazo_retorno')
            
            chave = (faccao, referencia, ciclo, op, descricao, 
                     str(data_entrada) if pd.notna(data_entrada) else '',
                     str(op_criada_em) if pd.notna(op_criada_em) else '',
                     str(data_envio) if pd.notna(data_envio) else '',
                     str(prazo_retorno) if pd.notna(prazo_retorno) else '')
            
            if chave not in agrupado:
                agrupado[chave] = {
                    'faccao': faccao,
                    'referencia': referencia,
                    'ciclo': ciclo,
                    'op': op,
                    'descricao': descricao,
                    'data_entrada': data_entrada,
                    'op_criada_em': op_criada_em,
                    'data_envio': data_envio,
                    'prazo_retorno': prazo_retorno,
                    'quantity_total_op': qtd_total_op,  # total da OP (referência)
                    # Por tamanho: location_quantity (o que AINDA está com a facção)
                    'PP': 0, 'P': 0, 'M': 0, 'G': 0, 'GG': 0, 'U': 0,
                }
            
            # Atualiza quantity_total_op (pega o maior valor — é o total da OP)
            if qtd_total_op > agrupado[chave]['quantity_total_op']:
                agrupado[chave]['quantity_total_op'] = qtd_total_op
            
            # SOMA location_quantity no tamanho correspondente
            if tamanho in tamanhos_padrao:
                agrupado[chave][tamanho] += qtd_location
            else:
                # Tamanhos numéricos (34, 36, 38...) vão para 'U'
                agrupado[chave]['U'] += qtd_location
        
        print(f"📊 Agrupados em {len(agrupado)} chaves únicas")
        
        if not agrupado:
            return pd.DataFrame()
        
        # ============================================================
        # CRIAR DATAFRAME FINAL
        # ============================================================
        colunas_final = [
            'Faccao', 'Faccao_Original', 'Cidade', 'Referencia', 'Ciclo', 'OP', 
            'OP Criada em', 'Cortou em', 'Data Entrada', 'Descricao',
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total', 
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 
            'Ret Total', 'Data Chegada', 'Status', 'Valor', 'Prazo Retorno',
            'Observacoes',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
            'Quantity', 'Location_Quantity'
        ]
        
        registros = []
        
        for chave, dados in agrupado.items():
            # ============================================================
            # QUANTIDADES POR TAMANHO (location_quantity = AINDA com a facção)
            # ============================================================
            pp = dados['PP']
            p = dados['P']
            m = dados['M']
            g = dados['G']
            gg = dados['GG']
            u = dados['U']
            location_quantity_total = pp + p + m + g + gg + u
            
            if location_quantity_total == 0:
                continue
            
            # quantity_total_op = total real da OP (referência)
            quantity_total_op = dados['quantity_total_op']
            
            # ============================================================
            # ENVIADOS = o que a facção recebeu.
            # Como 'location_quantity' diminui conforme ela devolve,
            # usamos o MAIOR entre (location atual) e (quantity da OP)
            # como referência de enviados.
            # 
            # IMPORTANTE: enviados é PRESERVADO entre importações
            # (a lógica de merge preserva isso). Aqui é só o valor inicial.
            # ============================================================
            enviado_total = max(quantity_total_op, location_quantity_total)
            
            # Distribuir enviados proporcionalmente por tamanho
            if location_quantity_total > 0:
                for tam in tamanhos_padrao:
                    proporcao = dados[tam] / location_quantity_total
                    dados[f'env_{tam}'] = int(round(enviado_total * proporcao))
            else:
                for tam in tamanhos_padrao:
                    dados[f'env_{tam}'] = 0
            
            env_pp = dados.get('env_PP', 0)
            env_p = dados.get('env_P', 0)
            env_m = dados.get('env_M', 0)
            env_g = dados.get('env_G', 0)
            env_gg = dados.get('env_GG', 0)
            env_u = dados.get('env_U', 0)
            
            enviado_total_calculado = env_pp + env_p + env_m + env_g + env_gg + env_u
            
            # ============================================================
            # RETORNADOS = Enviado - Ainda com a facção
            # ============================================================
            ret_pp = max(0, env_pp - pp)
            ret_p = max(0, env_p - p)
            ret_m = max(0, env_m - m)
            ret_g = max(0, env_g - g)
            ret_gg = max(0, env_gg - gg)
            ret_u = max(0, env_u - u)
            ret_total = ret_pp + ret_p + ret_m + ret_g + ret_gg + ret_u
            
            # ============================================================
            # DATAS
            # ============================================================
            data_entrada_str = ''
            if pd.notna(dados.get('data_entrada')):
                try:
                    data_entrada_str = pd.to_datetime(dados['data_entrada']).strftime('%d/%m/%Y')
                except:
                    pass
            
            op_criada_str = ''
            if pd.notna(dados.get('op_criada_em')):
                try:
                    op_criada_str = pd.to_datetime(dados['op_criada_em']).strftime('%d/%m/%Y')
                except:
                    pass
            
            prazo_retorno_str = ''
            if pd.notna(dados.get('prazo_retorno')):
                try:
                    prazo_retorno_str = pd.to_datetime(dados['prazo_retorno']).strftime('%d/%m/%Y')
                except:
                    pass
            
            registros.append({
                'Faccao': '',
                'Faccao_Original': dados['faccao'],
                'Cidade': '',
                'Referencia': dados['referencia'],
                'Ciclo': dados['ciclo'],
                'OP': dados['op'],
                'OP Criada em': op_criada_str,
                'Cortou em': '',
                'Data Entrada': data_entrada_str,
                'Descricao': dados['descricao'],
                # ENVIADOS (distribuídos proporcionalmente)
                'PP': env_pp,
                'P': env_p,
                'M': env_m,
                'G': env_g,
                'GG': env_gg,
                'U': env_u,
                'Total': enviado_total_calculado,
                # AINDA COM A FACÇÃO (location_quantity)
                'Ret PP': ret_pp,
                'Ret P': ret_p,
                'Ret M': ret_m,
                'Ret G': ret_g,
                'Ret GG': ret_gg,
                'Ret U': ret_u,
                'Ret Total': ret_total,
                'Data Chegada': '',
                'Status': 'FINALIZADO' if ret_total >= enviado_total_calculado else 'EM ANDAMENTO',
                'Valor': 0.0,
                'Prazo Retorno': prazo_retorno_str,
                'Observacoes': '',
                'Def PP': 0,
                'Def P': 0,
                'Def M': 0,
                'Def G': 0,
                'Def GG': 0,
                'Def U': 0,
                'Def Total': 0,
                'Quantity': quantity_total_op,
                'Location_Quantity': location_quantity_total
            })
        
        df_final = pd.DataFrame(registros, columns=colunas_final)
        print(f"📊 Registros finais criados: {len(df_final)}")
        
        if not df_final.empty:
            exemplo = df_final.iloc[0]
            print(f"📊 Exemplo: OP={exemplo['OP']} Ref={exemplo['Referencia']}")
            print(f"   Enviado: PP={exemplo['PP']} P={exemplo['P']} M={exemplo['M']} "
                  f"G={exemplo['G']} GG={exemplo['GG']} U={exemplo['U']} Total={exemplo['Total']}")
            print(f"   Ainda com facção: {exemplo['Location_Quantity']} peças")
            print(f"   Quantity (total OP): {exemplo['Quantity']}")
        
        return df_final
    
    def processar_dados_historico(self, df):
        """Processa dados do histórico"""
        if df.empty:
            return pd.DataFrame()
        
        tamanhos_padrao = ['PP', 'P', 'M', 'G', 'GG', 'U']
        
        df = df.copy()
        df['tamanho'] = df['tamanho'].fillna('').astype(str).str.strip().str.upper()
        df['quantidade_total'] = pd.to_numeric(
            df['quantidade_total'].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).fillna(0).astype(int)
        
        df = df[df['quantidade_total'] > 0]
        
        if df.empty:
            return pd.DataFrame()
        
        agrupado = {}
        
        for _, row in df.iterrows():
            op = str(row.get('op', '') or '').strip()
            referencia = str(row.get('referencia', '') or '').strip()
            ciclo = str(row.get('ciclo', '') or '').strip()
            descricao = str(row.get('descricao', '') or '').strip()
            tamanho = row.get('tamanho', '')
            qtd = int(row.get('quantidade_total', 0))
            
            chave = (op, referencia, ciclo, descricao)
            
            if chave not in agrupado:
                agrupado[chave] = {
                    'op': op, 'referencia': referencia, 'ciclo': ciclo, 'descricao': descricao,
                    'data_entrada': row.get('data_entrada'),
                    'op_criada_em': row.get('op_criada_em'),
                    'PP': 0, 'P': 0, 'M': 0, 'G': 0, 'GG': 0, 'U': 0,
                }
            
            if tamanho in tamanhos_padrao:
                agrupado[chave][tamanho] += qtd
            else:
                agrupado[chave]['U'] += qtd
        
        if not agrupado:
            return pd.DataFrame()
        
        colunas = [
            'Faccao', 'Referencia', 'Ciclo', 'OP',
            'OP Criada em', 'Cortou em', 'Data Entrada', 'Data Chegada',
            'Descricao',
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
            'Status', 'Observacoes'
        ]
        
        registros = []
        
        for chave, dados in agrupado.items():
            pp, p, m = dados['PP'], dados['P'], dados['M']
            g, gg, u = dados['G'], dados['GG'], dados['U']
            quantidade_total = pp + p + m + g + gg + u
            
            if quantidade_total == 0:
                continue
            
            data_entrada_str = ''
            if pd.notna(dados.get('data_entrada')):
                try:
                    data_entrada_str = pd.to_datetime(dados['data_entrada']).strftime('%d/%m/%Y')
                except:
                    pass
            
            op_criada_str = ''
            if pd.notna(dados.get('op_criada_em')):
                try:
                    op_criada_str = pd.to_datetime(dados['op_criada_em']).strftime('%d/%m/%Y')
                except:
                    pass
            
            registros.append({
                'Faccao': 'HISTÓRICO',
                'Referencia': dados['referencia'],
                'Ciclo': dados['ciclo'],
                'OP': dados['op'],
                'OP Criada em': op_criada_str,
                'Cortou em': '',
                'Data Entrada': data_entrada_str,
                'Data Chegada': '',
                'Descricao': dados['descricao'],
                'PP': pp, 'P': p, 'M': m, 'G': g, 'GG': gg, 'U': u,
                'Total': quantidade_total,
                'Ret PP': 0, 'Ret P': 0, 'Ret M': 0, 'Ret G': 0, 'Ret GG': 0, 'Ret U': 0,
                'Ret Total': 0,
                'Def PP': 0, 'Def P': 0, 'Def M': 0, 'Def G': 0, 'Def GG': 0, 'Def U': 0,
                'Def Total': 0,
                'Status': 'FINALIZADO',
                'Observacoes': 'OP sem location (produção concluída)'
            })
        
        return pd.DataFrame(registros, columns=colunas)
    
    def integrar_dados_banco(self, df_novo):
        """
        Integra dados do TOTVS PRESERVANDO 100% das edições locais.
        
        REGRAS:
        1. Se a linha (OP+Referencia+Ciclo+Faccao) JÁ EXISTE → 
           atualiza APENAS campos do TOTVS, preserva TODAS as edições
        2. Se a linha é NOVA → adiciona com valores padrão
        3. Se a linha EXISTE mas NÃO veio na importação →
           mantém intacta (histórico por facção)
        4. Campos compartilhados (Cortou em, Valor, Observações) são propagados
           para TODAS as linhas com mesmo Ciclo+OP
        """
        if df_novo.empty:
            return False
        
        print("\n" + "="*70)
        print("📥 INTEGRANDO DADOS DO TOTVS")
        print("="*70)
        
        chave_ordem = ['OP', 'Referencia', 'Ciclo', 'Faccao']
        
        for col in chave_ordem:
            if col not in df_novo.columns:
                df_novo[col] = ''
            df_novo[col] = df_novo[col].fillna('').astype(str).str.strip()
        
        # Remover duplicatas
        df_novo = df_novo.drop_duplicates(subset=chave_ordem, keep='first').copy()
        
        # ============================================================
        # PRIMEIRA IMPORTAÇÃO
        # ============================================================
        if self.df_banco is None or self.df_banco.empty:
            self.df_banco = df_novo.copy()
            self.salvar_banco()
            self.atualizar_status(f"🏄 Importadas {len(df_novo)} ordens")
            print(f"✅ Primeira importação: {len(df_novo)} registros")
            print("="*70 + "\n")
            return True
        
        # ============================================================
        # GARANTIR COLUNAS
        # ============================================================
        for col in df_novo.columns:
            if col not in self.df_banco.columns:
                self.df_banco[col] = ''
        
        df_local = self.df_banco.copy()
        for col in chave_ordem:
            if col not in df_local.columns:
                df_local[col] = ''
            df_local[col] = df_local[col].fillna('').astype(str).str.strip()
        
        # ============================================================
        # CRIAR MAPA DE CHAVES EXISTENTES
        # ============================================================
        mapa_existentes = {}
        for idx, row in df_local.iterrows():
            chave = (row['OP'], row['Referencia'], row['Ciclo'], row['Faccao'])
            mapa_existentes[chave] = idx
        
        # ============================================================
        # MAPA DE CAMPOS COMPARTILHADOS POR CICLO+OP
        # (Cortou em, Valor, Observações - aplicam a todas as linhas)
        # ============================================================
        compartilhados_por_ciclo_op = {}
        
        for _, row in df_local.iterrows():
            ciclo = str(row.get('Ciclo', '')).strip()
            op = str(row.get('OP', '')).strip()
            chave_cop = (ciclo, op)
            
            # Verifica se algum dos campos compartilhados tem valor
            cortou = str(row.get('Cortou em', '')).strip()
            valor = row.get('Valor', 0)
            observacoes = str(row.get('Observacoes', '')).strip()
            
            if chave_cop not in compartilhados_por_ciclo_op:
                compartilhados_por_ciclo_op[chave_cop] = {
                    'Cortou em': '',
                    'Valor': 0.0,
                    'Observacoes': ''
                }
            
            # Se algum valor existe, mantém o primeiro encontrado (não vazio)
            if cortou and not compartilhados_por_ciclo_op[chave_cop]['Cortou em']:
                compartilhados_por_ciclo_op[chave_cop]['Cortou em'] = cortou
            if valor and float(valor) > 0 and compartilhados_por_ciclo_op[chave_cop]['Valor'] == 0:
                compartilhados_por_ciclo_op[chave_cop]['Valor'] = float(valor)
            if observacoes and not compartilhados_por_ciclo_op[chave_cop]['Observacoes']:
                compartilhados_por_ciclo_op[chave_cop]['Observacoes'] = observacoes
        
        print(f"📊 Linhas no banco: {len(df_local)}")
        print(f"📊 Linhas vindas do TOTVS: {len(df_novo)}")
        print(f"📊 Chaves compartilhadas (Ciclo+OP): {len(compartilhados_por_ciclo_op)}")
        
        # ============================================================
        # PROCESSAR CADA LINHA DO TOTVS
        # ============================================================
        adicionados = 0
        atualizados = 0
        
        for _, row_nova in df_novo.iterrows():
            chave = (row_nova['OP'], row_nova['Referencia'], 
                     row_nova['Ciclo'], row_nova['Faccao'])
            
            if chave in mapa_existentes:
                # ============================================================
                # JÁ EXISTE - ATUALIZAR APENAS CAMPOS DO TOTVS
                # ============================================================
                idx = mapa_existentes[chave]
                
                # Atualiza APENAS campos que vêm do TOTVS
                # (NÃO toca em nada editável)
                campos_totvs = [
                    'OP Criada em',      # do create_date
                    'Data Entrada',      # do entry_date
                    'Prazo Retorno',
                    'Descricao',
                    'Quantity',
                    'Location_Quantity'
                ]
                
                for campo in campos_totvs:
                    if campo in row_nova.index:
                        valor_novo = row_nova[campo]
                        # Só atualiza se o valor não for vazio
                        if pd.notna(valor_novo) and str(valor_novo).strip():
                            df_local.at[idx, campo] = valor_novo
                
                atualizados += 1
            else:
                # ============================================================
                # NOVA LINHA - ADICIONAR
                # ============================================================
                nova_linha = row_nova.to_dict()
                
                # Garantir campos editáveis com valores padrão
                for campo in ['Cortou em', 'Data Chegada', 'Observacoes']:
                    if campo not in nova_linha or pd.isna(nova_linha[campo]):
                        nova_linha[campo] = ''
                
                for campo in ['PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
                             'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
                             'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
                             'Valor']:
                    if campo not in nova_linha or pd.isna(nova_linha[campo]):
                        nova_linha[campo] = 0
                
                df_local = pd.concat([df_local, pd.DataFrame([nova_linha])], ignore_index=True)
                mapa_existentes[chave] = len(df_local) - 1
                adicionados += 1
        
        print(f"📊 Adicionados: {adicionados} | Atualizados: {atualizados}")
        
        # ============================================================
        # PROPAGAR CAMPOS COMPARTILHADOS
        # (Garante que mesmo após importação, todas as linhas
        #  com mesmo Ciclo+OP recebam os valores editados)
        # ============================================================
        propagados = 0
        
        for idx, row in df_local.iterrows():
            ciclo = str(row.get('Ciclo', '')).strip()
            op = str(row.get('OP', '')).strip()
            chave_cop = (ciclo, op)
            
            if chave_cop in compartilhados_por_ciclo_op:
                dados_comp = compartilhados_por_ciclo_op[chave_cop]
                
                # Aplicar Cortou em (se vazio localmente)
                if dados_comp['Cortou em']:
                    valor_local = str(row.get('Cortou em', '')).strip()
                    if not valor_local:
                        df_local.at[idx, 'Cortou em'] = dados_comp['Cortou em']
                        propagados += 1
                
                # Aplicar Valor (se zerado localmente)
                if dados_comp['Valor'] > 0:
                    valor_local = row.get('Valor', 0)
                    try:
                        valor_num = float(valor_local) if pd.notna(valor_local) else 0
                    except:
                        valor_num = 0
                    if valor_num == 0:
                        df_local.at[idx, 'Valor'] = dados_comp['Valor']
                
                # Aplicar Observações (se vazio localmente)
                if dados_comp['Observacoes']:
                    valor_local = str(row.get('Observacoes', '')).strip()
                    if not valor_local:
                        df_local.at[idx, 'Observacoes'] = dados_comp['Observacoes']
        
        print(f"📊 Campos compartilhados propagados: {propagados}")
        
        # ============================================================
        # SALVAR
        # ============================================================
        self.df_banco = df_local.copy()
        self.salvar_banco()
        
        # ============================================================
        # LOG FINAL
        # ============================================================
        # Contar quantas linhas têm Cortou em preenchido (auditoria)
        if 'Cortou em' in self.df_banco.columns:
            com_cortou = self.df_banco[
                self.df_banco['Cortou em'].astype(str).str.strip() != ''
            ].shape[0]
            print(f"📊 Linhas com 'Cortou em' preenchido: {com_cortou}")
        
        if 'Observacoes' in self.df_banco.columns:
            com_obs = self.df_banco[
                self.df_banco['Observacoes'].astype(str).str.strip() != ''
            ].shape[0]
            print(f"📊 Linhas com 'Observações' preenchidas: {com_obs}")
        
        print("="*70 + "\n")
        
        status_msg = f"Banco: {adicionados} novos, {atualizados} atualizados (edições preservadas)"
        self.atualizar_status(status_msg)
        
        return True
    
    def integrar_dados_historico(self, df_novo):
        """Integra dados do histórico"""
        if df_novo.empty:
            return False
        
        chave_ordem = ['OP', 'Referencia', 'Ciclo']
        
        for col in chave_ordem:
            if col not in df_novo.columns:
                df_novo[col] = ''
            df_novo[col] = df_novo[col].fillna('').astype(str).str.strip()
        
        df_novo = df_novo.drop_duplicates(subset=chave_ordem, keep='first').copy()
        
        if not hasattr(self, 'df_historico') or self.df_historico is None or self.df_historico.empty:
            self.df_historico = df_novo.copy()
            self.salvar_historico()
            self.atualizar_status(f"📜 Importadas {len(df_novo)} OPs no histórico")
            return True
        
        df_merged = self.df_historico.copy()
        for col in chave_ordem:
            if col not in df_merged.columns:
                df_merged[col] = ''
            df_merged[col] = df_merged[col].fillna('').astype(str).str.strip()
        
        chaves_existentes = set()
        for _, row in df_merged.iterrows():
            chaves_existentes.add((row['OP'], row['Referencia'], row['Ciclo']))
        
        adicionados = 0
        
        for _, row in df_novo.iterrows():
            chave = (row['OP'], row['Referencia'], row['Ciclo'])
            if chave not in chaves_existentes:
                df_merged = pd.concat([df_merged, pd.DataFrame([row.to_dict()])], ignore_index=True)
                chaves_existentes.add(chave)
                adicionados += 1
        
        self.df_historico = df_merged.copy()
        self.salvar_historico()
        
        self.atualizar_status(f"Histórico: {adicionados} novos")
        return True
    
    # ===== FUNÇÕES DE ADIÇÃO =====
    
    def adicionar_produto(self):
        """Janela para adicionar novo produto"""
        janela = tk.Toplevel(self.parent)
        janela.title("🏖️ Adicionar Produto")
        janela.geometry("600x500")
        janela.transient(self.parent)
        janela.grab_set()
        janela.configure(bg=self.cores.BRANCO_NEVE)
        
        frame = ttk.Frame(janela, padding=20)
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="➕ Nova Ordem de Produção", 
                font=('Arial', 16, 'bold'),
                fg=self.cores.AZUL_MAR_ESCURO,
                bg=self.cores.BRANCO_NEVE).pack(pady=10)
        
        campos = {}
        campos_principais = [
            ('OP *:', 'OP'),
            ('Referência *:', 'Referencia'),
            ('Ciclo *:', 'Ciclo'),
            ('Facção:', 'Faccao'),
            ('Descrição:', 'Descricao')
        ]
        
        for i, (label, key) in enumerate(campos_principais):
            ttk.Label(frame, text=label, font=('Arial', 10)).grid(row=i, column=0, sticky='e', pady=5, padx=5)
            campos[key] = ttk.Entry(frame, font=('Arial', 10), width=40)
            campos[key].grid(row=i, column=1, pady=5, padx=5, sticky='w')
        
        qtd_frame = ttk.LabelFrame(frame, text="📦 Quantidades", padding=10)
        qtd_frame.grid(row=len(campos_principais), column=0, columnspan=2, pady=10, sticky='ew')
        
        tamanhos = ['PP', 'P', 'M', 'G', 'GG', 'U']
        for i, tam in enumerate(tamanhos):
            ttk.Label(qtd_frame, text=f"{tam}:").grid(row=0, column=i*2, padx=5, pady=5)
            campos[tam] = ttk.Entry(qtd_frame, width=8)
            campos[tam].insert(0, '0')
            campos[tam].grid(row=0, column=i*2+1, padx=5, pady=5)
        
        def salvar():
            if not campos['OP'].get().strip() or not campos['Referencia'].get().strip() or not campos['Ciclo'].get().strip():
                messagebox.showwarning("Aviso", "Preencha OP, Referência e Ciclo!")
                return
            
            messagebox.showinfo("Sucesso", "🏖️ Produto adicionado com sucesso!")
            janela.destroy()
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(campos_principais)+1, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="💾 Salvar", command=salvar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Cancelar", command=janela.destroy).pack(side=tk.LEFT, padx=5)
    
    # ===== PÁGINA DE RELATÓRIOS =====
    
    def criar_pagina_relatorios(self):
        """Cria página de relatórios e gráficos"""
        for widget in self.frame_relatorios.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self.frame_relatorios)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(
            main_frame,
            text="📊 Relatórios e Gráficos",
            font=('Arial', 20, 'bold'),
            fg=self.cores.AZUL_MAR_ESCURO,
            bg=self.cores.BRANCO_NEVE
        ).pack(pady=10)
        
        frame_controles = ttk.LabelFrame(main_frame, text="🎯 Controles do Relatório", padding=10)
        frame_controles.pack(fill='x', pady=10)
        
        btn_frame = ttk.Frame(frame_controles)
        btn_frame.pack(fill='x', pady=5)
        
        botoes = [
            ("📈 Status", self.gerar_relatorio_status),
            ("👥 Por Facção", self.gerar_relatorio_fornecedor),
            ("📅 Por Mês", self.gerar_relatorio_mensal),
            ("💲 Valor", self.gerar_relatorio_valor)
        ]
        
        for texto, comando in botoes:
            btn = tk.Button(
                btn_frame,
                text=texto,
                command=comando,
                font=('Arial', 10, 'bold'),
                bg=self.cores.AZUL_MAR,
                fg=self.cores.BRANCO,
                relief=tk.FLAT,
                padx=15,
                pady=8,
                cursor='hand2'
            )
            btn.pack(side='left', padx=5)
            
            def on_enter(e, b=btn):
                b.config(bg=self.cores.CORAL)
            def on_leave(e, b=btn):
                b.config(bg=self.cores.AZUL_MAR)
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
        
        self.frame_graficos = ttk.Frame(main_frame)
        self.frame_graficos.pack(fill='both', expand=True, pady=10)
    
    def get_dados_relatorio(self):
        """Retorna os dados para relatórios"""
        if self.df_filtrado is not None and not self.df_filtrado.empty:
            return self.df_filtrado
        return self.df_banco
    
    def gerar_relatorio_status(self):
        """Gera gráfico de status de produção"""
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()
        
        df = self.get_dados_relatorio()
        
        if df is None or df.empty:
            ttk.Label(self.frame_graficos, text="Nenhum dado disponível para gerar relatório", 
                     font=('Arial', 12),
                     background=self.cores.BRANCO_NEVE).pack()
            return
        
        status_counts = df['Status'].value_counts()
        
        fig = Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111)
        
        colors = ['#2ecc71', '#f39c12', '#e74c3c']
        wedges, texts, autotexts = ax.pie(status_counts.values, labels=status_counts.index,
                                        autopct='%1.1f%%', colors=colors[:len(status_counts)])
        
        for text in texts:
            text.set_fontsize(12)
        for autotext in autotexts:
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')
        
        if self.df_filtrado is not None:
            ax.set_title('Distribuição por Status (Dados Filtrados)', fontsize=16, fontweight='bold')
        else:
            ax.set_title('Distribuição por Status', fontsize=16, fontweight='bold')
        
        ax.legend(wedges, status_counts.index, title="Status", loc="center left", 
                 bbox_to_anchor=(1, 0, 0.5, 1), fontsize=11)
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        frame_stats = ttk.Frame(self.frame_graficos)
        frame_stats.pack(pady=10)
        
        total = len(df)
        for status, count in status_counts.items():
            percent = (count / total) * 100
            ttk.Label(frame_stats, text=f"{status}: {count} ({percent:.1f}%)", 
                     font=('Arial', 10),
                     background=self.cores.BRANCO_NEVE).pack()
    
    def gerar_relatorio_fornecedor(self):
        """Gera gráfico de produção por fornecedor"""
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()
        
        df = self.get_dados_relatorio()
        
        if df is None or df.empty or 'Faccao' not in df.columns:
            ttk.Label(self.frame_graficos, text="Nenhum dado disponível", 
                     font=('Arial', 12),
                     background=self.cores.BRANCO_NEVE).pack()
            return
        
        fornecedor_stats = df.groupby('Faccao').agg({
            'PP': 'sum', 'P': 'sum', 'M': 'sum', 'G': 'sum', 'GG': 'sum', 'U': 'sum'
        }).reset_index()
        
        fornecedor_stats['Total'] = fornecedor_stats['PP'] + fornecedor_stats['P'] + \
                                   fornecedor_stats['M'] + fornecedor_stats['G'] + \
                                   fornecedor_stats['GG'] + fornecedor_stats['U']
        
        fornecedor_stats = fornecedor_stats.sort_values('Total', ascending=False).head(20)
        
        fig = Figure(figsize=(14, 7), dpi=100)
        ax = fig.add_subplot(111)
        
        x = np.arange(len(fornecedor_stats))
        width = 0.13
        
        ax.bar(x - 2.5*width, fornecedor_stats['PP'], width, label='PP', color='#a8d5e2')
        ax.bar(x - 1.5*width, fornecedor_stats['P'], width, label='P', color='#3498db')
        ax.bar(x - 0.5*width, fornecedor_stats['M'], width, label='M', color='#2ecc71')
        ax.bar(x + 0.5*width, fornecedor_stats['G'], width, label='G', color='#f39c12')
        ax.bar(x + 1.5*width, fornecedor_stats['GG'], width, label='GG', color='#e74c3c')
        ax.bar(x + 2.5*width, fornecedor_stats['U'], width, label='U', color='#9b59b6')
        
        ax.set_xlabel('Facção', fontsize=13)
        ax.set_ylabel('Quantidade de Peças', fontsize=13)
        
        if self.df_filtrado is not None:
            ax.set_title('Produção por Facção (Top 20) - Dados Filtrados', fontsize=16, fontweight='bold', pad=20)
        else:
            ax.set_title('Produção por Facção (Top 20)', fontsize=16, fontweight='bold', pad=20)
        
        ax.set_xticks(x)
        ax.set_xticklabels(fornecedor_stats['Faccao'], rotation=45, ha='right', fontsize=10)
        ax.legend(fontsize=12, loc='upper right')
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def gerar_relatorio_mensal(self):
        """Gera gráfico de produção por mês"""
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()
        
        df = self.get_dados_relatorio()
        
        if df is None or df.empty or 'Data Entrada' not in df.columns:
            ttk.Label(self.frame_graficos, text="Nenhum dado disponível", 
                     font=('Arial', 12),
                     background=self.cores.BRANCO_NEVE).pack()
            return
        
        df_copy = df.copy()
        df_copy['Data Entrada'] = pd.to_datetime(df_copy['Data Entrada'], dayfirst=True, errors='coerce')
        df_copy = df_copy.dropna(subset=['Data Entrada'])
        
        df_copy['Mes_Numero'] = df_copy['Data Entrada'].dt.month
        df_copy['Ano'] = df_copy['Data Entrada'].dt.year
        df_copy['Mes_Ano'] = df_copy['Data Entrada'].dt.strftime('%m/%Y')
        
        df_copy['Total Enviado'] = df_copy['PP'] + df_copy['P'] + df_copy['M'] + df_copy['G'] + df_copy['GG'] + df_copy['U']
        df_copy['Total Finalizado'] = df_copy['Ret PP'] + df_copy['Ret P'] + df_copy['Ret M'] + df_copy['Ret G'] + df_copy['Ret GG'] + df_copy['Ret U']
        df_copy['Em Andamento'] = df_copy['Total Enviado'] - df_copy['Total Finalizado']
        df_copy['Em Andamento'] = df_copy['Em Andamento'].clip(lower=0)
        
        mensal_stats = df_copy.groupby(['Ano', 'Mes_Numero', 'Mes_Ano']).agg({
            'Total Enviado': 'sum',
            'Total Finalizado': 'sum',
            'Em Andamento': 'sum'
        }).reset_index()
        
        mensal_stats = mensal_stats.sort_values(['Ano', 'Mes_Numero'])
        
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        x_labels = mensal_stats['Mes_Ano'].tolist()
        x = range(len(x_labels))
        
        ax.plot(x, mensal_stats['Total Enviado'], marker='o', linewidth=3, color='#3498db', 
               label='Total Enviado', markersize=8)
        ax.plot(x, mensal_stats['Total Finalizado'], marker='s', linewidth=3, color='#2ecc71', 
               label='Total Finalizado', markersize=8)
        ax.plot(x, mensal_stats['Em Andamento'], marker='^', linewidth=3, color='#f39c12', 
               label='Em Andamento', markersize=8)
        
        ax.set_xlabel('Mês/Ano', fontsize=13)
        ax.set_ylabel('Quantidade de Peças', fontsize=13)
        
        if self.df_filtrado is not None:
            ax.set_title('Produção Mensal - Dados Filtrados', fontsize=16, fontweight='bold', pad=20)
        else:
            ax.set_title('Produção Mensal', fontsize=16, fontweight='bold', pad=20)
        
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, ha='right', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(fontsize=12, loc='upper left', framealpha=0.9)
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def gerar_relatorio_valor(self):
        """Gera gráfico de valor total por fornecedor"""
        for widget in self.frame_graficos.winfo_children():
            widget.destroy()
        
        df = self.get_dados_relatorio()
        
        if df is None or df.empty or 'Valor' not in df.columns:
            ttk.Label(self.frame_graficos, text="Nenhum dado disponível", 
                     font=('Arial', 12),
                     background=self.cores.BRANCO_NEVE).pack()
            return
        
        df_copy = df.copy()
        df_copy['Valor Total'] = df_copy['Total'] * df_copy['Valor']
        
        fornecedor_valor = df_copy.groupby('Faccao')['Valor Total'].sum().sort_values(ascending=False).head(10)
        
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        y_pos = range(len(fornecedor_valor))
        bars = ax.barh(y_pos, fornecedor_valor.values, color='#9b59b6')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(fornecedor_valor.index, fontsize=11)
        ax.set_xlabel('Valor Total (R$)', fontsize=13)
        
        if self.df_filtrado is not None:
            ax.set_title('Valor por Facção (Top 10) - Dados Filtrados', fontsize=16, fontweight='bold')
        else:
            ax.set_title('Valor por Facção (Top 10)', fontsize=16, fontweight='bold')
        
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
        
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                f'R$ {width:,.0f}', ha='left', va='center', fontsize=11)
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    # ===== PÁGINA DE HISTÓRICO COM PAGINAÇÃO =====
    
    def criar_pagina_historico(self):
        """Cria a página de histórico de OPs finalizadas (location NULL) COM PAGINAÇÃO e EDIÇÃO"""
        for widget in self.frame_historico.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self.frame_historico)
        main_frame.pack(fill='both', expand=True, padx=10, pady=3)       
        
        # ============================================================
        # FILTROS
        # ============================================================
        frame_filtros = ttk.LabelFrame(main_frame, text="🔍 Filtros", padding=10)
        frame_filtros.pack(fill='x', pady=3)
        
        filtros_row = ttk.Frame(frame_filtros)
        filtros_row.pack(fill='x')
        
        ttk.Label(filtros_row, text="Data Entrada - De:").pack(side='left', padx=5)
        self.entry_hist_data_ini = ttk.Entry(filtros_row, width=12)
        self.entry_hist_data_ini.pack(side='left', padx=5)
        
        ttk.Label(filtros_row, text="Até:").pack(side='left', padx=5)
        self.entry_hist_data_fim = ttk.Entry(filtros_row, width=12)
        self.entry_hist_data_fim.pack(side='left', padx=5)
        
        ttk.Label(filtros_row, text="Buscar (Ref/OP):").pack(side='left', padx=(15, 5))
        self.entry_hist_busca = ttk.Entry(filtros_row, width=15)
        self.entry_hist_busca.pack(side='left', padx=5)
        
        ttk.Button(
            filtros_row, 
            text="🔍 Filtrar", 
            command=self.aplicar_filtros_historico
        ).pack(side='left', padx=10)
        
        ttk.Button(
            filtros_row, 
            text="🔄 Limpar", 
            command=self.limpar_filtros_historico
        ).pack(side='left', padx=5)
        
        ttk.Button(
            filtros_row, 
            text="📜 Importar Histórico TOTVS",
            command=self.importar_historico_banco,
        ).pack(side='right', padx=5)
        
        ttk.Button(
            filtros_row, 
            text="📥 Exportar Tudo", 
            command=self.exportar_historico
        ).pack(side='right', padx=5)
        
        # Combo dummy para compatibilidade
        self.combo_hist_faccao = ttk.Combobox(filtros_row, width=1, state='readonly')
        self.combo_hist_faccao['values'] = ['Todas']
        self.combo_hist_faccao.set('Todas')
        
        # ============================================================
        # TABELA DE HISTÓRICO
        # ============================================================
        tabela_frame = ttk.Frame(main_frame)
        tabela_frame.pack(fill='both', expand=True)
        
        columns = [
            'Faccao', 'Referencia', 'Ciclo', 'OP',
            'OP Criada em', 'Cortou em', 'Data Envio', 'Data Chegada',
            'Descricao',
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
            'Status', 'Observacoes'
        ]
        
        self.tree_historico = ttk.Treeview(
            tabela_frame, columns=columns, show='headings', 
            height=20, selectmode='extended'
        )
        
        col_widths = {
            'Faccao': 130, 'Referencia': 90, 'Ciclo': 60, 'OP': 70,
            'OP Criada em': 90, 'Cortou em': 90, 'Data Envio': 90, 'Data Chegada': 90,
            'Descricao': 150,
            'PP': 45, 'P': 45, 'M': 45, 'G': 45, 'GG': 45, 'U': 45, 'Total': 60,
            'Ret PP': 55, 'Ret P': 45, 'Ret M': 45, 'Ret G': 45, 
            'Ret GG': 55, 'Ret U': 45, 'Ret Total': 65,
            'Def PP': 50, 'Def P': 45, 'Def M': 45, 'Def G': 45, 
            'Def GG': 50, 'Def U': 45, 'Def Total': 60,
            'Status': 80, 'Observacoes': 150
        }
        
        for col in columns:
            self.tree_historico.heading(col, text=col)
            self.tree_historico.column(
                col, width=col_widths.get(col, 80), 
                anchor='center', stretch=False
            )
        
        vsb = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tree_historico.yview)
        hsb = ttk.Scrollbar(tabela_frame, orient="horizontal", command=self.tree_historico.xview)
        self.tree_historico.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree_historico.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tabela_frame.grid_rowconfigure(0, weight=1)
        tabela_frame.grid_columnconfigure(0, weight=1)
        
        # ============================================================
        # PAGINAÇÃO - CONTROLES
        # ============================================================
        frame_paginacao = tk.Frame(main_frame, bg=self.cores.AZUL_AGUA, relief='flat')
        frame_paginacao.pack(fill='x', pady=8)
        
        self.lbl_hist_total = tk.Label(
            frame_paginacao,
            text="📦 0 registros",
            font=('Arial', 10, 'bold'),
            bg=self.cores.AZUL_AGUA,
            fg=self.cores.AZUL_MAR_ESCURO,
            padx=10
        )
        self.lbl_hist_total.pack(side='left')
        
        btn_ultima = tk.Button(
            frame_paginacao, text="⏭️ Última",
            command=self.hist_ir_ultima_pagina,
            font=('Arial', 10), bg=self.cores.AZUL_MAR, fg='white',
            relief='flat', padx=10, pady=3, cursor='hand2'
        )
        btn_ultima.pack(side='right', padx=2)
        
        btn_proxima = tk.Button(
            frame_paginacao, text="▶️ Próxima",
            command=self.hist_proxima_pagina,
            font=('Arial', 10), bg=self.cores.AZUL_MAR, fg='white',
            relief='flat', padx=10, pady=3, cursor='hand2'
        )
        btn_proxima.pack(side='right', padx=2)
        
        self.lbl_hist_pagina = tk.Label(
            frame_paginacao,
            text="Página 1 de 1",
            font=('Arial', 10, 'bold'),
            bg=self.cores.AZUL_AGUA,
            fg=self.cores.AZUL_MAR_ESCURO,
            padx=10
        )
        self.lbl_hist_pagina.pack(side='right')
        
        self.entry_hist_ir_pagina = tk.Entry(frame_paginacao, width=5, font=('Arial', 10))
        self.entry_hist_ir_pagina.pack(side='right', padx=2)
        self.entry_hist_ir_pagina.bind('<Return>', lambda e: self.hist_ir_pagina_especifica())
        
        tk.Button(
            frame_paginacao, text="Ir",
            command=self.hist_ir_pagina_especifica,
            font=('Arial', 10), bg=self.cores.CORAL, fg='white',
            relief='flat', padx=8, pady=3, cursor='hand2'
        ).pack(side='right', padx=2)
        
        btn_anterior = tk.Button(
            frame_paginacao, text="◀️ Anterior",
            command=self.hist_pagina_anterior,
            font=('Arial', 10), bg=self.cores.AZUL_MAR, fg='white',
            relief='flat', padx=10, pady=3, cursor='hand2'
        )
        btn_anterior.pack(side='right', padx=2)
        
        btn_primeira = tk.Button(
            frame_paginacao, text="⏮️ Primeira",
            command=self.hist_ir_primeira_pagina,
            font=('Arial', 10), bg=self.cores.AZUL_MAR, fg='white',
            relief='flat', padx=10, pady=3, cursor='hand2'
        )
        btn_primeira.pack(side='right', padx=2)
        
        self.combo_hist_por_pagina = ttk.Combobox(
            frame_paginacao,
            values=['50', '100', '200', '500'],
            width=5,
            state='readonly'
        )
        self.combo_hist_por_pagina.set(str(self.hist_por_pagina))
        self.combo_hist_por_pagina.pack(side='right', padx=5)
        self.combo_hist_por_pagina.bind('<<ComboboxSelected>>', self.hist_mudar_por_pagina)
        
        tk.Label(
            frame_paginacao, text="Itens/pág:",
            font=('Arial', 10), bg=self.cores.AZUL_AGUA,
            fg=self.cores.AZUL_MAR_ESCURO
        ).pack(side='right')
        
        # ============================================================
        # RODAPÉ COM TOTALIZADORES
        # ============================================================
        self.frame_total_historico = ttk.Frame(main_frame)
        self.frame_total_historico.pack(fill='x', pady=5)
        
        # Carregar dados iniciais
        self.atualizar_historico()
        
        # BINDS: duplo clique abre edição, botão direito abre menu
        self.tree_historico.bind('<Double-1>', self._editar_item_historico_event)
        self.tree_historico.bind('<Button-3>', self._menu_contexto_historico)

    def _editar_item_historico_event(self, event):
        """Handler do duplo clique na tree de histórico"""
        selecionados = self.tree_historico.selection()
        if not selecionados:
            return
        
        item = selecionados[0]
        values = self.tree_historico.item(item, 'values')
        columns = self.tree_historico['columns']
        dados = dict(zip(columns, values))
        
        self.editar_registro_historico(dados)
    
    
    def _menu_contexto_historico(self, event):
        """Menu de contexto (botão direito) na tree de histórico"""
        # Selecionar o item clicado
        item = self.tree_historico.identify_row(event.y)
        if not item:
            return
        
        self.tree_historico.selection_set(item)
        
        menu = tk.Menu(self.tree_historico, tearoff=0)
        menu.add_command(label="✏️ Editar", command=self.editar_selecionado_historico)
        menu.add_command(label="🗑️ Excluir", command=self.excluir_selecionado_historico)
        menu.add_separator()
        menu.add_command(label="📋 Ver Detalhes", command=lambda: self.ver_detalhes_historico(None))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    
    def editar_selecionado_historico(self):
        """Abre janela de edição para o item selecionado no histórico"""
        selecionados = self.tree_historico.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione um registro para editar")
            return
        
        if len(selecionados) > 1:
            messagebox.showwarning("Aviso", "Selecione apenas UM registro para editar")
            return
        
        item = selecionados[0]
        values = self.tree_historico.item(item, 'values')
        columns = self.tree_historico['columns']
        dados = dict(zip(columns, values))
        
        self.editar_registro_historico(dados)
    
    
    def editar_registro_historico(self, dados):
        """Abre modal de edição para um registro do histórico"""
        op = dados.get('OP', '')
        referencia = dados.get('Referencia', '')
        ciclo = dados.get('Ciclo', '')
        
        if not op or not referencia or not ciclo:
            messagebox.showerror("Erro", "Dados incompletos para edição")
            return
        
        # Localizar o registro no df_historico
        if self.df_historico is None or self.df_historico.empty:
            messagebox.showerror("Erro", "Histórico não carregado")
            return
        
        mask = (self.df_historico['OP'].astype(str) == str(op)) & \
               (self.df_historico['Referencia'].astype(str) == str(referencia)) & \
               (self.df_historico['Ciclo'].astype(str) == str(ciclo))
        
        if not mask.any():
            messagebox.showerror("Erro", "Registro não encontrado no histórico")
            return
        
        idx = self.df_historico[mask].index[0]
        registro = self.df_historico.loc[idx]
        
        # ============================================================
        # JANELA DE EDIÇÃO DO HISTÓRICO
        # ============================================================
        janela = tk.Toplevel(self.parent)
        janela.title(f"🏖️ Editar OP Histórica - {op}")
        janela.geometry("1050x550")
        janela.minsize(700, 500)
        janela.transient(self.parent)
        janela.grab_set()
        janela.configure(bg=self.cores.BRANCO_NEVE)
        
        # Frame com scroll
        outer_frame = ttk.Frame(janela)
        outer_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        canvas = tk.Canvas(outer_frame, bg=self.cores.BRANCO_NEVE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        main_frame = ttk.Frame(canvas, padding=15)
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor='nw')
        
        def configurar_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        def redimensionar_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        main_frame.bind('<Configure>', configurar_scroll)
        canvas.bind('<Configure>', redimensionar_canvas)
        
        def scroll_mouse(event):
            if event.num == 4:
                canvas.yview_scroll(-1, 'units')
            elif event.num == 5:
                canvas.yview_scroll(1, 'units')
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        
        canvas.bind('<MouseWheel>', scroll_mouse)
        canvas.bind('<Button-4>', scroll_mouse)
        canvas.bind('<Button-5>', scroll_mouse)
        
        campos = {}
        
        # ============================================================
        # INFORMAÇÕES PRINCIPAIS
        # ============================================================
        frame_principal = ttk.LabelFrame(main_frame, text="📋 Informações Principais", padding=10)
        frame_principal.pack(fill='x', pady=5)
        
        frame_principal.grid_columnconfigure(0, weight=1)
        frame_principal.grid_columnconfigure(2, weight=1)
        frame_principal.grid_columnconfigure(4, weight=1)
        
        ttk.Label(frame_principal, text="Referência *:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky='e', padx=(5, 2), pady=3
        )
        campos['Referencia'] = ttk.Entry(frame_principal, font=('Arial', 9), width=18)
        campos['Referencia'].insert(0, str(registro.get('Referencia', '')))
        campos['Referencia'].grid(row=0, column=1, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_principal, text="Ciclo *:", font=('Arial', 9, 'bold')).grid(
            row=0, column=2, sticky='e', padx=(10, 2), pady=3
        )
        campos['Ciclo'] = ttk.Entry(frame_principal, font=('Arial', 9), width=12)
        campos['Ciclo'].insert(0, str(registro.get('Ciclo', '')))
        campos['Ciclo'].grid(row=0, column=3, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_principal, text="OP *:", font=('Arial', 9, 'bold')).grid(
            row=0, column=4, sticky='e', padx=(10, 2), pady=3
        )
        campos['OP'] = ttk.Entry(frame_principal, font=('Arial', 9), width=12)
        campos['OP'].insert(0, str(registro.get('OP', '')))
        campos['OP'].grid(row=0, column=5, sticky='w', padx=2, pady=3)
        
        # ============================================================
        # DATAS
        # ============================================================
        ttk.Label(frame_principal, text="OP Criada em:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky='e', padx=(5, 2), pady=3
        )
        campos['OP Criada em'] = ttk.Entry(frame_principal, font=('Arial', 9), width=18)
        campos['OP Criada em'].insert(0, str(registro.get('OP Criada em', '')))
        campos['OP Criada em'].config(state='readonly')
        campos['OP Criada em'].grid(row=1, column=1, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_principal, text="Cortou em:", font=('Arial', 9, 'bold')).grid(
            row=1, column=2, sticky='e', padx=(10, 2), pady=3
        )
        campos['Cortou em'] = ttk.Entry(frame_principal, font=('Arial', 9), width=12)
        campos['Cortou em'].insert(0, str(registro.get('Cortou em', '')))
        campos['Cortou em'].grid(row=1, column=3, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_principal, text="Data Envio:", font=('Arial', 9, 'bold')).grid(
            row=1, column=4, sticky='e', padx=(10, 2), pady=3
        )
        campos['Data Envio'] = ttk.Entry(frame_principal, font=('Arial', 9), width=12)
        campos['Data Envio'].insert(0, str(registro.get('Data Envio', '')))
        campos['Data Envio'].config(state='readonly')
        campos['Data Envio'].grid(row=1, column=5, sticky='w', padx=2, pady=3)
        
        # ============================================================
        # FACÇÃO E DESCRIÇÃO
        # ============================================================
        frame_fornecedor = ttk.LabelFrame(main_frame, text="🏭 Facção e Descrição", padding=10)
        frame_fornecedor.pack(fill='x', pady=5)
        
        frame_fornecedor.grid_columnconfigure(0, weight=1)
        frame_fornecedor.grid_columnconfigure(2, weight=1)
        
        ttk.Label(frame_fornecedor, text="Facção:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky='e', padx=(5, 2), pady=3
        )
        campos['Faccao'] = ttk.Entry(frame_fornecedor, font=('Arial', 9), width=25)
        campos['Faccao'].insert(0, str(registro.get('Faccao', '')))
        campos['Faccao'].grid(row=0, column=1, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_fornecedor, text="Data Chegada:", font=('Arial', 9, 'bold')).grid(
            row=0, column=2, sticky='e', padx=(10, 2), pady=3
        )
        campos['Data Chegada'] = ttk.Entry(frame_fornecedor, font=('Arial', 9), width=18)
        campos['Data Chegada'].insert(0, str(registro.get('Data Chegada', '')))
        campos['Data Chegada'].grid(row=0, column=3, sticky='w', padx=2, pady=3)
        
        ttk.Label(frame_fornecedor, text="Descrição:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky='e', padx=(5, 2), pady=3
        )
        campos['Descricao'] = ttk.Entry(frame_fornecedor, font=('Arial', 9), width=50)
        campos['Descricao'].insert(0, str(registro.get('Descricao', '')))
        campos['Descricao'].grid(row=1, column=1, columnspan=3, sticky='w', padx=2, pady=3)
        
        # ============================================================
        # TAMANHOS
        # ============================================================
        frame_tamanhos = ttk.Frame(main_frame)
        frame_tamanhos.pack(fill='x', pady=5)
        
        frame_env = ttk.LabelFrame(frame_tamanhos, text="📦 Enviados", padding=8)
        frame_env.pack(side='left', fill='x', expand=True, padx=(0, 3))
        
        tamanhos = ['PP', 'P', 'M', 'G', 'GG', 'U']
        for i, tam in enumerate(tamanhos):
            ttk.Label(frame_env, text=f"{tam}:", font=('Arial', 9)).grid(
                row=0, column=i*2, padx=3, pady=2, sticky='e'
            )
            campos[tam] = ttk.Entry(frame_env, width=6, font=('Arial', 9))
            valor = registro.get(tam, '0')
            try:
                if float(valor) == int(float(valor)):
                    campos[tam].insert(0, str(int(float(valor))))
                else:
                    campos[tam].insert(0, str(valor))
            except:
                campos[tam].insert(0, '0')
            campos[tam].grid(row=0, column=i*2+1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_env, text="Total:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, padx=3, pady=3, sticky='e'
        )
        campos['Total'] = ttk.Entry(frame_env, width=10, font=('Arial', 9, 'bold'))
        try:
            qt_total = float(registro.get('Total', '0'))
            if qt_total == int(qt_total):
                campos['Total'].insert(0, str(int(qt_total)))
            else:
                campos['Total'].insert(0, str(qt_total))
        except:
            campos['Total'].insert(0, '0')
        campos['Total'].grid(row=1, column=1, columnspan=5, padx=3, pady=3, sticky='w')
        
        frame_comp = ttk.LabelFrame(frame_tamanhos, text="✅ Retornados", padding=8)
        frame_comp.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        completos = ['Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U']
        for i, ctam in enumerate(completos):
            tamanho = ctam.split()[1]
            ttk.Label(frame_comp, text=f"{tamanho}:", font=('Arial', 9)).grid(
                row=0, column=i*2, padx=3, pady=2, sticky='e'
            )
            campos[ctam] = ttk.Entry(frame_comp, width=6, font=('Arial', 9))
            valor = registro.get(ctam, '0')
            try:
                if float(valor) == int(float(valor)):
                    campos[ctam].insert(0, str(int(float(valor))))
                else:
                    campos[ctam].insert(0, str(valor))
            except:
                campos[ctam].insert(0, '0')
            campos[ctam].grid(row=0, column=i*2+1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_comp, text="Total:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, padx=3, pady=3, sticky='e'
        )
        campos['Ret Total'] = ttk.Entry(frame_comp, width=10, font=('Arial', 9, 'bold'))
        try:
            ctotal = float(registro.get('Ret Total', '0'))
            if ctotal == int(ctotal):
                campos['Ret Total'].insert(0, str(int(ctotal)))
            else:
                campos['Ret Total'].insert(0, str(ctotal))
        except:
            campos['Ret Total'].insert(0, '0')
        campos['Ret Total'].grid(row=1, column=1, columnspan=5, padx=3, pady=3, sticky='w')
        
        # ============================================================
        # DEFEITOS E STATUS
        # ============================================================
        frame_inferior = ttk.Frame(main_frame)
        frame_inferior.pack(fill='x', pady=5)
        
        frame_defeitos = ttk.LabelFrame(frame_inferior, text="⚠️ Defeitos", padding=8)
        frame_defeitos.pack(side='left', fill='x', expand=True, padx=(0, 3))
        
        defs = ['Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U']
        for i, dtam in enumerate(defs):
            tamanho = dtam.split()[1]
            ttk.Label(frame_defeitos, text=f"{tamanho}:", font=('Arial', 9)).grid(
                row=0, column=i*2, padx=3, pady=2, sticky='e'
            )
            campos[dtam] = ttk.Entry(frame_defeitos, width=6, font=('Arial', 9))
            valor = registro.get(dtam, '0')
            try:
                if float(valor) == int(float(valor)):
                    campos[dtam].insert(0, str(int(float(valor))))
                else:
                    campos[dtam].insert(0, str(valor))
            except:
                campos[dtam].insert(0, '0')
            campos[dtam].grid(row=0, column=i*2+1, padx=3, pady=2, sticky='w')
        
        ttk.Label(frame_defeitos, text="Total:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, padx=3, pady=3, sticky='e'
        )
        campos['Def Total'] = ttk.Entry(frame_defeitos, width=10, font=('Arial', 9, 'bold'))
        try:
            dtotal = float(registro.get('Def Total', '0'))
            if dtotal == int(dtotal):
                campos['Def Total'].insert(0, str(int(dtotal)))
            else:
                campos['Def Total'].insert(0, str(dtotal))
        except:
            campos['Def Total'].insert(0, '0')
        campos['Def Total'].grid(row=1, column=1, columnspan=5, padx=3, pady=3, sticky='w')
        
        frame_outros = ttk.LabelFrame(frame_inferior, text="📋 Status", padding=8)
        frame_outros.pack(side='left', fill='x', expand=True, padx=(3, 0))
        
        ttk.Label(frame_outros, text="Status:", font=('Arial', 9)).grid(
            row=0, column=0, sticky='e', padx=3, pady=2
        )
        status_options = ['EM ANDAMENTO', 'FINALIZADO', 'CANCELADO']
        campos['Status'] = ttk.Combobox(frame_outros, 
                                    values=status_options,
                                    width=15, state="readonly")
        status_atual = str(registro.get('Status', 'FINALIZADO')).upper()
        campos['Status'].set(status_atual)
        campos['Status'].grid(row=0, column=1, padx=3, pady=2, sticky='w')
        
        # Observações
        ttk.Label(frame_outros, text="Observações:", font=('Arial', 9)).grid(
            row=1, column=0, sticky='e', padx=3, pady=2
        )
        campos['Observacoes'] = tk.Text(frame_outros, font=('Arial', 9), height=3, width=30, wrap=tk.WORD)
        campos['Observacoes'].insert('1.0', str(registro.get('Observacoes', '')))
        campos['Observacoes'].grid(row=1, column=1, padx=3, pady=2, sticky='w')
        
        # ============================================================
        # BOTÕES
        # ============================================================
        frame_botoes = ttk.Frame(main_frame)
        frame_botoes.pack(fill='x', pady=15)
        
        btn_salvar = tk.Button(
            frame_botoes,
            text="💾 Salvar Alterações",
            command=lambda: self.salvar_edicao_historico(idx, campos, janela),
            font=('Arial', 11, 'bold'),
            bg=self.cores.VERDE_COQUEIRO,
            fg='white',
            relief='flat',
            padx=25,
            pady=10,
            cursor='hand2'
        )
        btn_salvar.pack(side='right', padx=5)
        
        btn_excluir = tk.Button(
            frame_botoes,
            text="🗑️ Excluir",
            command=lambda: self.excluir_registro_historico(idx, janela),
            font=('Arial', 11, 'bold'),
            bg=self.cores.CORAL,
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            cursor='hand2'
        )
        btn_excluir.pack(side='left', padx=5)
        
        btn_fechar = tk.Button(
            frame_botoes,
            text="❌ Fechar",
            command=janela.destroy,
            font=('Arial', 11),
            bg=self.cores.CINZA_MEDIO,
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            cursor='hand2'
        )
        btn_fechar.pack(side='right', padx=5)
        
        # Binds de cálculo automático
        for tam in tamanhos:
            campos[tam].bind('<KeyRelease>', lambda e, c=campos: self.calcular_total_edicao(c))
        
        for ctam in completos:
            campos[ctam].bind('<KeyRelease>', lambda e, c=campos: self.calcular_ctotal_edicao(c))
        
        for dtam in defs:
            campos[dtam].bind('<KeyRelease>', lambda e, c=campos: self.calcular_dtotal_edicao(c))
        
        campos['Referencia'].focus_set()
    
    
    def salvar_edicao_historico(self, idx, campos, janela):
        """Salva as alterações de um registro do histórico"""
        dados_atualizados = {}
        for key, widget in campos.items():
            if key == 'Observacoes':
                dados_atualizados[key] = widget.get('1.0', tk.END).strip()
            elif isinstance(widget, ttk.Combobox):
                dados_atualizados[key] = widget.get().strip()
            else:
                dados_atualizados[key] = widget.get().strip()
        
        if not dados_atualizados['OP'] or not dados_atualizados['Referencia'] or not dados_atualizados['Ciclo']:
            messagebox.showwarning("Aviso", "Preencha OP, Referência e Ciclo")
            return
        
        try:
            for tam in ['PP', 'P', 'M', 'G', 'GG', 'U']:
                valor = dados_atualizados.get(tam, '0').replace(',', '.')
                dados_atualizados[tam] = float(valor) if valor else 0.0
            
            qt_total = float(dados_atualizados.get('Total', '0').replace(',', '.'))
            dados_atualizados['Total'] = int(qt_total) if qt_total == int(qt_total) else qt_total
            
            for ctam in ['Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U']:
                valor = dados_atualizados.get(ctam, '0').replace(',', '.')
                dados_atualizados[ctam] = float(valor) if valor else 0.0
            
            ctotal = float(dados_atualizados.get('Ret Total', '0').replace(',', '.'))
            dados_atualizados['Ret Total'] = int(ctotal) if ctotal == int(ctotal) else ctotal
            
            for dtam in ['Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U']:
                valor = dados_atualizados.get(dtam, '0').replace(',', '.')
                dados_atualizados[dtam] = float(valor) if valor else 0.0
            
            dtotal = float(dados_atualizados.get('Def Total', '0').replace(',', '.'))
            dados_atualizados['Def Total'] = int(dtotal) if dtotal == int(dtotal) else dtotal
        except Exception as e:
            messagebox.showerror("Erro", f"Erro em valores numéricos: {str(e)}")
            return
        
        # Atualizar no df_historico
        for col, valor in dados_atualizados.items():
            self.df_historico.at[idx, col] = valor
        
        # Salvar arquivo
        self.salvar_historico()
        
        # Atualizar a visualização (mantendo a página atual)
        self.atualizar_historico()
        
        messagebox.showinfo("Sucesso", "📜 Registro do histórico atualizado com sucesso!")
        janela.destroy()
    
    
    def excluir_registro_historico(self, idx, janela):
        """Exclui um registro do histórico"""
        resposta = messagebox.askyesno(
            "Confirmar Exclusão",
            "Tem certeza que deseja excluir este registro do histórico?\n"
            "Esta ação não pode ser desfeita."
        )
        
        if not resposta:
            return
        
        self.df_historico = self.df_historico.drop(idx).reset_index(drop=True)
        self.salvar_historico()
        self.atualizar_historico()
        
        messagebox.showinfo("Excluído", "🗑️ Registro do histórico excluído com sucesso!")
        janela.destroy()
    
    
    def excluir_selecionado_historico(self):
        """Exclui o(s) registro(s) selecionado(s) no histórico (com confirmação)"""
        selecionados = self.tree_historico.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione pelo menos um registro para excluir")
            return
        
        if not messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja excluir {len(selecionados)} registro(s) do histórico?\n"
            "Esta ação não pode ser desfeita."
        ):
            return
        
        # Coletar chaves dos selecionados
        chaves = []
        columns = self.tree_historico['columns']
        
        for item in selecionados:
            values = self.tree_historico.item(item, 'values')
            dados = dict(zip(columns, values))
            chave = (str(dados.get('OP', '')), str(dados.get('Referencia', '')), str(dados.get('Ciclo', '')))
            chaves.append(chave)
        
        # Remover cada registro
        removidos = 0
        for op, ref, ciclo in chaves:
            mask = (self.df_historico['OP'].astype(str) == op) & \
                   (self.df_historico['Referencia'].astype(str) == ref) & \
                   (self.df_historico['Ciclo'].astype(str) == ciclo)
            if mask.any():
                self.df_historico = self.df_historico[~mask].reset_index(drop=True)
                removidos += 1
        
        self.salvar_historico()
        self.atualizar_historico()
        
        messagebox.showinfo("Excluído", f"🗑️ {removidos} registro(s) excluído(s) do histórico!")
    
    def atualizar_historico(self):
        """Atualiza a tabela de histórico aplicando paginação"""
        if not hasattr(self, 'tree_historico'):
            return
        
        if not hasattr(self, 'df_historico') or self.df_historico is None:
            self.carregar_dados_historico()
        
        if self.df_historico is None or self.df_historico.empty:
            self.hist_dados_filtrados = pd.DataFrame()
            self.hist_total_paginas = 1
            self.hist_pagina_atual = 1
            self._renderizar_pagina_historico()
            return
        
        df_hist = self.df_historico.copy()
        
        df_hist['_data_ordenacao'] = pd.to_datetime(
            df_hist['Data Entrada'], dayfirst=True, errors='coerce'
        )
        df_hist = df_hist.sort_values('_data_ordenacao', ascending=False, na_position='last')
        df_hist = df_hist.drop('_data_ordenacao', axis=1)
        
        self.hist_dados_filtrados = df_hist.reset_index(drop=True)
        
        total_registros = len(self.hist_dados_filtrados)
        self.hist_total_paginas = max(1, (total_registros + self.hist_por_pagina - 1) // self.hist_por_pagina)
        
        if self.hist_pagina_atual > self.hist_total_paginas:
            self.hist_pagina_atual = self.hist_total_paginas
        if self.hist_pagina_atual < 1:
            self.hist_pagina_atual = 1
        
        self._renderizar_pagina_historico()
    
    def _renderizar_pagina_historico(self):
        """Renderiza apenas a página atual do histórico"""
        if not hasattr(self, 'tree_historico'):
            return
        
        for item in self.tree_historico.get_children():
            self.tree_historico.delete(item)
        
        for widget in self.frame_total_historico.winfo_children():
            widget.destroy()
        
        if self.hist_dados_filtrados is None or self.hist_dados_filtrados.empty:
            self.lbl_hist_total.config(text="📦 0 registros")
            self.lbl_hist_pagina.config(text="Página 1 de 1")
            
            ttk.Label(
                self.frame_total_historico,
                text="📭 Nenhuma ordem encontrada. Clique em 'Importar Histórico TOTVS' para carregar.",
                font=('Arial', 11),
                foreground=self.cores.CINZA_ESCURO
            ).pack()
            return
        
        total = len(self.hist_dados_filtrados)
        inicio = (self.hist_pagina_atual - 1) * self.hist_por_pagina
        fim = min(inicio + self.hist_por_pagina, total)
        
        df_pagina = self.hist_dados_filtrados.iloc[inicio:fim]
        
        columns = [
            'Faccao', 'Referencia', 'Ciclo', 'OP',
            'OP Criada em', 'Cortou em', 'Data Entrada', 'Data Chegada',
            'Descricao',
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total',
            'Status', 'Observacoes'
        ]
        
        for _, row in df_pagina.iterrows():
            values = []
            for col in columns:
                valor = row[col] if col in row else ''
                
                if pd.isna(valor):
                    values.append('')
                elif col == 'Status':
                    values.append('✅ FINALIZADO')
                elif isinstance(valor, (int, float)):
                    values.append(f"{int(valor)}" if valor == int(valor) else f"{valor:.1f}")
                else:
                    values.append(str(valor))
            
            self.tree_historico.insert('', 'end', values=values)
        
        self.lbl_hist_total.config(text=f"📦 {total} registros totais")
        self.lbl_hist_pagina.config(text=f"Página {self.hist_pagina_atual} de {self.hist_total_paginas}")
        
        totais = {}
        colunas_numericas = [
            'PP', 'P', 'M', 'G', 'GG', 'U', 'Total',
            'Ret PP', 'Ret P', 'Ret M', 'Ret G', 'Ret GG', 'Ret U', 'Ret Total',
            'Def PP', 'Def P', 'Def M', 'Def G', 'Def GG', 'Def U', 'Def Total'
        ]
        
        for col in colunas_numericas:
            if col in self.hist_dados_filtrados.columns:
                totais[col] = pd.to_numeric(
                    self.hist_dados_filtrados[col], errors='coerce'
                ).fillna(0).sum()
            else:
                totais[col] = 0
        
        tk.Label(
            self.frame_total_historico,
            text=f"📦 OPs: {total}  |  "
                 f"👕 Enviadas: {int(totais.get('Total', 0))}  |  "
                 f"✅ Retornadas: {int(totais.get('Ret Total', 0))}  |  "
                 f"⚠️ Defeitos: {int(totais.get('Def Total', 0))}  |  "
                 f"📄 Exibindo: {inicio + 1}-{fim}",
            font=('Arial', 11, 'bold'),
            bg=self.cores.AZUL_AGUA,
            fg=self.cores.AZUL_MAR_ESCURO,
            padx=10, pady=8
        ).pack(fill='x')
    
    
    def hist_ir_primeira_pagina(self):
        """Vai para a primeira página"""
        if self.hist_pagina_atual != 1:
            self.hist_pagina_atual = 1
            self._renderizar_pagina_historico()
    
    
    def hist_pagina_anterior(self):
        """Vai para a página anterior"""
        if self.hist_pagina_atual > 1:
            self.hist_pagina_atual -= 1
            self._renderizar_pagina_historico()
    
    
    def hist_proxima_pagina(self):
        """Vai para a próxima página"""
        if self.hist_pagina_atual < self.hist_total_paginas:
            self.hist_pagina_atual += 1
            self._renderizar_pagina_historico()
    
    
    def hist_ir_ultima_pagina(self):
        """Vai para a última página"""
        if self.hist_pagina_atual != self.hist_total_paginas:
            self.hist_pagina_atual = self.hist_total_paginas
            self._renderizar_pagina_historico()
    
    
    def hist_ir_pagina_especifica(self):
        """Vai para uma página específica digitada pelo usuário"""
        try:
            pagina = int(self.entry_hist_ir_pagina.get().strip())
            if 1 <= pagina <= self.hist_total_paginas:
                self.hist_pagina_atual = pagina
                self._renderizar_pagina_historico()
                self.entry_hist_ir_pagina.delete(0, tk.END)
            else:
                messagebox.showwarning(
                    "Aviso",
                    f"Página inválida. Escolha entre 1 e {self.hist_total_paginas}"
                )
        except ValueError:
            messagebox.showwarning("Aviso", "Digite um número de página válido")
    
    
    def hist_mudar_por_pagina(self, event=None):
        """Muda a quantidade de itens por página"""
        try:
            novo_valor = int(self.combo_hist_por_pagina.get())
            if novo_valor > 0:
                self.hist_por_pagina = novo_valor
                self.hist_pagina_atual = 1
                self.atualizar_historico()
        except ValueError:
            pass
    
    def aplicar_filtros_historico(self):
        """Aplica filtros na tabela de histórico COM busca"""
        if not hasattr(self, 'tree_historico'):
            return
        
        if not hasattr(self, 'df_historico') or self.df_historico is None or self.df_historico.empty:
            return
        
        df_hist = self.df_historico.copy()
        
        # Filtro de data
        data_ini = self.entry_hist_data_ini.get().strip()
        data_fim = self.entry_hist_data_fim.get().strip()
        
        if data_ini or data_fim:
            df_hist['_data'] = pd.to_datetime(
                df_hist['Data Entrada'], dayfirst=True, errors='coerce'
            )
            
            if data_ini:
                try:
                    dt_ini = datetime.strptime(data_ini, '%d/%m/%Y')
                    df_hist = df_hist[df_hist['_data'] >= dt_ini]
                except ValueError:
                    messagebox.showerror("Erro", "Data inicial inválida. Use DD/MM/AAAA")
                    return
            
            if data_fim:
                try:
                    dt_fim = datetime.strptime(data_fim, '%d/%m/%Y')
                    df_hist = df_hist[df_hist['_data'] <= dt_fim]
                except ValueError:
                    messagebox.showerror("Erro", "Data final inválida. Use DD/MM/AAAA")
                    return
            
            df_hist = df_hist.drop('_data', axis=1)
        
        # Filtro de busca (OP ou Referência)
        termo_busca = self.entry_hist_busca.get().strip() if hasattr(self, 'entry_hist_busca') else ''
        if termo_busca:
            termo_upper = termo_busca.upper()
            mask = (
                df_hist['OP'].astype(str).str.upper().str.contains(termo_upper, na=False) |
                df_hist['Referencia'].astype(str).str.upper().str.contains(termo_upper, na=False)
            )
            df_hist = df_hist[mask]
        
        if df_hist.empty:
            self.hist_dados_filtrados = pd.DataFrame()
            self.hist_total_paginas = 1
            self.hist_pagina_atual = 1
            self._renderizar_pagina_historico()
            messagebox.showinfo("Resultado", "Nenhum registro encontrado com os filtros aplicados")
            return
        
        df_hist['_data_ordenacao'] = pd.to_datetime(
            df_hist['Data Entrada'], dayfirst=True, errors='coerce'
        )
        df_hist = df_hist.sort_values('_data_ordenacao', ascending=False, na_position='last')
        df_hist = df_hist.drop('_data_ordenacao', axis=1)
        
        self.hist_dados_filtrados = df_hist.reset_index(drop=True)
        self.hist_total_paginas = max(1, (len(df_hist) + self.hist_por_pagina - 1) // self.hist_por_pagina)
        self.hist_pagina_atual = 1
        
        self._renderizar_pagina_historico()
    
    
    def limpar_filtros_historico(self):
        """Limpa os filtros do histórico"""
        self.entry_hist_data_ini.delete(0, tk.END)
        self.entry_hist_data_fim.delete(0, tk.END)
        if hasattr(self, 'entry_hist_busca'):
            self.entry_hist_busca.delete(0, tk.END)
        self.hist_pagina_atual = 1
        self.atualizar_historico()
    
    
    def exportar_historico(self):
        """Exporta TODO o histórico filtrado para Excel (não só a página atual)"""
        if not hasattr(self, 'hist_dados_filtrados') or self.hist_dados_filtrados is None or self.hist_dados_filtrados.empty:
            messagebox.showwarning("Aviso", "Não há dados para exportar")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"historico_ops_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            if not file_path:
                return
            
            self.hist_dados_filtrados.to_excel(file_path, index=False)
            
            messagebox.showinfo(
                "Sucesso",
                f"📥 Histórico exportado!\n\n"
                f"• {len(self.hist_dados_filtrados)} registros\n"
                f"• Arquivo: {file_path}"
            )
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    
    def ver_detalhes_historico(self, event):
        """Abre modal com detalhes da OP selecionada no histórico"""
        selecionados = self.tree_historico.selection()
        if not selecionados:
            return
        
        item = selecionados[0]
        values = self.tree_historico.item(item, 'values')
        columns = self.tree_historico['columns']
        dados = dict(zip(columns, values))
        
        janela = tk.Toplevel(self.parent)
        janela.title(f"📋 Detalhes da OP {dados.get('OP', '')}")
        janela.geometry("600x550")
        janela.transient(self.parent)
        janela.grab_set()
        janela.configure(bg=self.cores.BRANCO_NEVE)
        
        frame = ttk.Frame(janela, padding=20)
        frame.pack(fill='both', expand=True)
        
        tk.Label(
            frame,
            text=f"📋 OP {dados.get('OP', '')} - Ref {dados.get('Referencia', '')}",
            font=('Arial', 14, 'bold'),
            fg=self.cores.AZUL_MAR_ESCURO,
            bg=self.cores.BRANCO_NEVE
        ).pack(pady=(0, 15))
        
        campos_exibir = [
            ('Facção', 'Faccao'),
            ('Referência', 'Referencia'),
            ('Ciclo', 'Ciclo'),
            ('OP', 'OP'),
            ('OP Criada em', 'OP Criada em'),
            ('Cortou em', 'Cortou em'),
            ('Data Entrada', 'Data Entrada'),
            ('Data Chegada', 'Data Chegada'),
            ('Descrição', 'Descricao'),
            ('Total Enviado', 'Total'),
            ('Total Retornado', 'Ret Total'),
            ('Total Defeitos', 'Def Total'),
            ('Status', 'Status'),
            ('Observações', 'Observacoes'),
        ]
        
        for label, key in campos_exibir:
            row_frame = ttk.Frame(frame)
            row_frame.pack(fill='x', pady=3)
            
            ttk.Label(
                row_frame, 
                text=f"{label}:", 
                font=('Arial', 10, 'bold'),
                width=15, anchor='e'
            ).pack(side='left')
            
            valor = dados.get(key, '')
            ttk.Label(
                row_frame,
                text=str(valor),
                font=('Arial', 10),
                anchor='w'
            ).pack(side='left', padx=10)
        
        ttk.Button(frame, text="Fechar", command=janela.destroy).pack(pady=15)
    
    # ===== FUNÇÕES DE PESQUISA =====
    
    def pesquisar_e_ir_para_aba(self):
        """Pesquisa facção e seleciona a aba correspondente"""
        faccao_pesquisa = self.entry_pesquisa_faccao.get().strip()
        
        if not faccao_pesquisa:
            messagebox.showwarning("Aviso", "Digite o nome da facção para pesquisar")
            return
        
        if self.df_banco is None or self.df_banco.empty or 'Faccao' not in self.df_banco.columns:
            messagebox.showinfo("Informação", "Nenhum fornecedor cadastrado")
            return
        
        fornecedores = sorted(self.df_banco['Faccao'].dropna().unique())
        
        faccao_encontrada = None
        for fornecedor in fornecedores:
            if faccao_pesquisa.lower() in fornecedor.lower():
                faccao_encontrada = fornecedor
                break
        
        if faccao_encontrada:
            self.notebook.select(self.frame_faccoes)
            self.selecionar_aba(faccao_encontrada)
            messagebox.showinfo("Encontrado", f"🏖️ Facção encontrada: {faccao_encontrada}")
        else:
            messagebox.showinfo("Não encontrado", f"Facção '{faccao_pesquisa}' não encontrada")
    
    def editar_registro_selecionado(self, tree, df_resultados):
        """Edita o registro selecionado na treeview de resultados"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um registro para editar")
            return
        
        item = selection[0]
        values = tree.item(item, 'values')
        
        referencia = values[1]
        ciclo = values[2]
        op = values[3]
        
        mask = (self.df_banco['OP'] == op) & \
            (self.df_banco['Referencia'] == referencia) & \
            (self.df_banco['Ciclo'] == ciclo)
        
        if mask.any():
            idx = self.df_banco[mask].index[0]
            self.abrir_janela_edicao(idx)
        else:
            messagebox.showerror("Erro", "Registro não encontrado no banco de dados")
    
    # ===== AJUDA =====
    
    def mostrar_ajuda(self):
        """Mostra ajuda com estilo praia"""
        messagebox.showinfo(
            "🏖️ Ajuda - Borana Controle de Produção",
            "🌊 Bem-vindo ao Sistema de Controle de Produção!\n\n"
            "📌 Funcionalidades:\n"
            "• Visualização de produção por facção\n"
            "• Edição de quantidades enviadas e recebidas\n"
            "• Registro de 'OP Criada em' e 'Cortou em'\n"
            "• Relatórios e gráficos interativos\n"
            "• Histórico completo de OPs finalizadas (location NULL)\n"
            "• Histórico com paginação (navegação rápida)\n"
            "• Pesquisa rápida por OP, referência e ciclo\n"
            "• Filtros por data e status\n\n"
            "🔄 Importar TOTVS (Ordens Ativas):\n"
            "• Busca ordens ativas (com location) no TOTVS\n"
            "• Rápido (poucos registros)\n"
            "• Atualiza ordens existentes preservando dados locais\n\n"
            "📜 Importar Histórico TOTVS:\n"
            "• Busca ordens SEM location (location NULL)\n"
            "• Ordens já concluídas/expedidas\n"
            "• Salvas em arquivo separado (BANCODEDADOS_HISTORICO.csv)\n"
            "• Só importa quando solicitado (botão na aba Histórico)\n"
            "• Navegação por páginas (padrão: 100 itens/página)\n\n"
            "📏 Tamanhos:\n"
            "• Todos os tamanhos: PP, P, M, G, GG, U\n"
            "• Tamanhos numéricos (34, 36, 38...) vão para 'U'\n\n"
            "💾 Dados Locais:\n"
            "• Ativas: BANCODEDADOS_FACCAO.csv\n"
            "• Histórico: BANCODEDADOS_HISTORICO.csv\n"
            "• Faça backups regularmente"
        )