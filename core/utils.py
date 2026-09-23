"""
Funções utilitárias do sistema
Centraliza a resolução de caminhos para funcionar tanto em dev quanto no .exe
"""

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """
    Retorna o diretório base da aplicação.
    
    - Em desenvolvimento: pasta do script principal
    - No .exe (PyInstaller): pasta onde o .exe está localizado
    
    Isso garante que arquivos de dados/JSON fiquem SEMPRE ao lado do .exe,
    e não na pasta temporária _MEIPASS (que é apagada ao fechar).
    """
    if getattr(sys, 'frozen', False):
        # Executando como .exe → pasta onde está o .exe
        return Path(sys.executable).parent
    else:
        # Executando como .py → pasta do projeto
        return Path(__file__).resolve().parent.parent


def get_config_dir() -> Path:
    """Diretório de config (ao lado do .exe ou do projeto)"""
    config_dir = get_app_dir() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Diretório de dados (ao lado do .exe ou do projeto)"""
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_resources_dir() -> Path:
    """
    Diretório de recursos empacotados (ícone, imagens internas).
    
    Diferente de get_app_dir, este retorna a pasta _MEIPASS no .exe
    (onde o PyInstaller extrai os arquivos do bundle).
    Use SOMENTE para ler recursos que vêm DENTRO do .exe.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def encontrar_icone():
    """Encontra o ícone em múltiplos locais possíveis"""
    locais = []
    
    # 1. Ao lado do .exe / projeto (arquivo externo — recomendado)
    app_dir = get_app_dir()
    locais.append(app_dir / "icone.ico")
    locais.append(app_dir / "icone.png")
    locais.append(app_dir / "recursos" / "icone.ico")
    locais.append(app_dir / "recursos" / "icone.png")
    
    # 2. Dentro do bundle PyInstaller (arquivo empacotado)
    res_dir = get_resources_dir()
    locais.append(res_dir / "icone.ico")
    locais.append(res_dir / "icone.png")
    locais.append(res_dir / "recursos" / "icone.ico")
    locais.append(res_dir / "recursos" / "icone.png")
    
    for loc in locais:
        if loc.exists():
            return str(loc)
    
    return None


def configurar_icone_app(root):
    """Configura o ícone da aplicação"""
    try:
        from PIL import Image, ImageTk
        
        caminho_icone = encontrar_icone()
        if caminho_icone:
            img = Image.open(caminho_icone)
            img_small = img.copy()
            img_small.thumbnail((64, 64), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img_small)
            root.iconphoto(True, photo)
            root._icon_photo = photo
            return True
    except Exception as e:
        print(f"⚠️ Erro ao configurar ícone: {e}")
    return False