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

# Catálogo digital (site) = pasta site/ deste repositório, com HTML/CSS/JS
# escritos à mão e versionados. python gerar.py site NÃO copia HTML pra cá —
# só escreve produtos.json/meta.json/fotos/fichas direto dentro dela (arquivos
# gerados, no .gitignore; o GitHub Actions os recria a cada publicação).
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

# Dois trilhos de saída (nunca misturar):
#   digital  -> fichas e catálogos leves (foto 1200 px). É o que o site/Actions/servidor usam.
#   impresso -> catálogo para a gráfica (foto ORIGINAL). Só local, nunca publicado.
SAIDA_DIGITAL  = SAIDA / "digital"
SAIDA_IMPRESSO = SAIDA / "impresso"

# Capas (PDF A4 do InDesign). Só o catálogo completo digital tem capa por enquanto; os catálogos
# por especialidade saem só com o miolo + índice até existirem as capas (assets/capas/<Especialidade>.pdf).
CAPAS = ASSETS / "capas"
CAPA_COMPLETO = CAPAS / "Catalogo_Completo.pdf"

SAIDA.mkdir(exist_ok=True)
SAIDA_DIGITAL.mkdir(exist_ok=True)
SAIDA_IMPRESSO.mkdir(exist_ok=True)
