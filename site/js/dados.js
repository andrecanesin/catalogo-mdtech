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

  // ângulo só é dado pendente em ótica/endoscópio; nos demais itens "não se aplica"
  function ehOtica(p) { return /^(endosc[oó]pio|[oó]tica|telesc)/i.test((p && p.nome) || ""); }

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
  async function carregar() {
    const [prod, meta] = await Promise.all([
      fetch("produtos.json").then(r => r.json()),
      fetch("meta.json").then(r => r.json()).catch(() => null)
    ]);
    return { produtos: prod, meta };
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
  function remover(cod) { _gravar(_ler().filter(x => x.codigo !== cod)); }
  function limpar() { _gravar([]); }

  // ---- mensagem de orçamento ----
  function _linhas(produtos) {
    const byCod = {}; produtos.forEach(p => byCod[p.codigo] = p);
    return _ler().map((x, i) => {
      const p = byCod[x.codigo];
      return `${i + 1}. ${x.codigo}${p ? " — " + p.nome : ""} — qtd: ${x.qtd}`;
    });
  }
  function texto(produtos) {
    const l = _linhas(produtos);
    const un = _ler().reduce((s, x) => s + x.qtd, 0);
    return `Olá! Gostaria de um orçamento dos seguintes itens MDTech:\n\n${l.join("\n")}\n\n` +
      `(${l.length} ite${l.length === 1 ? "m" : "ns"}, ${un} unidade${un === 1 ? "" : "s"})`;
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

    function renderLista() {
      const itens = lista();
      pop.innerHTML = `<div class="lista-head"><strong>Itens no orçamento</strong>
          <button class="lista-x" aria-label="Fechar lista">×</button></div>
        <ul>${itens.map(c => {
          const p = byCod[c], q = qtd(c), e = esc(c);
          return `<li><span class="mono">${e}</span><span class="n">${esc(p ? p.nome : "")}</span>
            <span class="qtd">
              <button data-menos="${e}" aria-label="Diminuir quantidade de ${e}" ${q <= 1 ? "disabled" : ""}>−</button>
              <input type="number" min="1" max="999" inputmode="numeric" value="${q}" data-qtd="${e}"
                     aria-label="Quantidade de ${e}">
              <button data-mais="${e}" aria-label="Aumentar quantidade de ${e}">+</button>
            </span>
            <button class="rem" data-rem="${e}" aria-label="Remover ${e} do orçamento">Remover</button></li>`;
        }).join("")}</ul>
        <button class="lista-limpar">Limpar lista</button>`;
      pop.querySelector(".lista-x").onclick = fecharLista;
      pop.querySelector(".lista-limpar").onclick = confirmarLimpar;
      pop.querySelectorAll("[data-rem]").forEach(b => b.onclick = () => remover(b.dataset.rem));
      pop.querySelectorAll("[data-menos]").forEach(b => b.onclick = () => definirQtd(b.dataset.menos, qtd(b.dataset.menos) - 1));
      pop.querySelectorAll("[data-mais]").forEach(b => b.onclick = () => definirQtd(b.dataset.mais, qtd(b.dataset.mais) + 1));
      pop.querySelectorAll("[data-qtd]").forEach(i => i.onchange = () => definirQtd(i.dataset.qtd, i.value));
    }
    function abrirLista() {
      renderLista(); pop.hidden = false;
      if (btLista) btLista.setAttribute("aria-expanded", "true");
      pop.querySelector(".lista-x").focus();
    }
    function fecharLista() {
      if (pop.hidden) return;
      pop.hidden = true;
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
      document.body.classList.toggle("com-bandeja", n > 0);
      $("qt").innerHTML = `<span>${n}</span> ite${n === 1 ? "m" : "ns"} no orçamento`;
      const wpp = linkWhatsApp(produtos), mail = linkEmail(produtos);
      const bw = $("bt-wpp"), bm = $("bt-mail");
      if (wpp) { bw.style.display = ""; bw.onclick = () => location.href = wpp; } else bw.style.display = "none";
      if (mail) { bm.style.display = ""; bm.onclick = () => location.href = mail; } else bm.style.display = "none";
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
         class="${c.completo ? "completo" : ""}">${seta}${MD.esc(c.nome)}</a>${c.completo ? '<div class="sep"></div>' : ""}`).join("") : "";
    const secProps = props.length ? (cats.length ? '<div class="sep"></div>' : "") + '<div class="grupo-menu">Propostas básicas (kits)</div>'
      + props.map(p => `<a href="${MD.esc(p.arquivo)}" download>${seta}${MD.esc(p.titulo)}
          <small>${MD.esc(p.itens)} itens</small></a>`).join("") : "";
    menu.innerHTML = secCats + secProps;

    const abrir = () => { menu.classList.add("on"); bd.classList.add("on"); btn.setAttribute("aria-expanded", "true"); };
    const fechar = () => { menu.classList.remove("on"); bd.classList.remove("on"); btn.setAttribute("aria-expanded", "false"); };
    btn.addEventListener("click", () => menu.classList.contains("on") ? fechar() : abrir());
    bd.addEventListener("click", fechar);
    document.addEventListener("keydown", e => { if (e.key === "Escape") fechar(); });
  }
  return { cfg, corEsp, corTexto, ehOtica, norm, esc, carregar, ligarBandeja, montarMenuDownloads, qtd, definirQtd,
           iconeAngulo, seloAngulo,
           lista, tem, alternar, remover, limpar,
           texto, linkWhatsApp, linkEmail };
})();
