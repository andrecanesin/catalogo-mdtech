#!/usr/bin/env bash
# Deploy por SSH/rsync (rodar na máquina do André, não no Actions: o build interno usa os preços reais, que ficam fora do git).
#   deploy/deploy.sh               gera tudo (fichas, catálogos, propostas, site) e envia
#   deploy/deploy.sh --so-enviar   reaproveita o que já está em saida/servidor
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "Falta deploy/.env (copie deploy/env.exemplo e preencha)."; exit 1; }
set -a; . deploy/.env; set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}" "${DEPLOY_PATH:?}" "${SITE_URL:?}"

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
  "${SSH[@]}" "$ALVO" "cat > '$HTPASSWD_REMOTO' && chmod 640 '$HTPASSWD_REMOTO'" < deploy/.htpasswd
elif ! "${SSH[@]}" "$ALVO" "test -s '$HTPASSWD_REMOTO'"; then
  echo "ERRO: não há logins. Rode: python deploy/logins.py"; exit 1
fi
sed "s|__HTPASSWD__|$HTPASSWD_REMOTO|" deploy/htaccess_interno > saida/servidor/interno/.htaccess

# 2) envio. Com rsync (Linux/Mac): sem --delete por padrão (DEPLOY_DELETE=1 apaga no servidor o que não existe mais aqui).
#    Sem rsync (Git Bash do Windows): tar compactado por SSH, que sobrescreve os arquivos e não apaga nada.
if command -v rsync >/dev/null 2>&1; then
  EXTRA=(); [ "${DEPLOY_DELETE:-0}" = "1" ] && EXTRA=(--delete)
  rsync -az --info=stats1 "${EXTRA[@]}" -e "ssh -p $PORTA" saida/servidor/ "$ALVO:$DEPLOY_PATH/"
else
  echo "rsync não encontrado: enviando com tar por SSH (sobrescreve, não apaga)."
  tar -C saida/servidor -czf - . | "${SSH[@]}" "$ALVO" "mkdir -p '$DEPLOY_PATH' && tar -C '$DEPLOY_PATH' -xzf -"
fi

# 2b) login dos vendedores (app em servidor/): código em ~/mdtech_app e dados em /var/lib/mdtech, FORA da pasta pública;
#     na pasta pública só a porta de entrada conta.py. Preços para o app: saida/app_dados/precos.json (gerado por 'gerar.py site --interno').
[ -f saida/app_dados/precos.json ] || { echo "Falta saida/app_dados/precos.json: rode sem --so-enviar."; exit 1; }
#     O Apache roda o CGI como www-data e com ProtectHome=read-only (lê /home, não grava): os dados ficam em /var/lib/mdtech,
#     criada uma vez com sudo (www-data:catalogo_mdtech, 2770; ver servidor/LEIA-ME.md). O código (público no GitHub) fica legível.
DADOS=/var/lib/mdtech
"${SSH[@]}" "$ALVO" "test -w $DADOS" || { echo "ERRO: $DADOS não existe ou não é gravável. Crie uma vez (servidor/LEIA-ME.md, 'Instalação'); o login novo não foi atualizado."; exit 1; }
tar -C servidor -czf - --exclude=__pycache__ mdtech_conta admin.py backup.py \
  | "${SSH[@]}" "$ALVO" "mkdir -p ~/mdtech_app && tar -C ~/mdtech_app -xzf - && chmod -R a+rX ~/mdtech_app"
"${SSH[@]}" "$ALVO" "cat > $DADOS/precos.json.novo && chmod 660 $DADOS/precos.json.novo && mv -f $DADOS/precos.json.novo $DADOS/precos.json" < saida/app_dados/precos.json
# tr -d '\r': no Windows o git pode trazer o arquivo com CRLF, e aí a 1ª linha (#!/usr/bin/python3) quebra o CGI (erro 500)
tr -d '\r' < servidor/conta.py | "${SSH[@]}" "$ALVO" "cat > '$DEPLOY_PATH/conta.py' && chmod 755 '$DEPLOY_PATH/conta.py'"

# 3) conferência no ar
cod="$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/interno/produtos.json")"
if [ "$cod" != "401" ]; then
  echo "ALERTA: /interno/produtos.json respondeu $cod (esperado 401). Apague $DEPLOY_PATH/interno no servidor AGORA e confira o Apache (AllowOverride AuthConfig)."
  exit 1
fi
if curl -s "$SITE_URL/produtos.json" | grep -Eq '"preco": [0-9]'; then
  echo "ALERTA: o site de clientes tem preço no produtos.json!"; exit 1
fi
cod="$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/conta.py/precos")"
if [ "$cod" != "401" ]; then
  echo "ALERTA: /conta.py/precos respondeu $cod (esperado 401). O login novo não está funcionando; o /interno antigo segue no ar."
  echo "Diagnóstico (usuário que roda o CGI):"
  printf '#!/usr/bin/python3\nimport os, pwd\nprint("Content-Type: text/plain")\nprint()\nprint("CGI roda como:", pwd.getpwuid(os.geteuid()).pw_name)\n' \
    | "${SSH[@]}" "$ALVO" "cat > '$DEPLOY_PATH/diag_cgi.py' && chmod 755 '$DEPLOY_PATH/diag_cgi.py'"
  curl -s "$SITE_URL/diag_cgi.py"; echo
  "${SSH[@]}" "$ALVO" "rm -f '$DEPLOY_PATH/diag_cgi.py'; echo 'dono dos arquivos:' \$(whoami); ls -la /var/lib/mdtech"
  exit 1
fi
# gravação: login com e-mail inexistente grava a tentativa errada no banco -> 401 (500 = o CGI não consegue gravar em /var/lib/mdtech)
cod="$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"email":"teste-deploy@invalido.local","senha":"x"}' "$SITE_URL/conta.py/entrar")"
if [ "$cod" != "401" ]; then
  echo "ALERTA: login de teste respondeu $cod (esperado 401): o app lê, mas não grava. Veja: sudo tail /var/log/apache2/catalogo.mdtechsm.com.br-error.log"
  exit 1
fi
echo "OK: clientes sem preço em $SITE_URL · /interno pede login (401) · login novo em $SITE_URL/entrar.html (preços só com sessão)."
