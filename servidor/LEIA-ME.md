# Login dos vendedores (Fase 1)

App Python **só com a biblioteca padrão** (padrão WSGI). Hoje roda por CGI no Apache; quando houver mod_wsgi ou proxy, serve-se
`mdtech_conta.app.app_do_servidor(HOME)` sem reescrever nada.

| No servidor | O quê |
|---|---|
| `~/public_html/conta.py` | porta de entrada CGI (único arquivo do app na pasta pública) |
| `~/mdtech_app/` | código (`mdtech_conta/`, `admin.py`) |
| `/var/lib/mdtech/usuarios.sqlite` | vendedores (senha só como hash scrypt), sessões e tentativas erradas |
| `/var/lib/mdtech/precos.json` | preços reais (de `dados/precos_reais.xlsx`), entregues só a quem tem sessão |

Tudo vai pelo `bash deploy/deploy.sh`.

**Permissões:** o Apache roda o CGI como `www-data` e com `ProtectHome=read-only` (o CGI lê `/home`, mas não grava). Por isso os dados ficam
em `/var/lib/mdtech` (`www-data:catalogo_mdtech`, modo `2770`: só o Apache e o dono da conta entram; o setgid mantém os arquivos novos no grupo).
`~/mdtech_app` é legível por todos (o código já é público no GitHub).

## Instalação (uma vez, com sudo)
```bash
ssh -t catalogo_mdtech@173.214.164.179 'sudo install -d -o www-data -g catalogo_mdtech -m 2770 /var/lib/mdtech && ls -ld /var/lib/mdtech'
```
Para desfazer: `sudo rm -rf /var/lib/mdtech` (apaga vendedores e sessões). Incluir `/var/lib/mdtech` no backup do servidor.

## Backup diário do banco (uma vez)
O `deploy.sh` envia o `backup.py`. Testar uma vez e agendar no cron do usuário (`crontab -e`, sem sudo):
```bash
ssh catalogo_mdtech@173.214.164.179 'python3 ~/mdtech_app/backup.py && ls -l ~/backups_mdtech'
```
Linha do cron (todo dia às 3h10; guarda as 14 últimas cópias em `~/backups_mdtech`):
```
10 3 * * * /usr/bin/python3 $HOME/mdtech_app/backup.py >> $HOME/backups_mdtech/backup.log 2>&1
```
Copiar para fora do servidor (na máquina do André, quando quiser): `scp catalogo_mdtech@173.214.164.179:backups_mdtech/usuarios-*.sqlite pasta-segura/`.
Para restaurar: parar de usar o site, copiar a cópia desejada sobre `/var/lib/mdtech/usuarios.sqlite` (dono `www-data:catalogo_mdtech`, modo 660).

## Gestão pela tela (dia a dia)
`vendedores.html` (menu da conta → "Gerenciar vendedores"), só para administradores: adicionar, **Enviar convite** (1º acesso) ou
**Enviar link de nova senha** (esqueceu), desativar/reativar, desbloquear, tornar administrador, nome e histórico de quem fez o quê.
**Sem senha na tela:** o convite é um link `entrar.html#convite=CÓDIGO`, de **uso único e válido por 7 dias** (gerar outro cancela o anterior),
enviado por WhatsApp ou e-mail com a mensagem pronta. O vendedor toca, cria a senha e já entra. O código vai depois do `#`: não chega aos logs
nem à pré-visualização do WhatsApp, e a página o tira da barra de endereço. No banco só fica o hash. A senha atual vale até o link ser usado.
O 1º administrador é feito pelo terminal: `admin.py tornar-admin email` (e `admin.py convite email` imprime um link, para emergências).

## Pelo terminal (1º administrador e emergências)
```bash
ssh catalogo_mdtech@173.214.164.179 python3 mdtech_app/admin.py adicionar fulano@empresa.com.br
```
A senha inicial aparece **uma única vez**: envie ao vendedor. No 1º acesso, `entrar.html` obriga a trocar por uma senha dele (mínimo de 10 caracteres).
Outros comandos: `redefinir` (esqueceu a senha: gera nova senha inicial e desconecta os aparelhos), `desativar` (saiu da empresa),
`reativar`, `desbloquear` (zera as tentativas erradas) e `listar`.

## Regras de segurança
- Sessão por cookie `HttpOnly` + `Secure` + `SameSite=Lax`, válida por 30 dias. O token fica no banco só como hash (SHA-256).
- Erros de senha geram espera progressiva (5 s, 10 s, 20 s… até 15 min): a partir do 3º erro do mesmo e-mail **no mesmo IP**, e do 10º erro do e-mail somando
  todos os IPs. 30 erros de um IP em 15 minutos bloqueiam o IP. Assim ninguém de fora trava o vendedor em outro aparelho.
- Trocar a senha desconecta os outros aparelhos. Sem a troca da senha inicial, nada de preço.
- Todo POST exige JSON e origem igual ao site (proteção contra CSRF). Erros nunca mostram detalhes ao navegador.
- Cookie `mdtech_vendedor=1` (sem segredo): só serve para o site de clientes não chamar o CGI à toa.

## Endereços
`GET /conta.py/eu` · `POST /conta.py/entrar` · `POST /conta.py/trocar-senha` · `POST /conta.py/sair` · `GET /conta.py/precos`

## Testar na sua máquina
```bash
python -m unittest discover -s servidor/testes
```
```bash
python servidor/dev.py adicionar teste@mdtech.com.br
```
```bash
python servidor/dev.py
```
Depois abra `http://127.0.0.1:8900/entrar.html` (precisa de `python gerar.py site` antes; os dados de teste ficam em `saida/dev_conta/`).
