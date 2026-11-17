# -*- coding: utf-8 -*-
"""Tratamento de textos vindos da base (que estão em CAIXA ALTA com specs no fim)."""
import re, base64, unicodedata
from . import config

def preco_num(item):
    """Preço do item (float) ou None. Aceita 1250, "1250.5" e "1.250,50"."""
    v = str((item or {}).get("preco") or "").strip().replace("R$", "").replace(" ", "")
    if not v:
        return None
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        n = float(v)
    except ValueError:
        return None
    return n if n > 0 else None

def brl(v):
    """1250 -> 'R$ 1.250,00' (formato brasileiro)."""
    if v is None:
        return ""
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def slug_arquivo(texto):
    """'Kit - Proposta Básica - Hérnia de Hiato' -> 'Kit_Proposta_Basica_Hernia_de_Hiato' (nome de arquivo)."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")

# palavras que ficam minúsculas no title case (exceto se forem a 1ª palavra)
_STOP = {"de", "da", "do", "das", "dos", "e", "com", "para", "em",
         "a", "o", "ao", "à", "no", "na", "tipo", "por", "um", "uma", "uns", "umas"}

# marcadores onde o NOME termina e começam specs (Ø, D=, C=, CM=, AV= do endoscópio, autoclavável)
# ou o ano de registro. Medidas soltas ("BULLDOG 25MM CURVO", "AGULHA 1.8MM") ficam no nome:
# são o que diferencia um item do outro (a spec de diâmetro e comprimento vem de D= e C=).
# MDTECH é removido à parte (pode aparecer no meio da frase, ex. "CAMISA MDTECH PARA X" — não é
# fim de nome, é a marca inserida ali; cortar nela perderia "PARA X").
_CORTE = re.compile(r"[\s,;-]+\(?(D\s*=|Ø|C\s*=|CM\s*=|AV\s*=|AUTOCLAV|\(1\d{2})", re.IGNORECASE)
_MDTECH = re.compile(r"\bMDTECH\b", re.IGNORECASE)
_TROCARTE = re.compile(r"\bTROC(?:ATER|ARTER)(ES|S)?\b", re.IGNORECASE)   # trocater/trocarter -> trocarte


def nome_produto(descricao: str) -> str:
    """'PINÇA DE APREENSÃO GOLFINHO MDTECH D=5MM C=330MM ...' -> 'Pinça de Apreensão Golfinho'.
       'CAMISA MDTECH PARA CISTOURETROSCOPIA D=16,5FR ...' -> 'Camisa para Cistouretroscopia'
       (MDTECH pode vir no meio ou no fim da frase — removido antes de cortar nas specs,
       pra não engolir descrição real que vem depois dele nos itens de Urologia/Histero)."""
    s = (descricao or "").strip()
    s = _MDTECH.sub("", s)
    s = _TROCARTE.sub(lambda m: "TROCARTE" + ("S" if m.group(1) else ""), s)       # grafia única (decidido em 17/11)
    s = re.sub(r"\s+", " ", s).strip()
    m = _CORTE.search(s)
    if m:
        s = s[:m.start()]
    s = re.sub(r"\s+", " ", s).strip(" -–—")
    # remove preposição/conectivo pendurado no final (corte pode deixar "... Rigido de")
    s = re.sub(r"\s+(de|da|do|das|dos|com|para|em|e|a|o|tipo|por)$", "", s, flags=re.IGNORECASE)
    s = title_case_pt(s)
    s = re.sub(r"(\d+)\.(\d+)\s*MM\b", r"\1,\2 mm", s, flags=re.IGNORECASE)   # 1.8MM -> 1,8 mm
    return re.sub(r"(\d)\s*MM\b", r"\1 mm", s, flags=re.IGNORECASE)             # 25MM -> 25 mm


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


def _virgula(v):
    """Decimal brasileiro nas medidas: '2.9' -> '2,9'."""
    return str(v).strip().replace(".", ",")


def diametro_fmt(item: dict) -> str:
    """Formata o diâmetro pro campo canônico certo: 'X mm' ou 'X Fr' (decimal com vírgula).
    Prioriza Ø (mm) se preenchido; senão usa Ø (Fr); senão vazio.
    Uso: fichas/catálogo/site chamam isso em vez de ler 'diametro' direto,
    pra não tratar Fr como se fosse mm (bainhas/pinças de Urologia são Fr)."""
    mm = (item.get("diametro") or "").strip()
    if mm:
        return f"{_virgula(mm)} mm"
    fr = (item.get("diametro_fr") or "").strip()
    if fr:
        return f"{_virgula(fr)} Fr"
    return ""


_OTICA = re.compile(r"^(endosc[oó]pio|[oó]tica|telesc)", re.IGNORECASE)
_USO_UNICO = re.compile(r"^clips?\b", re.IGNORECASE)


def eh_otica(item_ou_nome) -> bool:
    """Endoscópio/ótica/telescópio: só neles o 'ângulo' é o de visão da lente (selo com ícone, dado pendente).
    Espelha MD.ehOtica do site."""
    nome = item_ou_nome if isinstance(item_ou_nome, str) else nome_produto((item_ou_nome or {}).get("descricao", ""))
    return bool(_OTICA.match(nome or ""))


def uso_unico(item_ou_nome) -> bool:
    """Item de uso único (clips): 'Autoclavável' não se aplica. Espelha MD.usoUnico do site."""
    nome = item_ou_nome if isinstance(item_ou_nome, str) else nome_produto((item_ou_nome or {}).get("descricao", ""))
    return bool(_USO_UNICO.match(nome or ""))


def ncm_fmt(ncm) -> str:
    """NCM sempre no formato 9018.90.99 (a base mistura com e sem ponto)."""
    d = re.sub(r"\D", "", str(ncm or ""))
    return f"{d[:4]}.{d[4:6]}.{d[6:]}" if len(d) == 8 else str(ncm or "").strip()


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
