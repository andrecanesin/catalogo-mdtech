#!/usr/bin/env python3
"""Cria dados/precos_reais.xlsx (fora do git) a partir da planilha com Valor Unitário e IPI.
  python deploy/extrair_precos.py "C:/caminho/Base_MDTech_Consolidada_com_precos.xlsx"
Valor Total IPI = Valor Unitário × (1 + IPI). Um preço por código."""
import sys
from pathlib import Path
from openpyxl import load_workbook, Workbook
if len(sys.argv) != 2:
    sys.exit(__doc__)
ws = load_workbook(sys.argv[1], data_only=True)["BASE DE PRODUTOS"]
hdr = [c.value for c in ws[4]]
ic, iv, ip = hdr.index("Código"), hdr.index("Valor Unitário"), hdr.index("IPI")
out = Workbook(); p = out.active; p.title = "PRECOS"
p.append(["Código", "Valor Unitário", "IPI", "Valor Total IPI"])
vistos = set()
for r in ws.iter_rows(min_row=5, values_only=True):
    cod = r[ic]
    if cod is None or str(cod).strip() in vistos:
        continue
    cod = str(cod).strip(); vistos.add(cod)
    if r[iv] is None:
        print("sem valor unitário:", cod); continue
    p.append([cod, r[iv], r[ip] or 0, round(r[iv] * (1 + (r[ip] or 0)), 2)])
destino = Path(__file__).resolve().parent.parent / "dados" / "precos_reais.xlsx"
out.save(destino)
print(f"{len(vistos)} códigos -> {destino}")
