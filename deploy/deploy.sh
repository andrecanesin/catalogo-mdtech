#!/usr/bin/env bash
# Deploy por SSH (rodar na máquina do André, não no Actions: o build interno usa os preços reais, que ficam fora do git).
#   bash deploy/deploy.sh               gera tudo (fichas, catálogos, propostas, site), envia e troca a versão no ar
#   bash deploy/deploy.sh --so-enviar   reaproveita o que já está em saida/servidor
#   bash deploy/deploy.sh --simular     gera e envia, mostra o que a troca faria, e NÃO troca nada (bom para testar)
#   bash deploy/deploy.sh --voltar      volta para a versão anterior (rollback); rodar de novo volta mais uma
#
# Troca atômica: a versão nova chega inteira em ~/mdtech_deploy no servidor e só então entra no lugar da atual (deploy/remoto.sh).
# Arquivo que deixou de ser gerado sai junto (antes, o envio por tar só sobrescrevia e o velho ficava). Se a conferência no ar
# falhar, o script volta sozinho para a versão anterior.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "Falta deploy/.env (copie deploy/env.exemplo e preencha)."; exit 1; }
set -a; . deploy/.env; set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}" "${DEPLOY_PATH:?}" "${SITE_URL:?}"
PORTA="${DEPLOY_PORT:-22}"
ALVO="$DEPLOY_USER@$DEPLOY_HOST"
SSH=(ssh -p "$PORTA")

SO_ENVIAR=0; SIMULAR=0; VOLTAR=0
for arg in "$@"; do
  case "$arg" in
    --so-enviar) SO_ENVIAR=1 ;;
    --simular) SIMULAR=1 ;;
    --voltar) VOLTAR=1 ;;
    *) echo "Opção desconhecida: $arg (use --so-enviar, --simular ou --voltar)"; exit 1 ;;
  esac
done

# roda deploy/remoto.sh no servidor (tr -d '\r': no Windows o arquivo pode vir com CRLF)
remoto() { tr -d '\r' < deploy/remoto.sh | "${SSH[@]}" "$ALVO" bash -s -- "$@"; }

# conferência no ar; devolve o motivo da falha (vazio = tudo certo)
conferir() {
  local cod
  cod="$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/")"
  [ "$cod" = "200" ] || { echo "a página inicial respondeu $cod (esperado 200)"; return; }
  cod="$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/interno/produtos.json")"
  [ "$cod" = "401" ] || { echo "/interno/produtos.json respondeu $cod (esperado 401: lá estão os preços)"; return; }
  if curl -s "$SITE_URL/produtos.json" | grep -Eq '"preco": [0-9]'; then
    echo "o site de clientes tem preço no produtos.json"; return
  fi
  cod="$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/conta.py/precos")"
  [ "$cod" = "401" ] || { echo "/conta.py/precos respondeu $cod (esperado 401): o login novo não está funcionando"; return; }
  # gravação: login com e-mail inexistente grava a tentativa errada no banco -> 401 (500 = o CGI não consegue gravar em /var/lib/mdtech)
  cod="$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
    -d '{"email":"teste-deploy@invalido.local","senha":"x"}' "$SITE_URL/conta.py/entrar")"
  [ "$cod" = "401" ] || { echo "o login de teste respondeu $cod (esperado 401): o app lê, mas não grava (veja o log do Apache)"; return; }
}

# --voltar: rollback, sem testes nem build (pensado para emergência)
if [ "$VOLTAR" = "1" ]; then
  remoto voltar "$DEPLOY_PATH"
  motivo="$(conferir)"
  if [ -n "$motivo" ]; then echo "ALERTA: depois de voltar, $motivo."; exit 1; fi
  echo "OK: versão anterior no ar em $SITE_URL."
  exit 0
fi

# 0) só sobe a main limpa, igual à do GitHub, e com os testes passando (DEPLOY_FORCAR=1 ignora, só em emergência)
if [ "${DEPLOY_FORCAR:-0}" != "1" ]; then
  [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "ERRO: o deploy sai só da main (você está em '$(git rev-parse --abbrev-ref HEAD)'). Rode: git checkout main"; exit 1; }
  [ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "ERRO: há alterações não commitadas. Commite ou descarte antes do deploy."; exit 1; }
  git fetch -q origin main
  [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "ERRO: a main local difere da do GitHub. Rode: git pull"; exit 1; }
  python -m unittest discover -s tests -t . || { echo "ERRO: testes do núcleo falharam."; exit 1; }
  python -m unittest discover -s servidor/testes || { echo "ERRO: testes do login falharam."; exit 1; }
  if command -v ruff >/dev/null 2>&1; then ruff check . || { echo "ERRO: ruff encontrou problemas."; exit 1; }; fi
fi

if [ "$SO_ENVIAR" != "1" ]; then
  python gerar.py fichas --separados
  python gerar.py catalogo --todos --perfil digital
  python gerar.py kits
  python gerar.py site --interno
fi
[ -f saida/servidor/interno/produtos.json ] || { echo "saida/servidor/interno não existe: rode sem --so-enviar."; exit 1; }
[ -f saida/app_dados/precos.json ] || { echo "Falta saida/app_dados/precos.json: rode sem --so-enviar."; exit 1; }

# 1) logins: /interno NUNCA vai ao ar sem senha (lá estão os preços)
HOME_REMOTO="$("${SSH[@]}" "$ALVO" 'echo $HOME')"
HTPASSWD_REMOTO="$HOME_REMOTO/.htpasswd_mdtech"      # fora da pasta pública
if [ -f deploy/.htpasswd ]; then
  "${SSH[@]}" "$ALVO" "cat > '$HTPASSWD_REMOTO' && chmod 640 '$HTPASSWD_REMOTO'" < deploy/.htpasswd
elif ! "${SSH[@]}" "$ALVO" "test -s '$HTPASSWD_REMOTO'"; then
  echo "ERRO: não há logins. Rode: python deploy/logins.py"; exit 1
fi
sed "s|__HTPASSWD__|$HTPASSWD_REMOTO|" deploy/htaccess_interno > saida/servidor/interno/.htaccess

# 2) dados do login: o Apache roda o CGI como www-data com ProtectHome=read-only (lê /home, não grava), então os dados ficam em
#    /var/lib/mdtech, criada uma vez com sudo (www-data:catalogo_mdtech, 2770; ver servidor/LEIA-ME.md).
DADOS=/var/lib/mdtech
"${SSH[@]}" "$ALVO" "test -w $DADOS" || { echo "ERRO: $DADOS não existe ou não é gravável. Crie uma vez (servidor/LEIA-ME.md, 'Instalação'). Nada foi trocado."; exit 1; }

# 3) envio da versão nova para uma pasta ao lado (o site no ar ainda não muda)
ID="$(date +%Y%m%d-%H%M%S)"
echo "Enviando a versão $ID..."
tar -C saida/servidor -czf - . \
  | "${SSH[@]}" "$ALVO" "mkdir -p mdtech_deploy/site-$ID && tar -C mdtech_deploy/site-$ID -xzf -"
# conta.py = porta de entrada CGI do login (tr -d '\r': com CRLF a 1ª linha #!/usr/bin/python3 quebra o CGI, erro 500)
tr -d '\r' < servidor/conta.py | "${SSH[@]}" "$ALVO" "cat > mdtech_deploy/site-$ID/conta.py"
# app do login (vai para ~/mdtech_app na troca); o código é público no GitHub, então fica legível
tar -C servidor -czf - --exclude=__pycache__ mdtech_conta admin.py backup.py \
  | "${SSH[@]}" "$ALVO" "mkdir -p mdtech_deploy/app-$ID && tar -C mdtech_deploy/app-$ID -xzf -"

if [ "$SIMULAR" = "1" ]; then
  remoto ativar "$ID" "$DEPLOY_PATH" simular
  exit 0
fi

# 4) preços do login (dados, ficam fora da troca de versão) e troca
"${SSH[@]}" "$ALVO" "cat > $DADOS/precos.json.novo && chmod 660 $DADOS/precos.json.novo && mv -f $DADOS/precos.json.novo $DADOS/precos.json" < saida/app_dados/precos.json
remoto ativar "$ID" "$DEPLOY_PATH"

# 5) conferência no ar; se falhar, volta sozinho para a versão anterior
motivo="$(conferir)"
if [ -n "$motivo" ]; then
  echo "ALERTA: $motivo."
  echo "Voltando para a versão anterior..."
  if remoto voltar "$DEPLOY_PATH"; then
    motivo2="$(conferir)"
    if [ -n "$motivo2" ]; then echo "ALERTA: mesmo na versão anterior, $motivo2. Me mande esta saída."; else echo "A versão anterior está no ar e conferida."; fi
  else
    echo "ERRO ao voltar. Rode: bash deploy/deploy.sh --voltar"
  fi
  exit 1
fi
echo "OK: clientes sem preço em $SITE_URL · /interno pede login (401) · login novo em $SITE_URL/entrar.html (preços só com sessão)."
echo "Se algo estiver errado no site, volte com: bash deploy/deploy.sh --voltar"
