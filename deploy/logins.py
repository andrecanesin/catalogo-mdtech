#!/usr/bin/env python3
"""Gera deploy/.htpasswd (1 login por vendedor) a partir de deploy/vendedores.txt (1 e-mail por linha; o resto da linha é ignorado).
Senhas novas saem em deploy/senhas_vendedores.txt (para você enviar a cada um). Quem já tem senha mantém; quem saiu da lista é removido.
  python deploy/logins.py                     adiciona/remove conforme a lista
  python deploy/logins.py --resetar e@mail    nova senha para uma pessoa
Nada disto vai ao git (ver .gitignore)."""
import secrets, string, subprocess, sys
from pathlib import Path
D = Path(__file__).resolve().parent
lista = [l.split()[0].lower() for l in (D / "vendedores.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
resetar = sys.argv[sys.argv.index("--resetar") + 1].lower() if "--resetar" in sys.argv else None
atual = {}
if (D / ".htpasswd").exists():
    for l in (D / ".htpasswd").read_text().splitlines():
        if ":" in l:
            u, h = l.split(":", 1); atual[u] = h
alfabeto = string.ascii_letters.replace("l", "").replace("I", "").replace("O", "") + string.digits.replace("0", "").replace("1", "")
novos, saida = [], {}
for u in lista:
    if u in atual and u != resetar:
        saida[u] = atual[u]; continue
    senha = "".join(secrets.choice(alfabeto) for _ in range(12))
    h = subprocess.run(["openssl", "passwd", "-apr1", "-stdin"], input=senha, capture_output=True, text=True, check=True).stdout.strip()
    saida[u] = h; novos.append((u, senha))
(D / ".htpasswd").write_text("".join(f"{u}:{h}\n" for u, h in saida.items()))
if novos:
    with open(D / "senhas_vendedores.txt", "a", encoding="utf-8") as f:
        for u, s in novos: f.write(f"{u}\t{s}\n")
for u in atual:
    if u not in saida: print("removido:", u)
print(f"{len(saida)} logins; {len(novos)} senhas novas em deploy/senhas_vendedores.txt")
