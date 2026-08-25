/* Página de produto: lê ?codigo= e monta a ficha (mesma regra de vermelho). */
(function () {
  const $ = s => document.querySelector(s);
  const params = new URLSearchParams(location.search);
  const cod = params.get("codigo");

  const miss = '<span class="miss">—</span>';
  const v = x => (x != null && String(x).trim() !== "") ? String(x) : miss;

  function normEq(a, b) {
    const n = s => (s || "").toUpperCase().replace(/\s|\.C$/g, "").replace(/\.$/, "");
    return n(a) === n(b);
  }

  async function iniciar() {
    let produtos;
    try { produtos = await fetch("produtos.json").then(r => r.json()); }
    catch (e) {
      $("#alvo").innerHTML = `<div class="vazio"><b>Não consegui carregar o produto</b>
        Sirva a pasta por um servidor local.</div>`; return;
    }
    const p = produtos.find(x => x.codigo === cod) || produtos.find(x => normEq(x.codigo, cod));
    if (!p) {
      $("#alvo").innerHTML = `<div class="vazio"><b>Produto não encontrado</b>
        O código “${cod || ""}” não está no catálogo. <a href="index.html" style="color:var(--navy)">Voltar ao catálogo</a>.</div>`;
      return;
    }
    document.title = `${p.codigo} — ${p.nome} · MDTech`;
    const cor = MD.corEsp(p.especialidade);

    // foto
    const foto = p.foto
      ? `<div class="foto-g"><img src="${p.foto}" alt="${p.nome}"></div>`
      : `<div class="foto-g sem"><span class="t">sem foto</span><span class="mono" style="color:var(--mut)">${p.codigo}</span></div>`;

    // especialidades (cross-listing) como tags
    const esps = (p.especialidades && p.especialidades.length ? p.especialidades : [p.especialidade])
      .filter(Boolean)
      .map(e => `<span class="esp-tag" style="background:${MD.corEsp(e)}">${e}</span>`).join(" ");

    const anvisaMiss = !(p.anvisa && p.anvisa.trim());
    const ncmMiss = !(p.ncm && p.ncm.trim());

    $("#alvo").innerHTML = `
      <a class="voltar" href="index.html">← Voltar ao catálogo</a>
      <div class="ph">
        ${foto}
        <div class="info">
          ${esps}
          <h1>${p.nome || p.codigo}</h1>
          <div class="cod-g mono" style="color:${cor}">${p.codigo}</div>
          <table class="tabela">
            <tr><td class="k">Família</td><td class="v">${v(p.familia)}</td></tr>
            <tr><td class="k">Diâmetro (Ø)</td><td class="v">${p.diametro ? p.diametro + " mm" : miss}</td></tr>
            <tr><td class="k">Comprimento útil</td><td class="v">${p.comprimento ? p.comprimento + " mm" : miss}</td></tr>
            <tr><td class="k">Ângulo</td><td class="v">${v(p.angulo)}</td></tr>
            <tr><td class="k">Autoclavável</td><td class="v">${v(p.autoclavavel)}</td></tr>
          </table>
          <div class="regbox">
            <div class="col a"><div class="rlab">Registro ANVISA</div>
              <div class="rval ${anvisaMiss ? "miss" : ""}">${anvisaMiss ? "em registro" : p.anvisa}</div></div>
            <div class="col b"><div class="rlab">NCM</div>
              <div class="rval ${ncmMiss ? "miss" : ""}">${ncmMiss ? "—" : p.ncm}</div></div>
          </div>
          <div class="acoes" id="acoes"></div>
          <div class="desc-g"><div class="k">Descrição (padrão de cadastro)</div>
            <div class="t">${p.descricao || miss}</div></div>
        </div>
      </div>`;

    // ações
    const acoes = $("#acoes");
    const add = document.createElement("button");
    add.className = "b-add" + (MD.tem(p.codigo) ? " in" : "");
    add.textContent = MD.tem(p.codigo) ? "✓ Na lista de orçamento" : "+ Adicionar ao orçamento";
    add.addEventListener("click", () => {
      const dentro = MD.alternar(p.codigo);
      add.classList.toggle("in", dentro);
      add.textContent = dentro ? "✓ Na lista de orçamento" : "+ Adicionar ao orçamento";
    });
    acoes.appendChild(add);

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
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
