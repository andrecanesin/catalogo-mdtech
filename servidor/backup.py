#!/usr/bin/python3
"""Cópia de segurança do banco de login (SQLite), consistente mesmo com o site em uso.

  python3 ~/mdtech_app/backup.py                  copia /var/lib/mdtech/usuarios.sqlite para ~/backups_mdtech/
  python3 ~/mdtech_app/backup.py ORIGEM DESTINO   (para testes)

Guarda as 14 cópias mais recentes (uma por dia). Agendar no cron do usuário (ver LEIA-ME.md).
A cópia só tem hashes de senha e e-mails: ainda assim, fica fora da pasta pública (permissão 600).
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

MANTER = 14


def copiar(origem, pasta_destino, agora=None):
    origem, pasta_destino = Path(origem), Path(pasta_destino)
    pasta_destino.mkdir(parents=True, exist_ok=True)
    os.chmod(pasta_destino, 0o700)
    destino = pasta_destino / f"usuarios-{time.strftime('%Y-%m-%d', time.localtime(agora or time.time()))}.sqlite"
    tmp = destino.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    src = sqlite3.connect(origem)
    dst = sqlite3.connect(tmp)
    try:
        with dst:
            src.backup(dst)                      # API de backup do SQLite: copia sem travar quem está usando
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        src.close()
        dst.close()
    if ok != "ok":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"cópia com defeito: {ok}")
    os.chmod(tmp, 0o600)
    tmp.replace(destino)
    antigas = sorted(pasta_destino.glob("usuarios-*.sqlite"))[:-MANTER]
    for velha in antigas:
        velha.unlink()
    return destino


if __name__ == "__main__":
    origem = sys.argv[1] if len(sys.argv) > 1 else "/var/lib/mdtech/usuarios.sqlite"
    pasta = sys.argv[2] if len(sys.argv) > 2 else Path.home() / "backups_mdtech"
    print("backup:", copiar(origem, pasta))
