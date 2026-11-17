#!/usr/bin/env bash
# Parte do deploy que roda NO SERVIDOR. O deploy.sh envia este arquivo por SSH (bash -s -- <comando> ...); não precisa ficar no servidor.
#
# Troca de versão "atômica": a versão nova chega inteira numa pasta ao lado (~/mdtech_deploy/site-<id> e app-<id>) e só então
# entra no lugar da atual com dois `mv` (frações de segundo, nunca um site pela metade). A anterior fica guardada para voltar.
#   ativar  <id> <pasta_publica> [simular]   troca pela versão <id> já enviada (com "simular", só mostra o que faria e descarta)
#   voltar  <pasta_publica>                  volta para a versão guardada mais recente (rodar de novo volta mais uma)
#
# O que existe na pasta pública e o deploy não gera (o .htaccess da raiz criado à mão, .well-known do certificado, etc.)
# é copiado para a versão nova antes da troca. O que o deploy gera é substituído por inteiro: arquivo velho não fica para trás.
set -euo pipefail

BASE="$HOME/mdtech_deploy"
APP="$HOME/mdtech_app"
GUARDAR=2                       # versões anteriores guardadas para o rollback (cada uma ocupa o tamanho do site)

erro() { echo "ERRO: $*" >&2; exit 1; }

caminho_publico() {             # aceita caminho absoluto ou relativo à pasta do usuário; tira a barra do fim
  local p="${1%/}"
  case "$p" in /*) ;; *) p="$HOME/$p" ;; esac
  printf '%s' "$p"
}

# Copia para <novo> o que existe em <atual> e não veio no envio (menos __pycache__). Com "listar", só mostra.
preservar() {
  local atual="$1" novo="$2" modo="${3:-}" item nome
  while IFS= read -r -d '' item; do
    nome="${item##*/}"
    [ "$nome" = "__pycache__" ] && continue
    if [ ! -e "$novo/$nome" ] && [ ! -L "$novo/$nome" ]; then
      echo "  mantido (não é gerado pelo deploy): $nome"
      [ "$modo" = "listar" ] || cp -a "$item" "$novo/$nome"
    fi
  done < <(find "$atual" -mindepth 1 -maxdepth 1 -print0)
}

# A pasta nova herda dono do grupo, permissões e ACL da atual (senão o Apache pode ficar sem acesso: erro 403).
copiar_permissoes() {
  local ref="$1" alvo="$2"
  chmod --reference="$ref" "$alvo"
  chgrp --reference="$ref" "$alvo" 2>/dev/null \
    || erro "não consegui dar a $alvo o mesmo grupo de $ref ($(stat -c %G "$ref")). Nada foi trocado."
  if command -v getfacl >/dev/null 2>&1 && [ -n "$(getfacl -p --skip-base "$ref" 2>/dev/null)" ]; then
    getfacl -p "$ref" 2>/dev/null | setfacl --set-file=- "$alvo" \
      || erro "não consegui copiar a ACL de $ref para $alvo. Nada foi trocado."
  fi
}

# Põe <novo> no lugar de <atual>, guardando <atual> em <guardado>. Se o 2º mv falhar, desfaz o 1º.
trocar() {
  local atual="$1" novo="$2" guardado="$3"
  [ -L "$atual" ] && erro "$atual é um link simbólico; a troca automática não foi preparada para isso. Nada foi trocado."
  mv "$atual" "$guardado" || erro "não consegui mover $atual (é do seu usuário?). Nada foi trocado."
  if ! mv "$novo" "$atual"; then
    mv "$guardado" "$atual"
    erro "não consegui pôr a versão nova no lugar; a anterior foi mantida."
  fi
}

limpar_antigos() {
  local tipo
  for tipo in site-anterior app-anterior site-desfeito app-desfeito; do
    find "$BASE" -mindepth 1 -maxdepth 1 -type d -name "$tipo-*" -print0 | sort -z | head -z -n "-$GUARDAR" | xargs -0 -r rm -rf
  done
  # envios que nunca foram ativados (ex.: a conexão caiu no meio)
  find "$BASE" -mindepth 1 -maxdepth 1 -type d \( -name 'site-[0-9]*' -o -name 'app-[0-9]*' \) -print0 | xargs -0 -r rm -rf
}

ativar() {
  local id="$1" pub; pub="$(caminho_publico "$2")"; local simular="${3:-}"
  local novo_site="$BASE/site-$id" novo_app="$BASE/app-$id"
  [ -d "$novo_site" ] || erro "a versão $id não foi enviada ($novo_site não existe)."
  [ -d "$novo_app" ] || erro "o app da versão $id não foi enviado ($novo_app não existe)."
  [ -d "$pub" ] || erro "a pasta pública $pub não existe."
  [ -L "$pub" ] && erro "$pub é um link simbólico; a troca automática não foi preparada para isso. Nada foi trocado."
  [ -f "$novo_site/index.html" ] || erro "a versão $id não tem index.html: envio incompleto. Nada foi trocado."

  [ -f "$novo_site/conta.py" ] && chmod 755 "$novo_site/conta.py"     # CGI: precisa ser executável
  chmod -R a+rX "$novo_app"

  echo "Pasta pública: $pub (grupo $(stat -c %G "$pub"), permissões $(stat -c %a "$pub"))"
  if [ -n "$simular" ]; then
    preservar "$pub" "$novo_site" listar
    [ -d "$APP" ] && preservar "$APP" "$novo_app" listar
  else
    preservar "$pub" "$novo_site"
    [ -d "$APP" ] && preservar "$APP" "$novo_app"
  fi
  copiar_permissoes "$pub" "$novo_site"
  [ -d "$APP" ] && copiar_permissoes "$APP" "$novo_app"
  echo "Espaço livre: $(df -h "$HOME" | awk 'NR==2 {print $4 " de " $2}') · versão nova: $(du -sh "$novo_site" | cut -f1)"

  if [ -n "$simular" ]; then
    rm -rf "$novo_site" "$novo_app"
    echo "SIMULAÇÃO: tudo pronto para a troca, mas nada foi trocado (a versão enviada foi apagada)."
    return 0
  fi

  trocar "$pub" "$novo_site" "$BASE/site-anterior-$id"
  if [ -d "$APP" ]; then
    if ! trocar "$APP" "$novo_app" "$BASE/app-anterior-$id"; then
      mv "$pub" "$BASE/site-falhou-$id" && mv "$BASE/site-anterior-$id" "$pub"
      erro "o app não foi trocado; o site voltou para a versão anterior."
    fi
  else
    mv "$novo_app" "$APP"
  fi
  limpar_antigos
  echo "Versão $id no ar. Versões anteriores guardadas para voltar: $(find "$BASE" -mindepth 1 -maxdepth 1 -name 'site-anterior-*' | wc -l)."
}

voltar() {
  local pub; pub="$(caminho_publico "$1")"
  local anterior id agora
  anterior="$(find "$BASE" -mindepth 1 -maxdepth 1 -type d -name 'site-anterior-*' 2>/dev/null | sort | tail -n 1)"
  [ -n "$anterior" ] || erro "não há versão anterior guardada em $BASE."
  id="${anterior##*site-anterior-}"
  agora="$(date +%Y%m%d-%H%M%S)"
  trocar "$pub" "$anterior" "$BASE/site-desfeito-$agora"
  if [ -d "$BASE/app-anterior-$id" ] && [ -d "$APP" ]; then
    trocar "$APP" "$BASE/app-anterior-$id" "$BASE/app-desfeito-$agora"
  fi
  echo "Voltou para a versão que estava no ar antes do deploy $id. A que saiu ficou guardada em $BASE/site-desfeito-$agora."
}

mkdir -p "$BASE"
chmod 700 "$BASE"
case "${1:-}" in
  ativar) shift; ativar "$@" ;;
  voltar) shift; voltar "$@" ;;
  *) erro "uso: remoto.sh ativar <id> <pasta_publica> [simular] | voltar <pasta_publica>" ;;
esac
