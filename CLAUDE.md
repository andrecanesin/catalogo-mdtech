# MDTech — catálogo e materiais

> Lido automaticamente pelo Claude Code. Para decisões históricas, ver `DOCUMENTACAO_PROJETO.md`.
> Skill de UI/UX do projeto: `.claude/skills/mdtech-ui-ux/`.

## O que é
Marca própria MDTech, com produtos de 3 fornecedores (TONGLU = Laparoscopia, TIAN SONG = Urologia/Histeroscopia,
ASAP = óticas HD-4K, que ficam dentro das especialidades). Uma planilha (`dados/Base_MDTech_Consolidada.xlsx`) é a **fonte única da verdade** e
alimenta, via `gerar.py`: catálogos PDF, fichas técnicas PDF e o catálogo digital (site estático no GitHub Pages).

## Um repositório só
Tudo mora neste repositório (`andrecanesin/catalogo-mdtech`, público). O `site/` é uma pasta comum, não é mais repo separado.
```
dados/        planilha-base            assets/       imagens (por fornecedor), logos, fontes, ícones
mdtech/       núcleo Python            geradores/    catalogo, fichas, card, dashboard, site
site/         HTML/CSS/JS escritos à mão (+ arquivos gerados, ignorados no git)
.github/workflows/publicar.yml         publica no Pages a cada push na main
```
Os arquivos gerados (`site/produtos.json`, `meta.json`, `fotos/`, `fichas/`, `catalogos/`) estão no `.gitignore`;
o GitHub Actions os recria a cada publicação.

## Como publicar
1. Editar a planilha e/ou o HTML/CSS/JS do `site/`.
2. (Opcional) conferir local: `python gerar.py fichas --separados && python gerar.py site`, depois `python -m http.server` dentro de `site/`.
3. PR → ok → merge na `main`. O workflow **Publicar site** roda sozinho (aba Actions) e atualiza a **homologação** (Pages) em ~minutos.
4. Com o ok do André para a produção: `bash deploy/deploy.sh` na máquina dele (ver "Ambientes e nomes").
- Catálogos **digitais** (foto reduzida, ~6 MB no total) são gerados pelo Actions e vão junto com o site. Catálogos **impressos** (foto original)
  são só locais (`saida/impresso/`) e nunca passam pelo Actions nem pelo git (ver `site/PRODUCAO.md`).

## Ambientes e nomes (combinado em 16/11)
| Nome | Onde | Para quê |
|---|---|---|
| **Desenvolvimento** (local) | máquina do André ou sessão do Claude | alterar e testar |
| **PR** | GitHub | proposta de mudança; o André revisa e dá o "ok" |
| **Merge** | GitHub (`main`) | o "ok" aplicado: entra na versão oficial do código |
| **Homologação** | GitHub Pages (`andrecanesin.github.io/catalogo-mdtech`) | conferência e aprovação antes de subir; atualiza sozinha a cada merge |
| **Produção** ("no ar") | `catalogo.mdtechsm.com.br` | o que clientes e vendedores usam |
| **Deploy** ("subir para produção") | `bash deploy/deploy.sh`, só na máquina do André | leva a `main` para a produção |
| **Rollback** | | voltar à versão anterior se algo der errado |

Fluxo: alteração → **PR** → ok → **merge** → **homologação** (Actions, ~2 min) → André confere → **"ok para produção"** → **deploy** → **produção**.
- Usar "em homologação" e "em produção", nunca "publicado" (ambíguo).
- O deploy só acontece depois do ok explícito do André para a produção; é ele quem roda o comando (a sessão não alcança o SSH).
- **Login e preços não passam pela homologação:** o Pages é estático e público (não executa o app e nunca tem preço real). Eles estreiam em
  produção de forma **controlada**: só o André tem conta até aprovar, o `/interno` antigo segue no ar e só então os vendedores são cadastrados.
  Uma homologação dentro do servidor (ex.: `/homologacao/` com banco separado) fica para quando a intranet (Fase 2) crescer.

## Fluxo por tipo de alteração
| Alteração | Quem faz / valida | Publicação |
|---|---|---|
| Site (HTML/CSS/JS, `config.js`) | Claude edita e testa no navegador (Playwright) | PR → ok do André → merge → Actions (~1 min, fichas em cache) |
| Planilha (dados) | Claude edita só as células pedidas e confere o diff célula a célula | PR → ok → merge → Actions refaz as fichas (~2,5 min) |
| Layout das fichas ou do catálogo | Claude ajusta e confere o preview HTML (`--preview`) | PR → ok → merge → Actions refaz as fichas |
| Fotos novas (`assets/imagens/`) | André coloca os arquivos (nome = código) | commit/PR → Actions refaz fotos e fichas |
| Catálogos digitais (PDF) | Gerados com foto reduzida; completo com capa, por linha só miolo + índice | Actions, junto com o site (+25 s); nunca no git |
| Propostas básicas (kits) | Claude monta a aba KITS a partir da lista do André e confere código a código na base | Actions gera o PDF e o site lista no menu "Catálogos e propostas" (cada kit novo aparece sozinho) |
| Catálogos e propostas impressos | André gera na máquina (painel): foto ORIGINAL, paridade, `saida/impresso/`; sempre liberado (testes), com aviso do que falta de ANVISA/NCM | só local: nunca site, Actions nem git |
| Código Python (`mdtech/`, `geradores/`) | Claude altera e testa localmente | PR → ok → merge |
O Actions guarda as fichas em cache; a chave muda com planilha, `geradores/fichas.py`, `gerar.py`, `mdtech/*.py`, `assets/` e
`requirements.txt`. Para forçar a regeneração: Actions → Publicar site → Run workflow → marcar "Ignorar o cache".

## Comandos
```bash
python gerar.py tudo                  # checklist + dashboard + catálogos + fichas (local)
python gerar.py fichas --separados    # antes de 'site', para o botão de download aparecer
python gerar.py site                  # produtos.json + fotos + fichas -> site/
python gerar.py dashboard             # painel de pendências (inclui status das fotos)
python gerar.py catalogo Laparoscopia --preview   # preview HTML sem gerar PDF
python gerar.py catalogo --todos --perfil impressao --paridade par   # impresso (local, foto original, saida/impresso/)
python gerar.py kits --kit "Hérnia de Hiato"   # proposta básica (kit) em PDF -> saida/propostas/
python gerar.py kits --perfil impressao --paridade par   # propostas impressas (local, foto original, páginas casadas)
python painel.py                      # painel local do marketing (127.0.0.1:8800): o que falta de informação (ANVISA, NCM, foto) + impresso
```
Todas as flags: `LEIA-ME.md`.

## Regras de ouro
1. A base é a única fonte da verdade (ANVISA/NCM/specs só nela).
2. Nomes de coluna só em `mdtech/base.py` (`COLUNAS`); todo gerador lê via `mdtech.base.carregar()`.
3. Cor por especialidade em `mdtech/marca.py::ACCENT`; `site/js/config.js` é espelho manual (`accentTexto` = variante escura só para texto no site).
4. Diâmetro sempre via `mdtech.textos.diametro_fmt(item)` (mm vs Fr).
5. Foto = arquivo nomeado pelo código em `assets/imagens/<FORNECEDOR>/` (matcher tolerante, `mdtech/fotos.py`).
6. Não editar arquivos gerados à mão. Não commitar PDF grande (GitHub bloqueia > 100 MB).

## Modelo por tipo de tarefa
O padrão do projeto é **Sonnet 5.5 com esforço médio**. Antes de começar uma tarefa, avisar o André se ela
exigir outro modelo, dizendo qual e por quê.
- **Subir para Opus 5.5:** refatoração grande de `mdtech/` ou `geradores/`; redesenho do layout do catálogo ou
  do site; auditoria completa de código; depuração que não resolveu em duas tentativas.
- **Descer para Haiku 5.5:** tarefas repetitivas e simples (renomear, formatar, conferir listas).
- **Todo o resto:** seguir no Sonnet 5.5, sem avisar.

## Como trabalhamos (combinado com o André)
- Na branch designada da sessão: validar, commitar e fazer push normal **sem pedir aprovação a cada vez**; abrir o PR e mostrar
  o `git diff --stat` no relatório. **Nunca force-push** (só se o André autorizar a branch específica).
- **Merge e publicação:** o Claude só faz o merge de um PR depois do **"ok" explícito do André para aquele PR** (o ok vale
  para um PR, não é permanente). Antes: conferir que está aberto, sem conflito e no mesmo commit informado (`expectedHeadSha`);
  usar merge commit (`merge`), como nos PRs anteriores. Depois: **não disparar o workflow à mão** (o push na `main` já dispara o
  **Publicar site**, e um disparo manual cancela o automático por causa do `concurrency`); acompanhar a execução até terminar e
  informar verde/vermelho. Se ficar vermelho, ler o log do passo com erro e propor a correção em PR novo. O site publicado
  não é acessível a partir da sessão: a conferência visual do site no ar é do André.
- **Relatórios curtos e focados no resultado do projeto** (o que ficou pronto, o que o André precisa fazer, decisões pendentes).
  Detalhes de PR, merge e Actions só quando algo falhar ou exigir ação do André. Verde sem novidade = uma linha ou nada.
- Perguntar só o que for decisão do André (dados, marca, escopo, preços). Não repetir pergunta sem resposta, nem cobrá-la.
- O aviso "há alterações não commitadas" do hook de parada é automático: não é cobrança do André nem aprovação. Mesmo assim,
  nunca deixar trabalho validado sem commit ao fim de uma entrega.
- Nada sensível (contatos de fornecedores, preços internos) em repositório público.

## Impresso: plano para retomar (decidido em 09/11; o foco agora é o digital)
Hoje o painel gera o **nível A**: miolo de catálogos e propostas com foto ORIGINAL e páginas casadas (par/ímpar/caderno), em RGB e sem
sangria; capa, sangria, marcas de corte e CMYK são feitos no InDesign. Quando o André retomar o impresso:
- **Nível B (recomendado primeiro):** miolo pronto para a gráfica: sangria de 3 mm, marcas de corte, CMYK em PDF/X (Ghostscript + perfil
  ICC), páginas casadas e **relatório de resolução** das fotos (lista as abaixo de 300 dpi). Capa e contracapa seguem no InDesign.
- **Nível C:** arquivo único fechado: capa + miolo + contracapa em PDF/X, com lombada calculada, a partir das capas de impressão
  (com sangria) que o André fornecer em `assets/capas/`.
- **Página extra:** em vez de página em branco para casar a paridade, usar o PDF de conteúdo que o André colocar (ex.: `assets/impresso/pagina_extra.pdf`);
  sem o arquivo, segue em branco.
- **Falta definir (perguntar ao André):** ficha técnica de arquivo da gráfica (sangria, perfil ICC como FOGRA39, versão do PDF/X);
  encadernação (grampo, cola ou espiral: define lombada e paridade); se as capas já existem na versão de impressão.
- **Limitações:** a conversão para CMYK desloca um pouco as cores (o azul MDTech); pedir prova à gráfica antes da tiragem. As fotos da
  Tian Song (Urologia/Histeroscopia) são recortes de catálogo em PDF e têm baixa resolução; a fábrica não tem as originais (decidido: seguir
  assim por enquanto).
- Ao implementar, registrar as regras numa skill do projeto (`.claude/skills/mdtech-impresso/`) para os próximos trabalhos seguirem igual.

## Duas versões do site (decidido em 16/11)
- **Clientes** (raiz do domínio, aberto): `produtos.json` sem preço; o front esconde preço, total e aviso sozinho. É o que o Actions gera.
- **Interno** (`/interno`, 1 login por vendedor, Apache): igual, mas com o preço de `dados/precos_reais.xlsx`. Só se gera na máquina do André:
  `python gerar.py site --interno` → `saida/servidor/` (raiz = clientes, `interno/` = vendedores). O build interno recusa rodar com `SITE_PUBLICO=1`.
## Servidor (no ar desde 16/11)
- `https://catalogo.mdtechsm.com.br/` = clientes (aberto, sem preço); `/interno/` = vendedores (com preço). Apache 2.4 (Ubuntu), usuário `catalogo_mdtech`,
  pasta `~/public_html`, acesso por **chave SSH** (nunca senha no repositório nem no chat). A sessão na nuvem não alcança o SSH (só HTTPS): o deploy roda na máquina do André.
- Deploy: `bash deploy/deploy.sh` (ver `deploy/LEIA-ME.md`). Envia com `tar` por SSH para `~/mdtech_deploy` e troca a versão de uma vez (`deploy/remoto.sh`): arquivo velho sai, o que não é gerado
  (`.htaccess` da raiz, `.well-known`) é mantido, e se a conferência falhar volta sozinho. Rollback: `bash deploy/deploy.sh --voltar`; teste: `--simular` (17/11).
  Ele gera fichas, catálogos, propostas e `python gerar.py site --interno`, e no fim confere que `/interno` responde 401 e que a raiz não tem preço.
  O Actions só publica a versão de clientes no GitHub Pages (sem preço); o `/interno` só existe no servidor.
- Particularidades do servidor: `.htaccess` não aceita `Options` nem `Header` (dá erro 500), então o do `/interno` só tem diretivas de autenticação. A raiz tem um
  `.htaccess` com `DirectoryIndex index.html`, criado à mão (o deploy não o recria; sem ele o Apache lista as pastas). O `index.py` antigo, que só embutia o Pages num
  iframe, foi removido (cópia em `~/backup_antigo` no servidor).
- **O CGI roda como `www-data`** e o serviço do Apache tem `ProtectHome=read-only` e `ProtectSystem=full` (o CGI lê `/home`, mas não grava): os dados do
  login ficam em **`/var/lib/mdtech`** (`www-data:catalogo_mdtech`, `2770`, criada com sudo em 16/11; incluir no backup). O código fica em `~/mdtech_app` (legível).
  Logs de erro do site: `/var/log/apache2/catalogo.mdtechsm.com.br-error.log` (precisa de sudo).
- **Quebra de linha:** `.py` e `.sh` sempre LF (`.gitattributes`); com CRLF (checkout do Windows) a 1ª linha do `conta.py` quebra o CGI (erro 500).
  O `deploy.sh` também remove o `\r` ao enviar o `conta.py`. O log do Apache em 16/11 mostra **mod_python 3.5 com Python 3.14** carregado: opção a avaliar na
  Fase 2 para servir o app WSGI sem CGI (alternativa ao mod_wsgi).
- **`sudo` liberado em 16/11** (`(ALL : ALL) ALL`). Regras: **nunca mexer em `/root`** (o administrador configura o sistema dele lá); fora de
  `/home/catalogo_mdtech`, só com o ok do André e explicando antes o que o comando faz e como desfazer; nunca reiniciar o servidor (é do administrador). A senha do `sudo` só no terminal do André (`ssh -t`).
- **Bancos:** PostgreSQL já instalado pelo administrador; **Fase 1 segue em SQLite** e migra para o PostgreSQL no início da Fase 2, com usuário e banco
  próprios (`mdtech`), de preferência com autenticação "peer" (sem senha em arquivo); não usar o superusuário `postgres`. **MariaDB: não usar.**
- Login dos vendedores **provisório**: Basic Auth do Apache, 1 login por e-mail (`deploy/logins.py`; lista e senhas só locais, fora do git). Planejado: tela de login própria,
  mobile first, com troca da senha inicial no 1º acesso; SSO com o sistema GEWEB só se ele oferecer OIDC/OAuth/SAML ou API para validar usuário.
- Preços: só no site interno (decisão de 09/11 mantida: catálogos, fichas e propostas saem SEM preço). Reais, em `dados/precos_reais.xlsx` (local, fora do git);
  o repositório e o Pages são públicos, então o build interno recusa rodar com `SITE_PUBLICO=1`.

## Próximas fases: login dos vendedores e intranet (planejado em 16/11; construir no Opus 5.5)
- **Servidor consultado em 16/11:** Python 3.14.4 + venv, Apache 2.4.66 com CGI/cgid; **sem** PHP, MySQL, Node, mod_wsgi, mod_proxy e mod_rewrite; sem sudo; 1 vCPU, 3,4 GB.
  Então WordPress está descartado e um aplicativo ligado o tempo todo depende do administrador de infra.
- **Fase 1 (já, sem depender do administrador): login dos vendedores.** App Python no padrão WSGI, rodando por CGI hoje (migra para mod_wsgi/proxy depois sem reescrever).
  Usuários em SQLite fora da pasta pública, senha só como hash (scrypt/pbkdf2 da biblioteca padrão), troca obrigatória da senha inicial no 1º acesso, sessão por cookie seguro,
  bloqueio por tentativas, script para cadastrar/redefinir vendedores (substitui `deploy/logins.py`). Tela de login mobile first com a logo (skill `mdtech-ui-ux`).
  Os preços saem de um endereço que exige sessão e o front os junta aos cards: o catálogo vira um site só, sem preço, e `/interno` deixa de ser uma cópia.
  Manter o Basic Auth atual até o novo estar testado. Tudo por PR; o André usa Git Bash no Windows e prefere **um comando por vez**, esperando a resposta.
- **Fase 1 em construção (16/11):** confirmado login por e-mail e recuperação de senha manual (admin `redefinir`). Código em `servidor/`
  (`servidor/LEIA-ME.md`), tela `site/entrar.html`, preços via `/conta.py/precos` juntados pelo `dados.js`; o `deploy.sh` envia tudo. Falta: instalar no servidor,
  cadastrar os vendedores e, testado, desligar o `/interno` (Basic Auth).
- **Gestão dos vendedores pela tela** (16/11, pedido do André): `site/vendedores.html`, só administradores (coluna `admin`), com histórico
  (tabela `eventos`). Lógica em `servidor/mdtech_conta/gestao.py`, usada pela tela e pelo `admin.py`. 8 vendedores cadastrados em 16/11.
  **Convite por link** (16/11, pedido do André: copiar senha no celular é difícil): a tela não mostra senha; envia link de uso único (7 dias)
  por WhatsApp/e-mail para criar a senha (1º acesso e "esqueci a senha"). Tabela `convites` (só hash).
- **SSO com a GEWEB** só se ela
  oferecer OIDC/OAuth/SAML ou API para validar usuário (o André vai perguntar à GEWEB).
- **App para os vendedores: PWA** (decidido em 16/11; fazer depois das pendências da Fase 1). O próprio site vira app instalável (Android e iPhone),
  sem loja: funciona **sem internet** (service worker com `produtos.json`, fotos e busca; ~5 MB) e **atualiza sozinho** quando conecta (baixa só o que mudou;
  aviso "Sem internet: catálogo de dd/mm" / "Catálogo atualizado"). Preços offline só para quem entrou, com validade (ex.: 15 dias sem conectar) e apagados no "Sair".
  Lista de orçamento guardada e enviada quando a conexão voltar. **Aviso de instalação:** só para vendedores conectados (e logo depois de criar a senha pelo
  convite); Android com botão "Instalar" (evento `beforeinstallprompt`), iPhone com o passo a passo (Compartilhar → "Adicionar à Tela de Início");
  "Agora não" esconde por 30 dias; some quando já instalado. Depois de usar algumas semanas: avaliar Google Play (TWA, US$ 25) e, se preciso,
  App Store (distribuição privada, US$ 99/ano; a Apple recusa app que é só site). App nativo: não compensa agora.
  **Feito em 17/11 (PWA):** `site/sw.js` (service worker; nunca guarda `/conta.py` nem `/interno/`), `site/manifest.json`, ícones em `site/img/app/`,
  `site/js/app.js` (aviso de conexão, convite para instalar, fotos para usar sem internet). Fotos com `?v=<hash>` no `produtos.json` (só o que mudou é
  baixado de novo); todas as fotos (~5 MB) só para vendedor ou app instalado. Preços sem internet em `localStorage` (`mdtech_precos_off`, 15 dias,
  apagados no "Sair" e quando a sessão cai). Pedidos/Suporte sem internet entram numa fila (`mdtech_fila_envios`) e saem sozinhos na volta.
  **PDFs: baixados só quando tocados** (depois ficam guardados para abrir sem internet). Compartilhar um produto usa `p/<codigo>.html`
  (página fixa com a prévia Open Graph, gerada pelo `gerar.py site`, que leva ao `produto.html`).
  **Visual (17/11, pedido do André):** ícone do app com **fundo branco e o símbolo no azul claro da logo (`#38AAE1`)**; convite para instalar em
  **tela cheia**, fundo azul claro, ícone, título "Leve o catálogo no seu celular", 3 benefícios e, no iPhone, o passo a passo antes dos benefícios;
  botões sempre à vista no rodapé. "Agora não", "Entendi", × e Esc adiam por 30 dias. O convite aparece **só em celular e tablet**; no computador fica só o botão de instalar do próprio navegador (decidido em 17/11). Aviso de conexão = faixa fina **dentro do topo** (não cobre nada): "Sem internet · catálogo de dd/mm" em azul bem claro;
  "Conectado · catálogo atualizado" em `#1874A1`. Prévia do convite no WhatsApp: `site/img/app/compartilhar-app.jpg` (1200×630, Open Graph do `entrar.html`) — **conteúdo no quadrado central e celulares nas laterais**, porque o WhatsApp mostra ora o cartão largo, ora uma miniatura quadrada cortada no centro. O link do convite leva `?app=2` para driblar a prévia antiga que o WhatsApp guarda por endereço (se trocar a imagem de novo, subir o número em `entrar.html` e em `vendedores.js`).
  **Android sem o aviso de instalação do navegador** (ex.: **Samsung Internet**, navegador padrão dos Samsung): depois de 8 s o convite mostra o passo a passo
  pelo menu (Samsung: ☰ → Adicionar página a → Tela inicial; outros: ⋮ → Instalar app). Com o aviso (Chrome), aparece o botão "Instalar o app".
- **Fase 2 (depende do administrador): intranet básica** no mesmo app e login: comunicados, aniversariantes e repositório de arquivos e documentos (hoje tudo no grupo de WhatsApp).
  Pedidos preparados para o administrador: mod_wsgi ou proxy + systemd, rewrite/headers, endereços com HTTPS, backup testado, SSH só por chave + firewall, logs, e-mail SMTP,
  PostgreSQL (recomendado), disco e monitoramento. Aguardando o André falar com ele.
- **Institucional:** páginas estáticas no repositório, editadas pelo André (marketing). Aguardando o conteúdo.
- **Orçamento (ferramenta + campanha):** conversar depois do login. Perguntas: quem usa (vendedor, cliente ou os dois), saída (PDF com preço, WhatsApp), desconto, registro das
  propostas, objetivo e canais da campanha.
- **Pendências do André:** enviar os convites aos vendedores pela tela e apagar `deploy/senhas_vendedores.txt` e `deploy/.htpasswd` (não são mais usados).

## Próxima sessão (combinado em 16/11): revisão do projeto
Revisão completa feita em 16/11 por dois modelos, às cegas (Opus 5.5 e Fable 5.2; o Fable foi mais completo: 58 itens). **Começar estimando, item a item,
o modelo (Opus/Sonnet/Haiku) e o gasto de tokens, e atacar primeiro os mais críticos.** Decisões do André (16/11): repositório **continua público**
(por isso, nada sensível do servidor neste arquivo); senha do servidor **já trocada**; botão **Suporte só para vendedores conectados**; grafias dos
produtos: **adotar o termo de mercado** (decidido em 17/11: **trocarte**, como Medtronic/Aesculap e a literatura médica; planilha, nomes, família "Trocartes" e busca já ajustados; a busca ainda aceita trocater/trocarter).
1. ✅ **(17/11, em produção) Segurança rápida:** tirar o campo `fornecedor` do `produtos.json`/`meta.json` públicos (`geradores/site.py`; o site não usa); bloqueio de login
   por e-mail vira atraso progressivo (hoje qualquer um bloqueia um vendedor errando 5 vezes); política de senha com lista de senhas comuns.
2. ✅ **(17/11; falta só desligar o `/interno`) Rede de proteção:** testes + ruff em cada PR (workflow `pull_request`) e no `deploy.sh` (subir só a `main` limpa); backup diário do SQLite
   (`sqlite3 .backup`, 14 cópias, cron do usuário + cópia fora do servidor); deploy que apaga arquivos velhos, atômico e com rollback; transações no
   banco (`adicionar`, `usar_convite`); testes do núcleo (`nome_produto`, `diametro_fmt`, fotos, colunas obrigatórias em `base.carregar`);
   desligar o `/interno` (Fase 1). Backup no cron às 3h10 (`~/backups_mdtech`); cópia fora do servidor ainda não.
3. ✅ **(17/11, em produção) O que o cliente vê errado:** selo de ângulo em não-óticas (usar `MD.ehOtica`, ex.: 1.3-DS-24, A4001); nome dos endoscópios ("AV=30°,") e cards
   idênticos (A275/A276, A189-x: `mdtech/textos.py::nome_produto`); busca aceitando as grafias; NCM num formato só (88 com ponto, 64 sem);
   "Autoclavável" de uso único como "não se aplica"; medidas com vírgula. Pendente: eletrodos, evacuadores e A3104 seguem sem
   "Autoclavável" (o catálogo TIAN SONG urologia 2025 só marca autoclave nos endoscópios; perguntar a instrução de uso à TIAN SONG).
4. ✅ **(17/11, em produção) Celular e acessibilidade:** versão nos CSS/JS (`?v=`); Suporte só para vendedores; ação do produto perto do topo; Voltar desfaz o filtro
   (`pushState`); foco preso nos painéis; bandeja vazia fora do teclado; `role="menu"` errado; paginação com rótulos; botão "Ver resultados" (2,65:1);
   faixa de ajuda que some; textos de 9–11 px; grade sem esperar o `/precos`.
5. ✅ **(17/11; falta só "grafias e acentos", com o André) Privacidade e dados:** aviso de LGPD (formulários → Web3Forms) e anti-spam (honeypot); fontes locais (`assets/fontes`); retenção de eventos/IPs;
   grafias e acentos da base e nomes de família (com o André). Feito: aviso de LGPD nos dois formulários + `site/privacidade.html` (rascunho: o André
   confere o texto), campo-isca anti-robô, fontes locais em `site/fonts/` (woff2 subconjunto latino, a partir de `assets/fontes/`; sem Google Fonts),
   retenção no banco do login (`Banco.limpar_antigos`: sessões/convites vencidos, erros de senha com IP após 15 min, histórico após 1 ano; roda no login e todo dia no backup).
6. ✅ **(17/11) App offline (PWA) e Open Graph por produto.** Fora da v1 (decidido em 17/11): deploy pelo Actions (precisaria da chave SSH como segredo do GitHub) e Git LFS (exigiria reescrever o histórico).

## Estado da v1 (17/11)
Itens 1 a 6 da revisão feitos (PWA incluído). **Para fechar a v1:** o André envia os convites aos vendedores e confirma que todos entram; então se desliga o `/interno`
(Basic Auth) e se apagam `deploy/senhas_vendedores.txt` e `deploy/.htpasswd`. Autoclavável de eletrodos, evacuadores e A3104: **fica como está**
(decidido em 17/11). Cópia do backup fora do servidor: `bash deploy/baixar_backup.sh` (André, de vez em quando). Depois da v1: deploy pelo Actions, Git LFS, Fase 2 (intranet).

## Estado dos dados (base de 08/11/2026, 175 linhas / 152 SKUs únicos)
- ANVISA: em 16/11 entraram 31 células com o registro 82568299003 (endoscópios rígidos/Tiansong, aba de conferência da planilha do André).
  Ainda vazio em 18 SKUs: 814, A108, A151, A189(-1/-2/-3), A201(-1/-2), A204, A207(-2/-3/-4/-4-1), A215-2.C, A310.C.
- A219 = 82568290004 (arquivo ANVISA de 27/10 prevalece). A2101 = 82568290002 (o arquivo lista 2 números; decidido em 09/11 manter o da base).
- A215-2.C e A310.C sem registro (o nº 82568290004 só existia na aba antiga, removida).
- Comprimento vazio em 48 SKUs, diâmetro vazio em 35 SKUs: sobra só o que o fornecedor não informou nos catálogos
  TONGLU, TIAN SONG e ASAP.
- A108: Ø = 4 mm, conforme o catálogo TONGLU (Φ4×3000mm), decidido em 09/11; a descrição também foi ajustada para "D=4MM".
- Preço: **real** (16/11), coluna "Valor Total IPI" (= valor unitário + IPI de 5,2% ou 0%), 152 SKUs, em `dados/precos_reais.xlsx` (LOCAL, no `.gitignore`, nunca no git).
  A coluna `Preço (R$)` fictícia que ainda está na base do repositório é ignorada pelo site.
- `dashboard` mostra o mapa atualizado.

## Histórico resumido
- 23/09: corrigidos diâmetro em Fr ausente no site, A153.C ausente do catálogo de Laparoscopia (erro de linha inicial),
  cor de accent triplicada; removida a aba REGISTROS ANVISA (nenhum script a lia).
- 27/10: aplicados registros ANVISA do arquivo de 27/10 (35 linhas) e publicado o site.
- 05/11: decisão de unificar em repositório único, com publicação por GitHub Actions (este arquivo).
- 08/11: base com 24 comprimentos novos (17 extraídos das descrições e 7 dos catálogos da TONGLU: A206 e A145 = 330 mm;
  clamps A272, A273, A275, A276 e A277 = 65, 45, 25, 25 e 55 mm). Catálogos da TONGLU, TIAN SONG (urologia 2025 e
  cirurgia 2023.5) e ASAP conferidos: não trazem comprimento de camisas, peças guia, eletrodos, trocartes,
  adaptadores, evacuadores nem clips.
- 09/11: A108 com Ø 4 mm e descrição "D=4MM" (catálogo TONGLU prevalece); A2101 mantém 82568290002. Site com a auditoria
  de UX/UI aplicada (PR #4): contraste AA, orçamento com quantidade, fotos otimizadas, 2 colunas no celular.
- 09/11: propostas básicas (kits em PDF, aba KITS) publicadas no site: Hérnia de Hiato (33 itens) e Colecistectomia (21 itens).
- 10/11: **"Óticas HD-4K" deixou de ser especialidade**: é um tipo de item (endoscópios rígidos da ASAP, família "Endoscópios") dentro das
  especialidades: 2.9 mm (10-0385-00, 10-0393-00) só Histeroscopia; 4 mm (10-2023-00) Histeroscopia + Urologia; 10 mm (10-2516-00) só
  Laparoscopia. Fornecedor segue ASAP (marca vem primeiro). **Cores novas por especialidade: Laparoscopia laranja `#F5A623`, Urologia azul
  `#36A9E1`, Histeroscopia rosa `#C64B8C`** (o verde-água saiu). Catálogo PDF "Óticas HD-4K" deixou de existir (agora 3 por especialidade + o
  completo) e a capa do catálogo completo foi refeita com as 3 cores. Sem selo "HD-4K" nos cards.
