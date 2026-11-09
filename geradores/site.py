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
import json, os, shutil, unicodedata
from pathlib import Path

from mdtech import config, base as B, fotos as F, textos as T, marca as M


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
        "preco": T.preco_num(it),              # R$ da coluna "Preço (R$)" da base (hoje FICTÍCIO), ou None
        "preco_fmt": T.brl(T.preco_num(it)) or None,
        "preco_ficticio": bool(config.PRECOS_FICTICIOS and T.preco_num(it)),
        "foto": None,                          # preenchido se a foto for exportada (1600 px)
        "foto_thumb": None,                    # miniatura (600 px) usada na grade
        "ficha_pdf": None,                     # preenchido se a ficha técnica for copiada
        "_foto_src": None,                     # interno, removido no fim
    }


# Fotos do site: JPEG sobre fundo branco em dois tamanhos (o original chega a 7000 px / 5 MB).
FOTO_GRANDE = 1600   # lado maior: página de detalhe e zoom
FOTO_THUMB = 600     # lado maior: cards da grade


def _exportar_foto(src, codigo, fotodir, thumbdir):
    """Gera fotos/<codigo>.jpg (grande) e fotos/thumbs/<codigo>.jpg (miniatura). Não amplia."""
    from PIL import Image, ImageOps
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            fundo = Image.new("RGB", im.size, (255, 255, 255))
            fundo.paste(im, mask=im.split()[3])
            im = fundo
        else:
            im = im.convert("RGB")
        for pasta, lado, qual in ((fotodir, FOTO_GRANDE, 84), (thumbdir, FOTO_THUMB, 82)):
            c = im.copy()
            c.thumbnail((lado, lado), Image.LANCZOS)
            c.save(pasta / f"{codigo}.jpg", "JPEG", quality=qual, optimize=True, progressive=True)


def _copiar_fichas(produtos, outdir):
    """Casa saida/Ficha_<slug>_MDTech.pdf com cada produto e copia para
    site/fichas/<codigo>.pdf. Códigos cross-listing (2 especialidades) usam
    o mesmo sufixo de slug que geradores/fichas.py --separados gera."""
    fichadir = outdir / "fichas"
    copiadas = 0
    candidatos = list(config.SAIDA_DIGITAL.glob("Ficha_*_MDTech.pdf"))
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


MM = 72 / 25.4      # milímetro -> ponto PDF

# Índice geral do catálogo completo: cartões em posição fixa (mm) para os links serem colocados exatamente sobre eles.
_IG_TOPO, _IG_ALT, _IG_PASSO, _IG_ESQ, _IG_LARG = 72, 40, 46, 18, 174
# Botão "Todas as linhas" no topo de cada página do completo (centro do cabeçalho, livre de logo e rótulo).
_TL_ESQ, _TL_TOPO, _TL_LARG, _TL_ALT = 78, 5, 54, 8


def _fontes_css():
    from geradores.fichas import font_face
    return "".join([font_face("Poppins", "Poppins-Regular.ttf", 400), font_face("Poppins", "Poppins-SemiBold.ttf", 600),
                    font_face("Poppins", "Poppins-Bold.ttf", 700)])


def _pdf_indice_geral(linhas, destino):
    """Página 'Índice geral' (A4) do catálogo completo. linhas = [(nome, cor, n_produtos, n_familias)]."""
    from weasyprint import HTML
    from geradores.fichas import b64file
    logo = b64file(str(config.LOGO_COLORIDO))
    cards = "".join(
        f'<div class="c" style="top:{_IG_TOPO + i * _IG_PASSO}mm"><span class="b" style="background:{cor}"></span>'
        f'<div class="n">{nome}</div><div class="i">{np_} produtos · {nf} famílias</div>'
        f'<span class="go">Abrir &#8250;</span></div>'
        for i, (nome, cor, np_, nf) in enumerate(linhas))
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_fontes_css()}
    @page{{size:A4;margin:0}} *{{margin:0;padding:0;box-sizing:border-box}} body{{font-family:Poppins;color:#232D3C}}
    .logo{{position:absolute;left:18mm;top:13mm;height:9mm}}
    .k{{position:absolute;left:18mm;top:33mm;font-size:9pt;font-weight:600;color:#36A9E1;letter-spacing:.16em}}
    h1{{position:absolute;left:18mm;top:38mm;font-size:30pt;font-weight:700;color:#193C6C;bookmark-level:none}}
    .s{{position:absolute;left:18mm;top:55mm;width:174mm;font-size:10.5pt;color:#46515f}}
    .c{{position:absolute;left:{_IG_ESQ}mm;width:{_IG_LARG}mm;height:{_IG_ALT}mm;border:.6pt solid #DFE6EF;border-radius:3mm;background:#F4F7FB}}
    .c .b{{position:absolute;left:0;top:0;bottom:0;width:4mm;border-radius:3mm 0 0 3mm}}
    .c .n{{position:absolute;left:12mm;top:9mm;font-size:20pt;font-weight:700;color:#193C6C}}
    .c .i{{position:absolute;left:12mm;top:22mm;font-size:11pt;color:#46515f}}
    .c .go{{position:absolute;right:8mm;top:14mm;font-size:11pt;font-weight:600;color:#193C6C;background:#fff;
            border:.6pt solid #DFE6EF;border-radius:2mm;padding:2mm 4mm}}
    .t{{position:absolute;left:18mm;bottom:12mm;font-size:8pt;color:#606C7E}}
    </style></head><body><img class="logo" src="data:image/png;base64,{logo}">
    <div class="k">CATÁLOGO DE PRODUTOS</div><h1>Índice geral</h1>
    <div class="s">Toque em uma linha para ir ao índice dela. Em qualquer página, o botão “Todas as linhas”, no topo, volta para cá.</div>
    {cards}<div class="t">MDTech · Tecnologia que abre caminhos</div></body></html>"""
    HTML(string=html).write_pdf(str(destino))


def _pdf_botao_todas(destino):
    """Página A4 transparente só com o botão 'Todas as linhas' (sobreposta a cada página do completo)."""
    from weasyprint import HTML
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_fontes_css()}
    @page{{size:A4;margin:0}} body{{margin:0;font-family:Poppins}}
    .b{{position:absolute;left:{_TL_ESQ}mm;top:{_TL_TOPO}mm;width:{_TL_LARG}mm;height:{_TL_ALT}mm;border-radius:2mm;
        background:#193C6C;color:#fff;font-size:9pt;font-weight:600;text-align:center;line-height:{_TL_ALT}mm}}
    </style></head><body><div class="b">&#9666;&nbsp; Todas as linhas</div></body></html>"""
    HTML(string=html).write_pdf(str(destino))


def _link_interno(w, pagina, rect, alvo):
    """Link clicável na página `pagina` levando à página `alvo` (índices 0-based). O pypdf grava o destino como
    número; aqui ele é trocado pela referência da página (formato do padrão PDF, aceito por todos os leitores)."""
    from pypdf.annotations import Link
    from pypdf.generic import ArrayObject, NameObject
    a = w.add_annotation(page_number=pagina, annotation=Link(rect=rect, target_page_index=alvo))
    a[NameObject("/Dest")] = ArrayObject([w.pages[alvo].indirect_reference, NameObject("/Fit")])


def _montar_completo(arquivos, destino):
    """Catálogo completo navegável: capa + Índice geral + miolos na ordem da capa.
    arquivos = [(nome_da_linha, caminho_pdf)]. Links: Índice geral -> 1ª página (índice) de cada linha;
    botão 'Todas as linhas' no topo de cada página -> Índice geral. Os links internos de cada linha (Índice,
    família anterior/próxima) já vêm nos miolos, com ids únicos por linha."""
    import tempfile
    from pypdf import PdfReader, PdfWriter
    itens = B.carregar()
    linhas = []
    for nome, _ in arquivos:
        its = [i for i in itens if (i.get("especialidade") or "").strip() == nome]
        linhas.append((nome, M.accent_hex(nome), len({i["codigo"] for i in its}), len({i["familia"] for i in its})))

    with tempfile.TemporaryDirectory() as tmp:
        ig, bt = Path(tmp) / "indice_geral.pdf", Path(tmp) / "botao.pdf"
        _pdf_indice_geral(linhas, ig)
        _pdf_botao_todas(bt)
        w = PdfWriter()
        if config.CAPA_COMPLETO.exists():          # capa (InDesign) só no catálogo completo
            w.append(str(config.CAPA_COMPLETO), outline_item="Capa")
        else:
            print(f"[aviso] sem capa em {config.CAPA_COMPLETO}: catálogo completo sai sem capa")
        pag_ig = len(w.pages)
        w.append(str(ig), outline_item="Índice geral")
        inicios = []
        for nome, src in arquivos:
            inicios.append(len(w.pages))
            w.append(str(src), outline_item=nome)          # marcadores das famílias ficam dentro da linha
        botao = PdfReader(str(bt)).pages[0]
        H = float(w.pages[pag_ig].mediabox.height)
        for k in range(inicios[0], len(w.pages)):
            w.pages[k].merge_page(botao)
            _link_interno(w, k, (_TL_ESQ * MM, H - (_TL_TOPO + _TL_ALT) * MM, (_TL_ESQ + _TL_LARG) * MM,
                                 H - _TL_TOPO * MM), pag_ig)
        for i, ini in enumerate(inicios):
            topo = _IG_TOPO + i * _IG_PASSO
            _link_interno(w, pag_ig, (_IG_ESQ * MM, H - (topo + _IG_ALT) * MM, (_IG_ESQ + _IG_LARG) * MM,
                                      H - topo * MM), ini)
        w.page_mode = "/UseOutlines"                         # abre com os marcadores visíveis
        w.write(str(destino))


def _copiar_catalogos(outdir):
    """Copia os miolos de catálogo DIGITAIS (saida/digital/Miolo_Catalogo_<Especialidade>_MDTech.pdf,
    gerados por `gerar.py catalogo --todos --perfil digital`) para site/catalogos/ e monta um
    Catalogo_Completo_MDTech.pdf com a capa (assets/capas/Catalogo_Completo.pdf) + todos os miolos (via pypdf).

    Nome de saída no site fica sem o prefixo 'Miolo_' (é o miolo mesmo, sem
    capa/contra do InDesign — mas é o PDF completo e navegável, serve pra
    download direto)."""
    catdir = outdir / "catalogos"
    candidatos = sorted(config.SAIDA_DIGITAL.glob("Miolo_Catalogo_*_MDTech.pdf"))   # só o trilho digital
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
            from geradores.catalogo import ESPECS, _slug as slug_esp
            por_arquivo = {p.name: p for p in copiados}
            ordem = [(e, por_arquivo[f"Catalogo_{slug_esp(e)}_MDTech.pdf"]) for e in ESPECS
                     if f"Catalogo_{slug_esp(e)}_MDTech.pdf" in por_arquivo]     # ordem da capa, não alfabética
            _montar_completo(ordem, catdir / "Catalogo_Completo_MDTech.pdf")
        except Exception as e:
            print(f"[aviso] não consegui montar o catálogo completo: {e}")
    return len(copiados)


def _copiar_propostas(outdir, porcod):
    """Copia as propostas básicas (saida/propostas/<Kit>_MDTech.pdf, geradas por `gerar.py kits`) para
    site/propostas/ e escreve site/propostas.json com a lista dos kits (o site monta o menu e o filtro "Proposta básica"
    a partir dele). Cada kit leva `itens_lista` [{codigo, qtd}] na ordem da proposta, com o código já no formato do site."""
    pdir = outdir / "propostas"
    lista = []
    try:
        kits = B.carregar_kits()
    except ValueError:
        kits = {}
    for nome, linhas in kits.items():
        src = config.SAIDA_PROPOSTAS / f"{T.slug_arquivo(nome)}_MDTech.pdf"
        if not src.exists():
            print(f"[aviso] proposta sem PDF (rode 'python gerar.py kits'): {nome}")
            continue
        pdir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, pdir / src.name)
        partes = [p.strip() for p in nome.split(" - ") if p.strip()]
        itens_kit = []
        for r in linhas:
            prod = porcod.get(_norm(r["codigo"]))
            if prod:
                itens_kit.append({"codigo": prod["codigo"], "qtd": r["qtd"] or 1})
            else:
                print(f"[aviso] proposta '{nome}': código {r['codigo']} não está no catálogo do site")
        lista.append({"id": T.slug_arquivo(nome), "nome": nome, "itens_lista": itens_kit, "titulo": partes[-1], "tipo": " · ".join(partes[1:-1]) or "Proposta básica",
                      "arquivo": f"propostas/{src.name}", "itens": len(linhas),
                      "unidades": sum((r["qtd"] or 1) for r in linhas)})
    (outdir / "propostas.json").write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(lista)


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

    # TRAVA: preço REAL não vai ao site público. O workflow define SITE_PUBLICO=1 (GitHub Pages é público).
    if os.environ.get("SITE_PUBLICO") == "1" and not config.PRECOS_FICTICIOS and any(p["preco"] for p in produtos):
        raise SystemExit("ERRO: há preços reais na base e o destino é público (GitHub Pages). Publique no servidor com acesso "
                         "controlado, ou volte PRECOS_FICTICIOS = True (mdtech/config.py) com valores ilustrativos.")

    # exporta as fotos casadas p/ site/fotos/ (pasta gerada: recriada do zero a cada execução)
    outdir = config.SITE
    fotodir = outdir / "fotos"
    thumbdir = fotodir / "thumbs"
    if fotodir.exists():
        shutil.rmtree(fotodir)
    thumbdir.mkdir(parents=True, exist_ok=True)
    copiadas = 0
    for p in produtos:
        src = p.pop("_foto_src")
        if src:
            try:
                _exportar_foto(src, p["codigo"], fotodir, thumbdir)
                p["foto"] = f"fotos/{p['codigo']}.jpg"
                p["foto_thumb"] = f"fotos/thumbs/{p['codigo']}.jpg"
                copiadas += 1
            except Exception as e:
                print(f"[aviso] falha exportando foto {p['codigo']}: {e}")

    fichas_copiadas = _copiar_fichas(produtos, outdir)
    catalogos_copiados = _copiar_catalogos(outdir)
    propostas_copiadas = _copiar_propostas(outdir, porcod)

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
    print(f"Propostas básicas copiadas: {propostas_copiadas} "
          f"(rode 'python gerar.py kits' antes, se faltando)")
    print(f"Facetas: {len(meta['especialidades'])} especialidades · "
          f"{len(meta['familias'])} famílias · {len(meta['fornecedores'])} fornecedores")
    return outdir


if __name__ == "__main__":
    gerar()
