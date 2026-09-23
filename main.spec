# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# ============================================================
# IMPORTS OCULTOS (hidden imports)
# ============================================================
# Coleta automaticamente todos os submódulos dos pacotes internos
hiddenimports = []
hiddenimports += collect_submodules('modulos')
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('widgets')
hiddenimports += collect_submodules('config')

# Bibliotecas externas que costumam ter imports dinâmicos
hiddenimports += [
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL._tkinter_finder',
    'matplotlib',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.backends._backend_tk',
    'tkcalendar',
    'psycopg2',
    'psycopg2.extras',
    'psycopg2._psycopg',
    'pandas',
    'pandas._libs.tslibs.base',
    'openpyxl',
    'openpyxl.cell._writer',
    'numpy',
    'fpdf',
    'babel.numbers',  # usado pelo tkcalendar
]

# ============================================================
# DADOS (datas)
# ============================================================
# Inclui arquivos/pastas que precisam existir junto ao .exe
datas = [
    ('config', 'config'),         # JSONs e SQLite local
    ('recursos', 'recursos'),     # Ícones e imagens
]

# Coleta dados internos de bibliotecas que precisam de arquivos próprios
datas += collect_data_files('tkcalendar')
datas += collect_data_files('babel')
datas += collect_data_files('matplotlib')

# ============================================================
# ANÁLISE
# ============================================================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Reduz tamanho removendo módulos não usados
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# ============================================================
# EXECUTÁVEL
# ============================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Borana_ERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # não abrir janela preta (GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='recursos/icone.ico',  # ajuste o caminho se necessário
)