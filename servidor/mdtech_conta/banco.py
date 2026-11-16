"""Usuários, sessões e tentativas de login em SQLite (arquivo FORA da pasta pública)."""
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path

CONVITE_DIAS = 7                   # link de convite / nova senha: vale 7 dias e uma vez só
SESSAO_DIAS = 30                   # o vendedor fica conectado no celular por até 30 dias
JANELA = 15 * 60                   # janela das tentativas erradas (s)
MAX_POR_EMAIL = 5                  # erros seguidos por e-mail na janela -> bloqueio
MAX_POR_IP = 30                    # erros por endereço IP na janela -> bloqueio

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  nome TEXT NOT NULL DEFAULT '',
  hash TEXT NOT NULL,
  trocar_senha INTEGER NOT NULL DEFAULT 1,
  ativo INTEGER NOT NULL DEFAULT 1,
  criado INTEGER NOT NULL,
  atualizado INTEGER NOT NULL,
  ultimo_login INTEGER
);
CREATE TABLE IF NOT EXISTS sessoes (
  token_hash TEXT PRIMARY KEY,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  criada INTEGER NOT NULL,
  expira INTEGER NOT NULL,
  ultimo_uso INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessoes_usuario ON sessoes(usuario_id);
CREATE TABLE IF NOT EXISTS falhas (
  chave TEXT NOT NULL,
  quando INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS falhas_chave ON falhas(chave, quando);
CREATE TABLE IF NOT EXISTS convites (
  token_hash TEXT PRIMARY KEY,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  criado INTEGER NOT NULL,
  expira INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS eventos (
  quando INTEGER NOT NULL,
  autor TEXT NOT NULL,
  acao TEXT NOT NULL,
  alvo TEXT NOT NULL DEFAULT ''
);
"""


def normalizar_email(email):
    return (email or "").strip().lower()


def _hash_token(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class Banco:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        if not self.caminho.exists():
            # 0660: no servidor o CGI roda como www-data e o admin.py como catalogo_mdtech, e os dois gravam aqui. A pasta
            # /var/lib/mdtech é www-data:catalogo_mdtech com setgid (2770): todo arquivo novo fica no grupo catalogo_mdtech e
            # o SQLite cria o diário (-journal) com o mesmo modo do banco. Os demais usuários não entram na pasta.
            os.close(os.open(self.caminho, os.O_CREAT | os.O_WRONLY, 0o660))
            os.chmod(self.caminho, 0o660)
        self.con = sqlite3.connect(self.caminho, timeout=10, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(_ESQUEMA)
        colunas = {c["name"] for c in self.con.execute("PRAGMA table_info(usuarios)")}
        if "admin" not in colunas:                       # banco criado antes da tela de gestão (16/11)
            self.con.execute("ALTER TABLE usuarios ADD COLUMN admin INTEGER NOT NULL DEFAULT 0")

    def fechar(self):
        self.con.close()

    # ---------- usuários ----------
    def usuario(self, email):
        return self.con.execute("SELECT * FROM usuarios WHERE email = ?", (normalizar_email(email),)).fetchone()

    def usuario_por_id(self, uid):
        return self.con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()

    def criar_usuario(self, email, hash_senha, nome=""):
        agora = int(time.time())
        self.con.execute("INSERT INTO usuarios (email, nome, hash, trocar_senha, ativo, criado, atualizado) "
                         "VALUES (?, ?, ?, 1, 1, ?, ?)", (normalizar_email(email), nome, hash_senha, agora, agora))

    def definir_senha(self, uid, hash_senha, trocar_senha):
        self.con.execute("UPDATE usuarios SET hash = ?, trocar_senha = ?, atualizado = ? WHERE id = ?",
                         (hash_senha, int(trocar_senha), int(time.time()), uid))

    def definir_ativo(self, uid, ativo):
        self.con.execute("UPDATE usuarios SET ativo = ?, atualizado = ? WHERE id = ?", (int(ativo), int(time.time()), uid))
        if not ativo:
            self.encerrar_sessoes(uid)
            self.apagar_convites(uid)

    def definir_admin(self, uid, admin):
        self.con.execute("UPDATE usuarios SET admin = ?, atualizado = ? WHERE id = ?", (int(admin), int(time.time()), uid))

    def definir_nome(self, uid, nome):
        self.con.execute("UPDATE usuarios SET nome = ?, atualizado = ? WHERE id = ?", (nome, int(time.time()), uid))

    def listar(self):
        return self.con.execute("SELECT * FROM usuarios ORDER BY email").fetchall()

    def marcar_login(self, uid):
        self.con.execute("UPDATE usuarios SET ultimo_login = ? WHERE id = ?", (int(time.time()), uid))

    # ---------- sessões ----------
    def criar_sessao(self, uid):
        token = secrets.token_urlsafe(32)
        agora = int(time.time())
        self.con.execute("INSERT INTO sessoes (token_hash, usuario_id, criada, expira, ultimo_uso) VALUES (?, ?, ?, ?, ?)",
                         (_hash_token(token), uid, agora, agora + SESSAO_DIAS * 86400, agora))
        self.con.execute("DELETE FROM sessoes WHERE expira < ?", (agora,))
        return token

    def sessao(self, token):
        """Devolve o usuário (ativo) dono da sessão, ou None."""
        if not token or len(token) > 100:
            return None
        agora = int(time.time())
        lin = self.con.execute(
            "SELECT u.*, s.token_hash AS _th FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id "
            "WHERE s.token_hash = ? AND s.expira > ? AND u.ativo = 1", (_hash_token(token), agora)).fetchone()
        if lin:
            self.con.execute("UPDATE sessoes SET ultimo_uso = ? WHERE token_hash = ?", (agora, lin["_th"]))
        return lin

    def encerrar_sessao(self, token):
        if token:
            self.con.execute("DELETE FROM sessoes WHERE token_hash = ?", (_hash_token(token),))

    def encerrar_sessoes(self, uid, exceto_token=None):
        if exceto_token:
            self.con.execute("DELETE FROM sessoes WHERE usuario_id = ? AND token_hash <> ?", (uid, _hash_token(exceto_token)))
        else:
            self.con.execute("DELETE FROM sessoes WHERE usuario_id = ?", (uid,))

    # ---------- convites (link para criar a senha; uso único) ----------
    def criar_convite(self, uid):
        """Cancela os convites anteriores do usuário e devolve o código do novo (só o hash fica no banco)."""
        token = secrets.token_urlsafe(24)
        agora = int(time.time())
        self.con.execute("DELETE FROM convites WHERE usuario_id = ? OR expira < ?", (uid, agora))
        self.con.execute("INSERT INTO convites (token_hash, usuario_id, criado, expira) VALUES (?, ?, ?, ?)",
                         (_hash_token(token), uid, agora, agora + CONVITE_DIAS * 86400))
        return token

    def convite(self, token):
        """Usuário (ativo) dono de um convite válido, ou None."""
        if not token or len(token) > 100:
            return None
        return self.con.execute(
            "SELECT u.*, c.expira AS convite_expira FROM convites c JOIN usuarios u ON u.id = c.usuario_id "
            "WHERE c.token_hash = ? AND c.expira > ? AND u.ativo = 1", (_hash_token(token), int(time.time()))).fetchone()

    def apagar_convites(self, uid):
        self.con.execute("DELETE FROM convites WHERE usuario_id = ?", (uid,))

    def convite_pendente(self, uid):
        """Validade (epoch) do convite em aberto do usuário, ou None."""
        lin = self.con.execute("SELECT MAX(expira) AS e FROM convites WHERE usuario_id = ? AND expira > ?",
                               (uid, int(time.time()))).fetchone()
        return lin["e"]

    # ---------- tentativas erradas ----------
    def registrar_falha(self, *chaves):
        agora = int(time.time())
        self.con.executemany("INSERT INTO falhas (chave, quando) VALUES (?, ?)", [(c, agora) for c in chaves])
        self.con.execute("DELETE FROM falhas WHERE quando < ?", (agora - JANELA,))

    def falhas(self, chave):
        """(quantidade na janela, segundos até liberar)."""
        agora = int(time.time())
        lin = self.con.execute("SELECT COUNT(*) AS n, MIN(quando) AS primeira FROM falhas WHERE chave = ? AND quando >= ?",
                               (chave, agora - JANELA)).fetchone()
        n = lin["n"] or 0
        return n, (lin["primeira"] + JANELA - agora) if n else 0

    def limpar_falhas(self, chave):
        self.con.execute("DELETE FROM falhas WHERE chave = ?", (chave,))

    # ---------- histórico (quem fez o quê) ----------
    def registrar_evento(self, autor, acao, alvo=""):
        self.con.execute("INSERT INTO eventos (quando, autor, acao, alvo) VALUES (?, ?, ?, ?)",
                         (int(time.time()), autor, acao, alvo))

    def eventos(self, limite=50):
        return self.con.execute("SELECT * FROM eventos ORDER BY quando DESC, rowid DESC LIMIT ?", (limite,)).fetchall()
