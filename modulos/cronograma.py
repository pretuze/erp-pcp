"""
Módulo de Cronograma e Drops
Código completo do controle_cronograma_app.py adaptado para o ERP unificado
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import datetime
import logging
import threading
import time
import os
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from collections import defaultdict
from dataclasses import dataclass, field
import re
import hashlib
import queue
from contextlib import contextmanager

from config.cores import TemaPraia
from config.constantes import SUBSETORES_CRIACAO_ORDEM, SETORES_PRINCIPAIS
from core.database_manager import DatabaseManager
from widgets.scrollable_frame import ScrollableFrame

# ============================================================
# CONFIGURAÇÕES
# ============================================================

if getattr(__import__('sys'), 'frozen', False):
    APP_DIR = Path(__import__('sys').executable).parent
else:
    APP_DIR = Path(__file__).parent.parent

CONFIG_DIR = APP_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

DROPS_TEMPORARIOS_FILE = CONFIG_DIR / "drops_temporarios.json"
PRAZOS_FILE = CONFIG_DIR / "prazos.json"
ULTIMA_COLECAO_FILE = CONFIG_DIR / "ultima_colecao.json"

# ============================================================
# CORES DO TEMA
# ============================================================

class TemaPraia:
    """Paleta de cores inspirada em moda praia"""
    
    AZUL_MAR = "#0ea5e9"
    AZUL_MAR_ESCURO = "#0369a1"
    AZUL_MAR_MUITO_ESCURO = "#0c4a6e"
    AZUL_CEU = "#38bdf8"
    AZUL_AGUA = "#7dd3fc"
    AZUL_CLARO = "#bae6fd"
    
    VERDE_COQUEIRO = "#22c55e"
    VERDE_MAR = "#059669"
    VERDE_CLARO = "#86efac"
    
    AREIA = "#fbbf24"
    AREIA_CLARA = "#fde68a"
    AREIA_ESCURA = "#d97706"
    
    CORAL = "#fb7185"
    FLAMINGO = "#f472b6"
    ROSA_CLARO = "#fbcfe8"
    
    BRANCO = "#ffffff"
    BRANCO_NEVE = "#f8fafc"
    BRANCO_GELO = "#f1f5f9"
    
    CINZA_CLARO = "#e2e8f0"
    CINZA_MEDIO = "#94a3b8"
    CINZA_ESCURO = "#475569"
    
    STATUS_OK = "#22c55e"
    STATUS_ATENCAO = "#fbbf24"
    STATUS_ATRASADO = "#ef4444"
    STATUS_PRAZO = "#0ea5e9"

# ============================================================
# MAPEAMENTO DE SETORES
# ============================================================

SETORES_PRINCIPAIS = [
    "CORTE",
    "PRODUÇÃO", 
    "ACABAMENTO",
    "ETIQUETAGEM",
    "ESTOQUE",
    "OUTROS" 
]

MAPEAMENTO_SUB_SETORES = {
    # Corte
    "DESENVOLVIMENTO DE PRODUTO": "CORTE",
    "ENCAIXE E RISCO": "CORTE",
    "CORTE PILOTO": "CORTE",
    "ESTOQUE PILOTOS": "CORTE",
    "005-PCP": "CORTE",
    "SEPARACAO DE MATERIAIS": "CORTE",
    "ALMOXARIFADO TECIDOS": "CORTE",
    "CORTE": "CORTE",

    # Produção
    "030-ALMOXARIFADO AVIAMENTOS": "PRODUÇÃO",
    "DISTRIBUICAO COSTURA": "PRODUÇÃO",
    "GRUPO COSTURA BIQUINI": "PRODUÇÃO",
    "GRUPO COSTURA ROUPA": "PRODUÇÃO",
    "ALAELCIA FACCAO SERRA": "PRODUÇÃO",
    "AMELIA FACCAO GURIRI": "PRODUÇÃO",
    "ANDERSON FACCAO SAO GABRIEL DA PALHA": "PRODUÇÃO",
    "BLIZU SUBLIMACAO - COLATINA": "PRODUÇÃO",
    "CLEIDIANE FACCAO SERRA": "PRODUÇÃO",
    "DAIANE - 1 FACCAO GURIRI": "PRODUÇÃO",
    "DANIELE FACCAO VIANA": "PRODUÇÃO",
    "DANIELLY FACCAO SGP": "PRODUÇÃO",
    "DULCINEIA FACCAO SGP": "PRODUÇÃO",
    "EDNA OFICNIA SAO MATEUS": "PRODUÇÃO",
    "EDNAIDE FACCAO LINHARES": "PRODUÇÃO",
    "ELIANE - SAO MATEUS": "PRODUÇÃO",
    "ESTAMPARIA GUSTAVO": "PRODUÇÃO",
    "ESTOQUE PRODUCAO CROCHE": "PRODUÇÃO",
    "EXTERNO COSTURA ANGELITA OFICINA SAO MAT": "PRODUÇÃO",
    "EXTERNO COSTURA EDIVANIA SAO GABRIEL DA": "PRODUÇÃO",
    "EXTERNO COSTURA JAQUELINE FELIX - SERRA": "PRODUÇÃO",
    "EXTERNO COSTURA OFICINA HOSANA VILA VELH": "PRODUÇÃO",
    "EXTERNO COSTURA ROSA RUFINO - SERRA": "PRODUÇÃO",
    "EXTERNO CROCHE ROBSON TEIXEIRA": "PRODUÇÃO",
    "FABIOLA FACCAO SAO MATEUS": "PRODUÇÃO",
    "FABRICIA FACCAO NOVA VENECIA": "PRODUÇÃO",
    "FACCAO ADEINDIA - LINHARES": "PRODUÇÃO",
    "FACCAO DAIANA 2 GURIRI": "PRODUÇÃO",
    "FERNANDO FACCAO COLATINA": "PRODUÇÃO",
    "GABRIELLY PIEKARZ": "PRODUÇÃO",
    "IONES FACCAO GURIRI": "PRODUÇÃO",
    "JOAO GUILHERME - LINHARES": "PRODUÇÃO",
    "LUZIA FACCAO LINHARES": "PRODUÇÃO",
    "MAICQUELINE FACCAO LINHARES": "PRODUÇÃO",
    "MARCILENE FACCAO LINHARES": "PRODUÇÃO",
    "DHESSYK - MANTENA": "PRODUÇÃO",
    "PRISCILA - MANTENA": "PRODUÇÃO",
    "FERNANDA DE SOUZA - MANTENA": "PRODUÇÃO",
    "MARINETE SAO GABRIEL DA PALHA": "PRODUÇÃO",
    "NEUZA - MANTENA": "PRODUÇÃO",
    "MARIA LIANE - MANTENA": "PRODUÇÃO",
    "OFICINA CIDA GURIRI NOVO": "PRODUÇÃO",
    "PALOMA FACCAO MARILANDIA": "PRODUÇÃO",
    "ROSANE FACCAO SAO GABRIEL DA PALHA": "PRODUÇÃO",
    "ROSANGELA FACCAO FRIBURGO": "PRODUÇÃO",
    "ROSIANI MACHADO FACCAO VILA VELHA": "PRODUÇÃO",
    "SUZANA APARECIDA FACCAO SAO MATEUS": "PRODUÇÃO",
    "VALDIRENE - SAO MATEUS": "PRODUÇÃO",
    "VERAIDES OFICINA SAO MATEUS": "PRODUÇÃO",
    "VERONICA NOVO OFICINA SAO MATEUSI": "PRODUÇÃO",

    # Acabamento
    "060-ACABAMENTO/LIMPEZA": "ACABAMENTO", 
    "REVISAO DE COSTURA": "ACABAMENTO",
    "065-REVISAO QUALIDADE": "ACABAMENTO",

    # Etiquetagem
    "070-ETIQUETAGEM E EMBALAGEM": "ETIQUETAGEM",
    
    # Estoque
    "FINALIZACAO": "ESTOQUE",
    "CONFERENCIA": "ESTOQUE",    
}

ORDEM_TAMANHOS = {"PP": 0, "P": 1, "M": 2, "G": 3, "GG": 4, "XG": 5, "XGG": 6, "ÚNICO": 7}

def normalizar_setor(sub_setor: str) -> str:
    """Converte um sub-setor do banco para o setor principal correspondente"""
    if not sub_setor:
        return "ESTOQUE"
    
    sub_setor_upper = sub_setor.upper().strip()
    
    if sub_setor_upper in MAPEAMENTO_SUB_SETORES:
        return MAPEAMENTO_SUB_SETORES[sub_setor_upper]
    
    for key, value in MAPEAMENTO_SUB_SETORES.items():
        if key in sub_setor_upper or sub_setor_upper in key:
            return value
    
    if any(palavra in sub_setor_upper for palavra in ["CORT", "CORTE", "ENCAIXE", "RISCO", "PILOTO", "ALMOXARIFADO TECIDOS"]):
        return "CORTE"
    elif any(palavra in sub_setor_upper for palavra in ["COSTUR", "FACCAO", "OFICINA", "ESTAMPARIA", "CROCHE", "PRODU"]):
        return "PRODUÇÃO"
    elif any(palavra in sub_setor_upper for palavra in ["ACAB", "LIMPEZA", "REVISAO", "QUALIDADE"]):
        return "ACABAMENTO"
    elif any(palavra in sub_setor_upper for palavra in ["ETIQUET", "EMBALAGEM"]):
        return "ETIQUETAGEM"
    elif any(palavra in sub_setor_upper for palavra in ["ESTOQ", "FINALIZACAO", "CONFERENCIA"]):
        return "ESTOQUE"
    
    return "OUTROS"

# ============================================================
# DAOs PARA CONSULTAR O BANCO
# ============================================================

class ColecoesDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def listar_todas(self) -> List[Dict]:
        query = """
            SELECT DISTINCT 
                collection_code,
                collection_name
            FROM public.products
            WHERE collection_code IS NOT NULL 
              AND collection_code != ''
              AND collection_name IS NOT NULL
              AND collection_name != ''
            ORDER BY collection_name
        """
        return self.db.execute_query(query, db_type='totvs')


class ProdutosDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def listar_por_colecao(self, collection_name: str) -> List[Dict]:
        query = """
            SELECT 
                product_code,
                product_size,
                group_code,
                group_name,
                collection_code,
                collection_name
            FROM public.products
            WHERE collection_name = %s
              AND group_code IS NOT NULL
              AND group_code != ''
            ORDER BY group_code, product_size
        """
        return self.db.execute_query(query, (collection_name,), db_type='totvs')


class OrdensProducaoDAO:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def buscar_por_produtos(self, product_codes: List[str]) -> List[Dict]:
        if not product_codes:
            return []
        
        placeholders = ','.join(['%s'] * len(product_codes))
        query = """
            SELECT 
                cycle_code,
                order_code,
                product_code,
                size_name,
                quantity,
                finished_quantity,
                pending_quantity,
                status,
                estimated_delivery_date,
                insert_date,
                last_change_date,
                locations,
                reference_code,
                reference_name
            FROM public.production_order_items
            WHERE product_code IN ({placeholders})
              AND status IN (10, 20, 30, 40)
              AND quantity >= 5
            ORDER BY cycle_code, order_code
        """.format(placeholders=placeholders)
        
        return self.db.execute_query(query, tuple(product_codes), db_type='totvs')
    
    def buscar_locations_por_produtos(self, product_codes: List[str]) -> List[Dict]:
        """Busca as locations para os produtos - MÉTODO ADICIONADO"""
        if not product_codes:
            return []
        
        logging.info(f"Buscando locations para {len(product_codes)} produtos")
        
        ordens = self.buscar_por_produtos(product_codes)
        logging.info(f"Encontradas {len(ordens)} ordens de produção")
        
        locations_normalizadas = []
        
        for ordem in ordens:
            cycle_code = str(ordem.get('cycle_code', ''))
            order_code = str(ordem.get('order_code', ''))
            op = f"{cycle_code}-{order_code}" if cycle_code and order_code else ""
            product_code = str(ordem.get('product_code', ''))
            size_name = ordem.get('size_name', '')
            quantity_total = ordem.get('quantity', 0)
            
            if quantity_total <= 1:
                continue
            
            locations_data = ordem.get('locations')
            if not locations_data:
                continue
            
            if isinstance(locations_data, str):
                try:
                    locations_data = json.loads(locations_data)
                except:
                    continue
            
            if not isinstance(locations_data, list):
                continue
            
            for loc in locations_data:
                loc_product_code = loc.get('productCode')
                if not loc_product_code:
                    continue
                
                loc_product_code = str(loc_product_code)
                
                if product_code and loc_product_code != product_code:
                    continue
                
                location_name = loc.get('locationName', '')
                sub_setor_original = location_name
                if location_name:
                    location_name = normalizar_setor(location_name)
                
                quantity = loc.get('quantity', 0)
                timestamp = loc.get('entryDate', None)
                
                if timestamp and isinstance(timestamp, str):
                    try:
                        timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        timestamp = None
                
                loc_size_name = loc.get('productSize', size_name) or size_name
                
                locations_normalizadas.append({
                    'product_code': loc_product_code,
                    'op': op,
                    'location_name': location_name,
                    'sub_setor_original': sub_setor_original,
                    'quantity': quantity,
                    'timestamp': timestamp,
                    'size_name': loc_size_name,
                    'quantity_total': quantity_total
                })
        
        seen = set()
        unique_locations = []
        for loc in locations_normalizadas:
            key = (loc['product_code'], loc['op'], loc['location_name'], loc['quantity'], loc['size_name'])
            if key not in seen:
                seen.add(key)
                unique_locations.append(loc)
        
        logging.info(f"Locations normalizadas: {len(unique_locations)} registros únicos")
        return unique_locations


# ============================================================
# GERENCIADOR DE DROPS TEMPORÁRIOS
# ============================================================

class GerenciadorDropsTemporarios:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.drops: Dict[str, Dict] = {}
            self._carregar()
    
    def _carregar(self):
        if DROPS_TEMPORARIOS_FILE.exists():
            try:
                with open(DROPS_TEMPORARIOS_FILE, 'r', encoding='utf-8') as f:
                    self.drops = json.load(f)
            except Exception as e:
                logging.error(f"Erro ao carregar drops temporários: {e}")
                self.drops = {}
        else:
            self.drops = {}
            self._salvar()
    
    def _salvar(self):
        try:
            with open(DROPS_TEMPORARIOS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.drops, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Erro ao salvar drops temporários: {e}")
    
    def criar_drop(self, nome: str, quantidade_referencias: int) -> Dict:
        if nome in self.drops:
            raise ValueError(f"Drop '{nome}' já existe")
        
        drop_data = {
            "nome": nome,
            "quantidade_referencias": quantidade_referencias,
            "data_criacao": datetime.datetime.now().isoformat(),
            "status": "criacao",
            "subsetores": {},
            "referencias_movidas": 0,
            "drop_permanente": None,
            "historico": []
        }
        
        for sub in SUBSETORES_CRIACAO_ORDEM:
            drop_data["subsetores"][sub] = {
                "quantidade": 0,
                "data_entrada": None,
                "data_saida": None,
                "observacao": ""
            }
        
        primeiro_sub = SUBSETORES_CRIACAO_ORDEM[0]
        drop_data["subsetores"][primeiro_sub]["quantidade"] = quantidade_referencias
        drop_data["subsetores"][primeiro_sub]["data_entrada"] = datetime.datetime.now().isoformat()
        
        self.drops[nome] = drop_data
        self._salvar()
        return drop_data
    
    def obter_drop(self, nome: str) -> Optional[Dict]:
        return self.drops.get(nome)
    
    def listar_drops(self) -> List[Dict]:
        return [{"nome": nome, **dados} for nome, dados in self.drops.items()]
    
    def obter_drops_ativos(self) -> List[Dict]:
        return [{"nome": nome, **dados} for nome, dados in self.drops.items()
                if dados.get("status") != "vinculado"]
    
    def remover_drop(self, nome: str) -> bool:
        if nome in self.drops:
            del self.drops[nome]
            self._salvar()
            return True
        return False
    
    def recarregar(self):
        """Recarrega os drops do arquivo"""
        self._carregar()
        return self.drops

# ============================================================
# GERENCIADOR DE PRAZOS
# ============================================================

class PrazoManager:
    def __init__(self):
        self.prazos: Dict[str, Dict[str, dict]] = {}
        self.datas_lancamento: Dict[str, datetime.date] = {}
        self.carregar_prazos()
    
    def carregar_prazos(self) -> None:
        if PRAZOS_FILE.exists():
            try:
                with open(PRAZOS_FILE, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                
                for nome_colecao, dados_colecao in dados.items():
                    self.prazos[nome_colecao] = dados_colecao.get('prazos_setores', {})
                    if 'data_lancamento' in dados_colecao and dados_colecao['data_lancamento']:
                        try:
                            self.datas_lancamento[nome_colecao] = datetime.date.fromisoformat(dados_colecao['data_lancamento'])
                        except:
                            pass
            except Exception as e:
                logging.error(f"Erro ao carregar prazos: {e}")
    
    def salvar_prazos(self) -> None:
        try:
            dados = {}
            for nome_colecao, prazos_setores in self.prazos.items():
                dados[nome_colecao] = {
                    'prazos_setores': prazos_setores
                }
                if nome_colecao in self.datas_lancamento:
                    dados[nome_colecao]['data_lancamento'] = self.datas_lancamento[nome_colecao].isoformat()
            
            with open(PRAZOS_FILE, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Erro ao salvar prazos: {e}")
    
    def definir_prazo_setor(self, collection_name: str, setor: str, data_limite: Optional[datetime.date], observacao: str = "") -> None:
        if collection_name not in self.prazos:
            self.prazos[collection_name] = {}
        self.prazos[collection_name][setor] = {
            'data_limite': data_limite.isoformat() if data_limite else None,
            'observacao': observacao
        }
        self.salvar_prazos()
    
    def definir_data_lancamento(self, collection_name: str, data: Optional[datetime.date]) -> None:
        if data:
            self.datas_lancamento[collection_name] = data
        else:
            self.datas_lancamento.pop(collection_name, None)
        self.salvar_prazos()
    
    def obter_prazo_setor(self, collection_name: str, setor: str) -> Optional[dict]:
        if collection_name in self.prazos and setor in self.prazos[collection_name]:
            return self.prazos[collection_name][setor]
        return None
    
    def obter_data_lancamento(self, collection_name: str) -> Optional[datetime.date]:
        return self.datas_lancamento.get(collection_name)

# ============================================================
# COMPONENTES DE INTERFACE
# ============================================================

class Badge(tk.Frame):
    CORES_BADGE = {
        "sucesso": TemaPraia.VERDE_COQUEIRO,
        "atencao": TemaPraia.AREIA,
        "erro": TemaPraia.CORAL,
        "info": TemaPraia.AZUL_MAR,
        "destaque": TemaPraia.FLAMINGO,
        "neutro": TemaPraia.CINZA_MEDIO
    }
    
    def __init__(self, parent, texto, tipo="info", tamanho=10, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        cores = TemaPraia()
        cor_fundo = self.CORES_BADGE.get(tipo, cores.AZUL_MAR)
        
        self.configure(
            bg=cor_fundo,
            relief=tk.FLAT,
            padx=8,
            pady=3
        )
        
        self.label = tk.Label(
            self,
            text=texto,
            font=('Arial', tamanho, 'bold'),
            fg=cores.BRANCO,
            bg=cor_fundo
        )
        self.label.pack()


class ImageManager:
    _instance = None
    _indice_imagens: Dict[str, str] = {}
    _cache_imagens: Dict[str, tk.PhotoImage] = {}
    _cache_max_size = 200
    _indexado = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.local_image_path = Path(r"\\192.168.1.240\Auxiliar\COMPARTILHAR\13 - Modelagem\03 - FOTOS COLEÇÕES")
            self.local_image_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
    
    def indexar_imagens(self, force: bool = False) -> None:
        if self._indexado and not force:
            return
        
        if not self.local_image_path.exists():
            logging.warning(f"Caminho de imagens não encontrado: {self.local_image_path}")
            self._indexado = True
            return
        
        self._indice_imagens = {}
        total_arquivos = 0
        
        try:
            for ext in self.local_image_extensions:
                for arquivo in self.local_image_path.rglob(f"*{ext}"):
                    if arquivo.is_file():
                        nome_sem_ext = arquivo.stem.upper()
                        caminho_str = str(arquivo)
                        self._indice_imagens[nome_sem_ext] = caminho_str
                        
                        nome_limpo = nome_sem_ext
                        for sufixo in ['_FRENTE', '_COSTAS', '_FRONT', '_BACK', '_1', '_2', '_3', ' FRENTE', ' COSTAS', ' FRONT', ' BACK']:
                            if nome_limpo.endswith(sufixo):
                                nome_limpo = nome_limpo[:-len(sufixo)]
                                self._indice_imagens[nome_limpo] = caminho_str
                                break
                        
                        total_arquivos += 1
                        if total_arquivos >= 50000:
                            break
                if total_arquivos >= 50000:
                    break
            
            self._indexado = True
            logging.info(f"Imagens indexadas: {len(self._indice_imagens)} arquivos")
            
        except Exception as e:
            logging.error(f"Erro ao indexar imagens: {e}")
            self._indexado = True
    
    def tratar_codigo_para_busca(self, codigo: str) -> str:
        if not codigo:
            return ""
        
        codigo = codigo.upper().strip()
        
        for prefixo in ['PP-', 'PR-', 'PP ', 'PR ', 'PP_', 'PR_']:
            if codigo.startswith(prefixo):
                codigo = codigo[len(prefixo):].strip()
                break
        else:
            if codigo.startswith('PP') and len(codigo) > 2:
                codigo = codigo[2:].strip()
            elif codigo.startswith('PR') and len(codigo) > 2:
                codigo = codigo[2:].strip()
        
        cores_sufixo = ['PRETO', 'BRANCO', 'AZUL', 'VERMELHO', 'VERDE', 'AMARELO', 
                       'ROSA', 'CINZA', 'MARROM', 'LARANJA', 'ROXO', 'BEGE',
                       'WHITE', 'BLACK', 'RED', 'BLUE', 'GREEN', 'YELLOW', 'PINK',
                       'OFF', 'ONCA', 'FLORAL', 'LISTRADO']
        for cor in cores_sufixo:
            if codigo.endswith(cor):
                codigo = codigo[:-len(cor)].strip()
                break
        
        codigo = re.sub(r'[PPMGX]{1,3}$', '', codigo).strip()
        return codigo
    
    def buscar_imagem(self, codigo: str) -> Optional[str]:
        if not self._indexado:
            self.indexar_imagens()
        
        if not codigo or not self._indice_imagens:
            return None
        
        codigo_busca = self.tratar_codigo_para_busca(codigo)
        if not codigo_busca:
            return None
        
        for nome_arquivo, caminho in self._indice_imagens.items():
            if codigo_busca == nome_arquivo:
                return caminho
        
        for nome_arquivo, caminho in self._indice_imagens.items():
            if codigo_busca in nome_arquivo:
                return caminho
        
        codigo_original = codigo.upper().strip()
        if codigo_original != codigo_busca:
            for nome_arquivo, caminho in self._indice_imagens.items():
                if codigo_original in nome_arquivo:
                    return caminho
        
        return None
    
    def carregar_imagem(self, caminho: str, tamanho_maximo: tuple = (150, 150)) -> Optional[tk.PhotoImage]:
        if not caminho or not os.path.exists(caminho):
            return None
        
        cache_key = f"{caminho}_{tamanho_maximo[0]}_{tamanho_maximo[1]}"
        if cache_key in self._cache_imagens:
            return self._cache_imagens[cache_key]
        
        try:
            from PIL import Image, ImageTk
            
            if len(self._cache_imagens) >= self._cache_max_size:
                first_key = next(iter(self._cache_imagens))
                del self._cache_imagens[first_key]
            
            img = Image.open(caminho)
            img.thumbnail(tamanho_maximo, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._cache_imagens[cache_key] = photo
            return photo
            
        except Exception as e:
            logging.error(f"Erro ao carregar imagem {caminho}: {e}")
            return None
    
    def buscar_e_carregar_imagem(self, codigo: str, tamanho_maximo: tuple = (150, 150)) -> Optional[tk.PhotoImage]:
        caminho = self.buscar_imagem(codigo)
        if caminho:
            return self.carregar_imagem(caminho, tamanho_maximo)
        return None


# ============================================================
# CARD GRUPO
# ============================================================

class CardGrupo(tk.Frame):
    def __init__(self, parent, grupo_view, image_manager=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.grupo_view = grupo_view
        self.image_manager = image_manager or ImageManager()
        self._imagem_carregada = False
        
        cores = TemaPraia()
        
        self.configure(
            bg=cores.BRANCO,
            relief=tk.RAISED,
            borderwidth=2,
            highlightthickness=2,
            highlightbackground=cores.AZUL_MAR,
            highlightcolor=cores.AZUL_MAR,
        )
        
        self._criar_widgets()
        self._carregar_imagem()
    
    def _criar_widgets(self):
        cores = TemaPraia()
        
        content = tk.Frame(self, bg=cores.BRANCO, relief=tk.FLAT)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        
        # Linha superior: código e total
        header_frame = tk.Frame(content, bg=cores.BRANCO)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        indicador = tk.Frame(
            header_frame,
            bg=cores.AZUL_MAR,
            width=5,
            height=25,
            relief=tk.FLAT,
            highlightthickness=0
        )
        indicador.pack(side=tk.LEFT, padx=(0, 8))
        indicador.pack_propagate(False)
        
        lbl_codigo = tk.Label(
            header_frame,
            text=self.grupo_view.group_code,
            font=('Arial', 12, 'bold'),
            fg=cores.AZUL_MAR_ESCURO,
            bg=cores.BRANCO
        )
        lbl_codigo.pack(side=tk.LEFT)
        
        total = self.grupo_view.total_quantidade
        badge_bg = cores.VERDE_COQUEIRO if total > 0 else cores.CINZA_MEDIO
        badge_frame = tk.Frame(
            header_frame,
            bg=badge_bg,
            relief=tk.FLAT,
            padx=6,
            pady=2
        )
        badge_frame.pack(side=tk.RIGHT)
        
        lbl_total = tk.Label(
            badge_frame,
            text=f"{total} peças",
            font=('Arial', 8, 'bold'),
            fg=cores.BRANCO,
            bg=badge_bg
        )
        lbl_total.pack()
        
        # Linha do meio: imagem e detalhes
        content_row = tk.Frame(content, bg=cores.BRANCO)
        content_row.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Coluna da imagem
        img_col = tk.Frame(content_row, bg=cores.BRANCO)
        img_col.pack(side=tk.LEFT, padx=(0, 10))
        
        self.img_frame = tk.Frame(
            img_col,
            bg=cores.AZUL_AGUA,
            width=85,
            height=85,
            relief=tk.RAISED,
            borderwidth=2,
            highlightthickness=1,
            highlightbackground=cores.AZUL_MAR
        )
        self.img_frame.pack()
        self.img_frame.pack_propagate(False)
        
        self.img_label = tk.Label(
            self.img_frame,
            text="🏄",
            font=('Arial', 30),
            bg=cores.AZUL_AGUA,
            fg=cores.AZUL_MAR
        )
        self.img_label.pack(fill=tk.BOTH, expand=True)
        
        # Nome do grupo
        lbl_nome = tk.Label(
            content_row,
            text=self.grupo_view.group_name,
            font=('Arial', 10, 'bold'),
            fg=cores.CINZA_ESCURO,
            bg=cores.BRANCO,
            wraplength=130,
            justify=tk.LEFT
        )
        lbl_nome.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Sub-setores e tamanhos
        info_col = tk.Frame(content, bg=cores.BRANCO)
        info_col.pack(fill=tk.X, pady=(5, 0))
        
        sub_setores = self.grupo_view.quantidade_por_sub_setor()
        if sub_setores:
            for sub_setor, tamanhos in sub_setores.items():
                if sub_setor:
                    sub_frame = tk.Frame(info_col, bg=cores.BRANCO)
                    sub_frame.pack(fill=tk.X, pady=2)
                    
                    lbl_sub = tk.Label(
                        sub_frame,
                        text=f"📍 {sub_setor}",
                        font=('Arial', 8, 'bold'),
                        fg=cores.AZUL_MAR_ESCURO,
                        bg=cores.BRANCO,
                        width=16,
                        anchor='w'
                    )
                    lbl_sub.pack(side=tk.LEFT)
                    
                    tamanhos_ordenados = sorted(
                        tamanhos.keys(),
                        key=lambda x: ORDEM_TAMANHOS.get(x, 99)
                    )
                    
                    tags_frame = tk.Frame(sub_frame, bg=cores.BRANCO)
                    tags_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
                    
                    for tam in tamanhos_ordenados:
                        qtd = tamanhos[tam]
                        if qtd > 0:
                            cores_tam = {
                                'PP': cores.AZUL_CEU,
                                'P': cores.AZUL_CEU,
                                'M': cores.AZUL_CEU,
                                'G': cores.AZUL_CEU,
                                'GG': cores.AZUL_CEU,
                                'XG': cores.AZUL_CEU,
                                'XGG': cores.AZUL_CEU,
                                'ÚNICO': cores.AZUL_CEU
                            }
                            cor_badge = cores_tam.get(tam, cores.AZUL_MAR)
                            
                            tag = tk.Frame(
                                tags_frame,
                                bg=cor_badge,
                                relief=tk.FLAT,
                                padx=5,
                                pady=1
                            )
                            tag.pack(side=tk.LEFT, padx=2, pady=1)
                            
                            tk.Label(
                                tag,
                                text=f"{tam}: {qtd}",
                                font=('Arial', 8, 'bold'),
                                fg=cores.BRANCO,
                                bg=cor_badge
                            ).pack()
        
        # Lead time
        lead_times = self.grupo_view.lead_time_por_setor()
        if lead_times:
            lead_frame = tk.Frame(info_col, bg=cores.BRANCO)
            lead_frame.pack(fill=tk.X, pady=(3, 0))
            
            tk.Label(
                lead_frame,
                text="⏱️ Lead Time:",
                font=('Arial', 8, 'bold'),
                fg=cores.CINZA_ESCURO,
                bg=cores.BRANCO
            ).pack(side=tk.LEFT)
            
            for setor, dias in lead_times.items():
                if dias <= 2:
                    cor = cores.VERDE_COQUEIRO
                elif dias <= 4:
                    cor = cores.AREIA
                else:
                    cor = cores.CORAL
                
                lead_badge = tk.Frame(
                    lead_frame,
                    bg=cor,
                    relief=tk.FLAT,
                    padx=4,
                    pady=1
                )
                lead_badge.pack(side=tk.LEFT, padx=3)
                
                lbl = tk.Label(
                    lead_badge,
                    text=f"{setor}: {dias}d",
                    font=('Arial', 7, 'bold'),
                    fg=cores.BRANCO,
                    bg=cor
                )
                lbl.pack()
    
    def _carregar_imagem(self):
        if self._imagem_carregada:
            return
            
        cores = TemaPraia()
        
        image = self.image_manager.buscar_e_carregar_imagem(
            self.grupo_view.group_code, 
            tamanho_maximo=(80, 80)
        )
        
        if image:
            self.img_label.config(image=image, text="")
            self.img_label.image = image
            self.img_frame.configure(bg=cores.BRANCO)
        else:
            for produto in self.grupo_view.produtos[:3]:
                image = self.image_manager.buscar_e_carregar_imagem(
                    produto.product_code,
                    tamanho_maximo=(80, 80)
                )
                if image:
                    self.img_label.config(image=image, text="")
                    self.img_label.image = image
                    self.img_frame.configure(bg=cores.BRANCO)
                    break
            else:
                self.img_label.config(text="🏄", font=('Arial', 28))
                self.img_frame.configure(bg=cores.AZUL_AGUA)
        
        self._imagem_carregada = True


# ============================================================
# SETOR ROW
# ============================================================

class SetorRow(tk.Frame):
    def __init__(self, parent, setor_nome: str, grupos_views, 
                 collection_name: str, prazo_manager, image_manager, 
                 *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.setor_nome = setor_nome
        self.grupos_views = grupos_views
        self.collection_name = collection_name
        self.prazo_manager = prazo_manager
        self.image_manager = image_manager
        self._expandido = False
        self._cards_criados = False
        
        cores = TemaPraia()
        
        self.configure(
            bg=cores.BRANCO,
            relief=tk.RAISED,
            borderwidth=1,
            highlightthickness=2,
            highlightbackground=cores.AZUL_MAR,
            highlightcolor=cores.AZUL_MAR,
            cursor='hand2'
        )
        
        self._criar_widgets()
        self.bind('<Button-1>', self._toggle_expand)
        for child in self.winfo_children():
            child.bind('<Button-1>', self._toggle_expand)
    
    def _criar_widgets(self):
        cores = TemaPraia()
        
        main_frame = tk.Frame(self, bg=cores.BRANCO, height=50)
        main_frame.pack(fill=tk.X, padx=12, pady=8)
        main_frame.pack_propagate(False)
        
        icones_setores = {
            "CORTE": "✂️",
            "PRODUÇÃO": "🧵",
            "ACABAMENTO": "✨",
            "ETIQUETAGEM": "🔖",
            "ESTOQUE": "📦",
            "OUTROS": "📌"
        }
        icone = icones_setores.get(self.setor_nome, "🏄")
        
        lbl_icone = tk.Label(
            main_frame,
            text=icone,
            font=('Arial', 20),
            bg=cores.BRANCO
        )
        lbl_icone.pack(side=tk.LEFT, padx=(0, 10))
        
        lbl_setor = tk.Label(
            main_frame,
            text=self.setor_nome,
            font=('Arial', 14, 'bold'),
            fg=cores.AZUL_MAR_ESCURO,
            bg=cores.BRANCO
        )
        lbl_setor.pack(side=tk.LEFT, padx=(0, 15))
        
        total_grupos = len(self.grupos_views)
        total_pecas = sum(g.total_quantidade for g in self.grupos_views)
        
        stats_badge = tk.Frame(
            main_frame,
            bg=cores.AZUL_AGUA,
            relief=tk.FLAT,
            padx=8,
            pady=2
        )
        stats_badge.pack(side=tk.LEFT, padx=(0, 15))
        
        lbl_stats = tk.Label(
            stats_badge,
            text=f"{total_grupos} grupos • {total_pecas} peças",
            font=('Arial', 9, 'bold'),
            fg=cores.AZUL_MAR_ESCURO,
            bg=cores.AZUL_AGUA
        )
        lbl_stats.pack()
        
        # Prazo
        prazo_info = self.prazo_manager.obter_prazo_setor(self.collection_name, self.setor_nome)
        if prazo_info and prazo_info.get('data_limite'):
            try:
                data = datetime.date.fromisoformat(prazo_info['data_limite'])
                prazo_texto = f"📅 {data.strftime('%d/%m/%Y')}"
                if prazo_info.get('observacao'):
                    prazo_texto += f" ({prazo_info['observacao']})"
                cor_prazo = cores.VERDE_COQUEIRO if data >= datetime.date.today() else cores.CORAL
            except:
                prazo_texto = "📅 Prazo inválido"
                cor_prazo = cores.CORAL
        else:
            prazo_texto = "📅 Prazo não definido"
            cor_prazo = cores.CINZA_MEDIO
        
        lbl_prazo = tk.Label(
            main_frame,
            text=prazo_texto,
            font=('Arial', 9, 'bold'),
            fg=cor_prazo,
            bg=cores.BRANCO
        )
        lbl_prazo.pack(side=tk.LEFT)
        
        # Botão de prazo
        btn_prazo = tk.Button(
            main_frame,
            text="📅",
            font=('Arial', 11),
            bg=cores.AREIA,
            fg=cores.BRANCO,
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor='hand2',
            command=self._abrir_prazo
        )
        btn_prazo.pack(side=tk.RIGHT, padx=5)
        btn_prazo.bind('<Button-1>', lambda e: e.stopPropagation())
        
        # Indicador de expansão
        self.lbl_expand = tk.Label(
            main_frame,
            text="▼" if not self._expandido else "▲",
            font=('Arial', 12, 'bold'),
            fg=cores.AZUL_MAR,
            bg=cores.BRANCO
        )
        self.lbl_expand.pack(side=tk.RIGHT, padx=5)
        
        # Frame para os cards
        self.cards_frame = tk.Frame(self, bg=cores.AZUL_AGUA)
        self.cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.cards_frame.pack_forget()
        
        self._criar_cards()
    
    def _criar_cards(self):
        if self._cards_criados:
            return
        
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        
        if not self.grupos_views:
            lbl_empty = tk.Label(
                self.cards_frame,
                text="🌊 Nenhum grupo neste setor",
                font=('Arial', 10),
                fg=TemaPraia.CINZA_MEDIO,
                bg=TemaPraia.AZUL_AGUA
            )
            lbl_empty.pack(pady=15)
            self._cards_criados = True
            return
        
        cols = 4
        for idx, grupo_view in enumerate(self.grupos_views):
            row = idx // cols
            col = idx % cols
            
            card = CardGrupo(
                self.cards_frame,
                grupo_view,
                self.image_manager
            )
            card.grid(row=row, column=col, padx=6, pady=6, sticky='nsew')
            self.cards_frame.columnconfigure(col, weight=1)
        
        for i in range((len(self.grupos_views) + cols - 1) // cols):
            self.cards_frame.rowconfigure(i, weight=1)
        
        self._cards_criados = True
    
    def _toggle_expand(self, event=None):
        self._expandido = not self._expandido
        
        if self._expandido:
            self.lbl_expand.config(text="▲")
            self.cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        else:
            self.lbl_expand.config(text="▼")
            self.cards_frame.pack_forget()
    
    def _abrir_prazo(self):
        PrazoSetorDialog(self, self.collection_name, self.setor_nome, self.prazo_manager)


class PrazoSetorDialog(tk.Toplevel):
    def __init__(self, parent, collection_name: str, setor_nome: str, prazo_manager):
        super().__init__(parent)
        
        self.collection_name = collection_name
        self.setor_nome = setor_nome
        self.prazo_manager = prazo_manager
        
        cores = TemaPraia()
        
        self.title(f"📅 Prazo - {setor_nome}")
        self.geometry("400x250")
        self.resizable(False, False)
        self.configure(bg=cores.BRANCO_NEVE)
        self.transient(parent)
        self.grab_set()
        
        self._criar_widgets()
        self._carregar_prazo_existente()
    
    def _criar_widgets(self):
        cores = TemaPraia()
        
        main_frame = tk.Frame(self, bg=cores.BRANCO_NEVE)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(
            main_frame,
            text=f"📅 Definir Prazo",
            font=('Arial', 16, 'bold'),
            fg=cores.AZUL_MAR_ESCURO,
            bg=cores.BRANCO_NEVE
        ).pack(anchor='w', pady=(0, 5))
        
        tk.Label(
            main_frame,
            text=f"{self.setor_nome}",
            font=('Arial', 12),
            fg=cores.CINZA_ESCURO,
            bg=cores.BRANCO_NEVE
        ).pack(anchor='w', pady=(0, 15))
        
        data_frame = tk.Frame(main_frame, bg=cores.BRANCO_NEVE)
        data_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            data_frame,
            text="📅 Data Limite:",
            font=('Arial', 10),
            fg=cores.CINZA_ESCURO,
            bg=cores.BRANCO_NEVE
        ).pack(side=tk.LEFT)
        
        self.entry_data = tk.Entry(
            data_frame,
            font=('Arial', 10),
            bg=cores.BRANCO,
            fg=cores.CINZA_ESCURO,
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=2,
            highlightbackground=cores.CARD_BORDER,
            highlightcolor=cores.AZUL_MAR,
            width=15
        )
        self.entry_data.pack(side=tk.LEFT, padx=10)
        self.entry_data.insert(0, "DD/MM/AAAA")
        self.entry_data.bind('<FocusIn>', lambda e: self.entry_data.select_range(0, tk.END))
        
        obs_frame = tk.Frame(main_frame, bg=cores.BRANCO_NEVE)
        obs_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            obs_frame,
            text="📝 Observação:",
            font=('Arial', 10),
            fg=cores.CINZA_ESCURO,
            bg=cores.BRANCO_NEVE
        ).pack(anchor='w')
        
        self.entry_obs = tk.Entry(
            obs_frame,
            font=('Arial', 10),
            bg=cores.BRANCO,
            fg=cores.CINZA_ESCURO,
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=2,
            highlightbackground=cores.CARD_BORDER,
            highlightcolor=cores.AZUL_MAR
        )
        self.entry_obs.pack(fill=tk.X, pady=(5, 0))
        
        btn_frame = tk.Frame(main_frame, bg=cores.BRANCO_NEVE)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        tk.Button(
            btn_frame,
            text="💾 Salvar",
            font=('Arial', 10, 'bold'),
            bg=cores.VERDE_COQUEIRO,
            fg=cores.BRANCO,
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2',
            command=self._salvar
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame,
            text="❌ Cancelar",
            font=('Arial', 10),
            bg=cores.BRANCO_NEVE,
            fg=cores.CINZA_MEDIO,
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.destroy
        ).pack(side=tk.RIGHT)
        
        tk.Button(
            btn_frame,
            text="🗑️ Limpar",
            font=('Arial', 9),
            bg=cores.CORAL,
            fg=cores.BRANCO,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2',
            command=self._limpar
        ).pack(side=tk.RIGHT, padx=5)
    
    def _carregar_prazo_existente(self):
        prazo_info = self.prazo_manager.obter_prazo_setor(self.collection_name, self.setor_nome)
        if prazo_info and prazo_info.get('data_limite'):
            try:
                data = datetime.date.fromisoformat(prazo_info['data_limite'])
                self.entry_data.delete(0, tk.END)
                self.entry_data.insert(0, data.strftime("%d/%m/%Y"))
                if prazo_info.get('observacao'):
                    self.entry_obs.insert(0, prazo_info['observacao'])
            except:
                pass
    
    def _parse_data(self, texto: str) -> Optional[datetime.date]:
        try:
            if texto and texto.strip() and texto != "DD/MM/AAAA":
                return datetime.datetime.strptime(texto.strip(), "%d/%m/%Y").date()
        except ValueError:
            pass
        return None
    
    def _salvar(self):
        try:
            data = self._parse_data(self.entry_data.get())
            observacao = self.entry_obs.get().strip()
            
            self.prazo_manager.definir_prazo_setor(self.collection_name, self.setor_nome, data, observacao)
            messagebox.showinfo("✅ Sucesso", f"Prazo para {self.setor_nome} salvo com sucesso!")
            self.destroy()
        except Exception as e:
            logging.error(f"Erro ao salvar prazo: {e}")
            messagebox.showerror("❌ Erro", f"Erro ao salvar prazo:\n{str(e)}")
    
    def _limpar(self):
        if messagebox.askyesno("Confirmar", f"Deseja remover o prazo para {self.setor_nome}?"):
            self.prazo_manager.definir_prazo_setor(self.collection_name, self.setor_nome, None, "")
            self.entry_data.delete(0, tk.END)
            self.entry_data.insert(0, "DD/MM/AAAA")
            self.entry_obs.delete(0, tk.END)
            messagebox.showinfo("✅ Sucesso", f"Prazo para {self.setor_nome} removido!")


# ============================================================
# COLEÇÃO FRAME
# ============================================================

class ColecaoFrame(tk.Frame):
    def __init__(self, parent, collection_name: str, grupos,
                 prazo_manager, image_manager, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.collection_name = collection_name
        self.grupos = grupos
        self.prazo_manager = prazo_manager
        self.image_manager = image_manager
        
        cores = TemaPraia()
        self.configure(bg=cores.BRANCO_NEVE)
        
        self._criar_widgets()
    
    def _criar_widgets(self):
        cores = TemaPraia()
        
        header_frame = tk.Frame(self, bg=cores.AZUL_MAR, relief=tk.FLAT)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        header_content = tk.Frame(header_frame, bg=cores.AZUL_MAR)
        header_content.pack(fill=tk.X, padx=20, pady=12)
        
        tk.Label(
            header_content,
            text=f"{self.collection_name}",
            font=('Arial', 20, 'bold'),
            fg=cores.BRANCO,
            bg=cores.AZUL_MAR
        ).pack(side=tk.LEFT)
        
        # Data de Lançamento
        data_lancamento = self.prazo_manager.obter_data_lancamento(self.collection_name)
        if data_lancamento:
            lancamento_texto = f"📅 Lançamento: {data_lancamento.strftime('%d/%m/%Y')}"
        else:
            lancamento_texto = "📅 Data de Lançamento não definida"
        
        lbl_lancamento = tk.Label(
            header_content,
            text=lancamento_texto,
            font=('Arial', 11),
            fg=cores.BRANCO,
            bg=cores.AZUL_MAR
        )
        lbl_lancamento.pack(side=tk.LEFT, padx=(15, 0))
        
        # Stats
        total_grupos = len(self.grupos)
        total_produtos = sum(len(g.produtos) for g in self.grupos)
        total_pecas = sum(g.total_quantidade for g in self.grupos)
        
        stats_text = f"{total_grupos} grupos • {total_produtos} produtos • {total_pecas} peças"
        lbl_stats = tk.Label(
            header_content,
            text=stats_text,
            font=('Arial', 10),
            fg=cores.BRANCO,
            bg=cores.AZUL_MAR
        )
        lbl_stats.pack(side=tk.RIGHT, padx=10)
        
        # Separador
        separator = tk.Frame(self, bg=cores.AZUL_MAR, height=1)
        separator.pack(fill=tk.X, pady=(0, 10))
        
        # Scrollable frame
        self.scroll_frame = ScrollableFrame(self)
        self.scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._carregar_setores()
    
    def _carregar_setores(self):
        for widget in self.scroll_frame.inner_frame.winfo_children():
            widget.destroy()
        
        setores_dict = defaultdict(list)
        
        for grupo in self.grupos:
            localizacoes_por_setor = defaultdict(list)
            
            for loc in grupo.localizacoes:
                setor_principal = normalizar_setor(loc.location_name)
                localizacoes_por_setor[setor_principal].append(loc)
            
            if not localizacoes_por_setor:
                from dataclasses import dataclass
                grupo_view = GrupoSetorView(
                    group_code=grupo.group_code,
                    group_name=grupo.group_name,
                    collection_name=grupo.collection_name,
                    setor_atual="ESTOQUE",
                    localizacoes=[],
                    produtos=grupo.produtos,
                    historico=grupo.historico,
                    status_atual=grupo.status_atual
                )
                setores_dict["ESTOQUE"].append(grupo_view)
            else:
                for setor, locs in localizacoes_por_setor.items():
                    grupo_view = GrupoSetorView(
                        group_code=grupo.group_code,
                        group_name=grupo.group_name,
                        collection_name=grupo.collection_name,
                        setor_atual=setor,
                        localizacoes=locs,
                        produtos=grupo.produtos,
                        historico=grupo.historico,
                        status_atual=grupo.status_atual
                    )
                    setores_dict[setor].append(grupo_view)
        
        setores_para_exibir = []
        for setor in SETORES_PRINCIPAIS:
            if setor != "OUTROS":
                setores_para_exibir.append(setor)
        if "OUTROS" in SETORES_PRINCIPAIS:
            setores_para_exibir.append("OUTROS")
        
        for setor in setores_dict.keys():
            if setor not in setores_para_exibir:
                setores_para_exibir.append(setor)
        
        for setor_nome in setores_para_exibir:
            grupos_views = setores_dict.get(setor_nome, [])
            grupos_views.sort(key=lambda g: g.group_code)
            
            row = SetorRow(
                self.scroll_frame.inner_frame,
                setor_nome,
                grupos_views,
                self.collection_name,
                self.prazo_manager,
                self.image_manager
            )
            row.pack(fill=tk.X, pady=3)
        
        if not setores_para_exibir:
            lbl_empty = tk.Label(
                self.scroll_frame.inner_frame,
                text="🌊 Nenhum setor encontrado",
                font=('Arial', 14),
                fg=TemaPraia.CINZA_MEDIO,
                bg=TemaPraia.AZUL_AGUA
            )
            lbl_empty.pack(pady=50)


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class Produto:
    product_code: str
    product_size: str
    group_code: str
    group_name: str
    collection_name: str
    collection_code: str


@dataclass
class LocalizacaoProduto:
    product_code: str
    op: str
    location_name: str
    sub_setor_original: str = ""
    quantity: int = 0
    timestamp: Optional[datetime.datetime] = None
    size_name: str = ""


@dataclass
class GrupoSetorView:
    group_code: str
    group_name: str
    collection_name: str
    setor_atual: str
    localizacoes: List[LocalizacaoProduto] = field(default_factory=list)
    produtos: List[Produto] = field(default_factory=list)
    historico: List[Dict] = field(default_factory=list)
    status_atual: List[Dict] = field(default_factory=list)
    
    @property
    def total_quantidade(self) -> int:
        return sum(loc.quantity for loc in self.localizacoes)
    
    def quantidade_por_sub_setor(self) -> Dict[str, Dict[str, int]]:
        result = defaultdict(lambda: defaultdict(int))
        for loc in self.localizacoes:
            sub_setor = loc.sub_setor_original if loc.sub_setor_original else loc.location_name
            if sub_setor and loc.size_name:
                result[sub_setor][loc.size_name] += loc.quantity
        return dict(result)
    
    def lead_time_por_setor(self) -> Dict[str, int]:
        result = {}
        locs_setor = [loc for loc in self.localizacoes if loc.location_name == self.setor_atual]
        if not locs_setor:
            return result
        
        agora = datetime.datetime.now()
        timestamps = [loc.timestamp for loc in locs_setor if loc.timestamp]
        if timestamps:
            data_mais_antiga = min(timestamps)
            if isinstance(data_mais_antiga, datetime.datetime):
                if data_mais_antiga.tzinfo:
                    agora_local = datetime.datetime.now(data_mais_antiga.tzinfo)
                else:
                    agora_local = agora
                dias = (agora_local - data_mais_antiga).total_seconds() / 86400.0
                result[self.setor_atual] = int(math.ceil(dias))
        return result


@dataclass
class GrupoProduto:
    group_code: str
    group_name: str
    collection_name: str
    produtos: List[Produto] = field(default_factory=list)
    localizacoes: List[LocalizacaoProduto] = field(default_factory=list)
    imagem_path: Optional[str] = None
    imagem_base64: Optional[str] = None
    historico: List[Dict] = field(default_factory=list)
    status_atual: List[Dict] = field(default_factory=list)
    
    @property
    def total_quantidade(self) -> int:
        return sum(loc.quantity for loc in self.localizacoes)
    
    @property
    def setores(self) -> Set[str]:
        return {loc.location_name for loc in self.localizacoes if loc.location_name}
    
    def quantidade_por_setor(self) -> Dict[str, int]:
        result = defaultdict(int)
        for loc in self.localizacoes:
            if loc.location_name:
                result[loc.location_name] += loc.quantity
        return dict(result)
    
    def quantidade_por_sub_setor(self) -> Dict[str, Dict[str, int]]:
        result = defaultdict(lambda: defaultdict(int))
        for loc in self.localizacoes:
            sub_setor = loc.sub_setor_original if loc.sub_setor_original else loc.location_name
            if sub_setor and loc.size_name:
                result[sub_setor][loc.size_name] += loc.quantity
        return dict(result)
    
    def lead_time_por_setor(self) -> Dict[str, int]:
        result = {}
        locs_por_setor = defaultdict(list)
        for loc in self.localizacoes:
            if loc.location_name and loc.timestamp:
                locs_por_setor[loc.location_name].append(loc)
        
        agora = datetime.datetime.now()
        for setor, locs in locs_por_setor.items():
            timestamps = [loc.timestamp for loc in locs if loc.timestamp]
            if timestamps:
                data_mais_antiga = min(timestamps)
                if isinstance(data_mais_antiga, datetime.datetime):
                    if data_mais_antiga.tzinfo:
                        agora_local = datetime.datetime.now(data_mais_antiga.tzinfo)
                    else:
                        agora_local = agora
                    dias = (agora_local - data_mais_antiga).total_seconds() / 86400.0
                    result[setor] = int(math.ceil(dias))
        return result


# ============================================================
# MÓDULO PRINCIPAL
# ============================================================

class ModuloCronograma:
    """Módulo de Cronograma e Drops - COMPLETO E FUNCIONAL"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.cores = TemaPraia()
        
        # Banco de dados
        self.db = DatabaseManager()
        
        # DAOs
        self.colecoes_dao = ColecoesDAO(self.db)
        self.produtos_dao = ProdutosDAO(self.db)
        self.ordens_dao = OrdensProducaoDAO(self.db)
        
        # Gerenciadores
        self.prazo_manager = PrazoManager()
        self.image_manager = ImageManager()
        self.gerenciador_drops = GerenciadorDropsTemporarios()
        
        # Dados
        self.colecao_atual = None
        self.grupos_atuais: List[GrupoProduto] = []
        self._carregando = False
        
        # Interface
        self._criar_interface()
        
        # Carregar coleções do banco
        self._carregar_colecoes()
    
    def _criar_interface(self):
        """Cria a interface do módulo de cronograma"""
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Barra de ferramentas
        toolbar = tk.Frame(main_frame, bg=self.cores.AZUL_MAR_ESCURO, height=50)
        toolbar.pack(fill='x', pady=(0, 10))
        toolbar.pack_propagate(False)      
                
        # Seletor de drop
        select_frame = tk.Frame(toolbar, bg=self.cores.AZUL_MAR_ESCURO)
        select_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(
            select_frame,
            text="Drop:",
            font=('Arial', 11, 'bold'),
            fg=self.cores.BRANCO,
            bg=self.cores.AZUL_MAR_ESCURO
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        self.combo_colecoes = ttk.Combobox(
            select_frame,
            font=('Arial', 10),
            width=35,
            state='readonly'
        )
        self.combo_colecoes.pack(side=tk.LEFT)
        self.combo_colecoes.bind('<<ComboboxSelected>>', self._on_colecao_selecionada)
        
        # Botão carregar
        btn_carregar = tk.Button(
            toolbar,
            text="🚀 Carregar",
            font=('Arial', 10, 'bold'),
            bg=self.cores.VERDE_COQUEIRO,
            fg=self.cores.BRANCO,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor='hand2',
            command=self._carregar_colecao_selecionada
        )
        btn_carregar.pack(side=tk.LEFT, padx=10)
        
        # Botão atualizar
        btn_atualizar = tk.Button(
            toolbar,
            text="🔄 Atualizar",
            font=('Arial', 10),
            bg=self.cores.AZUL_CEU,
            fg=self.cores.BRANCO,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor='hand2',
            command=self._carregar_colecoes
        )
        btn_atualizar.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = tk.Label(
            toolbar,
            text="🌊 Aguardando seleção...",
            font=('Arial', 10, 'italic'),
            fg=self.cores.BRANCO,
            bg=self.cores.AZUL_MAR_ESCURO
        )
        self.status_label.pack(side=tk.RIGHT, padx=15)
        
        # Notebook para abas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=10)
        
        # Aba inicial
        self.aba_inicial = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_inicial, text='🏠 Início')
        self._criar_aba_inicial()
    
    def _criar_aba_inicial(self):
        """Cria a aba inicial com instruções"""
        cores = TemaPraia()
        
        frame = tk.Frame(self.aba_inicial, bg=cores.AZUL_AGUA)
        frame.pack(fill='both', expand=True)
        
        center = tk.Frame(frame, bg=cores.AZUL_AGUA)
        center.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(
            center,
            text="📅 Cronograma de Produção",
            font=('Arial', 28, 'bold'),
            fg=cores.AZUL_MAR_ESCURO,
            bg=cores.AZUL_AGUA
        ).pack(pady=10)
        
        tk.Label(
            center,
            text="Selecione um drop na lista acima para visualizar o cronograma.",
            font=('Arial', 14),
            fg=cores.CINZA_ESCURO,
            bg=cores.AZUL_AGUA
        ).pack(pady=5)
        
        # Ícones decorativos
        icons_frame = tk.Frame(center, bg=cores.AZUL_AGUA)
        icons_frame.pack(pady=20)
        
        for icon in ["👙", "🏄", "🌞", "🌴", "🐚", "🩱", "🍹"]:
            tk.Label(
                icons_frame,
                text=icon,
                font=('Arial', 24),
                bg=cores.AZUL_AGUA
            ).pack(side=tk.LEFT, padx=10)
    
    def _carregar_colecoes(self):
        """Carrega as coleções do banco de dados"""
        try:
            self.status_label.config(text="🔄 Carregando drops...")
            self.parent.update()
            
            colecoes = self.colecoes_dao.listar_todas()
            
            if colecoes:
                nomes = [c['collection_name'] for c in colecoes if c.get('collection_name')]
                self.combo_colecoes['values'] = nomes
                if nomes:
                    self.combo_colecoes.set(nomes[0])
                self.status_label.config(text=f"✅ {len(nomes)} drops carregados")
                logging.info(f"Drops carregados: {nomes}")
            else:
                self.combo_colecoes['values'] = []
                self.status_label.config(text="⚠️ Nenhum drop encontrado")
                messagebox.showwarning("Aviso", "Nenhum drop encontrado no banco de dados.")
                
        except Exception as e:
            logging.error(f"Erro ao carregar drops: {e}")
            self.status_label.config(text=f"❌ Erro: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao carregar drops:\n{str(e)}")
    
    def _on_colecao_selecionada(self, event):
        """Evento de seleção de coleção"""
        self._carregar_colecao_selecionada()
    
    def _carregar_colecao_selecionada(self):
        """Carrega a coleção selecionada e exibe o cronograma"""
        if self._carregando:
            return
        
        collection_name = self.combo_colecoes.get().strip()
        
        if not collection_name:
            messagebox.showwarning("Aviso", "Selecione um drop primeiro.")
            return
        
        if collection_name not in self.combo_colecoes['values']:
            messagebox.showwarning("Aviso", f"Drop '{collection_name}' não encontrado na lista.")
            return
        
        self.colecao_atual = collection_name
        self._carregando = True
        self.status_label.config(text=f"⏳ Carregando {collection_name}...")
        self.parent.update()
        
        try:
            # Buscar produtos da coleção
            produtos_raw = self.produtos_dao.listar_por_colecao(collection_name)
            logging.info(f"Produtos encontrados: {len(produtos_raw)}")
            
            if not produtos_raw:
                messagebox.showwarning("Aviso", f"Nenhum produto encontrado para o drop '{collection_name}'.")
                self.status_label.config(text=f"⚠️ Nenhum produto para {collection_name}")
                self._carregando = False
                return
            
            # Agrupar produtos por grupo
            grupos_dict = defaultdict(list)
            for p in produtos_raw:
                group_code = p.get('group_code', '')
                if group_code:
                    grupos_dict[group_code].append(p)
            
            logging.info(f"Grupos encontrados: {len(grupos_dict)}")
            
            # Buscar localizações
            all_product_codes = [p['product_code'] for p in produtos_raw if p.get('product_code')]
            locations_raw = self.ordens_dao.buscar_locations_por_produtos(all_product_codes)
            logging.info(f"Locations encontradas: {len(locations_raw)}")
            
            # Organizar localizações por produto
            locations_por_produto = defaultdict(list)
            for loc in locations_raw:
                product_code = loc.get('product_code', '')
                if product_code:
                    locations_por_produto[product_code].append(loc)
            
            # Criar objetos GrupoProduto
            grupos = []
            for group_code, produtos_data in grupos_dict.items():
                produtos = []
                for p in produtos_data:
                    produto = Produto(
                        product_code=p.get('product_code', ''),
                        product_size=p.get('product_size', ''),
                        group_code=p.get('group_code', ''),
                        group_name=p.get('group_name', ''),
                        collection_name=p.get('collection_name', ''),
                        collection_code=p.get('collection_code', '')
                    )
                    produtos.append(produto)
                
                locations_grupo = []
                for produto in produtos:
                    locs = locations_por_produto.get(produto.product_code, [])
                    for loc in locs:
                        timestamp = loc.get('timestamp')
                        if timestamp and isinstance(timestamp, str):
                            try:
                                timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            except:
                                timestamp = None
                        
                        location = LocalizacaoProduto(
                            product_code=loc.get('product_code', ''),
                            op=loc.get('op', ''),
                            location_name=loc.get('location_name', ''),
                            sub_setor_original=loc.get('sub_setor_original', ''),
                            quantity=loc.get('quantity', 0),
                            timestamp=timestamp,
                            size_name=loc.get('size_name', '')
                        )
                        locations_grupo.append(location)
                
                grupo = GrupoProduto(
                    group_code=group_code,
                    group_name=produtos_data[0].get('group_name', ''),
                    collection_name=collection_name,
                    produtos=produtos,
                    localizacoes=locations_grupo
                )
                grupos.append(grupo)
            
            grupos.sort(key=lambda g: g.group_code)
            self.grupos_atuais = grupos
            
            # Atualizar interface
            self._atualizar_interface_colecao(grupos)
            self.status_label.config(text=f"✅ {len(grupos)} grupos para {collection_name}")
            
        except Exception as e:
            logging.error(f"Erro ao carregar dados do drop: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.config(text=f"❌ Erro: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao carregar dados do drop:\n{str(e)}")
        finally:
            self._carregando = False
    
    def _atualizar_interface_colecao(self, grupos: List[GrupoProduto]):
        """Atualiza a interface com os dados da coleção"""
        try:
            self._remover_aba_colecao_atual()
            
            colecao_frame = ColecaoFrame(
                self.notebook,
                self.colecao_atual,
                grupos,
                self.prazo_manager,
                self.image_manager
            )
            self.notebook.add(colecao_frame, text=f"{self.colecao_atual}")
            self.notebook.select(colecao_frame)
            
            logging.info(f"Aba atualizada para drop: {self.colecao_atual}")
            
        except Exception as e:
            logging.error(f"Erro ao atualizar interface: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao atualizar interface:\n{str(e)}")
    
    def _remover_aba_colecao_atual(self):
        """Remove a aba da coleção atual"""
        if not self.colecao_atual:
            return
        
        for tab_id in reversed(self.notebook.tabs()):
            tab_text = self.notebook.tab(tab_id, 'text') or ''
            if tab_text == self.colecao_atual or tab_text.endswith(f" {self.colecao_atual}"):
                self.notebook.forget(tab_id)