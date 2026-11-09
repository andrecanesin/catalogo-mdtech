/* Página de produto: lê ?codigo= e monta a ficha (mesma regra de vermelho). */
(function () {
  const $ = s => document.querySelector(s);
  const params = new URLSearchParams(location.search);
  const cod = params.get("codigo");

  const toque = window.matchMedia("(pointer:coarse)").matches;   // celular/tablet: "Toque", não "Clique"
  const miss = '<span class="miss">—</span>';
  const naoAplica = '<span class="na">não se aplica</span>';   // campo que não existe para o produto (≠ pendente)
  const esc = s => MD.esc(s);
  const v = x => (x != null && String(x).trim() !== "") ? esc(x) : miss;

  // Diâmetro: usa diametro_fmt (já vem pronto "16,5 Fr" ou "5 mm" do site.py);
  // se o produtos.json ainda for antigo (sem diametro_fmt), cai pro comportamento
  // anterior (mm) e por último tenta diametro_fr, senão mostra "—".
  function fmtDiametro(p) {
    if (p.diametro_fmt && String(p.diametro_fmt).trim() !== "") return p.diametro_fmt;
    if (p.diametro && String(p.diametro).trim() !== "") return p.diametro + " mm";
    if (p.diametro_fr && String(p.diametro_fr).trim() !== "") return p.diametro_fr + " Fr";
    return null;
  }

  function normEq(a, b) {
    const n = s => (s || "").toUpperCase().replace(/\s|\.C$/g, "").replace(/\.$/, "");
    return n(a) === n(b);
  }

  // ---- zoom da foto (lightbox) ----
  // Cria o próprio markup do lightbox via JS (não depende de nada estar
  // pré-existente no produto.html — funciona mesmo se o HTML ficar desatualizado).
  function garantirZoomDom() {
    let bg = $("#zoom-bg");
    if (bg) return bg;
    bg = document.createElement("div");
    bg.id = "zoom-bg"; bg.className = "zoom-bg"; bg.setAttribute("aria-hidden", "true");
    bg.innerHTML = `<button class="zoom-x" id="zoom-x" aria-label="Fechar zoom">×</button>
      <img id="zoom-img" alt="">`;
    document.body.appendChild(bg);
    return bg;
  }

  function ligarZoom(src, alt) {
    const bg = garantirZoomDom();
    const img = bg.querySelector("#zoom-img"), botaoX = bg.querySelector("#zoom-x");
    const abrir = (e) => { e.preventDefault(); img.src = src; img.alt = alt; bg.classList.add("on"); };
    const fechar = () => bg.classList.remove("on");
    document.querySelectorAll(".foto-g img.principal").forEach(el => {
      el.addEventListener("click", abrir);
      el.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") abrir(e); });
    });
    bg.addEventListener("click", fechar);
    botaoX.addEventListener("click", (e) => { e.stopPropagation(); fechar(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") fechar(); });
  }

  async function iniciar() {
    MD.montarMenuDownloads();          // menu "Catálogos e propostas" (também no topo das páginas internas)
    let produtos;
    try { produtos = await fetch("produtos.json").then(r => r.json()); }
    catch (e) {
      $("#alvo").innerHTML = `<div class="vazio"><b>Não consegui carregar o produto</b>
        Sirva a pasta por um servidor local.</div>`; return;
    }
    const p = produtos.find(x => x.codigo === cod) || produtos.find(x => normEq(x.codigo, cod));
    if (!p) {
      $("#alvo").innerHTML = `<div class="vazio"><b>Produto não encontrado</b>
        O código “${esc(cod || "")}” não está no catálogo. <a href="index.html" style="color:var(--navy)">Voltar ao catálogo</a>.</div>`;
      return;
    }
    document.title = `${p.codigo} — ${p.nome} · MDTech`;
    const cor = MD.corTexto(p.especialidade);

    // foto (com zoom + selo de ângulo)
    const foto = p.foto
      ? `<div class="foto-g">
           <img class="principal" src="${esc(p.foto)}" alt="${esc(p.codigo + " — " + p.nome)}" tabindex="0"
                role="button" aria-label="Ampliar foto de ${esc(p.codigo)}">
           <span class="zoom-hint">🔍 ${toque ? "Toque" : "Clique"} na imagem para ampliar</span>
           ${MD.seloAngulo(p.angulo, p.familia)}
         </div>`
      : `<div class="foto-g sem"><span class="t">sem foto</span><span class="mono" style="color:var(--mut)">${esc(p.codigo)}</span></div>`;

    // especialidades (cross-listing) como tags
    const esps = (p.especialidades && p.especialidades.length ? p.especialidades : [p.especialidade])
      .filter(Boolean)
      .map(e => `<span class="esp-tag" style="background:${MD.corTexto(e)}">${esc(e)}</span>`).join(" ");

    const anvisaMiss = !(p.anvisa && p.anvisa.trim());
    const ncmMiss = !(p.ncm && p.ncm.trim());
    const diametroTxt = fmtDiametro(p);

    $("#alvo").innerHTML = `
      <a class="voltar" href="index.html">← Voltar ao catálogo</a>
      <div class="ph">
        ${foto}
        <div class="info">
          ${esps}
          <h1>${esc(p.nome || p.codigo)}</h1>
          <div class="cod-g mono" style="color:${cor}">${esc(p.codigo)}</div>
          <table class="tabela">
            <tr><td class="k">Família</td><td class="v">${v(p.familia)}</td></tr>
            <tr><td class="k">Diâmetro (Ø)</td><td class="v">${diametroTxt ? esc(diametroTxt) : miss}</td></tr>
            <tr><td class="k">Comprimento útil</td><td class="v">${p.comprimento ? esc(p.comprimento) + " mm" : miss}</td></tr>
            <tr><td class="k">Ângulo</td><td class="v">${p.angulo ? esc(p.angulo) : (MD.ehOtica(p) ? miss : naoAplica)}</td></tr>
            <tr><td class="k">Autoclavável</td><td class="v">${v(p.autoclavavel)}</td></tr>
          </table>
          <div class="regbox">
            <div class="col a"><div class="rlab">Registro ANVISA</div>
              <div class="rval ${anvisaMiss ? "miss" : ""}">${anvisaMiss ? "em registro" : esc(p.anvisa)}</div></div>
            <div class="col b"><div class="rlab">NCM</div>
              <div class="rval ${ncmMiss ? "miss" : ""}">${ncmMiss ? "—" : esc(p.ncm)}</div></div>
          </div>
          ${MD.mostrarPreco() ? `<div class="preco-g"><span class="k">Preço de tabela</span>
            <b>${p.preco ? esc(MD.brl(p.preco)) : "Sob consulta"}</b>
            ${p.preco && p.preco_ficticio ? `<small>${esc((MD.cfg.precos || {}).aviso || "Valores ilustrativos.")}</small>` : ""}</div>` : ""}
          <div class="acoes" id="acoes"></div>
          <div class="desc-g"><div class="k">Descrição (padrão de cadastro)</div>
            <div class="t">${p.descricao ? esc(p.descricao) : miss}</div></div>
        </div>
      </div>`;

    // ações
    const acoes = $("#acoes");
    const add = document.createElement("button");
    add.className = "b-add" + (MD.tem(p.codigo) ? " in" : "");
    add.textContent = MD.tem(p.codigo) ? "✓ No orçamento" : "+ Adicionar no orçamento";
    const marcar = () => {
      const dentro = MD.tem(p.codigo);
      add.classList.toggle("in", dentro);
      add.setAttribute("aria-pressed", dentro ? "true" : "false");
      add.textContent = dentro ? "✓ No orçamento" : "+ Adicionar no orçamento";
    };
    marcar();
    add.addEventListener("click", () => MD.alternar(p.codigo));
    document.addEventListener("orcamento:mudou", marcar);   // também quando remove pela lista
    acoes.appendChild(add);

    // ficha técnica em PDF (gerada por `python gerar.py fichas --separados`
    // e copiada para site/fichas/<codigo>.pdf pelo gerar.py site)
    if (p.ficha_pdf) {
      const bf = document.createElement("a");
      bf.className = "b-ficha"; bf.href = p.ficha_pdf; bf.download = "";
      bf.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16"/></svg> Baixar ficha técnica (PDF)`;
      acoes.appendChild(bf);
    }

    const wpp = MD.linkWhatsApp(produtos);
    if (wpp && (MD.cfg.contato && MD.cfg.contato.whatsapp)) {
      const b = document.createElement("button");
      b.className = "b-wpp"; b.textContent = "Pedir orçamento no WhatsApp";
      b.addEventListener("click", () => {
        if (!MD.tem(p.codigo)) MD.alternar(p.codigo);
        location.href = MD.linkWhatsApp(produtos);
      });
      acoes.appendChild(b);
    }

    if (p.foto) ligarZoom(p.foto, p.codigo + " — " + p.nome);

    MD.ligarBandeja(produtos);

    // "Voltar ao catálogo" volta ao ponto anterior (busca, filtros e página ficam na URL da grade)
    const volta = document.querySelector(".voltar");
    if (volta) volta.addEventListener("click", e => {
      try {
        const ref = new URL(document.referrer);
        if (ref.origin === location.origin && /(index\.html|\/)$/.test(ref.pathname) && history.length > 1) {
          e.preventDefault(); history.back();
        }
      } catch (err) { /* sem referrer: segue o link */ }
    });
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
