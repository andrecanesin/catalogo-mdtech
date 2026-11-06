#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exportador do CATÁLOGO DIGITAL (site estático).

  python gerar.py site

Lê a base (fonte da verdade) e escreve DIRETO dentro de config.SITE (o
repositório git do catálogo digital — HTML/CSS/JS/fotos já vivem lá,
escritos à mão e versionados; este script só atualiza os dados):
  - produtos.json : lista de SKUs que o front consome (busca/filtro no navegador)
  - meta.json     : facetas (especialidades, famílias, fornecedores) + contadores
  - fotos/        : fotos casadas copiadas por código (faltantes = placeholder no front)
  - fichas/       : ficha técnica em PDF por código (se já gerada em saida/)
  - catalogos/     : catálogos por especialidade + catálogo completo (merge)

Não copia index.html/css/js — eles já estão em config.SITE, não em outro
lugar. Não existe pasta de build separada.

Site é ESTÁTICO: sem servidor, sem preço, aberto (indexável). Ação do usuário no
front = "Pedir orçamento" (junta os códigos escolhidos e dispara WhatsApp/e-mail).

Cross-listing Uro↔Histero: um código que aparece em 2 especialidades vira UM
produto só, com 'especialidades'/'familias' em lista (o front filtra por
pertencimento). O 1º valor é o primário (usado no card).

Pré-requisitos para os dois passos novos (fichas/catálogos):
  - Fichas: rode antes `python gerar.py fichas --separados` (gera
    saida/Ficha_<slug>_MDTech.pdf, um por código). Este script casa cada
    PDF ao código pelo mesmo slug usado em geradores/fichas.py e copia
    para site/fichas/<codigo>.pdf.
  - Catálogos: rode antes `python gerar.py catalogo` para cada especialidade
    (gera saida/Catalogo_<Especialidade>_MDTech.pdf). Este script copia os
    que existirem para site/catalogos/ e monta um "Catalogo_Completo_MDTech.pdf"
    juntando todos (requer pypdf, já é dependência do projeto).
  Se um PDF não existir em saida/, o passo correspondente é pulado sem erro
  (o botão/link some no front até o arquivo existir).
"""
import json, shutil, unicodedata
from pathlib import Path

from mdtech import config, base as B, fotos as F, textos as T


def _norm(s):
    return (s or "").upper().replace(" ", "").replace(".C", "").rstrip(".")


def _slug(s):
    return (unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
            .replace(" ", "_").replace("/", "-"))


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
        "diametro_fr": (it.get("diametro_fr") or "").strip(),
        "diametro_fmt": T.diametro_fmt(it),
        "comprimento": (it.get("comprimento") or "").strip(),
        "angulo": (it.get("angulo") or "").strip(),
        "autoclavavel": "Sim" if T.eh_sim(it.get("autoclavavel"))
                        else (it.get("autoclavavel") or "").strip(),
        "anvisa": (it.get("anvisa") or "").strip(),
        "ncm": (it.get("ncm") or "").strip(),
        "foto": None,                          # preenchido se a foto for copiada
        "ficha_pdf": None,                     # preenchido se a ficha técnica for copiada
        "_foto_src": None,                     # interno, removido no fim
    }


def _copiar_fichas(produtos, outdir):
    """Casa saida/Ficha_<slug>_MDTech.pdf com cada produto e copia para
    site/fichas/<codigo>.pdf. Códigos cross-listing (2 especialidades) usam
    o mesmo sufixo de slug que geradores/fichas.py --separados gera."""
    fichadir = outdir / "fichas"
    copiadas = 0
    candidatos = list(config.SAIDA.glob("Ficha_*_MDTech.pdf"))
    if not candidatos:
        return 0
    fichadir.mkdir(parents=True, exist_ok=True)
    for p in produtos:
        slug = _slug(p["codigo"])
        achado = None
        for arq in candidatos:
            nome = arq.stem  # "Ficha_<slug...>_MDTech"
            if nome == f"Ficha_{slug}_MDTech" or nome.startswith(f"Ficha_{slug}_"):
                achado = arq
                break
        if achado:
            destino = fichadir / f"{p['codigo']}.pdf"
            shutil.copyfile(achado, destino)
            p["ficha_pdf"] = f"fichas/{destino.name}"
            copiadas += 1
    return copiadas


def _copiar_catalogos(outdir):
    """Copia os miolos de catálogo (saida/Miolo_Catalogo_<Especialidade>_MDTech.pdf,
    gerados por `gerar.py catalogo --todos`) para site/catalogos/ e monta um
    Catalogo_Completo_MDTech.pdf juntando todos (via pypdf).

    Nome de saída no site fica sem o prefixo 'Miolo_' (é o miolo mesmo, sem
    capa/contra do InDesign — mas é o PDF completo e navegável, serve pra
    download direto)."""
    catdir = outdir / "catalogos"
    candidatos = sorted(config.SAIDA.glob("Miolo_Catalogo_*_MDTech.pdf"))
    if not candidatos:
        return 0
    catdir.mkdir(parents=True, exist_ok=True)
    copiados = []
    for src in candidatos:
        nome_site = src.name.replace("Miolo_Catalogo_", "Catalogo_", 1)
        destino = catdir / nome_site
        shutil.copyfile(src, destino)
        copiados.append(destino)

    if len(copiados) > 1:
        try:
            from pypdf import PdfWriter
            w = PdfWriter()
            for src in copiados:
                w.append(str(src))
            w.write(str(catdir / "Catalogo_Completo_MDTech.pdf"))
        except Exception as e:
            print(f"[aviso] não consegui montar o catálogo completo: {e}")
    return len(copiados)


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

    fichas_copiadas = _copiar_fichas(produtos, outdir)
    catalogos_copiados = _copiar_catalogos(outdir)

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
        "com_ficha_pdf": fichas_copiadas,
        "especialidades": _facet("especialidades"),
        "familias": _facet("familias"),
        "fornecedores": _facet("fornecedor"),
    }

    for p in produtos:
        p.pop("_foto_src", None)

    (outdir / "produtos.json").write_text(
        json.dumps(produtos, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Site: {len(produtos)} produtos -> {outdir/'produtos.json'}")
    print(f"Fotos copiadas: {copiadas}/{len(produtos)} "
          f"({meta['sem_foto']} sem foto → placeholder no front)")
    print(f"Fichas técnicas copiadas: {fichas_copiadas}/{len(produtos)} "
          f"(rode 'python gerar.py fichas --separados' antes, se faltando)")
    print(f"Catálogos PDF copiados: {catalogos_copiados} "
          f"(rode 'python gerar.py catalogo' antes, se faltando)")
    print(f"Facetas: {len(meta['especialidades'])} especialidades · "
          f"{len(meta['familias'])} famílias · {len(meta['fornecedores'])} fornecedores")
    return outdir


if __name__ == "__main__":
    gerar()
