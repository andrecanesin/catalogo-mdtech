#!/usr/bin/env bash
# Deploy por SSH/rsync (rodar na máquina do André, não no Actions: o build interno usa os preços reais, que ficam fora do git).
#   deploy/deploy.sh               gera tudo (fichas, catálogos, propostas, site) e envia
#   deploy/deploy.sh --so-enviar   reaproveita o que já está em saida/servidor
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "Falta deploy/.env (copie deploy/env.exemplo e preencha)."; exit 1; }
set -a; . deploy/.env; set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}" "${DEPLOY_PATH:?}" "${SITE_URL:?}"
PORTA="${DEPLOY_PORT:-22}"
ALVO="$DEPLOY_USER@$DEPLOY_HOST"
SSH=(ssh -p "$PORTA")

if [ "${1:-}" != "--so-enviar" ]; then
  python gerar.py fichas --separados
  python gerar.py catalogo --todos --perfil digital
  python gerar.py kits
  python gerar.py site --interno
fi
[ -f saida/servidor/interno/produtos.json ] || { echo "saida/servidor/interno não existe: rode sem --so-enviar."; exit 1; }

# 1) logins: /interno NUNCA vai ao ar sem senha (lá estão os preços)
HOME_REMOTO="$("${SSH[@]}" "$ALVO" 'echo $HOME')"
HTPASSWD_REMOTO="$HOME_REMOTO/.htpasswd_mdtech"      # fora da pasta pública
if [ -f deploy/.htpasswd ]; then
  rsync -e "ssh -p $PORTA" --chmod=F640 deploy/.htpasswd "$ALVO:$HTPASSWD_REMOTO"
elif ! "${SSH[@]}" "$ALVO" "test -s '$HTPASSWD_REMOTO'"; then
  echo "ERRO: não há logins. Rode: python deploy/logins.py"; exit 1
fi
sed "s|__HTPASSWD__|$HTPASSWD_REMOTO|" deploy/htaccess_interno > saida/servidor/interno/.htaccess

# 2) envio (sem --delete por padrão: DEPLOY_DELETE=1 apaga no servidor o que não existe mais aqui)
EXTRA=(); [ "${DEPLOY_DELETE:-0}" = "1" ] && EXTRA=(--delete)
rsync -az --info=stats1 "${EXTRA[@]}" -e "ssh -p $PORTA" saida/servidor/ "$ALVO:$DEPLOY_PATH/"

# 3) conferência no ar
cod="$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/interno/produtos.json")"
if [ "$cod" != "401" ]; then
  echo "ALERTA: /interno/produtos.json respondeu $cod (esperado 401). Apague $DEPLOY_PATH/interno no servidor AGORA e confira o Apache (AllowOverride AuthConfig)."
  exit 1
fi
if curl -s "$SITE_URL/produtos.json" | grep -Eq '"preco": [0-9]'; then
  echo "ALERTA: o site de clientes tem preço no produtos.json!"; exit 1
fi
echo "OK: clientes sem preço em $SITE_URL · /interno pede login (401)."
