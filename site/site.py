#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exportador do CATÁLOGO DIGITAL (site estático).

  python gerar.py site

Lê a base (fonte da verdade) e escreve em saida/site/:
  - produtos.json : lista de SKUs que o front consome (busca/filtro no navegador)
  - meta.json     : facetas (especialidades, famílias, fornecedores) + contadores
  - fotos/        : fotos casadas copiadas por código (faltantes = placeholder no front)

Site é ESTÁTICO: sem servidor, sem preço, aberto (indexável). Ação do usuário no
front = "Pedir orçamento" (junta os códigos escolhidos e dispara WhatsApp/e-mail).

Cross-listing Uro↔Histero: um código que aparece em 2 especialidades vira UM
produto só, com 'especialidades'/'familias' em lista (o front filtra por
pertencimento). O 1º valor é o primário (usado no card).
"""
import json, shutil
from pathlib import Path

from mdtech import config, base as B, fotos as F, textos as T


def _norm(s):
    return (s or "").upper().replace(" ", "").replace(".C", "").rstrip(".")


def _fornecedor(it):
    m = (it.get("marca") or "").upper()
    e = (it.get("especialidade") or "").strip()
    if "TONGLU" in m or e == "Laparoscopia":
        return "TONGLU"
    if "TIAN" in m or e in ("Urologia", "Histeroscopia", "Ginecologia"):
        return "TIAN SONG"
    return "ASAP"


def _produto(it):
    cod = (it.get("codigo") or "").strip()
    esp = (it.get("especialidade") or "").strip()
    fam = (it.get("familia") or "").strip()
    return {
        "codigo": cod,
        "nome": T.nome_produto(it.get("descricao", "")),
        "descricao": (it.get("descricao") or "").strip(),
        "especialidade": esp,                 # primário (card)
        "especialidades": [esp] if esp else [],  # p/ filtro (cross-listing)
        "familia": fam,
        "familias": [fam] if fam else [],
        "fornecedor": _fornecedor(it),
        "diametro": (it.get("diametro") or "").strip(),
        "comprimento": (it.get("comprimento") or "").strip(),
        "angulo": (it.get("angulo") or "").strip(),
        "autoclavavel": "Sim" if T.eh_sim(it.get("autoclavavel"))
                        else (it.get("autoclavavel") or "").strip(),
        "anvisa": (it.get("anvisa") or "").strip(),
        "ncm": (it.get("ncm") or "").strip(),
        "foto": None,                          # preenchido se a foto for copiada
        "_foto_src": None,                     # interno, removido no fim
    }


def gerar():
    itens = B.carregar()

    # dedup por código; cross-listing acumula especialidade/família em lista
    ordem, porcod = [], {}
    for it in itens:
        cod = (it.get("codigo") or "").strip()
        if not cod:
            continue
        k = _norm(cod)
        if k not in porcod:
            p = _produto(it)
            p["_foto_src"] = str(F.buscar(cod)) if F.buscar(cod) else None
            porcod[k] = p
            ordem.append(k)
        else:
            p = porcod[k]
            e = (it.get("especialidade") or "").strip()
            f = (it.get("familia") or "").strip()
            if e and e not in p["especialidades"]:
                p["especialidades"].append(e)
            if f and f not in p["familias"]:
                p["familias"].append(f)

    produtos = [porcod[k] for k in ordem]

    # copia fotos casadas p/ site/fotos/
    outdir = config.SITE
    fotodir = outdir / "fotos"
    fotodir.mkdir(parents=True, exist_ok=True)
    copiadas = 0
    for p in produtos:
        src = p.pop("_foto_src")
        if src:
            ext = Path(src).suffix.lower()
            destino = fotodir / f"{p['codigo']}{ext}"
            try:
                shutil.copyfile(src, destino)
                p["foto"] = f"fotos/{destino.name}"
                copiadas += 1
            except Exception as e:
                print(f"[aviso] falha copiando foto {p['codigo']}: {e}")

    # facetas p/ montar os filtros do front
    def _facet(campo):
        vals = set()
        for p in produtos:
            v = p[campo]
            if isinstance(v, list):
                vals.update(x for x in v if x)
            elif v:
                vals.add(v)
        return sorted(vals)

    meta = {
        "total": len(produtos),
        "com_foto": copiadas,
        "sem_foto": len(produtos) - copiadas,
        "especialidades": _facet("especialidades"),
        "familias": _facet("familias"),
        "fornecedores": _facet("fornecedor"),
    }

    (outdir / "produtos.json").write_text(
        json.dumps(produtos, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Site: {len(produtos)} produtos -> {outdir/'produtos.json'}")
    print(f"Fotos copiadas: {copiadas}/{len(produtos)} "
          f"({meta['sem_foto']} sem foto → placeholder no front)")
    print(f"Facetas: {len(meta['especialidades'])} especialidades · "
          f"{len(meta['familias'])} famílias · {len(meta['fornecedores'])} fornecedores")
    return outdir


if __name__ == "__main__":
    gerar()
