# -*- coding: utf-8 -*-
"""Identidade visual MDTech: cores, cores por especialidade e carregador de fontes.
Trocar a paleta ou as fontes AQUI reflete em fichas, catálogo e cards."""
from PIL import ImageFont
from . import config

# ----- paleta base -----
NAVY  = (25, 60, 108)     # #193C6C
CYAN  = (54, 169, 225)    # #36A9E1
INK   = (35, 45, 60)
GRAY  = (96, 108, 126)
MUT   = (120, 135, 155)
PANEL = (244, 247, 251)
LINE  = (223, 230, 239)
CHIP  = (233, 244, 251)
NAVY2 = (31, 72, 124)
SUB   = (150, 175, 205)
WHITE = (255, 255, 255)

TAGLINE = "TECNOLOGIA QUE ABRE CAMINHOS"

# ----- accent por especialidade (ÚNICA fonte de verdade — catálogo PDF e
# site/js/config.js espelham estes valores; mudou aqui, muda os dois: no
# catálogo é automático (via accent()), no site precisa copiar o hex manual
# em site/js/config.js -> accent{} porque JS não importa Python) -----
ACCENT = {
    "Laparoscopia": (245, 166, 35),    # #F5A623  laranja
    "Urologia":     (54, 169, 225),    # #36A9E1  azul
    "Ginecologia":  (198, 75, 140),    # #C64B8C  rosa
    "Histeroscopia":(198, 75, 140),    # #C64B8C  rosa
}
def accent(especialidade: str):
    return ACCENT.get((especialidade or "").strip(), CYAN)

def accent_hex(especialidade: str) -> str:
    r, g, b = accent(especialidade)
    return f"#{r:02X}{g:02X}{b:02X}"

# Variante ESCURA da cor da especialidade, só para TEXTO (código do produto etc.): passa no contraste AA.
# A cor original continua em faixas, bordas e tarjas. Espelho manual em site/js/config.js -> accentTexto.
ACCENT_TEXTO = {
    "Laparoscopia": "#996207", "Urologia": "#1874A1",
    "Ginecologia": "#A83A74", "Histeroscopia": "#A83A74",
}
def accent_texto_hex(especialidade: str) -> str:
    return ACCENT_TEXTO.get((especialidade or "").strip(), "#1874A1")

# ----- fontes -----
_ARQ = {
    "bold":  "Poppins-Bold.ttf",
    "med":   "Poppins-Medium.ttf",
    "reg":   "Poppins-Regular.ttf",
    "mono":  "IBMPlexMono-Bold.ttf",
    "monor": "IBMPlexMono-Regular.ttf",
}
_cache = {}
def fonte(estilo: str, tamanho: int):
    """fonte('bold', 50) -> ImageFont. Cai para a fonte padrão se o arquivo faltar."""
    chave = (estilo, tamanho)
    if chave in _cache:
        return _cache[chave]
    arq = _ARQ[estilo]
    caminho = config.FONTES / arq
    try:
        f = ImageFont.truetype(str(caminho), tamanho)
    except Exception:
        try:
            f = ImageFont.truetype(arq, tamanho)      # tenta pelo nome do sistema
        except Exception:
            print(f"[aviso] fonte ausente: {arq} — usando fonte padrão")
            f = ImageFont.load_default()
    _cache[chave] = f
    return f

# atalhos
bold  = lambda s: fonte("bold",  s)
med   = lambda s: fonte("med",   s)
reg   = lambda s: fonte("reg",   s)
mono  = lambda s: fonte("mono",  s)
monor = lambda s: fonte("monor", s)
