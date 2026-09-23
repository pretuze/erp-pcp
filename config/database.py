"""
Configurações de banco de dados
"""

from config.constantes import DB_CONFIG, DB_TOTVS_CONFIG

class DatabaseConfig:
    """Configurações centralizadas de banco de dados"""
    
    PRINCIPAL = DB_CONFIG
    TOTVS = DB_TOTVS_CONFIG
    
    @classmethod
    def get_principal(cls):
        return cls.PRINCIPAL.copy()
    
    @classmethod
    def get_totvs(cls):
        return cls.TOTVS.copy()