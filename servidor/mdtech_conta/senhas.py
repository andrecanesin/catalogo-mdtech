"""Hash de senha com scrypt (biblioteca padrão). Formato guardado: scrypt$n$r$p$sal_b64$hash_b64."""
import base64
import hashlib
import hmac
import secrets
import string

N, R, P, TAM = 2 ** 14, 8, 1, 32     # ~16 MB de memória e ~50 ms por verificação: bom para CGI em 1 vCPU
MINIMO = 10                          # tamanho mínimo da senha escolhida pelo vendedor

# senha inicial: sem caracteres ambíguos (l, I, O, 0, 1), fácil de ditar
_ALFABETO = "".join(c for c in string.ascii_letters + string.digits if c not in "lIO01")


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def gerar_hash(senha):
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=N, r=R, p=P, dklen=TAM)
    return f"scrypt${N}${R}${P}${_b64(sal)}${_b64(h)}"


def conferir(senha, guardado):
    try:
        alg, n, r, p, sal, h = guardado.split("$")
        if alg != "scrypt":
            return False
        esperado = base64.b64decode(h)
        calc = hashlib.scrypt(senha.encode("utf-8"), salt=base64.b64decode(sal),
                              n=int(n), r=int(r), p=int(p), dklen=len(esperado))
        return hmac.compare_digest(calc, esperado)
    except (ValueError, TypeError):
        return False


# usado quando o e-mail não existe: o tempo de resposta fica igual ao de uma senha errada
_HASH_FALSO = gerar_hash(secrets.token_urlsafe(16))


def conferir_falso(senha):
    conferir(senha, _HASH_FALSO)
    return False


def senha_inicial(tamanho=12):
    return "".join(secrets.choice(_ALFABETO) for _ in range(tamanho))


def problema_nova_senha(nova, email="", atual=""):
    """Devolve o motivo de recusa (texto para o vendedor) ou None se a senha serve."""
    if len(nova) < MINIMO:
        return f"A senha precisa ter pelo menos {MINIMO} caracteres."
    if len(nova) > 200:
        return "A senha é longa demais."
    if atual and nova == atual:
        return "A nova senha precisa ser diferente da atual."
    usuario = email.split("@")[0].lower()
    if len(usuario) >= 4 and usuario in nova.lower():
        return "A senha não pode conter o seu e-mail."
    if len(set(nova)) < 4:
        return "Use uma senha menos repetitiva."
    return None
