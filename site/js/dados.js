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
    try { return JSON.parse(localStorage.getItem(CHAVE)) || []; }
    catch (e) { return []; }
  }
  function salvar(arr) {
    localStorage.setItem(CHAVE, JSON.stringify(arr));
    document.dispatchEvent(new CustomEvent("orcamento:mudou", { detail: arr }));
  }
  function tem(cod) { return lista().includes(cod); }
  function alternar(cod) {
    const arr = lista(); const i = arr.indexOf(cod);
    if (i >= 0) arr.splice(i, 1); else arr.push(cod);
    salvar(arr); return arr.includes(cod);
  }
  function remover(cod) { salvar(lista().filter(c => c !== cod)); }
  function limpar() { salvar([]); }

  // ---- mensagem de orçamento ----
  function _linhas(produtos) {
    const byCod = {}; produtos.forEach(p => byCod[p.codigo] = p);
    return lista().map((c, i) => {
      const p = byCod[c];
      return p ? `${i + 1}. ${p.codigo} — ${p.nome}` : `${i + 1}. ${c}`;
    });
  }
  function texto(produtos) {
    const l = _linhas(produtos);
    return `Olá! Gostaria de um orçamento dos seguintes itens MDTech:\n\n${l.join("\n")}\n\n(${l.length} ite${l.length === 1 ? "m" : "ns"})`;
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
          const p = byCod[c];
          return `<li><span class="mono">${esc(c)}</span><span class="n">${esc(p ? p.nome : "")}</span>
            <button data-rem="${esc(c)}" aria-label="Remover ${esc(c)} do orçamento">Remover</button></li>`;
        }).join("")}</ul>
        <button class="lista-limpar">Limpar lista</button>`;
      pop.querySelector(".lista-x").onclick = fecharLista;
      pop.querySelector(".lista-limpar").onclick = confirmarLimpar;
      pop.querySelectorAll("[data-rem]").forEach(b => b.onclick = () => remover(b.dataset.rem));
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
      else if (!pop.hidden) renderLista();
    }
    function confirmarLimpar() { if (confirm("Remover todos os itens do orçamento?")) limpar(); }
    $("bt-limpar").onclick = confirmarLimpar;
    document.addEventListener("orcamento:mudou", atualizar);
    window.addEventListener("resize", atualizar);
    atualizar();
  }

  return { cfg, corEsp, norm, esc, carregar, ligarBandeja,
           iconeAngulo, seloAngulo,
           lista, tem, alternar, remover, limpar,
           texto, linkWhatsApp, linkEmail };
})();
