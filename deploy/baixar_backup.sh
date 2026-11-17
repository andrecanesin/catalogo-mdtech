#!/usr/bin/env bash
# Baixa as cópias do banco do login (backup diário do servidor) para uma pasta daqui: a cópia FORA do servidor.
#   bash deploy/baixar_backup.sh                 baixa para ~/backups_mdtech_servidor
#   bash deploy/baixar_backup.sh /outra/pasta
# Guarde a pasta fora do repositório (tem e-mails e hashes de senha dos vendedores). Rodar de vez em quando (ex.: toda semana).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "Falta deploy/.env (copie deploy/env.exemplo e preencha)."; exit 1; }
set -a; . deploy/.env; set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}"
DESTINO="${1:-$HOME/backups_mdtech_servidor}"
mkdir -p "$DESTINO"
chmod 700 "$DESTINO"
scp -P "${DEPLOY_PORT:-22}" "$DEPLOY_USER@$DEPLOY_HOST:backups_mdtech/usuarios-*.sqlite" "$DESTINO/"
echo "OK: $(ls "$DESTINO" | wc -l) cópia(s) em $DESTINO (a mais recente: $(ls "$DESTINO" | sort | tail -n 1))"
