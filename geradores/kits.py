# -*- coding: utf-8 -*-
"""Propostas básicas: um PDF por kit (conjunto de itens para um tipo de uso do médico).

  python gerar.py kits                         # todos os kits da aba KITS
  python gerar.py kits --kit "Hérnia de Hiato" # um kit (busca pelo nome)
  python gerar.py kits --kit "Hérnia de Hiato" --preview   # HTML no navegador, sem gerar PDF

A proposta é uma RELAÇÃO COMPLETA: todos os itens fazem parte do kit (o vendedor oferece tudo ao médico);
os grupos só dividem a lista em seções. Os kits ficam na aba KITS da planilha-base (mdtech.base.carregar_kits); os dados de cada produto
(nome, Ø, comprimento, ANVISA, foto) vêm da BASE DE PRODUTOS pelo código. A foto é a reduzida (como no digital).
Preço é opcional: se alguma linha do kit tiver 'Preço unit. (R$)', o PDF ganha as colunas de preço e o total.
Saída: saida/propostas/Kit_<...>_MDTech.pdf (local; é um material comercial para enviar ao médico).
"""
import re, unicodedata
from datetime import date
from weasyprint import HTML

from mdtech import config, base as B, fotos as F, textos as T
from geradores.fichas import font_face, b64file, esc, accent, NAVY, INK, LINE, MUT, LAB, ZEBRA



def _slug(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def _brl(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _titulo(nome):
    """'Kit - Proposta Básica - Hérnia de Hiato' -> ('Kit', 'Proposta Básica', 'Hérnia de Hiato')."""
    partes = [p.strip() for p in nome.split(" - ") if p.strip()]
    if len(partes) >= 3:
        return partes[0], " · ".join(partes[1:-1]), partes[-1]
    if len(partes) == 2:
        return partes[0], "Proposta básica", partes[1]
    return "Kit", "Proposta básica", nome


def _linha(r, it, com_preco):
    """Uma linha da tabela. `it` = produto da base (ou None se o código não existir)."""
    if it is None:
        nome_html = (f'<div class="c mono">{esc(r["codigo"])}</div>'
                     f'<div class="nm falta">código não encontrado na base</div>')
        foto, diam, comp, anv = '<div class="ph"><span>sem foto</span></div>', "—", "—", "—"
        nome_curto = ""
    else:
        nome_curto = T.nome_produto(it.get("descricao", ""))
        nome_html = (f'<div class="c mono">{esc(r["codigo"])}</div><div class="nm">{esc(nome_curto)}</div>'
                     + (f'<div class="obs">{esc(r["obs"])}</div>' if r["obs"] else ""))
        p = F.buscar(r["codigo"])
        foto = (f'<img src="data:image/jpeg;base64,{F.jpeg_reduzido_b64(str(p), lado=360)}">' if p
                else '<div class="ph"><span>sem foto</span></div>')
        d = T.diametro_fmt(it)
        diam = esc(d) if d else '<span class="falta">—</span>'
        comp = f'{esc(it["comprimento"])} mm' if it.get("comprimento") else '<span class="falta">—</span>'
        anv = esc(it["anvisa"]) if it.get("anvisa") else '<span class="falta it">em registro</span>'
    cel = [f'<td class="f">{foto}</td>', f'<td class="n">{nome_html}</td>',
           f'<td class="s">{diam}</td>', f'<td class="s">{comp}</td>', f'<td class="a mono">{anv}</td>']
    cel.append(f'<td class="q">{r["qtd"] if r["qtd"] else 1}</td>')
    if com_preco:
        pu = r["preco"]
        cel.append(f'<td class="p">{_brl(pu) if pu is not None else "—"}</td>')
        cel.append(f'<td class="p">{_brl(pu * (r["qtd"] or 1)) if pu is not None else "—"}</td>')
    return "<tr>" + "".join(cel) + "</tr>"


def _tabela(linhas, produtos, com_preco):
    cab = ['<th class="f"></th>', '<th class="n">Item</th>', '<th class="s">Ø</th>', '<th class="s">Comp.</th>',
           '<th class="a">Registro ANVISA</th>', '<th class="q">Qtd</th>']
    if com_preco:
        cab += ['<th class="p">Unit. (R$)</th>', '<th class="p">Total (R$)</th>']
    corpo = "".join(_linha(r, B.por_codigo_exato(produtos, r["codigo"]), com_preco) for r in linhas)
    return f'<table class="it"><thead><tr>{"".join(cab)}</tr></thead><tbody>{corpo}</tbody></table>'


def _doc_html(nome, linhas, produtos):
    ac = accent("Laparoscopia")
    faces = "".join([font_face("Poppins", "Poppins-Regular.ttf", 400), font_face("Poppins", "Poppins-Medium.ttf", 500),
                     font_face("Poppins", "Poppins-SemiBold.ttf", 600), font_face("Poppins", "Poppins-Bold.ttf", 700),
                     font_face("Plex", "IBMPlexMono-Regular.ttf", 400), font_face("Plex", "IBMPlexMono-Medium.ttf", 500)])
    logo = b64file(str(config.LOGO_BRANCO))
    logo_c = b64file(str(config.LOGO_COLORIDO))
    kicker, tipo, titulo = _titulo(nome)
    hoje = date.today().strftime("%d/%m/%Y")

    grupos = {}
    for r in linhas:
        grupos.setdefault(r["grupo"], []).append(r)
    com_preco = any(r["preco"] is not None for r in linhas)
    n_itens = len(linhas)
    n_un = sum((r["qtd"] or 1) for r in linhas)

    secoes = ""
    for g, rs in grupos.items():
        # seção curta não quebra entre páginas; a longa (itens principais) pode quebrar
        secoes += (f'<div class="{"grp" if len(rs) <= 8 else ""}"><div class="h2">{esc(g)}</div>'
                   + _tabela(rs, produtos, com_preco) + '</div>')
    if com_preco:
        tot = sum((r["preco"] or 0) * (r["qtd"] or 1) for r in linhas)
        secoes += f'<div class="total">Total do kit: <b>R$ {_brl(tot)}</b></div>'

    resumo = f'<b>{n_itens}</b> itens · <b>{n_un}</b> unidades'
    if len(grupos) > 1:
        resumo += " &nbsp;|&nbsp; " + " · ".join(f"{esc(g)} <b>{len(rs)}</b>" for g, rs in grupos.items())

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{esc(nome)}</title><style>
    {faces}
    @page {{ size:A4; margin:12mm 14mm 18mm 14mm;
      @bottom-left  {{ content:"MDTech · Tecnologia que abre caminhos"; font:7pt Poppins; color:{MUT}; }}
      @bottom-center{{ content:"{hoje}"; font:7pt Poppins; color:{MUT}; }}
      @bottom-right {{ content:counter(page) " / " counter(pages); font:7pt Poppins; color:{MUT}; }} }}
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:Poppins;color:{INK};font-size:9pt;}}
    .mono{{font-family:Plex;}}
    .head{{background:{NAVY};margin:-12mm -14mm 7mm -14mm;padding:9mm 14mm 8mm 20mm;position:relative;
           display:flex;align-items:center;justify-content:space-between;}}
    .head::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:6mm;background:{ac};}}
    .head img{{height:11mm;}}
    .head .mid{{text-align:center;flex:1;}}
    .head .mid .k{{color:{ac};font-weight:600;font-size:9pt;letter-spacing:.18em;text-transform:uppercase;}}
    .head .mid .s{{color:#aeb9cc;font-size:7.5pt;margin-top:.6mm;}}
    .head .rt{{text-align:right;color:#aeb9cc;font-size:7pt;letter-spacing:.16em;}}
    h1{{font-size:22pt;font-weight:700;color:{NAVY};line-height:1.1;margin-bottom:3mm;}}
    .resumo{{background:#f4f7fb;border-left:1.4mm solid {ac};border-radius:1.5mm;padding:2.6mm 4mm;
             font-size:9pt;color:#33404f;margin-bottom:5mm;}}
    .resumo b{{color:{NAVY};}}
    .h2{{font-size:11.5pt;font-weight:700;color:{NAVY};padding-bottom:1.6mm;border-bottom:1.6pt solid {ac};
         margin:5mm 0 2mm 0;page-break-after:avoid;}}
    table.it{{width:100%;border-collapse:collapse;}}
    table.it thead{{display:table-header-group;}}
    table.it th{{font-size:6.5pt;font-weight:500;color:{LAB};letter-spacing:.09em;text-transform:uppercase;
                 text-align:left;padding:1.4mm 2mm;border-bottom:.6pt solid {LINE};}}
    table.it td{{padding:1.8mm 2mm;border-bottom:.5pt solid {LINE};vertical-align:middle;}}
    table.it tr{{page-break-inside:avoid;}}
    table.it tbody tr:nth-child(even) td{{background:{ZEBRA};}}
    td.f,th.f{{width:19mm;padding-left:0;}}
    td.f img{{width:16mm;height:12mm;object-fit:contain;display:block;background:#fff;border:.5pt solid {LINE};
              border-radius:1mm;padding:.5mm;}}
    .ph{{width:16mm;height:12mm;border:.6pt dashed #E06666;border-radius:1mm;display:flex;align-items:center;
         justify-content:center;font-size:5.5pt;color:#E06666;font-weight:600;}}
    td.n .c{{font-size:8pt;color:{ac};font-weight:500;}}
    td.n .nm{{font-size:9pt;font-weight:600;color:{NAVY};line-height:1.2;}}
    td.n .obs{{font-size:7pt;color:{LAB};}}
    td.s{{font-size:8.5pt;white-space:nowrap;width:15mm;}}
    td.a{{font-size:7.5pt;white-space:nowrap;width:27mm;color:#4a5568;}}
    td.q,th.q{{width:11mm;text-align:center;font-weight:700;color:{NAVY};font-size:10pt;}}
    td.p,th.p{{width:21mm;text-align:right;font-size:8.5pt;white-space:nowrap;}}
    .falta{{color:#E06666;font-weight:700;}} .it{{font-style:italic;font-weight:400;}}
    .total{{text-align:right;margin-top:3mm;font-size:10pt;color:{NAVY};}}
    .grp{{page-break-inside:avoid;}}
    .wm{{text-align:center;margin-top:9mm;page-break-inside:avoid;}} .wm img{{height:12mm;}}
    </style></head><body>
      <div class="head"><img src="data:image/png;base64,{logo}">
        <div class="mid"><div class="k">{esc(kicker)}</div><div class="s">Instrumental cirúrgico · Padrão ANVISA</div></div>
        <div class="rt">{esc(tipo).upper()}</div></div>
      <h1>{esc(titulo)}</h1>
      <div class="resumo">{resumo}</div>
      {secoes}
      <div class="wm"><img src="data:image/png;base64,{logo_c}"></div>
    </body></html>"""


def _kits_escolhidos(kit):
    todos = B.carregar_kits()
    if not kit:
        return todos
    k = _slug(kit).lower()
    achados = {n: v for n, v in todos.items() if k in _slug(n).lower()}
    if not achados:
        print(f"[erro] kit não encontrado: {kit!r}. Kits na planilha: {', '.join(todos) or '(nenhum)'}")
    return achados


def _avisos(nome, linhas, produtos):
    faltam = [r["codigo"] for r in linhas if B.por_codigo_exato(produtos, r["codigo"]) is None]
    if faltam:
        print(f"  [aviso] {nome}: código(s) fora da base: {', '.join(faltam)}")


def preview(kit=None):
    produtos = B.carregar()
    saidas = []
    for nome, linhas in _kits_escolhidos(kit).items():
        _avisos(nome, linhas, produtos)
        doc = _doc_html(nome, linhas, produtos).replace("</head>", """<style>
          html{background:#dde3ec;} body{max-width:210mm;margin:24px auto;padding:12mm 14mm;background:#fff;
          box-shadow:0 4px 28px rgba(20,30,50,.25);box-sizing:border-box;}</style></head>""")
        out = config.SAIDA / f"Preview_{_slug(nome)}.html"
        out.write_text(doc, encoding="utf-8")
        print(f"Preview: {nome} -> {out}")
        saidas.append(str(out))
    return saidas


def gerar(kit=None):
    produtos = B.carregar()
    saidas = []
    for nome, linhas in _kits_escolhidos(kit).items():
        _avisos(nome, linhas, produtos)
        out = config.SAIDA_PROPOSTAS / f"{_slug(nome)}_MDTech.pdf"
        HTML(string=_doc_html(nome, linhas, produtos), base_url=str(config.IMAGENS)).write_pdf(str(out))
        un = sum((r["qtd"] or 1) for r in linhas)
        print(f"  {nome}: {len(linhas)} itens, {un} unidades -> {out}")
        saidas.append(str(out))
    return saidas


if __name__ == "__main__":
    gerar()
