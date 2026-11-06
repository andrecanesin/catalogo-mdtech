# -*- coding: utf-8 -*-
"""Helpers de desenho usados por todos os geradores (Pillow)."""
from PIL import Image, ImageDraw

def canvas(w, h, bg=(255, 255, 255)):
    img = Image.new("RGBA", (w, h), bg + (255,))
    return img, ImageDraw.Draw(img)

def rrect(d, xy, r, fill=None, outline=None, w=1):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=w)

def medir(d, t, f):
    b = d.textbbox((0, 0), t, font=f); return b[2]-b[0], b[3]-b[1]

def texto(d, xy, t, f, fill):
    d.text(xy, t, font=f, fill=fill)

def texto_centro(d, cx, y, t, f, fill):
    w, _ = medir(d, t, f); d.text((cx-w/2, y), t, font=f, fill=fill)

def texto_espacado(d, cx, y, t, f, fill, track=3):
    w = sum(medir(d, c, f)[0]+track for c in t) - track
    x = cx - w/2
    for c in t:
        d.text((x, y), c, font=f, fill=fill); x += medir(d, c, f)[0] + track

def carregar_recortada(caminho, pad=8):
    """Abre PNG e recorta as sobras transparentes (bbox do canal alfa)."""
    im = Image.open(str(caminho)).convert("RGBA")
    bbox = im.split()[3].getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        im = im.crop((max(0, x0-pad), max(0, y0-pad),
                      min(im.width, x1+pad), min(im.height, y1+pad)))
    return im

def quebrar(d, texto, fonte, max_w):
    """Quebra 'texto' em linhas que cabem em max_w (por palavra)."""
    palavras = str(texto).split()
    linhas, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if medir(d, teste, fonte)[0] <= max_w or not atual:
            atual = teste
        else:
            linhas.append(atual); atual = p
    if atual:
        linhas.append(atual)
    return linhas or [""]

def multilinha(d, xy, texto, fonte, fill, max_w, leading=None,
               max_linhas=None, centro=False, cx=None):
    """Desenha texto quebrado em linhas. Retorna a altura total usada."""
    linhas = quebrar(d, texto, fonte, max_w)
    if max_linhas and len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while linhas and medir(d, linhas[-1] + "…", fonte)[0] > max_w:
            linhas[-1] = linhas[-1].rsplit(" ", 1)[0] if " " in linhas[-1] else linhas[-1][:-1]
        linhas[-1] += "…"
    x, y = xy
    lh = leading or int(medir(d, "Ag", fonte)[1] * 1.35)
    for ln in linhas:
        if centro and cx is not None:
            w, _ = medir(d, ln, fonte); d.text((cx - w/2, y), ln, font=fonte, fill=fill)
        else:
            d.text((x, y), ln, font=fonte, fill=fill)
        y += lh
    return len(linhas) * lh

def ajustar(d, texto, criar_fonte, max_w, tam_ini, max_linhas=2, tam_min=20):
    """Reduz o tamanho da fonte até o texto caber em max_linhas dentro de max_w.
    'criar_fonte' é uma função tamanho->ImageFont. Retorna (fonte, linhas)."""
    t = tam_ini
    while t >= tam_min:
        f = criar_fonte(t)
        linhas = quebrar(d, texto, f, max_w)
        if len(linhas) <= max_linhas:
            return f, linhas
        t -= 2
    return criar_fonte(tam_min), quebrar(d, texto, criar_fonte(tam_min), max_w)

def encaixar(img, im, box, anchor="c"):
    """Cola 'im' dentro de 'box' preservando proporção. anchor: c/tl/bl."""
    x0, y0, x1, y1 = box; bw, bh = x1-x0, y1-y0; iw, ih = im.size
    s = min(bw/iw, bh/ih); nw, nh = int(iw*s), int(ih*s)
    r = im.resize((nw, nh), Image.LANCZOS)
    px = {"c": x0+(bw-nw)//2, "tl": x0, "bl": x0}[anchor]
    py = {"c": y0+(bh-nh)//2, "tl": y0, "bl": y1-nh}[anchor]
    img.alpha_composite(r, (int(px), int(py)))
