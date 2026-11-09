/* Grade do catálogo: busca + filtros (client-side) + paginação + bandeja de orçamento.
   Especialidade é o filtro principal. Família só aparece no desktop.
   No mobile os filtros abrem numa gaveta (botão "Filtrar"). */
(function () {
  let PRODUTOS = [], META = null, PROPOSTAS = [];
  const estado = { termo: "", especialidades: new Set(), familias: new Set(), proposta: "", pagina: 1 };
  const propostaAtiva = () => PROPOSTAS.find(k => k.id === estado.proposta) || null;
  const PORPAGINA = (MD.cfg.produtosPorPagina) || 20;

  const $ = s => document.querySelector(s);
  const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };

  function specsLinha(p) {
    const partes = [];
    const diam = p.diametro_fmt || (p.diametro ? p.diametro + " mm" : (p.diametro_fr ? p.diametro_fr + " Fr" : null));
    if (diam) partes.push(`Ø ${diam}`);
    if (p.comprimento) partes.push(`${p.comprimento} mm`);
    if (p.angulo) partes.push(p.angulo);
    return partes.join(" · ");
  }

  function passaFiltro(p) {
    const { termo, especialidades, familias } = estado;
    const kit = propostaAtiva();
    if (kit && !kit.itens_lista.some(i => i.codigo === p.codigo)) return false;
    if (termo) {
      const alvo = MD.norm(`${p.codigo} ${p.nome} ${p.descricao}`);
      // todas as palavras precisam aparecer, em qualquer ordem ("pinça maryland" = "maryland pinça")
      if (!termo.split(/\s+/).filter(Boolean).every(t => alvo.includes(t))) return false;
    }
    if (especialidades.size && !(p.especialidades || []).some(e => especialidades.has(e))) return false;
    if (familias.size && !(p.familias || []).some(f => familias.has(f))) return false;
    return true;
  }

  // estado visual do botão "+ Adicionar no orçamento" (sem recriar a grade: o foco do teclado fica onde está)
  function marcarAdd(btn) {
    const dentro = MD.tem(btn.dataset.cod);
    btn.classList.toggle("in", dentro);
    btn.setAttribute("aria-pressed", dentro ? "true" : "false");
    btn.textContent = dentro ? "✓ No orçamento" : "+ Adicionar no orçamento";
  }
  function sincronizarBotoes() { document.querySelectorAll(".card .add").forEach(marcarAdd); }

  // Com filtro de família ativo, códigos listados em cfg.ultimosNaFamilia[familia]
  // vão para o fim da lista (ordem estável). Sem filtro de família, vale a ordem da base.
  function ordenar(lista) {
    const kit = propostaAtiva();
    if (kit) {   // dentro de uma proposta, vale a ordem dela (itens principais primeiro)
      const pos = {}; kit.itens_lista.forEach((i, n) => pos[i.codigo] = n);
      return lista.slice().sort((a, b) => pos[a.codigo] - pos[b.codigo]);
    }
    const regras = MD.cfg.ultimosNaFamilia || {};
    const ultimos = new Set();
    estado.familias.forEach(f => (regras[f] || []).forEach(c => ultimos.add(c)));
    if (!ultimos.size) return lista;
    return lista.filter(p => !ultimos.has(p.codigo)).concat(lista.filter(p => ultimos.has(p.codigo)));
  }

  function cardProduto(p) {
    const cor = MD.corTexto(p.especialidade);
    const card = el("article", "card");

    let foto;
    const href = `produto.html?codigo=${encodeURIComponent(p.codigo)}`;
    if (p.foto) {
      foto = el("a", "foto"); foto.href = href;
      const im = el("img"); im.src = p.foto_thumb || p.foto; im.alt = `${p.codigo} — ${p.nome}`;
      im.loading = "lazy"; im.decoding = "async";
      foto.appendChild(im);
    } else {
      foto = el("a", "foto sem"); foto.href = href;
      foto.innerHTML = `<span class="t">sem foto</span><span class="c mono">${MD.esc(p.codigo)}</span>`;
    }
    const esps = (p.especialidades && p.especialidades.length ? p.especialidades : [p.especialidade]).filter(Boolean);
    const tags = el("span", "tags");
    esps.forEach(e => {
      const t = el("span", "tag", MD.esc(e));
      t.style.background = MD.corTexto(e);
      tags.appendChild(t);
    });
    foto.appendChild(tags);
    card.appendChild(foto);

    const corpo = el("div", "corpo");
    const link = el("a"); link.href = href;
    link.innerHTML = `<div class="cod mono">${MD.esc(p.codigo)}</div><div class="nome">${MD.esc(p.nome || p.codigo)}</div>`;
    link.querySelector(".cod").style.color = cor;
    corpo.appendChild(link);
    corpo.appendChild(el("div", "specs", MD.esc(specsLinha(p)) || "&nbsp;"));
    if (MD.mostrarPreco()) corpo.appendChild(el("div", "preco" + (p.preco ? "" : " sem"), p.preco ? MD.esc(MD.brl(p.preco)) : "Preço sob consulta"));

    const add = el("button", "add");
    add.dataset.cod = p.codigo;
    marcarAdd(add);
    add.addEventListener("click", () => MD.alternar(p.codigo));   // o evento orcamento:mudou atualiza os botões
    corpo.appendChild(add);

    const kit = propostaAtiva(), it = kit && kit.itens_lista.find(i => i.codigo === p.codigo);
    if (it) corpo.insertBefore(el("div", "kit-qtd", `Na proposta: ${it.qtd} un.`), add);
    card.appendChild(corpo);
    return card;
  }

  function facetGrupo(nome, valores, chave, contagem, classe, colapsavel) {
    const box = colapsavel ? el("details", "grupo " + classe) : el("div", "grupo" + (classe ? " " + classe : ""));
    if (colapsavel) {
      box.appendChild(el("summary", null, `${MD.esc(nome)} (${valores.length})`));
      if (window.matchMedia("(min-width:901px)").matches || estado[chave].size) box.open = true;
    } else box.appendChild(el("h3", null, nome));
    valores.forEach(v => {
      const lab = el("label", "facet");
      const cb = el("input"); cb.type = "checkbox"; cb.value = v;
      cb.checked = estado[chave].has(v);
      cb.addEventListener("change", () => {
        cb.checked ? estado[chave].add(v) : estado[chave].delete(v);
        estado.pagina = 1;
        render();
      });
      lab.appendChild(cb);
      lab.appendChild(el("span", null, MD.esc(v)));
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

    // especialidade = filtro principal (destacado). família = secundário, recolhível (também no celular).
    side.appendChild(facetGrupo("Especialidade", esp, "especialidades", contar("especialidades"), "grupo-esp"));

    // proposta básica (kit): escolha única; mostra só os itens dela e permite pedir o orçamento da proposta toda
    if (PROPOSTAS.length) {
      const box = el("div", "grupo grupo-prop"); box.appendChild(el("h3", null, "Proposta básica"));
      PROPOSTAS.forEach(k => {
        const lab = el("label", "facet"), cb = el("input"); cb.type = "checkbox"; cb.value = k.id; cb.checked = estado.proposta === k.id;
        cb.addEventListener("change", () => {
          estado.proposta = cb.checked ? k.id : ""; estado.pagina = 1;
          box.querySelectorAll("input").forEach(i => { i.checked = i.value === estado.proposta; });
          render();
        });
        lab.appendChild(cb); lab.appendChild(el("span", null, MD.esc(k.titulo))); lab.appendChild(el("span", "n", k.itens_lista.length));
        box.appendChild(lab);
      });
      side.appendChild(box);
    }
    side.appendChild(facetGrupo("Família", fam, "familias", contar("familias"), "grupo-fam", true));

    const limpar = el("button", "limpar", "Limpar filtros");
    limpar.addEventListener("click", () => {
      estado.especialidades.clear(); estado.familias.clear(); estado.proposta = "";
      estado.termo = ""; estado.pagina = 1; $("#busca").value = "";
      side.querySelectorAll("input").forEach(i => i.checked = false);
      render();
    });
    side.appendChild(limpar);

    // aplicar / ver resultados (só mobile)
    const aplicar = el("button", "aplicar so-mobile", "Ver resultados");
    aplicar.id = "bt-aplicar";
    aplicar.addEventListener("click", fecharGaveta);
    side.appendChild(aplicar);
  }

  function chipsAtivos() {
    const cont = $("#chips"); cont.innerHTML = "";
    const todos = [];
    estado.especialidades.forEach(v => todos.push(["especialidades", v]));
    estado.familias.forEach(v => todos.push(["familias", v]));
    const kitAtivo = propostaAtiva();
    if (kitAtivo) {
      const c = el("span", "chip", "Proposta: " + MD.esc(kitAtivo.titulo)), x = el("button", null, "×");
      x.setAttribute("aria-label", "Remover filtro proposta " + kitAtivo.titulo);
      x.addEventListener("click", () => {
        estado.proposta = ""; estado.pagina = 1;
        document.querySelectorAll("#filtros .grupo-prop input").forEach(i => { i.checked = false; });
        render();
      });
      c.appendChild(x); cont.appendChild(c);
    }
    todos.forEach(([chave, v]) => {
      const c = el("span", "chip", MD.esc(v));
      const x = el("button", null, "×");
      x.setAttribute("aria-label", `Remover filtro ${v}`);
      x.addEventListener("click", () => {
        estado[chave].delete(v);
        estado.pagina = 1;
        const cb = document.querySelector(`#filtros input[value="${CSS.escape(v)}"]`);
        if (cb) cb.checked = false;
        render();
      });
      c.appendChild(x); cont.appendChild(c);
    });
  }

  function nAtivos() { return estado.especialidades.size + estado.familias.size + (estado.proposta ? 1 : 0); }

  // faixa da proposta escolhida: resumo, PDF e "adicionar tudo ao orçamento" (depois, "Pedir por e-mail" na bandeja)
  function faixaProposta() {
    let f = $("#faixa-prop");
    const kit = propostaAtiva();
    if (!kit) { if (f) f.remove(); return; }
    if (!f) { f = el("div", "faixa-prop"); f.id = "faixa-prop"; $("#grade").parentNode.insertBefore(f, $("#grade")); }
    const un = kit.itens_lista.reduce((s, i) => s + i.qtd, 0);
    const tudo = kit.itens_lista.every(i => MD.qtd(i.codigo) >= i.qtd);
    f.innerHTML = `<div><b>Proposta básica: ${MD.esc(kit.titulo)}</b><span>${kit.itens_lista.length} itens · ${un} unidades</span></div>
      <div class="acoes"><button class="pr-add${tudo ? " in" : ""}" type="button">${tudo ? "✓ Proposta no orçamento" : "Adicionar a proposta ao orçamento"}</button>
      <a class="pr-pdf" href="${MD.esc(kit.arquivo)}" download>Baixar PDF</a></div>`;
    f.querySelector(".pr-add").onclick = () => { if (!tudo) MD.adicionarVarios(kit.itens_lista); };
  }

  // ---- paginação ----
  function montarPaginacao(totalItens) {
    const box = $("#paginacao"); box.innerHTML = "";
    const totalPag = Math.max(1, Math.ceil(totalItens / PORPAGINA));
    if (totalPag <= 1) return;
    if (estado.pagina > totalPag) estado.pagina = totalPag;

    const irPara = n => { estado.pagina = n; render(); window.scrollTo({ top: 0, behavior: "smooth" }); };

    const ant = el("button", null, "‹");
    ant.disabled = estado.pagina === 1;
    ant.addEventListener("click", () => irPara(estado.pagina - 1));
    box.appendChild(ant);

    // janela de páginas em volta da atual (máx 5 números)
    let ini = Math.max(1, estado.pagina - 2);
    let fim = Math.min(totalPag, ini + 4);
    ini = Math.max(1, fim - 4);
    for (let n = ini; n <= fim; n++) {
      const b = el("button", n === estado.pagina ? "ativo" : "", String(n));
      b.addEventListener("click", () => irPara(n));
      box.appendChild(b);
    }

    const prox = el("button", null, "›");
    prox.disabled = estado.pagina === totalPag;
    prox.addEventListener("click", () => irPara(estado.pagina + 1));
    box.appendChild(prox);

    box.appendChild(el("span", "rt", `página ${estado.pagina} de ${totalPag}`));
  }

  function render() {
    const grade = $("#grade");
    const listaFiltrada = ordenar(PRODUTOS.filter(passaFiltro));
    const inicio = (estado.pagina - 1) * PORPAGINA;
    const paginaAtual = listaFiltrada.slice(inicio, inicio + PORPAGINA);

    grade.innerHTML = "";
    if (!listaFiltrada.length) {
      grade.appendChild(el("div", "vazio", "<b>Nenhum produto encontrado</b>Ajuste a busca ou remova filtros."));
    } else {
      const frag = document.createDocumentFragment();
      paginaAtual.forEach(p => frag.appendChild(cardProduto(p)));
      grade.appendChild(frag);
    }
    const ilustr = MD.mostrarPreco() && PRODUTOS.some(p => p.preco && p.preco_ficticio);
    $("#cont").innerHTML = `<b>${listaFiltrada.length}</b> de ${PRODUTOS.length} produtos` +
      (ilustr ? ` <span class="cont-aviso">· preços ilustrativos</span>` : "");
    chipsAtivos(); faixaProposta();
    const n = nAtivos();
    $("#fnum").textContent = n ? ` (${n})` : "";
    montarPaginacao(listaFiltrada.length);
    const ap = $("#bt-aplicar"), nr = listaFiltrada.length;
    if (ap) ap.textContent = `Ver ${nr} resultado${nr === 1 ? "" : "s"}`;
    gravarURL();
  }

  // ---- estado na URL: voltar do detalhe (ou compartilhar o link) mantém busca, filtros e página ----
  function lerURL() {
    const u = new URLSearchParams(location.search);
    const q = u.get("q");
    if (q) { $("#busca").value = q; estado.termo = MD.norm(q.trim()); }
    u.getAll("esp").forEach(v => estado.especialidades.add(v));
    u.getAll("fam").forEach(v => estado.familias.add(v));
    estado.proposta = u.get("prop") || "";
    estado.pagina = Math.max(1, parseInt(u.get("p"), 10) || 1);
  }
  function gravarURL() {
    const u = new URLSearchParams();
    const q = $("#busca").value.trim();
    if (q) u.set("q", q);
    estado.especialidades.forEach(v => u.append("esp", v));
    estado.familias.forEach(v => u.append("fam", v));
    if (estado.proposta) u.set("prop", estado.proposta);
    if (estado.pagina > 1) u.set("p", estado.pagina);
    const s = u.toString();
    try { history.replaceState(null, "", location.pathname + (s ? "?" + s : "")); } catch (e) { /* file:// */ }
  }

  // ---- gaveta mobile (filtros) ----
  function abrirGaveta() {
    $("#filtros").classList.add("aberto"); $("#backdrop").classList.add("on");
    $("#btn-filtrar").setAttribute("aria-expanded", "true");
    const x = document.querySelector("#filtros .drawer-x"); if (x) x.focus();
  }
  function fecharGaveta() {
    if (!$("#filtros").classList.contains("aberto")) return;
    $("#filtros").classList.remove("aberto"); $("#backdrop").classList.remove("on");
    $("#btn-filtrar").setAttribute("aria-expanded", "false");
    $("#btn-filtrar").focus();
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
    $("#busca").addEventListener("input", e => { estado.termo = MD.norm(e.target.value.trim()); estado.pagina = 1; render(); });
    // busca/filtros/página vindos da URL (ex.: do detalhe de um produto: index.html?q=termo)
    lerURL();
    const bf = $("#btn-filtrar");
    bf.setAttribute("aria-controls", "filtros"); bf.setAttribute("aria-expanded", "false");
    bf.addEventListener("click", abrirGaveta);
    $("#backdrop").addEventListener("click", fecharGaveta);
    document.addEventListener("keydown", e => { if (e.key === "Escape") fecharGaveta(); });
    document.addEventListener("orcamento:mudou", () => { sincronizarBotoes(); faixaProposta(); });
    try { const r = await fetch("propostas.json"); PROPOSTAS = (r.ok ? await r.json() : []).filter(k => k.id && (k.itens_lista || []).length); } catch (e) { PROPOSTAS = []; }

    montarFiltros();
    MD.montarMenuDownloads();
    render();
    MD.ligarBandeja(PRODUTOS);
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
