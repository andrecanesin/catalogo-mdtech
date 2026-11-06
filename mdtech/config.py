# -*- coding: utf-8 -*-
"""Caminhos e constantes globais do projeto. Editar aqui muda para todos os geradores."""
from pathlib import Path

RAIZ    = Path(__file__).resolve().parent.parent      # .../materiais-mdtech
DADOS   = RAIZ / "dados"
ASSETS  = RAIZ / "assets"
IMAGENS = ASSETS / "imagens"
LOGOS   = ASSETS / "logos"
FONTES  = ASSETS / "fontes"
SAIDA   = RAIZ / "saida"

# Catálogo digital (site) = repositório git próprio, com HTML/CSS/JS
# escritos à mão e versionados. python gerar.py site NÃO copia nada pra cá —
# só escreve produtos.json/meta.json/fotos/ direto dentro dele, no lugar já
# rastreado pelo git.
SITE = RAIZ / "site"

# Base = fonte única da verdade
BASE_XLSX = DADOS / "Base_MDTech_Consolidada.xlsx"
BASE_ABA  = "BASE DE PRODUTOS"   # nome da aba de produtos (ajuste se necessário)

# Logos oficiais
LOGO_BRANCO   = LOGOS / "logo-mdtech-hor-branco.png"   # p/ fundo navy
LOGO_COLORIDO = LOGOS / "logo-topo-reduzido.png"       # p/ fundo claro

# Extensões de imagem aceitas para as fotos por código
EXTS_IMG = (".png", ".jpg", ".jpeg", ".webp")

# Ícones do selo de ângulo (catálogo PDF, ficha técnica PDF e site digital).
# Arquivo nomeado pelo número de graus, ex.: assets/icones/angulos/30.png
# p/ um item com Ângulo = "30°". Ângulo sem ícone correspondente = sem selo
# (não quebra nada, só não desenha o selo naquele item).
ICONES_ANGULO = ASSETS / "icones" / "angulos"

# Link de contato clicável no catálogo DIGITAL (deixe "" para não exibir)
# ex.: "https://wa.me/55SEUNUMERO"  ou  "mailto:marcelo@mdtechsm.com.br"
CONTATO_URL   = ""
CONTATO_LABEL = "Fale com a MDTech"

SAIDA.mkdir(exist_ok=True)
