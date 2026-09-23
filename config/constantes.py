"""
Constantes globais do sistema
"""

APP_NAME = "Borana ERP - Gestão de Produção"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Borana Moda Praia"

# Configuração do banco de dados principal (Railway)
DB_CONFIG = {
    'host': 'caboose.proxy.rlwy.net',
    'port': 45649,
    'database': 'railway',
    'user': 'postgres',
    'password': 'UWKjEVQAzWDEOcGTOGvqrYChNuyFgrpY'
}

# Configuração do banco de dados do TOTVS
DB_TOTVS_CONFIG = {
    'host': 'totvsdb.c14i0o2cq8ri.us-east-2.rds.amazonaws.com',
    'port': 5432,
    'database': 'borana',
    'user': 'pedro',
    'password': 'Vw2@QWUdx4',
    'schema': 'public'
}

# Caminhos
LOCAL_IMAGE_PATH = r"\\192.168.1.240\Auxiliar\COMPARTILHAR\13 - Modelagem\03 - FOTOS COLEÇÕES"

# Setores principais
SETORES_PRINCIPAIS = [
    "CORTE",
    "PRODUÇÃO", 
    "ACABAMENTO",
    "ETIQUETAGEM",
    "ESTOQUE",
    "OUTROS" 
]

# Subsetores da criação em ordem de fluxo
SUBSETORES_CRIACAO_ORDEM = [
    "APROVAÇÃO",
    "MODELAGEM", 
    "PILOTAGEM",
    "FICHA TÉCNICA",
    "GRADAÇÃO",
    "ENCAIXE",
    "RISCO",
    "CORTE PILOTO"
]