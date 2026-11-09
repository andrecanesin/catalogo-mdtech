# -*- coding: utf-8 -*-
"""Leitura da base (fonte da verdade) num lugar só.

O CONTRATO de nomes de coluna vive AQUI. Se a base mudar um nome de coluna,
ajuste o dicionário COLUNAS abaixo — os 3 geradores continuam funcionando
porque acessam os campos por chave canônica (ex.: p['codigo'], p['descricao']).
"""
from openpyxl import load_workbook
from . import config

# chave canônica  ->  nome exato da coluna na planilha
COLUNAS = {
    "marca":        "Marca",
    "especialidade":"Especialidade",
    "familia":      "Família",
    "codigo":       "Código",
    "descricao":    "Descrição (PT)",
    "diametro":     "Ø (mm)",
    "diametro_fr":  "Ø (Fr)",
    "comprimento":  "Comp. (mm)",
    "angulo":       "Ângulo",
    "autoclavavel": "Autoclavável",
    "anvisa":       "Registro ANVISA",
    "imagem":       "Imagem (status)",
    "ncm":          "NCM",
    "id":           "Id (sistema)",
    "tambem_em":    "Também em",
}

def carregar(caminho=None, aba=None):
    """Retorna lista de dicts (um por SKU) com chaves canônicas.
    Linhas sem 'codigo' são ignoradas."""
    caminho = str(caminho or config.BASE_XLSX)
    aba = aba or config.BASE_ABA
    wb = load_workbook(caminho, data_only=True)
    ws = wb[aba] if aba in wb.sheetnames else wb[wb.sheetnames[0]]

    # localizar a linha de cabeçalho (a que contém a coluna 'Código')
    lin_hdr = None
    for r in range(1, 12):
        valores = [(c.value or "").strip() if isinstance(c.value, str) else c.value
                   for c in ws[r]]
        if COLUNAS["codigo"] in valores:
            lin_hdr = r; cabecalho = valores; break
    if lin_hdr is None:
        raise ValueError("Cabeçalho não encontrado (coluna 'Código' ausente nas 12 primeiras linhas)")

    idx = {chave: cabecalho.index(nome)
           for chave, nome in COLUNAS.items() if nome in cabecalho}

    itens = []
    for linha in ws.iter_rows(min_row=lin_hdr+1, values_only=True):
        reg = {}
        for chave, i in idx.items():
            v = linha[i] if i < len(linha) else None
            reg[chave] = ("" if v is None else str(v).strip())
        cod = reg.get("codigo", "")
        if not cod:
            continue
        if cod.startswith("—") or "exemplo" in reg.get("marca", "").lower():
            continue                      # pula linhas-modelo
        itens.append(reg)
    return itens

# ---- KITS (propostas básicas): contrato de colunas da aba KITS ----
COLUNAS_KITS = {
    "kit":    "Kit",
    "grupo":  "Grupo",
    "ordem":  "Ordem",
    "codigo": "Código",
    "qtd":    "Qtd",
    "obs":    "Observação",
    "preco":  "Preço unit. (R$)",
}

def carregar_kits(caminho=None):
    """Retorna {nome_do_kit: [linhas]} lidas da aba KITS, na ordem Grupo (ordem de aparição) e Ordem.
    Cada linha: dict com kit, grupo, ordem, codigo, qtd (int ou None), obs, preco (float ou None)."""
    caminho = str(caminho or config.BASE_XLSX)
    wb = load_workbook(caminho, data_only=True)
    if config.KITS_ABA not in wb.sheetnames:
        raise ValueError(f"Aba '{config.KITS_ABA}' não existe na base")
    ws = wb[config.KITS_ABA]
    lin_hdr = None
    for r in range(1, 12):
        valores = [(c.value or "").strip() if isinstance(c.value, str) else c.value for c in ws[r]]
        if COLUNAS_KITS["kit"] in valores and COLUNAS_KITS["codigo"] in valores:
            lin_hdr = r; cabecalho = valores; break
    if lin_hdr is None:
        raise ValueError("Cabeçalho da aba KITS não encontrado (colunas 'Kit' e 'Código')")
    idx = {k: cabecalho.index(n) for k, n in COLUNAS_KITS.items() if n in cabecalho}

    def num(v, tipo):
        try:
            return tipo(str(v).replace(",", ".")) if v not in (None, "") else None
        except ValueError:
            return None

    kits, grupos = {}, {}
    for linha in ws.iter_rows(min_row=lin_hdr + 1, values_only=True):
        g = lambda k: (linha[idx[k]] if k in idx and idx[k] < len(linha) else None)
        kit, cod = str(g("kit") or "").strip(), str(g("codigo") or "").strip()
        if not kit or not cod:
            continue
        grupo = str(g("grupo") or "").strip() or "Itens do kit"
        reg = {"kit": kit, "grupo": grupo, "codigo": cod,
               "ordem": num(g("ordem"), int) or 0, "qtd": num(g("qtd"), int),
               "obs": str(g("obs") or "").strip(), "preco": num(g("preco"), float)}
        grupos.setdefault(kit, {}).setdefault(grupo, len(grupos.get(kit, {})))
        kits.setdefault(kit, []).append(reg)
    for kit, linhas in kits.items():
        linhas.sort(key=lambda r: (grupos[kit][r["grupo"]], r["ordem"]))
    return kits

def por_codigo_exato(itens, codigo):
    """Busca pelo código exato (sem diferenciar caixa/espaços). Diferente de por_codigo, NÃO ignora o sufixo .C:
    A215 e A215.C são produtos distintos."""
    c = (codigo or "").upper().replace(" ", "")
    for i in itens:
        if (i.get("codigo", "") or "").upper().replace(" ", "") == c:
            return i
    return None

def por_especialidade(itens, especialidade):
    e = especialidade.strip().lower()
    return [i for i in itens if i.get("especialidade","").strip().lower() == e]

def por_codigo(itens, codigo):
    c = _norm(codigo)
    for i in itens:
        if _norm(i.get("codigo","")) == c:
            return i
    return None

def _norm(s):
    return (s or "").upper().replace(" ", "").replace(".C", "").rstrip(".")
