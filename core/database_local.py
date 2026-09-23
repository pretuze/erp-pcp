"""
Gerenciador do banco de dados local SQLite
"""

import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

class DatabaseLocal:
    """Gerenciador do banco de dados local SQLite"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            
            # IMPORTANTE: usar get_config_dir() para salvar
            # o arquivo SEMPRE ao lado do .exe
            from core.utils import get_config_dir
            self.db_path = get_config_dir() / "borana_local.db"
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"📂 Banco local: {self.db_path}")
            
            self._criar_tabelas()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        try:
            yield conn
        finally:
            conn.close()
    
    def _criar_tabelas(self):
        """Cria as tabelas necessárias no SQLite"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Tabela de drops temporários
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS drops_temporarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE NOT NULL,
                        dados JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de prazos
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS prazos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chave TEXT NOT NULL,
                        setor TEXT NOT NULL,
                        data_limite TEXT,
                        observacao TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(chave, setor)
                    )
                ''')
                
                # Tabela de meses cadastrados
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS meses_cadastrados (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chave TEXT UNIQUE NOT NULL,
                        nome TEXT NOT NULL,
                        ano INTEGER NOT NULL,
                        inicio TEXT NOT NULL,
                        fim TEXT NOT NULL,
                        feriados JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de colaboradores
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS colaboradores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de metas
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS metas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        grupo TEXT UNIQUE NOT NULL,
                        num_funcionarios INTEGER DEFAULT 1,
                        meta_diaria_por_funcionario INTEGER DEFAULT 15,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Inserir metas padrão se não existirem
                cursor.execute("SELECT COUNT(*) FROM metas")
                if cursor.fetchone()[0] == 0:
                    metas_padrao = [
                        ('biquini', 5, 15),
                        ('roupa', 4, 15),
                        ('acabamento', 3, 50)
                    ]
                    for grupo, num_func, meta_diaria in metas_padrao:
                        cursor.execute('''
                            INSERT INTO metas (grupo, num_funcionarios, meta_diaria_por_funcionario)
                            VALUES (?, ?, ?)
                        ''', (grupo, num_func, meta_diaria))
                
                # Inserir colaboradores padrão se não existirem
                cursor.execute("SELECT COUNT(*) FROM colaboradores")
                if cursor.fetchone()[0] == 0:
                    colaboradores_padrao = ['Ana', 'Maria', 'José', 'Carlos', 'Fernanda']
                    for nome in colaboradores_padrao:
                        cursor.execute('INSERT INTO colaboradores (nome) VALUES (?)', (nome,))
                
                conn.commit()
                logging.info("Banco de dados local inicializado com sucesso")
                
        except Exception as e:
            logging.error(f"Erro ao criar tabelas no SQLite: {e}")
            raise
    
    def salvar_drop(self, nome: str, dados: Dict) -> bool:
        """Salva um drop temporário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO drops_temporarios (nome, dados, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (nome, json.dumps(dados))
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Erro ao salvar drop: {e}")
            return False
    
    def carregar_drops(self) -> Dict[str, Dict]:
        """Carrega todos os drops temporários"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nome, dados FROM drops_temporarios ORDER BY nome")
                rows = cursor.fetchall()
                return {row['nome']: json.loads(row['dados']) for row in rows}
        except Exception as e:
            logging.error(f"Erro ao carregar drops: {e}")
            return {}
    
    def remover_drop(self, nome: str) -> bool:
        """Remove um drop temporário"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM drops_temporarios WHERE nome = ?", (nome,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Erro ao remover drop: {e}")
            return False
    
    def salvar_prazo(self, chave: str, setor: str, data_limite: str, observacao: str = "") -> bool:
        """Salva um prazo para um setor"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO prazos (chave, setor, data_limite, observacao, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (chave, setor, data_limite, observacao)
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Erro ao salvar prazo: {e}")
            return False
    
    def carregar_prazos(self, chave: str) -> Dict:
        """Carrega os prazos de uma chave"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT setor, data_limite, observacao FROM prazos WHERE chave = ?", (chave,))
                rows = cursor.fetchall()
                return {row['setor']: {'data_limite': row['data_limite'], 'observacao': row['observacao']} for row in rows}
        except Exception as e:
            logging.error(f"Erro ao carregar prazos: {e}")
            return {}
    
    def salvar_mes(self, chave: str, nome: str, ano: int, inicio: str, fim: str, feriados: List) -> bool:
        """Salva um mês cadastrado"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO meses_cadastrados (chave, nome, ano, inicio, fim, feriados) VALUES (?, ?, ?, ?, ?, ?)",
                    (chave, nome, ano, inicio, fim, json.dumps(feriados))
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Erro ao salvar mês: {e}")
            return False
    
    def carregar_meses(self) -> Dict:
        """Carrega todos os meses cadastrados"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chave, nome, ano, inicio, fim, feriados FROM meses_cadastrados")
                rows = cursor.fetchall()
                return {
                    row['chave']: {
                        'nome': row['nome'],
                        'ano': row['ano'],
                        'inicio': row['inicio'],
                        'fim': row['fim'],
                        'feriados': json.loads(row['feriados']) if row['feriados'] else []
                    }
                    for row in rows
                }
        except Exception as e:
            logging.error(f"Erro ao carregar meses: {e}")
            return {}
    
    def salvar_colaborador(self, nome: str) -> bool:
        """Salva um colaborador"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO colaboradores (nome) VALUES (?)", (nome,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Erro ao salvar colaborador: {e}")
            return False
    
    def remover_colaborador(self, nome: str) -> bool:
        """Remove um colaborador"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM colaboradores WHERE nome = ?", (nome,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Erro ao remover colaborador: {e}")
            return False
    
    def carregar_colaboradores(self) -> List[str]:
        """Carrega todos os colaboradores"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nome FROM colaboradores ORDER BY nome")
                return [row['nome'] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Erro ao carregar colaboradores: {e}")
            return []
    
    def salvar_meta(self, grupo: str, num_funcionarios: int, meta_diaria: int) -> bool:
        """Salva uma meta de produção"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO metas (grupo, num_funcionarios, meta_diaria_por_funcionario, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                    (grupo, num_funcionarios, meta_diaria)
                )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Erro ao salvar meta: {e}")
            return False
    
    def carregar_metas(self) -> Dict:
        """Carrega todas as metas"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT grupo, num_funcionarios, meta_diaria_por_funcionario FROM metas")
                rows = cursor.fetchall()
                return {
                    row['grupo']: {
                        'num_funcionarios': row['num_funcionarios'],
                        'meta_diaria_por_funcionario': row['meta_diaria_por_funcionario']
                    }
                    for row in rows
                }
        except Exception as e:
            logging.error(f"Erro ao carregar metas: {e}")
            return {}