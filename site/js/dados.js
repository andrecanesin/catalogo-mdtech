/* Núcleo compartilhado entre a grade e a página de produto:
   - carrega produtos.json / meta.json
   - gerencia a lista de orçamento (persistida no navegador)
   - monta a mensagem de WhatsApp / e-mail
   - resolve o ícone do selo de ângulo (img/angulos/<graus>.png)
   Sem dependências externas. */
window.MD = (function () {
  const CHAVE = "mdtech_orcamento";
  const cfg = window.MDTECH || {};
  const accent = (cfg.accent) || {};

  function corEsp(esp) { return accent[esp] || "#36A9E1"; }
  // cor para texto (ou fundo de texto branco): variante escura que passa no AA
  function corTexto(esp) { return (cfg.accentTexto || {})[esp] || "#1874A1"; }

  // Etiqueta da especialidade: fundo na cor viva da especialidade e texto BRANCO (decisão do André, 10/11: o branco em negrito, com sombra
  // sutil, basta para o uso em tela; sobre laranja e azul vivos o contraste fica abaixo de 4,5:1, é exceção consciente ao AA só nas etiquetas).
  // É a MESMA etiqueta em todo lugar onde o nome da especialidade aparece (card, produto, filtro, chip, menu de catálogos).
  function corSobre(esp) { return "#FFFFFF"; }
  function pillEsp(esp) { return `<span class="pill-esp" style="background:${corEsp(esp)};color:${corSobre(esp)}">${esc(esp)}</span>`; }

  // ângulo só é dado pendente em ótica/endoscópio; nos demais itens "não se aplica"
  function ehOtica(p) { return /^(endosc[oó]pio|[oó]tica|telesc)/i.test((p && p.nome) || ""); }

  // item de uso único (clips): "Autoclavável" não se aplica (espelha mdtech/textos.py::uso_unico)
  function usoUnico(p) { return /^clips?\b/i.test((p && p.nome) || ""); }

  // ---- normalização p/ busca (sem acento, minúsculo) ----
  function norm(s) {
    return (s || "").toString().toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  // escapa texto antes de entrar em innerHTML (URL e dados nunca viram HTML)
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g,
      c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // ---- dados ----
  // esperarPrecos=false (grade): devolve na hora, sem esperar o /conta.py/precos (CGI pode ser lento); "precos" é uma
  // promessa que resolve quando os preços do vendedor chegarem (true = algum preço mudou: vale redesenhar).
  async function carregar(op) {
    const esperar = !op || op.esperarPrecos !== false;
    const [prod, meta] = await Promise.all([
      fetch("produtos.json").then(r => r.json()),
      fetch("meta.json").then(r => r.json()).catch(() => null)
    ]);
    detectarPrecos(prod);
    const precos = aplicarPrecosVendedor(prod).then(mudou => { detectarPrecos(prod); return mudou; }).catch(() => false);
    if (esperar) await precos;
    return { produtos: prod, meta, precos };
  }

  // Foco preso num painel aberto (Tab e Shift+Tab circulam só dentro dele). Devolve a função que solta.
  function prenderFoco(painel) {
    const sel = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const ao = e => {
      if (e.key !== "Tab") return;
      const itens = [...painel.querySelectorAll(sel)].filter(x => x.offsetParent !== null && !x.closest("[hidden]"));
      if (!itens.length) return;
      const pri = itens[0], ult = itens[itens.length - 1];
      if (e.shiftKey && document.activeElement === pri) { e.preventDefault(); ult.focus(); }
      else if (!e.shiftKey && document.activeElement === ult) { e.preventDefault(); pri.focus(); }
      else if (!painel.contains(document.activeElement)) { e.preventDefault(); pri.focus(); }
    };
    document.addEventListener("keydown", ao);
    return () => document.removeEventListener("keydown", ao);
  }

  // ---- login dos vendedores (app /conta.py no servidor; ver servidor/LEIA-ME.md) ----
  const _conta = cfg.conta || {};
  let _estadoConta = { status: 0 };       // 0 = sem app aqui · 200 conectado · 401 não conectado · 403 falta trocar a senha
  function contaAtiva() { return !!_conta.ativo && (_conta.hosts || []).includes(location.hostname); }
  // cookie sem segredo que o servidor põe no login: só quem já entrou aciona o servidor (clientes nunca chamam o CGI)
  function ehVendedor() { return /(?:^|;\s*)mdtech_vendedor=1/.test(document.cookie); }
  function esquecerVendedor() { document.cookie = "mdtech_vendedor=; Path=/; Max-Age=0; SameSite=Lax"; }
  async function contaReq(rota, corpo) {
    const op = { credentials: "same-origin", cache: "no-store", headers: {} };
    if (corpo !== undefined) { op.method = "POST"; op.headers["Content-Type"] = "application/json"; op.body = JSON.stringify(corpo); }
    try {
      const r = await fetch((_conta.url || "/conta.py") + rota, op);
      let dados = {}; try { dados = await r.json(); } catch (e) { /* resposta sem JSON (ex.: 404 do servidor) */ }
      return { status: r.status, dados };
    } catch (e) { return { status: 0, dados: { erro: "Sem conexão com o servidor. Confira a internet e tente de novo." } }; }
  }
  // Com sessão de vendedor, troca o preço de cada produto pelo preço real. Sem sessão (ou fora do servidor), não mexe em nada.
  async function aplicarPrecosVendedor(prod) {
    if (!contaAtiva()) return false;
    if (!ehVendedor()) { _estadoConta = { status: 401 }; montarContaTopo(); return false; }
    const r = await contaReq("/precos");
    if (r.status === 401) esquecerVendedor();          // sessão expirou ou foi encerrada
    _estadoConta = { status: r.status, email: r.dados.email || "", admin: !!r.dados.admin };
    let mudou = false;
    if (r.status === 200 && r.dados.precos) {
      (prod || []).forEach(p => { const v = r.dados.precos[p.codigo];
        if (v) { p.preco = v; p.preco_ficticio = false; mudou = true; } });
    }
    montarContaTopo();
    return mudou;
  }
  // Topo (ao lado de "Catálogos e propostas"): "Entrar" para quem não entrou; para o vendedor, ícone de conectado com menu
  // (e-mail, preços de tabela, trocar a senha, sair). Criado via JS: não depende de markup fixo nas páginas.
  function montarContaTopo() {
    const ref = document.getElementById("btn-catalogos");
    if (!ref || !contaAtiva()) return;
    document.querySelectorAll(".conta-topo, .conta-menu").forEach(e => e.remove());
    const volta = encodeURIComponent(location.pathname.split("/").pop() + location.search);
    const icone = '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" width="18" height="18" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
    const st = _estadoConta.status;
    if (st !== 200) {
      const a = document.createElement("a");
      a.className = "conta-topo"; a.href = "entrar.html?volta=" + volta;
      a.innerHTML = icone + '<span>Entrar</span>';
      a.setAttribute("aria-label", "Entrar (acesso de vendedores)");
      ref.after(a); return;
    }
    const email = _estadoConta.email || "";
    const bt = document.createElement("button");
    bt.type = "button"; bt.className = "conta-topo on";
    bt.setAttribute("aria-expanded", "false");
    bt.setAttribute("aria-label", "Minha conta: conectado como " + email);
    bt.innerHTML = icone + '<span class="l-conta">Conectado</span><i class="conta-ponto" aria-hidden="true"></i>';
    const menu = document.createElement("div");
    menu.className = "conta-menu"; menu.hidden = true;
    menu.innerHTML = `<p class="conta-menu-quem">Conectado como<b>${esc(email)}</b></p>
      <p class="conta-menu-info">Preços de tabela visíveis no catálogo.</p>
      ${_estadoConta.admin ? '<a href="vendedores.html">Gerenciar vendedores</a>' : ""}<a href="entrar.html#trocar">Trocar a senha</a><button type="button" class="conta-sair">Sair</button>`;
    ref.after(bt); document.body.appendChild(menu);
    const abrir = () => { const r = bt.getBoundingClientRect();
      menu.style.top = Math.round(r.bottom + 8) + "px";
      menu.style.right = Math.max(10, Math.round(window.innerWidth - r.right)) + "px";
      menu.hidden = false; bt.setAttribute("aria-expanded", "true"); };
    const fechar = (foco) => { if (menu.hidden) return; menu.hidden = true; bt.setAttribute("aria-expanded", "false"); if (foco) bt.focus(); };
    bt.addEventListener("click", e => { e.stopPropagation(); menu.hidden ? abrir() : fechar(); });
    document.addEventListener("click", e => { if (!menu.contains(e.target)) fechar(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") fechar(true); });
    window.addEventListener("resize", () => fechar());
    menu.querySelector(".conta-sair").onclick = async () => { await contaReq("/sair", {}); location.reload(); };
  }

  // ---- ícone de ângulo ----
  // Selo aparece em qualquer ótica/endoscópio (Uro, Histero e Óticas HD-4K
  // todos usam "ângulo" como ângulo de visão da lente). A única exceção
  // hoje é a pinça Mixter 90° (Laparoscopia): ali "ângulo" é a geometria da
  // ponta da pinça, não vista de lente — não leva selo. Critério: família
  // não é uma pinça (mais robusto que checar especialidade, cobre qualquer
  // ótica nova que apareça em qualquer especialidade).
  function _ehPinca(familia) {
    return /pin[cç]a/i.test(familia || "");
  }

  // Grafias que o mercado usa para a mesma coisa: quem busca por uma acha todas.
  const GRAFIAS = [
    [/\btroc(?:arte|ater|arter)s?\b/, "trocarte trocater trocarter"],
    [/\bres?sectosc[oó]pi\w*/, "ressectoscopio resectoscopio ressectoscopia resectoscopia"],
    [/\bveress?\b/, "veress verres"],                      // agulha de Veress (grafia antiga: Verres)
    [/\bmetzenbaum\b/, "metzenbaum metzembaum"],
    [/\ba?l+igator\b/, "alligator aligator"],
  ];
  // texto de busca de um produto: o normal + todas as grafias dos termos que ele tem
  function textoBusca(s) {
    const n = norm(s);
    return GRAFIAS.reduce((t, [re, todas]) => re.test(n) ? t + " " + todas : t, n);
  }

  // "30°" -> "img/angulos/30.png". Ícones que ainda não existirem em
  // site/img/angulos/ simplesmente não aparecem (o <img> some via onerror).
  function iconeAngulo(angulo) {
    if (!angulo) return null;
    const n = String(angulo).match(/-?\d+/);
    if (!n) return null;
    return `img/angulos/${n[0]}.png`;
  }
  function seloAngulo(angulo, familia, classeExtra) {
    if (_ehPinca(familia)) return "";
    const src = iconeAngulo(angulo);
    if (!src) return "";
    return `<span class="selo-angulo${classeExtra ? " " + classeExtra : ""}">
      <img src="${src}" alt="Ângulo ${angulo}" onerror="this.closest('.selo-angulo').style.display='none'">
      <span>${angulo}</span>
    </span>`;
  }

  // ---- lista de orçamento (localStorage) ----
  function lista() {
    return _ler().map(x => x.codigo);
  }
  // guardado como [{codigo, qtd}]; listas antigas (só códigos) viram qtd 1
  function _ler() {
    try {
      const a = JSON.parse(localStorage.getItem(CHAVE)) || [];
      return a.map(x => typeof x === "string" ? { codigo: x, qtd: 1 }
                      : { codigo: String(x.codigo || ""), qtd: Math.max(1, parseInt(x.qtd, 10) || 1) })
              .filter(x => x.codigo);
    } catch (e) { return []; }
  }
  function _gravar(itens) {
    try { localStorage.setItem(CHAVE, JSON.stringify(itens)); } catch (e) { /* navegador sem storage */ }
    document.dispatchEvent(new CustomEvent("orcamento:mudou", { detail: itens.map(x => x.codigo) }));
  }
  function tem(cod) { return lista().includes(cod); }
  function qtd(cod) { const i = _ler().find(x => x.codigo === cod); return i ? i.qtd : 0; }
  function definirQtd(cod, n) {
    const itens = _ler(), i = itens.find(x => x.codigo === cod);
    if (!i) return;
    i.qtd = Math.min(999, Math.max(1, parseInt(n, 10) || 1));
    _gravar(itens);
  }
  function alternar(cod) {
    const itens = _ler(), i = itens.findIndex(x => x.codigo === cod);
    if (i >= 0) itens.splice(i, 1); else itens.push({ codigo: cod, qtd: 1 });
    _gravar(itens); return i < 0;
  }
  // adiciona vários de uma vez (ex.: proposta básica): [{codigo, qtd}]; quem já está na lista ganha a quantidade da proposta
  function adicionarVarios(novos) {
    const itens = _ler();
    novos.forEach(n => { const i = itens.find(x => x.codigo === n.codigo);
      if (i) i.qtd = Math.min(999, Math.max(i.qtd, n.qtd || 1)); else itens.push({ codigo: n.codigo, qtd: Math.min(999, n.qtd || 1) }); });
    _gravar(itens);
  }
  function remover(cod) { _gravar(_ler().filter(x => x.codigo !== cod)); }
  function limpar() { _gravar([]); }

  // ---- preços (coluna "Preço (R$)" da base; hoje fictícios) ----
  const _pc = cfg.precos || {};
  // o site de clientes não tem preço nenhum no produtos.json: então não mostra cartão, "sob consulta", total nem aviso
  let _temPrecos = true;
  const detectarPrecos = prod => { _temPrecos = (prod || []).some(p => p.preco); };
  const mostrarPreco = () => _pc.mostrar !== false && _temPrecos;
  // preço com destaque tipográfico: "R$" pequeno, reais em negrito, centavos menores (card e página do produto)
  const precoHTML = v => { const [r, c] = Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).split(",");
    return `<span class="pz-m">R$</span><span class="pz-v">${r}</span><span class="pz-c">,${c}</span>`; };
  const brl = v => "R$ " + Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // total do orçamento: soma preço × quantidade dos itens que têm preço
  function totalLista(produtos) {
    const byCod = {}; produtos.forEach(p => byCod[p.codigo] = p);
    let total = 0, semPreco = 0, ficticio = false;
    _ler().forEach(x => { const p = byCod[x.codigo];
      if (p && p.preco) { total += p.preco * x.qtd; if (p.preco_ficticio) ficticio = true; } else semPreco++; });
    return { total, semPreco, ficticio };
  }

  // ---- mensagem de orçamento ----
  function _linhas(produtos) {
    const byCod = {}; produtos.forEach(p => byCod[p.codigo] = p);
    return _ler().map((x, i) => {
      const p = byCod[x.codigo];
      const pr = mostrarPreco() && p && p.preco ? ` — ${brl(p.preco)} × ${x.qtd} = ${brl(p.preco * x.qtd)}` : "";
      return `${i + 1}. ${x.codigo}${p ? " — " + p.nome : ""} — qtd: ${x.qtd}${pr}`;
    });
  }
  function texto(produtos) {
    const l = _linhas(produtos);
    const un = _ler().reduce((s, x) => s + x.qtd, 0);
    const t = totalLista(produtos);
    const tot = mostrarPreco() && t.total ? `\nTotal estimado: ${brl(t.total)}${t.ficticio ? " (" + (_pc.aviso || "valores ilustrativos") + ")" : ""}` : "";
    return `Olá! Gostaria de um orçamento dos seguintes itens MDTech:\n\n${l.join("\n")}\n\n` +
      `(${l.length} ite${l.length === 1 ? "m" : "ns"}, ${un} unidade${un === 1 ? "" : "s"})` + tot;
  }
  function linkWhatsApp(produtos) {
    const num = (cfg.contato && cfg.contato.whatsapp) || "";
    if (!num) return null;
    return `https://wa.me/${num}?text=${encodeURIComponent(texto(produtos))}`;
  }
  function linkEmail(produtos) {
    const mail = (cfg.contato && cfg.contato.email) || "";
    if (!mail) return null;
    const assunto = "Pedido de orçamento — Catálogo MDTech";
    return `mailto:${mail}?subject=${encodeURIComponent(assunto)}&body=${encodeURIComponent(texto(produtos))}`;
  }

  // ---- compartilhar link (produto ou proposta): menu nativo do celular; no computador, copia o link ----
  async function compartilhar(titulo, url, botao) {
    const avisar = t => { if (!botao) return; const o = botao.dataset.txt || botao.textContent; botao.dataset.txt = o;
      botao.textContent = t; setTimeout(() => { botao.textContent = o; }, 2200); };
    if (navigator.share && window.matchMedia("(pointer:coarse)").matches) {
      try { await navigator.share({ title: titulo, url }); return; } catch (e) { if (e && e.name === "AbortError") return; }
    }
    try { await navigator.clipboard.writeText(url); avisar("✓ Link copiado"); }
    catch (e) { window.prompt("Copie o link:", url); }
  }

  // ---- trilha de navegação (breadcrumb): onde estou na hierarquia Catálogo › Especialidade › Família › Produto ----
  // passos: [{t: texto, href?: link}]; o último é a página atual (sem link, aria-current). Só aparece no desktop (CSS).
  const urlGrade = (esp, fam) => "index.html" + (esp || fam ? "?" + new URLSearchParams(
    [esp ? ["esp", esp] : null, fam ? ["fam", fam] : null].filter(Boolean)).toString() : "");
  function trilha(passos) {
    return `<nav class="trilha" aria-label="Você está em"><ol>` + passos.map((p, i) => i === passos.length - 1
      ? `<li aria-current="page">${esc(p.t)}</li>` : `<li><a href="${esc(p.href)}">${esc(p.t)}</a></li>`).join("") + `</ol></nav>`;
  }

  // ---- envio por e-mail sem sair do site (Web3Forms; chave em config.js -> suporte.chaveEmail) ----
  // Usado pelo Suporte e pelo pedido de orçamento. Sem a chave, os dois caem no modo antigo (WhatsApp / mailto).
  const _chaveEmail = ((cfg.suporte && cfg.suporte.chaveEmail) || "").trim();
  const emailAtivo = () => !!_chaveEmail;
  const emailValido = v => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v || "");
  // armadilha = campo escondido que gente não vê e robô preenche: se vier preenchido, finge que enviou e não manda nada.
  async function enviarEmail({ assunto, nome, contato, corpo, armadilha }) {
    if (armadilha) return;
    const dados = { access_key: _chaveEmail, subject: String(assunto).slice(0, 200), from_name: "Catálogo MDTech",
      name: String(nome || "(sem nome)").slice(0, 120), message: String(corpo).slice(0, 8000) };
    if (emailValido(contato)) dados.email = contato;            // vira o "responder para" do e-mail
    const r = await fetch("https://api.web3forms.com/submit", { method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(dados) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.success === false) throw new Error(j.message || r.status);
  }

  // ---- bandeja de orçamento (grade e página de produto usam a mesma) ----
  // Markup esperado: #bandeja com #qt, #bt-lista, #bt-limpar, #bt-mail, #bt-wpp.
  function ligarBandeja(produtos) {
    const bandeja = document.getElementById("bandeja");
    if (!bandeja) return;
    const $ = id => document.getElementById(id);
    const byCod = {}; produtos.forEach(p => byCod[p.codigo] = p);

    // painel "Ver lista": itens com botão de remover (criado por JS, sem depender de markup)
    const pop = document.createElement("div");
    pop.className = "lista-pop"; pop.id = "lista-pop"; pop.hidden = true;
    pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "Itens no orçamento");
    document.body.appendChild(pop);
    const btLista = $("bt-lista");

    // Pedido de orçamento por e-mail (dentro do site). Nada é gravado no aparelho; ao enviar, a lista é esvaziada.
    let orc = null;
    function montarOrc() {
      const raiz = document.createElement("div");
      raiz.innerHTML = `
        <div class="sup-bg" id="orc-bg" hidden></div>
        <div class="sup-panel" id="orc-panel" role="dialog" aria-modal="true" aria-labelledby="orc-t" hidden>
          <div class="sup-head"><strong id="orc-t">Pedir orçamento</strong>
            <button class="sup-x" id="orc-x" type="button" aria-label="Fechar">×</button></div>
          <div id="orc-form">
            <p class="sup-sub" id="orc-res"></p>
            <label class="sup-campo">Seu nome <input id="orc-nome" type="text" autocomplete="name" placeholder="Como posso te chamar?"></label>
            <label class="sup-campo">Hospital, clínica ou empresa <input id="orc-emp" type="text" autocomplete="organization" placeholder="Opcional"></label>
            <label class="sup-campo">Como te respondo? <input id="orc-ret" type="text" autocomplete="email" placeholder="E-mail ou telefone"></label>
            <label class="sup-campo">Observação <textarea id="orc-obs" rows="3" placeholder="Opcional: prazo, cidade, dúvidas"></textarea></label>
            <label class="sup-isca" aria-hidden="true">Não preencha este campo <input id="orc-isca" type="text" tabindex="-1" autocomplete="off"></label>
            <p class="sup-lgpd">Usamos o que você informa só para responder a esta mensagem. O envio passa pelo serviço Web3Forms (EUA) e chega por e-mail à equipe da MDTech; nada fica salvo neste aparelho. <a href="privacidade.html" target="_blank" rel="noopener">Política de privacidade</a></p>
            <p class="sup-st" id="orc-st" role="status" aria-live="polite"></p>
            <button class="sup-go sup-mail" id="orc-send" type="button" aria-disabled="true">Enviar pedido</button>
          </div>
          <div id="orc-feito" class="sup-feito" hidden>
            <p class="sup-ok-t">✓ Pedido enviado</p>
            <p>Recebemos a sua lista e vamos responder pelo contato informado.</p>
            <button class="sup-go sup-mail" id="orc-fechar" type="button">Fechar</button>
          </div>
        </div>`;
      document.body.appendChild(raiz);
      const q = id => raiz.querySelector("#" + id);
      const o = { bg: q("orc-bg"), painel: q("orc-panel"), x: q("orc-x"), form: q("orc-form"), feito: q("orc-feito"), res: q("orc-res"),
        nome: q("orc-nome"), isca: q("orc-isca"), emp: q("orc-emp"), ret: q("orc-ret"), obs: q("orc-obs"), st: q("orc-st"), send: q("orc-send"), fechar: q("orc-fechar") };
      let enviando = false;
      const pronto = () => o.nome.value.trim() && o.ret.value.trim() && lista().length > 0 && !enviando;
      const checar = () => { const ok = !!pronto(); o.send.setAttribute("aria-disabled", ok ? "false" : "true"); o.send.classList.toggle("off", !ok); };
      o.fecharTudo = () => { if (o.soltar) { o.soltar(); o.soltar = null; } o.painel.hidden = true; o.bg.hidden = true; o.form.hidden = false; o.feito.hidden = true; if ($("bt-mail")) $("bt-mail").focus(); };
      o.x.onclick = o.bg.onclick = o.fechar.onclick = o.fecharTudo;
      document.addEventListener("keydown", ev => { if (ev.key === "Escape" && !o.painel.hidden) o.fecharTudo(); });
      [o.nome, o.ret].forEach(i => i.addEventListener("input", checar));
      o.send.addEventListener("click", async () => {
        if (!pronto()) { (o.nome.value.trim() ? o.ret : o.nome).focus(); return; }
        const nome = o.nome.value.trim(), emp = o.emp.value.trim(), ret = o.ret.value.trim(), obs = o.obs.value.trim();
        const corpo = ["Pedido de orçamento — Catálogo MDTech", "Nome: " + nome, emp ? "Empresa: " + emp : null, "Contato: " + ret,
          obs ? "Observação: " + obs : null, "", texto(produtos)].filter(l => l !== null).join("\n");
        enviando = true; o.st.className = "sup-st"; o.st.textContent = "Enviando…"; checar();
        try {
          await enviarEmail({ assunto: "Orçamento catálogo MDTech · " + lista().length + " ite" + (lista().length === 1 ? "m" : "ns") + " · " + nome,
            nome, contato: ret, corpo, armadilha: o.isca.value });
          [o.nome, o.emp, o.ret, o.obs, o.isca].forEach(i => i.value = ""); o.st.textContent = "";
          o.form.hidden = true; o.feito.hidden = false; o.fechar.focus();
          limpar();                                  // pedido enviado: esvazia a lista
        } catch (err) {
          o.st.className = "sup-st erro"; o.st.textContent = "Não foi possível enviar agora. Tente de novo ou use o WhatsApp.";
        }
        enviando = false; checar();
      });
      o.checar = checar;
      return o;
    }
    function abrirOrc() {
      if (!orc) orc = montarOrc();
      const n = lista().length, un = lista().reduce((s, c) => s + qtd(c), 0), t = totalLista(produtos);
      orc.res.textContent = n + " ite" + (n === 1 ? "m" : "ns") + ", " + un + " unidade" + (un === 1 ? "" : "s") +
        (mostrarPreco() && t.total ? " · total estimado " + brl(t.total) + (t.ficticio ? " (valores ilustrativos)" : "") : "") + ".";
      orc.st.textContent = ""; orc.form.hidden = false; orc.feito.hidden = true;
      orc.painel.hidden = false; orc.bg.hidden = false; orc.checar(); orc.nome.focus();
      if (orc.soltar) orc.soltar();
      orc.soltar = prenderFoco(orc.painel);
    }

    function rodapeTotal() {
      if (!mostrarPreco()) return "";
      const t = totalLista(produtos);
      if (!t.total) return "";
      return `<div class="lista-total"><span>Total estimado</span><b>${brl(t.total)}</b></div>` +
        (t.ficticio ? `<p class="aviso-preco">${esc(_pc.aviso || "Valores ilustrativos.")}</p>` : "") +
        (t.semPreco ? `<p class="aviso-preco">${t.semPreco} ite${t.semPreco === 1 ? "m" : "ns"} sem preço não entra${t.semPreco === 1 ? "" : "m"} no total.</p>` : "");
    }

    function renderLista() {
      const itens = lista();
      pop.innerHTML = `<div class="lista-head"><strong>Itens no orçamento</strong>
          <button class="lista-x" aria-label="Fechar lista">×</button></div>
        <ul>${itens.map(c => {
          const p = byCod[c], q = qtd(c), e = esc(c);
          const sub = mostrarPreco() && p && p.preco ? `<span class="sub">${brl(p.preco * q)}` +
            (q > 1 ? `<small>${q} × ${brl(p.preco)}</small>` : "") + `</span>` : "";
          return `<li><span class="mono">${e}</span><span class="n">${esc(p ? p.nome : "")}</span>${sub}
            <span class="qtd">
              <button data-menos="${e}" aria-label="Diminuir quantidade de ${e}" ${q <= 1 ? "disabled" : ""}>−</button>
              <input type="number" min="1" max="999" inputmode="numeric" value="${q}" data-qtd="${e}"
                     aria-label="Quantidade de ${e}">
              <button data-mais="${e}" aria-label="Aumentar quantidade de ${e}">+</button>
            </span>
            <button class="rem" data-rem="${e}" aria-label="Remover ${e} do orçamento">Remover</button></li>`;
        }).join("")}</ul>${rodapeTotal()}
        <button class="lista-limpar">Limpar lista</button>`;
      pop.querySelector(".lista-x").onclick = fecharLista;
      pop.querySelector(".lista-limpar").onclick = confirmarLimpar;
      pop.querySelectorAll("[data-rem]").forEach(b => b.onclick = () => remover(b.dataset.rem));
      pop.querySelectorAll("[data-menos]").forEach(b => b.onclick = () => definirQtd(b.dataset.menos, qtd(b.dataset.menos) - 1));
      pop.querySelectorAll("[data-mais]").forEach(b => b.onclick = () => definirQtd(b.dataset.mais, qtd(b.dataset.mais) + 1));
      pop.querySelectorAll("[data-qtd]").forEach(i => i.onchange = () => definirQtd(i.dataset.qtd, i.value));
    }
    let soltarLista = null;
    function abrirLista() {
      renderLista(); pop.hidden = false;
      if (soltarLista) soltarLista();
      soltarLista = prenderFoco(pop);
      if (btLista) btLista.setAttribute("aria-expanded", "true");
      pop.querySelector(".lista-x").focus();
    }
    function fecharLista() {
      if (pop.hidden) return;
      pop.hidden = true;
      if (soltarLista) { soltarLista(); soltarLista = null; }
      if (btLista) { btLista.setAttribute("aria-expanded", "false"); btLista.focus(); }
    }
    if (btLista) {
      btLista.setAttribute("aria-haspopup", "dialog"); btLista.setAttribute("aria-expanded", "false");
      btLista.onclick = () => pop.hidden ? abrirLista() : fecharLista();
    }
    document.addEventListener("keydown", e => { if (e.key === "Escape") fecharLista(); });

    function atualizar() {
      const n = lista().length;
      bandeja.classList.toggle("on", n > 0);
      bandeja.inert = n === 0;                       // vazia = escondida: nem Tab nem leitor de tela chegam nela
      if (n === 0) bandeja.setAttribute("aria-hidden", "true"); else bandeja.removeAttribute("aria-hidden");
      document.body.classList.toggle("com-bandeja", n > 0);
      const tq = mostrarPreco() ? totalLista(produtos) : { total: 0 };
      $("qt").innerHTML = `<span>${n}</span> ite${n === 1 ? "m" : "ns"} no orçamento` +
        (tq.total ? `<em class="qt-tot">Total estimado ${brl(tq.total)}</em>` : "");
      const wpp = linkWhatsApp(produtos), mail = linkEmail(produtos);
      const bw = $("bt-wpp"), bm = $("bt-mail");
      if (wpp) { bw.style.display = ""; bw.onclick = () => location.href = wpp; } else bw.style.display = "none";
      if (emailAtivo()) { bm.style.display = ""; bm.onclick = abrirOrc; }
      else if (mail) { bm.style.display = ""; bm.onclick = () => location.href = mail; } else bm.style.display = "none";
      document.documentElement.style.setProperty("--h-bandeja", n > 0 ? bandeja.offsetHeight + "px" : "0px");
      if (n === 0) { pop.hidden = true; if (btLista) btLista.setAttribute("aria-expanded", "false"); }
      else if (!pop.hidden) {
        const f = document.activeElement, attrs = ["data-menos", "data-mais", "data-qtd", "data-rem"];
        const a = f && pop.contains(f) && attrs.find(k => f.hasAttribute(k));
        const sel = a ? `[${a}="${CSS.escape(f.getAttribute(a))}"]` : null;
        renderLista();
        const novo = sel && pop.querySelector(sel);
        (novo && !novo.disabled ? novo : pop.querySelector(".lista-x")).focus();
      }
    }
    function confirmarLimpar() { if (confirm("Remover todos os itens do orçamento?")) limpar(); }
    $("bt-limpar").onclick = confirmarLimpar;
    document.addEventListener("orcamento:mudou", atualizar);
    window.addEventListener("resize", atualizar);
    atualizar();
  }

  // Menu "Catálogos e propostas" (botão #btn-catalogos, menu #menu-catalogos, fundo #backdrop-catalogos).
  // Usado pela grade e pela página de produto.
  async function montarMenuDownloads() {
    const q = id => document.getElementById(id);
    const btn = q("btn-catalogos"), menu = q("menu-catalogos"), bd = q("backdrop-catalogos");
    const ativo = MD.cfg.catalogosAtivo;
    const base = MD.cfg.catalogosBase || "";
    const cats = (ativo && MD.cfg.catalogos) || [];
    if (!btn || !menu || !bd) return;
    // propostas básicas (kits): lista gerada em site/propostas.json (cada kit novo na planilha aparece sozinho)
    let props = [];
    try { const r = await fetch("propostas.json"); props = r.ok ? await r.json() : []; } catch (e) { props = []; }
    if (!cats.length && !props.length) { btn.style.display = "none"; return; }

    const externo = /^https?:\/\//i.test(base);
    const seta = '<svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16"/></svg>';
    const secCats = cats.length ? '<div class="grupo-menu">Catálogos</div>' + cats.map(c => `
      <a href="${MD.esc(base + c.arquivo)}" ${externo ? 'target="_blank" rel="noopener"' : "download"}
         class="${c.completo ? "completo" : ""}">${seta}${(cfg.accent || {})[c.nome] ? pillEsp(c.nome) : MD.esc(c.nome)}</a>${c.completo ? '<div class="sep"></div>' : ""}`).join("") : "";
    const secProps = props.length ? (cats.length ? '<div class="sep"></div>' : "") + '<div class="grupo-menu">Propostas básicas (kits)</div>'
      + props.map(p => `<a href="${MD.esc(p.arquivo)}" download>${seta}${MD.esc(p.titulo)}
          <small>${MD.esc(p.itens)} itens</small></a>`).join("") : "";
    menu.innerHTML = secCats + secProps;

    const abrir = () => { const topo = document.querySelector(".top");
      if (topo) menu.style.top = Math.round(topo.getBoundingClientRect().bottom + 6) + "px";
      menu.classList.add("on"); bd.classList.add("on"); btn.setAttribute("aria-expanded", "true");
      soltar = prenderFoco(menu); const a = menu.querySelector("a"); if (a) a.focus(); };
    const fechar = () => { if (!menu.classList.contains("on")) return;
      menu.classList.remove("on"); bd.classList.remove("on"); btn.setAttribute("aria-expanded", "false");
      if (soltar) { soltar(); soltar = null; } btn.focus(); };
    let soltar = null;
    btn.setAttribute("aria-controls", menu.id);
    btn.addEventListener("click", () => menu.classList.contains("on") ? fechar() : abrir());
    bd.addEventListener("click", fechar);
    document.addEventListener("keydown", e => { if (e.key === "Escape") fechar(); });
  }
  return { contaAtiva, contaReq, ehVendedor, esquecerVendedor, brl, precoHTML, detectarPrecos, totalLista, mostrarPreco, cfg, corEsp, corTexto, corSobre, pillEsp, ehOtica, usoUnico, textoBusca, norm, esc, carregar, prenderFoco, ligarBandeja, montarMenuDownloads, trilha, compartilhar, urlGrade, emailAtivo, emailValido, enviarEmail, qtd, definirQtd,
           iconeAngulo, seloAngulo,
           lista, tem, alternar, adicionarVarios, remover, limpar,
           texto, linkWhatsApp, linkEmail };
})();
