"""
Paleta de cores unificada para todo o sistema
"""

class TemaPraia:
    """Paleta de cores inspirada em moda praia"""
    
    # Cores principais
    AZUL_MAR = "#006994"
    AZUL_MAR_ESCURO = "#004D73"
    AZUL_MAR_MUITO_ESCURO = "#003552"
    AZUL_CEU = "#4FC3F7"
    AZUL_AGUA = "#7DD3FC"
    AZUL_CLARO = "#B3E5FC"
    
    # Cores de destaque
    VERDE_COQUEIRO = "#22C55E"
    VERDE_MAR = "#059669"
    VERDE_CLARO = "#86EFAC"
    
    AREIA = "#F5DEB3"
    AREIA_CLARA = "#FDE68A"
    AREIA_ESCURA = "#D97706"
    
    CORAL = "#FF7F50"
    FLAMINGO = "#FB7185"
    ROSA_CLARO = "#FBCFE8"
    
    # Neutros
    BRANCO = "#FFFFFF"
    BRANCO_NEVE = "#F8FAFC"
    BRANCO_GELO = "#F1F5F9"
    
    CINZA_CLARO = "#E2E8F0"
    CINZA_MEDIO = "#94A3B8"
    CINZA_ESCURO = "#475569"
    
    # Status
    STATUS_OK = "#22C55E"
    STATUS_ATENCAO = "#FBBF24"
    STATUS_ATRASADO = "#EF4444"
    STATUS_PRAZO = "#006994"
    
    @classmethod
    def get_style_dict(cls):
        return {
            'bg_principal': cls.BRANCO_NEVE,
            'bg_card': cls.BRANCO,
            'bg_header': cls.AZUL_MAR,
            'fg_header': cls.BRANCO,
            'fg_principal': cls.AZUL_MAR_ESCURO,
            'fg_secundario': cls.CINZA_ESCURO,
            'destaque': cls.CORAL,
            'sucesso': cls.VERDE_COQUEIRO,
            'atencao': cls.AREIA,
            'erro': cls.STATUS_ATRASADO,
            'borda': cls.AZUL_MAR,
        }