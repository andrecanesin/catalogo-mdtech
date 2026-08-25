/* Grade do catálogo: busca + filtros (client-side) + bandeja de orçamento.
   Especialidade é o filtro principal. Família só aparece no desktop.
   No mobile os filtros abrem numa gaveta (botão "Filtrar"). */
(function () {
  let PRODUTOS = [], META = null;
  const estado = { termo: "", especialidades: new Set(), familias: new Set() };

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
    const { termo, especialidades, familias } = estado;
    if (termo) {
      const alvo = MD.norm(`${p.codigo} ${p.nome} ${p.descricao}`);
      if (!alvo.includes(termo)) return false;
    }
    if (especialidades.size && !(p.especialidades || []).some(e => especialidades.has(e))) return false;
    if (familias.size && !(p.familias || []).some(f => familias.has(f))) return false;
    return true;
  }

  function cardProduto(p) {
    const cor = MD.corEsp(p.especialidade);
    const card = el("article", "card");

    let foto;
    const href = `produto.html?codigo=${encodeURIComponent(p.codigo)}`;
    if (p.foto) {
      foto = el("a", "foto"); foto.href = href;
      const im = el("img"); im.src = p.foto; im.alt = p.nome; im.loading = "lazy";
      foto.appendChild(im);
    } else {
      foto = el("a", "foto sem"); foto.href = href;
      foto.innerHTML = `<span class="t">sem foto</span><span class="c mono">${p.codigo}</span>`;
    }
    const tag = el("span", "tag", p.especialidade || "—");
    tag.style.background = cor;
    foto.appendChild(tag);
    card.appendChild(foto);

    const corpo = el("div", "corpo");
    const link = el("a"); link.href = href;
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

  function facetGrupo(nome, valores, chave, contagem, classe) {
    const box = el("div", "grupo" + (classe ? " " + classe : ""));
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

    // cabeçalho da gaveta (só aparece no mobile, via CSS)
    const head = el("div", "drawer-head");
    head.appendChild(el("strong", null, "Filtros"));
    const fechar = el("button", "drawer-x", "×");
    fechar.setAttribute("aria-label", "Fechar filtros");
    fechar.addEventListener("click", fecharGaveta);
    head.appendChild(fechar);
    side.appendChild(head);

    const esp = (META && META.especialidades) || Object.keys(contar("especialidades"));
    const fam = (META && META.familias) || Object.keys(contar("familias"));

    // especialidade = filtro principal (destacado). família = secundário, só desktop.
    side.appendChild(facetGrupo("Especialidade", esp, "especialidades", contar("especialidades"), "grupo-esp"));
    side.appendChild(facetGrupo("Família", fam, "familias", contar("familias"), "so-desktop"));

    const limpar = el("button", "limpar", "Limpar filtros");
    limpar.addEventListener("click", () => {
      estado.especialidades.clear(); estado.familias.clear();
      estado.termo = ""; $("#busca").value = "";
      side.querySelectorAll("input").forEach(i => i.checked = false);
      render();
    });
    side.appendChild(limpar);

    // aplicar / ver resultados (só mobile)
    const aplicar = el("button", "aplicar so-mobile", "Ver resultados");
    aplicar.addEventListener("click", fecharGaveta);
    side.appendChild(aplicar);
  }

  function chipsAtivos() {
    const cont = $("#chips"); cont.innerHTML = "";
    const todos = [];
    estado.especialidades.forEach(v => todos.push(["especialidades", v]));
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

  function nAtivos() { return estado.especialidades.size + estado.familias.size; }

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
    const n = nAtivos();
    $("#fnum").textContent = n ? ` (${n})` : "";
  }

  // ---- gaveta mobile ----
  function abrirGaveta() { $("#filtros").classList.add("aberto"); $("#backdrop").classList.add("on"); }
  function fecharGaveta() { $("#filtros").classList.remove("aberto"); $("#backdrop").classList.remove("on"); }

  // ---- bandeja de orçamento ----
  function atualizarBandeja() {
    const n = MD.lista().length;
    $("#bandeja").classList.toggle("on", n > 0);
    $("#qt").innerHTML = `<span>${n}</span> ite${n === 1 ? "m" : "ns"} na lista`;
    const wpp = MD.linkWhatsApp(PRODUTOS), mail = MD.linkEmail(PRODUTOS);
    const bw = $("#bt-wpp"), bm = $("#bt-mail");
    if (wpp) { bw.style.display = ""; bw.onclick = () => location.href = wpp; } else bw.style.display = "none";
    if (mail) { bm.style.display = ""; bm.onclick = () => location.href = mail; } else bm.style.display = "none";
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
    $("#busca").addEventListener("input", e => { estado.termo = MD.norm(e.target.value.trim()); render(); });
    $("#btn-filtrar").addEventListener("click", abrirGaveta);
    $("#backdrop").addEventListener("click", fecharGaveta);
    $("#bt-limpar").addEventListener("click", () => MD.limpar());
    document.addEventListener("orcamento:mudou", () => { atualizarBandeja(); render(); });

    montarFiltros();
    render();
    atualizarBandeja();
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
