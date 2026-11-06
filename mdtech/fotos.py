# -*- coding: utf-8 -*-
"""Casamento de foto por código — a lógica tolerante que estava duplicada nos 3 scripts.

Tolera: caixa (a153 == A153), sufixo '.C' de autoclavável ausente no arquivo,
espaços, e variações de traço/ponto. Retorna o Path da melhor foto ou None.
"""
from pathlib import Path
from . import config

def _chave(s: str) -> str:
    s = (s or "").upper().strip()
    for lixo in (" ", "_"):
        s = s.replace(lixo, "")
    if s.endswith(".C"):        # A153.C -> A153
        s = s[:-2]
    return s.rstrip(".")

def _indice(pasta: Path):
    """Mapa {chave_normalizada: Path} de todas as imagens da pasta E subpastas.

    Recursivo (rglob): o arquivo pode estar em imagens/TONGLU, imagens/TIAN_SONG,
    imagens/ASAP ou solto na raiz. O código é a chave única, então não importa em
    qual subpasta a foto esteja. Se o mesmo código existir em 2 subpastas, vence a
    primeira em ordem alfabética de caminho (determinístico).
    """
    idx = {}
    for p in sorted(pasta.rglob("*")):
        if p.is_file() and p.suffix.lower() in config.EXTS_IMG:
            idx.setdefault(_chave(p.stem), p)
    return idx

_CACHE = {}
def buscar(codigo: str, pasta: Path = None):
    pasta = Path(pasta or config.IMAGENS)
    if pasta not in _CACHE:
        _CACHE[pasta] = _indice(pasta)
    return _CACHE[pasta].get(_chave(codigo))

def subpasta(codigo: str, pasta: Path = None):
    """Nome da subpasta onde a foto foi achada (ex.: 'TONGLU'), ou None.
    Útil para o checklist/dashboard apontarem foto no fornecedor errado."""
    p = buscar(codigo, pasta)
    if p is None:
        return None
    base = Path(pasta or config.IMAGENS)
    rel = p.relative_to(base)
    return rel.parts[0] if len(rel.parts) > 1 else "(raiz)"

def checklist(itens, pasta: Path = None):
    """Retorna (casadas, faltantes) a partir de uma lista de dicts com 'codigo'."""
    casadas, faltantes = [], []
    for it in itens:
        cod = it.get("codigo", "")
        (casadas if buscar(cod, pasta) else faltantes).append(cod)
    return casadas, faltantes
