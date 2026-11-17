/* App (PWA) do lado da página: aviso de conexão, convite para instalar (só vendedores conectados) e fotos para usar sem internet.
   O service worker (sw.js) é registrado em dados.js; aqui só a parte que o vendedor vê. Criado via JS: não depende de markup fixo. */
(function () {
  const ls = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sem armazenamento */ } }
  };
  const instalado = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  // ---------- 1) faixa de conexão: "Sem internet: catálogo de dd/mm" e "Conexão de volta: catálogo atualizado" ----------
  let faixa = null, tempo = null;
  function mostrarFaixa(texto, tipo, ms) {
    if (!faixa) {
      faixa = document.createElement("div");
      faixa.className = "app-faixa"; faixa.setAttribute("role", "status"); faixa.setAttribute("aria-live", "polite");
      document.body.appendChild(faixa);
    }
    faixa.textContent = texto; faixa.dataset.tipo = tipo; faixa.hidden = false;
    clearTimeout(tempo);
    if (ms) tempo = setTimeout(() => { faixa.hidden = true; }, ms);
  }
  function dataCatalogo() {
    const t = Number(ls.get("mdtech_catalogo_em"));
    return t ? new Date(t).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "";
  }
  function semInternet() {
    if (navigator.onLine) return;
    const d = dataCatalogo();
    mostrarFaixa("Sem internet" + (d ? ": catálogo de " + d : "") + ". Pedidos ficam guardados e saem quando a conexão voltar.", "off");
  }
  window.addEventListener("offline", semInternet);
  window.addEventListener("online", async () => {
    mostrarFaixa("Conexão de volta: catálogo atualizado.", "on", 4000);   // antes: o aviso de pedido enviado (se houver) vem depois
    try { await fetch("produtos.json", { cache: "no-store" }); ls.set("mdtech_catalogo_em", String(Date.now())); } catch (e) { /* ainda instável */ }
    guardarFotos();
  });
  document.addEventListener("envios:enviados", e => {
    const n = (e.detail && e.detail.n) || 1;
    mostrarFaixa(n === 1 ? "O pedido guardado sem internet foi enviado." : n + " pedidos guardados sem internet foram enviados.", "on", 5000);
  });
  document.addEventListener("DOMContentLoaded", semInternet);

  // ---------- 2) fotos para usar sem internet (~5 MB): só vendedor ou app instalado (clientes não baixam tudo à toa) ----------
  async function guardarFotos() {
    if (!("serviceWorker" in navigator) || !navigator.onLine) return;
    if (!((window.MD && MD.ehVendedor && MD.ehVendedor()) || instalado())) return;
    try {
      const prod = await (await fetch("produtos.json")).json();
      const urls = [];
      prod.forEach(p => { if (p.foto_thumb) urls.push(p.foto_thumb); if (p.foto) urls.push(p.foto); });
      const reg = await navigator.serviceWorker.ready;
      if (reg.active) reg.active.postMessage({ tipo: "fotos", urls });
    } catch (e) { /* tenta de novo na próxima visita */ }
  }
  window.addEventListener("load", () => setTimeout(guardarFotos, 3000));

  // ---------- 3) convite para instalar: só vendedor conectado; "Agora não" esconde por 30 dias; some se já instalado ----------
  let pedido = null, vendedor = false;
  window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); pedido = e; convidar(); });
  window.addEventListener("appinstalled", () => { fechar(); pedido = null; });
  document.addEventListener("conta:pronta", e => { vendedor = !!(e.detail && e.detail.status === 200); convidar(); });

  function convidar() {
    if (!vendedor || instalado() || document.querySelector(".app-convite")) return;
    if (Date.now() < Number(ls.get("mdtech_instalar_depois") || 0)) return;
    if (pedido) montar("android");
    else if (ios) montar("ios");
  }
  function fechar() { const c = document.querySelector(".app-convite"); if (c) c.remove(); }
  function montar(tipo) {
    const c = document.createElement("div");
    c.className = "app-convite"; c.setAttribute("role", "dialog"); c.setAttribute("aria-labelledby", "app-conv-t");
    const compartilhar = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
      '<path d="M12 3v12M8 7l4-4 4 4M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
    c.innerHTML = `<img src="img/app/icone-192.png" alt="" width="44" height="44">
      <div class="app-conv-txt"><b id="app-conv-t">Instale o catálogo no celular</b>
        <span>${tipo === "ios"
          ? `Toque em <b>Compartilhar</b> ${compartilhar} e depois em <b>“Adicionar à Tela de Início”</b>.`
          : "Abre como app, direto da tela inicial, e funciona sem internet."}</span></div>
      <div class="app-conv-bt">${tipo === "android" ? '<button type="button" class="app-instalar">Instalar</button>' : ""}
        <button type="button" class="app-depois">Agora não</button></div>`;
    document.body.appendChild(c);
    const depois = c.querySelector(".app-depois");
    depois.onclick = () => { ls.set("mdtech_instalar_depois", String(Date.now() + 30 * 864e5)); fechar(); };
    const bt = c.querySelector(".app-instalar");
    if (bt) bt.onclick = async () => {
      if (!pedido) return fechar();
      pedido.prompt();
      try { await pedido.userChoice; } catch (e) { /* ok */ }
      pedido = null; fechar();
    };
  }
})();
