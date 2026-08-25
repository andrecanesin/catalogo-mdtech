/* Grade do catálogo: busca + filtros (client-side) + bandeja de orçamento. */
(function () {
  let PRODUTOS = [], META = null;
  const estado = { termo: "", especialidades: new Set(), fornecedores: new Set(), familias: new Set() };

  const $ = s => document.querySelector(s);
  const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };

  function specsLinha(p) {
    const partes = [];
    if (p.diametro) partes.push(`Ø ${p.diametro} mm`);
    if (p.comprimento) partes.push(`${p.comprimento} mm`);
    if (p.angulo) partes.push(p.angulo);
    return partes.join(" · ");
  }

  function passaFiltro(p) {
    const { termo, especialidades, fornecedores, familias } = estado;
    if (termo) {
      const alvo = MD.norm(`${p.codigo} ${p.nome} ${p.descricao}`);
      if (!alvo.includes(termo)) return false;
    }
    if (especialidades.size && !(p.especialidades || []).some(e => especialidades.has(e))) return false;
    if (fornecedores.size && !fornecedores.has(p.fornecedor)) return false;
    if (familias.size && !(p.familias || []).some(f => familias.has(f))) return false;
    return true;
  }

  function cardProduto(p) {
    const cor = MD.corEsp(p.especialidade);
    const card = el("article", "card");

    // foto ou placeholder
    let foto;
    if (p.foto) {
      foto = el("a", "foto");
      foto.href = `produto.html?codigo=${encodeURIComponent(p.codigo)}`;
      foto.appendChild(el("img")).src = p.foto;
      foto.querySelector("img").alt = p.nome;
    } else {
      foto = el("a", "foto sem");
      foto.href = `produto.html?codigo=${encodeURIComponent(p.codigo)}`;
      foto.innerHTML = `<span class="t">sem foto</span><span class="c mono">${p.codigo}</span>`;
    }
    const tag = el("span", "tag", p.especialidade || "—");
    tag.style.background = cor;
    foto.appendChild(tag);
    card.appendChild(foto);

    const corpo = el("div", "corpo");
    const link = el("a"); link.href = `produto.html?codigo=${encodeURIComponent(p.codigo)}`;
    link.innerHTML = `<div class="cod mono">${p.codigo}</div><div class="nome">${p.nome || p.codigo}</div>`;
    link.querySelector(".cod").style.color = cor;
    corpo.appendChild(link);
    corpo.appendChild(el("div", "specs", specsLinha(p) || "&nbsp;"));

    const add = el("button", "add" + (MD.tem(p.codigo) ? " in" : ""));
    add.innerHTML = MD.tem(p.codigo) ? "✓ Na lista" : "+ Orçamento";
    add.addEventListener("click", () => {
      const dentro = MD.alternar(p.codigo);
      add.classList.toggle("in", dentro);
      add.innerHTML = dentro ? "✓ Na lista" : "+ Orçamento";
    });
    corpo.appendChild(add);

    card.appendChild(corpo);
    return card;
  }

  function facet(nome, valores, chave, contagem) {
    const box = el("div");
    box.appendChild(el("h3", null, nome));
    valores.forEach(v => {
      const lab = el("label", "facet");
      const cb = el("input"); cb.type = "checkbox"; cb.value = v;
      cb.checked = estado[chave].has(v);
      cb.addEventListener("change", () => {
        cb.checked ? estado[chave].add(v) : estado[chave].delete(v);
        render();
      });
      lab.appendChild(cb);
      lab.appendChild(el("span", null, v));
      if (contagem && contagem[v] != null) lab.appendChild(el("span", "n", contagem[v]));
      box.appendChild(lab);
    });
    return box;
  }

  function contar(campo) {
    const c = {};
    PRODUTOS.forEach(p => {
      const vals = Array.isArray(p[campo]) ? p[campo] : [p[campo]];
      vals.forEach(v => { if (v) c[v] = (c[v] || 0) + 1; });
    });
    return c;
  }

  function montarFiltros() {
    const side = $("#filtros"); side.innerHTML = "";
    const esp = (META && META.especialidades) || Object.keys(contar("especialidades"));
    const forn = (META && META.fornecedores) || Object.keys(contar("fornecedor"));
    const fam = (META && META.familias) || Object.keys(contar("familias"));
    side.appendChild(facet("Especialidade", esp, "especialidades", contar("especialidades")));
    side.appendChild(facet("Fornecedor", forn, "fornecedores", contar("fornecedor")));
    side.appendChild(facet("Família", fam, "familias", contar("familias")));
    const limpar = el("button", "limpar", "Limpar filtros");
    limpar.addEventListener("click", () => {
      estado.especialidades.clear(); estado.fornecedores.clear(); estado.familias.clear();
      estado.termo = ""; $("#busca").value = "";
      side.querySelectorAll("input").forEach(i => i.checked = false);
      render();
    });
    side.appendChild(limpar);
  }

  function chipsAtivos() {
    const cont = $("#chips"); cont.innerHTML = "";
    const todos = [];
    estado.especialidades.forEach(v => todos.push(["especialidades", v]));
    estado.fornecedores.forEach(v => todos.push(["fornecedores", v]));
    estado.familias.forEach(v => todos.push(["familias", v]));
    todos.forEach(([chave, v]) => {
      const c = el("span", "chip", v);
      const x = el("button", null, "×");
      x.setAttribute("aria-label", `Remover filtro ${v}`);
      x.addEventListener("click", () => {
        estado[chave].delete(v);
        const cb = document.querySelector(`#filtros input[value="${CSS.escape(v)}"]`);
        if (cb) cb.checked = false;
        render();
      });
      c.appendChild(x); cont.appendChild(c);
    });
  }

  function render() {
    const grade = $("#grade");
    const lista = PRODUTOS.filter(passaFiltro);
    grade.innerHTML = "";
    if (!lista.length) {
      grade.appendChild(el("div", "vazio", "<b>Nenhum produto encontrado</b>Ajuste a busca ou remova filtros."));
    } else {
      const frag = document.createDocumentFragment();
      lista.forEach(p => frag.appendChild(cardProduto(p)));
      grade.appendChild(frag);
    }
    $("#cont").innerHTML = `<b>${lista.length}</b> de ${PRODUTOS.length} produtos`;
    chipsAtivos();
  }

  // ---- bandeja de orçamento ----
  function atualizarBandeja() {
    const n = MD.lista().length;
    const b = $("#bandeja");
    b.classList.toggle("on", n > 0);
    $("#qt").innerHTML = `<span>${n}</span> ite${n === 1 ? "m" : "ns"} na lista`;
    const wpp = MD.linkWhatsApp(PRODUTOS), mail = MD.linkEmail(PRODUTOS);
    const bw = $("#bt-wpp"), bm = $("#bt-mail");
    if (wpp) { bw.style.display = ""; bw.onclick = () => location.href = wpp; }
    else bw.style.display = "none";
    if (mail) { bm.style.display = ""; bm.onclick = () => location.href = mail; }
    else bm.style.display = "none";
  }

  function ligarBandeja() {
    $("#bt-limpar").addEventListener("click", () => { MD.limpar(); });
    document.addEventListener("orcamento:mudou", () => {
      atualizarBandeja();
      // re-sincroniza botões dos cards visíveis
      document.querySelectorAll(".card .add").forEach(btn => {
        // rerender é mais simples/seguro:
      });
      render();
    });
  }

  async function iniciar() {
    try {
      const d = await MD.carregar();
      PRODUTOS = d.produtos; META = d.meta;
    } catch (e) {
      $("#grade").innerHTML = `<div class="vazio"><b>Não consegui carregar os produtos</b>
        Rode <code>python gerar.py site</code> e sirva a pasta por um servidor (ex.: <code>python -m http.server</code>).</div>`;
      return;
    }
    $("#busca").addEventListener("input", e => {
      estado.termo = MD.norm(e.target.value.trim()); render();
    });
    montarFiltros();
    ligarBandeja();
    render();
    atualizarBandeja();
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
