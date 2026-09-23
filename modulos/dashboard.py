"""
Módulo de Dashboard - Visão geral da produção
"""

import tkinter as tk
from tkinter import ttk
from config.cores import TemaPraia
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ModuloDashboard:
    """Módulo de Dashboard - Visão geral da produção"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.cores = TemaPraia()
        self._criar_interface()
    
    def _criar_interface(self):
        """Cria a interface do dashboard"""
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Título - usando tk.Label para ter mais controle sobre cores
        tk.Label(
            main_frame,
            text="📊 Dashboard de Produção",
            font=('Segoe UI', 20, 'bold'),
            fg=self.cores.AZUL_MAR_ESCURO,
            bg=self.cores.BRANCO_NEVE
        ).pack(anchor='w', pady=(0, 15))
        
        # Cards de métricas
        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill='x', pady=10)
        
        self.cards = {}
        metricas = [
            ('Total Produção', '0 peças', self.cores.VERDE_COQUEIRO, '📦'),
            ('Facções Ativas', '0', self.cores.AZUL_MAR, '🏭'),
            ('Drops em Criação', '0', self.cores.CORAL, '🎨'),
            ('Meta Mensal', '0%', self.cores.AREIA_ESCURA, '🎯')
        ]
        
        for i, (titulo, valor, cor, icone) in enumerate(metricas):
            card = tk.Frame(
                cards_frame,
                bg=self.cores.BRANCO,
                relief=tk.RAISED,
                bd=2,
                highlightthickness=2,
                highlightbackground=cor
            )
            card.pack(side=tk.LEFT, padx=10, expand=True, fill='x')
            
            tk.Label(
                card,
                text=f"{icone} {titulo}",
                font=('Segoe UI', 11),
                bg=self.cores.BRANCO,
                fg=self.cores.CINZA_ESCURO
            ).pack(pady=(10, 0))
            
            lbl_valor = tk.Label(
                card,
                text=valor,
                font=('Segoe UI', 20, 'bold'),
                bg=self.cores.BRANCO,
                fg=cor
            )
            lbl_valor.pack(pady=(5, 10))
            
            self.cards[titulo] = lbl_valor
        
        # Área de gráficos
        graficos_frame = tk.Frame(
            main_frame,
            bg=self.cores.BRANCO,
            relief=tk.RAISED,
            bd=2
        )
        graficos_frame.pack(fill='both', expand=True, pady=15)
        
        tk.Label(
            graficos_frame,
            text="📈 Produção Diária",
            font=('Segoe UI', 14, 'bold'),
            bg=self.cores.BRANCO,
            fg=self.cores.AZUL_MAR_ESCURO
        ).pack(pady=5)
        
        # Figura para gráfico
        self.fig = plt.Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, graficos_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
    
    def atualizar(self, dados):
        """Atualiza o dashboard com novos dados"""
        try:
            if 'total_producao' in dados:
                self.cards['Total Produção'].config(text=f"{dados['total_producao']} peças")
            if 'faccoes_ativas' in dados:
                self.cards['Facções Ativas'].config(text=str(dados['faccoes_ativas']))
            if 'drops_ativos' in dados:
                self.cards['Drops em Criação'].config(text=str(dados['drops_ativos']))
            if 'meta_progresso' in dados:
                self.cards['Meta Mensal'].config(text=f"{dados['meta_progresso']:.1f}%")
            
            self.ax.clear()
            if dados.get('producao_diaria'):
                datas = list(dados['producao_diaria'].keys())
                valores = list(dados['producao_diaria'].values())
                self.ax.bar(range(len(datas)), valores, color=self.cores.CORAL)
                self.ax.set_xticks(range(len(datas)))
                self.ax.set_xticklabels(datas, rotation=45, ha='right', fontsize=8)
                self.ax.set_ylabel('Peças')
                self.ax.set_title('Produção Diária (Últimos 7 dias)')
            self.canvas.draw()
            
        except Exception as e:
            import logging
            logging.error(f"Erro ao atualizar dashboard: {e}")