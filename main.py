"""
Borana ERP - Sistema de Gestão de Produção Integrado
Versão: 2.0.0
Autor: Borana Moda Praia
Ponto de entrada do sistema
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import traceback
import sys
from datetime import datetime

# Importar módulos
from config.cores import TemaPraia
from core.utils import configurar_icone_app
from modulos.faccoes import ModuloFaccoes
from modulos.cronograma import ModuloCronograma
from modulos.produtividade import ModuloProdutividade

# Constantes
APP_NAME = "Borana ERP - PCP"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Borana"

class BoranaERP:
    """Sistema ERP unificado para gestão de produção"""
    
    def __init__(self):
        # ============================================================
        # JANELA PRINCIPAL
        # ============================================================
        
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.state('zoomed')
        self.root.configure(bg=TemaPraia.BRANCO_NEVE)
        
        # Configurar ícone
        configurar_icone_app(self.root)
        
        # ============================================================
        # MENU PRINCIPAL
        # ============================================================
        
        self._criar_menu()
        
        # ============================================================
        # HEADER COM ABAS INTEGRADAS
        # ============================================================
        
        self._criar_header_com_abas()
        
        # ============================================================
        # ÁREA DE CONTEÚDO
        # ============================================================
        
        # Frame para o conteúdo principal (abaixo do header)
        self.content_frame = tk.Frame(
            self.root,
            bg=TemaPraia.BRANCO_NEVE
        )
        self.content_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Inicializar módulos no frame de conteúdo
        self._inicializar_modulos()
        
        # ============================================================
        # BARRA DE STATUS
        # ============================================================
        
        self.status_bar = tk.Label(
            self.root,
            text="🏭 Borana ERP - Pronto para usar!",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg=TemaPraia.AZUL_AGUA,
            fg=TemaPraia.AZUL_MAR_ESCURO,
            font=('Arial', 10)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ============================================================
        # INICIALIZAÇÃO
        # ============================================================
        
        self._carregar_dados_iniciais()
    
    def _criar_menu(self):
        """Cria o menu principal"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu Arquivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Arquivo", menu=file_menu)
        file_menu.add_command(label="📊 Gerar Relatório", command=self._gerar_relatorio_geral)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Sair", command=self.root.quit)
        
        # Menu Ferramentas
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔧 Ferramentas", menu=tools_menu)
        tools_menu.add_command(label="💾 Backup", command=self._fazer_backup)
        tools_menu.add_separator()
        tools_menu.add_command(label="📋 Logs", command=self._ver_logs)
        
        # Menu Ajuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Ajuda", menu=help_menu)
        help_menu.add_command(label="📖 Manual", command=self._mostrar_ajuda)
        help_menu.add_command(label="ℹ️ Sobre", command=self._mostrar_sobre)
    
    def _criar_header_com_abas(self):
        """Cria o cabeçalho da aplicação com abas integradas"""
        
        # ============================================================
        # HEADER PRINCIPAL
        # ============================================================
        
        header = tk.Frame(
            self.root,
            bg=TemaPraia.AZUL_MAR,
            height=100  # Altura suficiente para título + abas
        )
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # ============================================================
        # PARTE SUPERIOR DO HEADER (Título + Relógio)
        # ============================================================
        
        top_frame = tk.Frame(header, bg=TemaPraia.AZUL_MAR)
        top_frame.pack(fill=tk.X, pady=(8, 0))
        
        # Título
        tk.Label(
            top_frame,
            text=f"🏖️ {APP_NAME}",
            font=('Arial', 18, 'bold'),
            fg=TemaPraia.BRANCO,
            bg=TemaPraia.AZUL_MAR
        ).pack(side=tk.LEFT, padx=20)
        
        # Versão
        tk.Label(
            top_frame,
            text=f"v{APP_VERSION}",
            font=('Arial', 10),
            fg=TemaPraia.AZUL_AGUA,
            bg=TemaPraia.AZUL_MAR
        ).pack(side=tk.LEFT, padx=5)
        
        # Relógio
        self.lbl_relogio = tk.Label(
            top_frame,
            font=('Arial', 11),
            fg=TemaPraia.BRANCO,
            bg=TemaPraia.AZUL_MAR
        )
        self.lbl_relogio.pack(side=tk.RIGHT, padx=20)
        self._atualizar_relogio()
        
        # ============================================================
        # PARTE INFERIOR DO HEADER (Abas)
        # ============================================================
        
        # Frame para as abas
        tab_frame = tk.Frame(header, bg=TemaPraia.AZUL_MAR)
        tab_frame.pack(fill=tk.X, pady=(8, 8), padx=10)
        
        # Configurar estilo personalizado para as abas
        style = ttk.Style()
        style.theme_use('clam')
        
        # Estilo do notebook
        style.configure(
            'Header.TNotebook',
            background=TemaPraia.AZUL_MAR,
            borderwidth=0,
            tabmargins=[2, 2, 2, 0]
        )
        
        # Estilo das abas
        style.configure(
            'Header.TNotebook.Tab',
            background=TemaPraia.AZUL_AGUA,
            foreground=TemaPraia.AZUL_MAR_ESCURO,
            padding=[20, 8],
            font=('Arial', 10, 'bold'),
            borderwidth=0,
            focuscolor='none'
        )
        
        # Estilo das abas quando selecionadas ou com hover
        style.map(
            'Header.TNotebook.Tab',
            background=[
                ('selected', TemaPraia.BRANCO_NEVE),
                ('active', TemaPraia.BRANCO)
            ],
            foreground=[
                ('selected', TemaPraia.AZUL_MAR_ESCURO),
                ('active', TemaPraia.AZUL_MAR_ESCURO)
            ],
            relief=[('selected', 'flat')]
        )
        
        # ============================================================
        # NOTEBOOK COM AS ABAS (APENAS PARA NAVEGAÇÃO)
        # ============================================================
        
        self.notebook = ttk.Notebook(tab_frame, style='Header.TNotebook')
        self.notebook.pack(fill='both', expand=True)
        
        # Criar abas vazias apenas para navegação (sem Dashboard)
        for tab_name in ['🏭 Facções', '📅 Cronograma', '⚡ Produtividade']:
            empty_frame = ttk.Frame(self.notebook)
            self.notebook.add(empty_frame, text=tab_name)
        
        # Selecionar a primeira aba (Facções) como padrão
        self.notebook.select(0)
        
        # Vincular evento de mudança de aba para atualizar o conteúdo
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
    
    def _inicializar_modulos(self):
        """Inicializa os módulos no frame de conteúdo"""
        
        # Frame para cada módulo (todos empilhados, apenas um visível por vez)
        # Facções (primeiro, será o padrão)
        self.frame_faccoes = tk.Frame(self.content_frame, bg=TemaPraia.BRANCO_NEVE)
        self.modulo_faccoes = ModuloFaccoes(self.frame_faccoes, self)
        self.frame_faccoes.pack(fill='both', expand=True)  # Visível por padrão
        
        # Cronograma
        self.frame_cronograma = tk.Frame(self.content_frame, bg=TemaPraia.BRANCO_NEVE)
        self.modulo_cronograma = ModuloCronograma(self.frame_cronograma, self)
        
        # Produtividade
        self.frame_produtividade = tk.Frame(self.content_frame, bg=TemaPraia.BRANCO_NEVE)
        self.modulo_produtividade = ModuloProdutividade(self.frame_produtividade, self)
    
    def _on_tab_changed(self, event):
        """Manipula a mudança de aba"""
        # Obter o índice da aba selecionada
        tab_index = self.notebook.index(self.notebook.select())
        
        # Esconder todos os frames
        self.frame_faccoes.pack_forget()
        self.frame_cronograma.pack_forget()
        self.frame_produtividade.pack_forget()
        
        # Mostrar o frame correspondente
        if tab_index == 0:  # Facções
            self.frame_faccoes.pack(fill='both', expand=True)
            self.status_bar.config(text="🏭 Facções - Gestão de terceirizados")
        elif tab_index == 1:  # Cronograma
            self.frame_cronograma.pack(fill='both', expand=True)
            self.status_bar.config(text="📅 Cronograma - Gestão de drops e prazos")
        elif tab_index == 2:  # Produtividade
            self.frame_produtividade.pack(fill='both', expand=True)
            self.status_bar.config(text="⚡ Produtividade - Controle interno de produção")
    
    def _atualizar_relogio(self):
        """Atualiza o relógio no header"""
        agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        self.lbl_relogio.config(text=f"🕐 {agora}")
        self.root.after(1000, self._atualizar_relogio)
    
    def _carregar_dados_iniciais(self):
        """Carrega dados iniciais"""
        # Atualizar dados iniciais se necessário
        pass
    
    # ================================================================
    # FUNÇÕES DO MENU
    # ================================================================
    
    def _gerar_relatorio_geral(self):
        messagebox.showinfo("Relatório", "Função de relatório geral em desenvolvimento")
    
    def _fazer_backup(self):
        messagebox.showinfo("Backup", "Função de backup em desenvolvimento")
    
    def _ver_logs(self):
        messagebox.showinfo("Logs", "Função de visualização de logs em desenvolvimento")
    
    def _mostrar_ajuda(self):
        messagebox.showinfo(
            "📖 Ajuda - Borana ERP",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "Módulos disponíveis:\n"
            "🏭 Facções - Gestão de terceirizados\n"
            "📅 Cronograma - Gestão de drops e prazos\n"
            "⚡ Produtividade - Controle interno\n\n"
            f"Desenvolvido por: {APP_AUTHOR}"
        )
    
    def _mostrar_sobre(self):
        messagebox.showinfo(
            "ℹ️ Sobre",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "Sistema integrado de gestão de produção\n"
            "Borana Moda Praia\n"
            f"Desenvolvido por: {APP_AUTHOR}\n\n"
            "Módulos:\n"
            "• Facções (Terceirizados)\n"
            "• Cronograma (Drops)\n"
            "• Produtividade (Interna)"
        )
    
    def run(self):
        """Executa a aplicação"""
        self.root.mainloop()

# ================================================================
# PONTO DE ENTRADA
# ================================================================

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        app = BoranaERP()
        app.run()
    except Exception as e:
        logging.error(f"Erro fatal: {e}")
        logging.error(traceback.format_exc())
        messagebox.showerror(
            "Erro Fatal",
            f"Ocorreu um erro ao iniciar o sistema:\n\n{str(e)}\n\n"
            "Verifique os logs para mais detalhes."
        )