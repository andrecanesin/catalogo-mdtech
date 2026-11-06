# -*- coding: utf-8 -*-
"""Tratamento de textos vindos da base (que estão em CAIXA ALTA com specs no fim)."""
import re, base64
from . import config

# palavras que ficam minúsculas no title case (exceto se forem a 1ª palavra)
_STOP = {"de", "da", "do", "das", "dos", "e", "com", "para", "em",
         "a", "o", "ao", "à", "no", "na", "tipo", "por", "um", "uma", "uns", "umas"}

# marcadores onde o NOME termina e começam specs (Ø, D=, C=, mm, autoclavável, ano de registro).
# MDTECH é removido à parte (pode aparecer no meio da frase, ex. "CAMISA MDTECH PARA X" — não é
# fim de nome, é a marca inserida ali; cortar nela perderia "PARA X").
_CORTE = re.compile(r"\s+(D\s*=|Ø|C\s*=|\d+[.,]?\d*\s*MM|AUTOCLAV|\(1\d{2})", re.IGNORECASE)
_MDTECH = re.compile(r"\bMDTECH\b", re.IGNORECASE)


def nome_produto(descricao: str) -> str:
    """'PINÇA DE APREENSÃO GOLFINHO MDTECH D=5MM C=330MM ...' -> 'Pinça de Apreensão Golfinho'.
       'CAMISA MDTECH PARA CISTOURETROSCOPIA D=16,5FR ...' -> 'Camisa para Cistouretroscopia'
       (MDTECH pode vir no meio ou no fim da frase — removido antes de cortar nas specs,
       pra não engolir descrição real que vem depois dele nos itens de Urologia/Histero)."""
    s = (descricao or "").strip()
    s = _MDTECH.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = _CORTE.search(s)
    if m:
        s = s[:m.start()]
    s = re.sub(r"\s+", " ", s).strip(" -–—")
    # remove preposição/conectivo pendurado no final (corte pode deixar "... Rigido de")
    s = re.sub(r"\s+(de|da|do|das|dos|com|para|em|e|a|o|tipo|por)$", "", s, flags=re.IGNORECASE)
    return title_case_pt(s)


def title_case_pt(s: str) -> str:
    palavras = s.split()
    out = []
    for i, p in enumerate(palavras):
        low = p.lower()
        if i > 0 and low in _STOP:                       # de, e, da, tipo... minúsculo
            out.append(low)
        elif any(ch.isdigit() for ch in p) or "°" in p:  # 90°, 4K, HD-4K
            out.append(p)
        elif p.isupper() and len(p) <= 2:                # siglas curtas: HF, AV, CM, ML...
            out.append(p)
        else:
            out.append(low[:1].upper() + low[1:])
    return " ".join(out)


def eh_sim(v) -> bool:
    return str(v).strip().lower() in ("sim", "s", "x", "true", "1", "yes")


def diametro_fmt(item: dict) -> str:
    """Formata o diâmetro pro campo canônico certo: 'X mm' ou 'X Fr'.
    Prioriza Ø (mm) se preenchido; senão usa Ø (Fr); senão vazio.
    Uso: fichas/catálogo/site chamam isso em vez de ler 'diametro' direto,
    pra não tratar Fr como se fosse mm (bainhas/pinças de Urologia são Fr)."""
    mm = (item.get("diametro") or "").strip()
    if mm:
        return f"{mm} mm"
    fr = (item.get("diametro_fr") or "").strip()
    if fr:
        return f"{fr} Fr"
    return ""


def icone_angulo_b64(angulo):
    """'30°' -> base64 do PNG em assets/icones/angulos/30.png, ou None se
    o ângulo estiver vazio ou não existir ícone correspondente ainda
    (ex.: 90° até chegar o ícone). Usado por catalogo.py e fichas.py pra
    desenhar o selo de ângulo sobre a foto do produto."""
    if not angulo:
        return None
    m = re.search(r"-?\d+", str(angulo))
    if not m:
        return None
    p = config.ICONES_ANGULO / f"{m.group(0)}.png"
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()
