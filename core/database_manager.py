"""
Gerenciador de conexões com PostgreSQL
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import List, Dict, Optional, Tuple

from config.database import DatabaseConfig

class DatabaseManager:
    """Gerenciador unificado de conexões com PostgreSQL"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._connections = {}
    
    def get_connection(self, db_type='principal'):
        """Obtém conexão com o banco de dados"""
        config = DatabaseConfig.get_principal() if db_type == 'principal' else DatabaseConfig.get_totvs()
        key = db_type
        
        if key not in self._connections or self._connections[key].closed:
            try:
                conn = psycopg2.connect(
                    host=config['host'],
                    port=config['port'],
                    database=config['database'],
                    user=config['user'],
                    password=config['password'],
                    connect_timeout=15
                )
                conn.autocommit = False
                self._connections[key] = conn
                logging.info(f"Conexão com PostgreSQL estabelecida ({db_type})")
            except Exception as e:
                logging.error(f"Erro ao conectar ao PostgreSQL: {e}")
                raise ConnectionError(f"Erro ao conectar ao banco: {e}")
        return self._connections[key]
    
    def close_all(self):
        """Fecha todas as conexões"""
        for conn in self._connections.values():
            if conn and not conn.closed:
                conn.close()
        self._connections.clear()
    
    def execute_query(self, query: str, params: tuple = None, db_type='principal') -> List[Dict]:
        """Executa uma query e retorna resultados"""
        conn = self.get_connection(db_type)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or ())
                results = cur.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logging.error(f"Erro ao executar query: {e}")
            raise
    
    def execute_update(self, query: str, params: tuple = None, db_type='principal') -> int:
        """Executa um update e retorna número de linhas afetadas"""
        conn = self.get_connection(db_type)
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                conn.commit()
                return cur.rowcount
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao executar update: {e}")
            raise