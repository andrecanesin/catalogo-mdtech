/* "Colar pedido": para o vendedor transformar o pedido que o cliente mandou (WhatsApp ou e-mail) em lista de orçamento, com os preços,
   sem procurar item a item. Só aparece para vendedor conectado (como o Suporte). O markup é criado aqui.
   Lê o texto do pedido gerado pelo site ("1. A0322 — nome — qtd: 1") e também listas soltas ("A0322 x2"); ver MD.lerPedido (dados.js). */
(function () {
  if (!(window.MD && MD.contaAtiva && MD.contaAtiva() && MD.ehVendedor())) return;
  function iniciar() {
    const ref = document.getElementById("btn-catalogos");
    if (!ref) return;
    const bt = document.createElement("button");
    bt.type = "button"; bt.className = "btn-catalogos btn-pedido"; bt.setAttribute("aria-haspopup", "dialog");
    bt.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" width="16" height="16" aria-hidden="true"><rect x="8" y="3" width="11" height="14" rx="2"/><path d="M5 7v12a2 2 0 0 0 2 2h9"/></svg>' +
      '<span class="l-longo">Colar pedido do cliente</span><span class="l-curto">Colar pedido</span>';
    ref.after(bt);

    const raiz = document.createElement("div");
    raiz.innerHTML = `
      <div class="sup-bg" id="ped-bg" hidden></div>
      <div class="sup-panel" id="ped-panel" role="dialog" aria-modal="true" aria-labelledby="ped-t" hidden>
        <div class="sup-head"><strong id="ped-t">Colar pedido do cliente</strong>
          <button class="sup-x" id="ped-x" type="button" aria-label="Fechar">×</button></div>
        <p class="sup-sub">Cole aqui a mensagem que o cliente enviou. A lista de orçamento é montada com os itens e as quantidades, e você vê os preços.</p>
        <label class="sup-campo">Pedido do cliente <textarea id="ped-txt" rows="8" placeholder="1. A0322 — Endoscópio Rígido — qtd: 1&#10;2. M1015 — Cabo de Alto Frequência — qtd: 2"></textarea></label>
        <label class="ped-subst" id="ped-subst-l" hidden><input type="checkbox" id="ped-subst" checked> Substituir a lista atual (<span id="ped-n"></span>)</label>
        <p class="sup-st" id="ped-st" role="status" aria-live="polite"></p>
        <button class="sup-go sup-mail off" id="ped-go" type="button" aria-disabled="true">Montar a lista</button>
      </div>`;
    document.body.appendChild(raiz);
    const q = id => raiz.querySelector("#" + id);
    const e = { bg: q("ped-bg"), painel: q("ped-panel"), x: q("ped-x"), txt: q("ped-txt"), st: q("ped-st"), go: q("ped-go"),
      sl: q("ped-subst-l"), s: q("ped-subst"), n: q("ped-n") };
    let produtos = null, soltar = null;
    const pronto = () => e.txt.value.trim().length > 0;
    function checar() { e.go.setAttribute("aria-disabled", pronto() ? "false" : "true"); e.go.classList.toggle("off", !pronto()); }
    function fechar() {
      if (e.painel.hidden) return;
      e.painel.hidden = true; e.bg.hidden = true; if (soltar) { soltar(); soltar = null; } bt.focus();
    }
    async function abrir() {
      const n = MD.lista().length;
      e.sl.hidden = n === 0; e.n.textContent = n + " ite" + (n === 1 ? "m" : "ns");
      e.st.textContent = ""; e.st.className = "sup-st";
      e.painel.hidden = false; e.bg.hidden = false; checar(); e.txt.focus();
      soltar = MD.prenderFoco(e.painel);
      if (!produtos) { try { produtos = await (await fetch("produtos.json")).json(); } catch (err) { /* tenta ao montar */ } }
    }
    async function montar() {
      if (!pronto()) { e.txt.focus(); return; }
      if (!produtos) { try { produtos = await (await fetch("produtos.json")).json(); }
        catch (err) { e.st.className = "sup-st erro"; e.st.textContent = "Sem internet: não consegui ler o catálogo. Tente de novo."; return; } }
      const r = MD.lerPedido(e.txt.value, produtos);
      if (!r.itens.length) {
        e.st.className = "sup-st erro";
        e.st.textContent = "Não encontrei nenhum código do catálogo no texto." + (r.desconhecidos.length ? " Não reconhecidos: " + r.desconhecidos.join(", ") + "." : "");
        return;
      }
      if (!e.sl.hidden && e.s.checked) MD.substituirLista(r.itens);
      else MD.adicionarVarios(r.itens);
      const aviso = r.desconhecidos.length ? " Não encontrados no catálogo: " + r.desconhecidos.join(", ") + " (confira com o cliente)." : "";
      e.txt.value = ""; fechar();
      const li = document.createElement("div");
      li.className = "aviso-pedido"; li.setAttribute("role", "status");
      li.textContent = r.itens.length + " ite" + (r.itens.length === 1 ? "m" : "ns") + " na lista." + aviso;
      document.body.appendChild(li); setTimeout(() => li.remove(), aviso ? 9000 : 5000);
      const ver = document.getElementById("bt-lista"); if (ver) setTimeout(() => ver.click(), 150);   // já mostra a lista com os preços
    }
    bt.addEventListener("click", () => e.painel.hidden ? abrir() : fechar());
    e.x.addEventListener("click", fechar); e.bg.addEventListener("click", fechar);
    document.addEventListener("keydown", ev => { if (ev.key === "Escape") fechar(); });
    e.txt.addEventListener("input", checar);
    e.go.addEventListener("click", montar);
  }
  document.addEventListener("DOMContentLoaded", iniciar);
})();
