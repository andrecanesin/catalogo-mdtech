/* Service worker do Catálogo MDTech (PWA): o catálogo abre e funciona sem internet e se atualiza sozinho quando a conexão volta.

   O que guarda (só no aparelho de quem usa):
   - páginas, CSS, JS, fontes e ícones;
   - produtos.json, meta.json e propostas.json (catálogo sem preço);
   - fotos: as que a pessoa vê e, para vendedores ou app instalado, todas (~5 MB), mandadas pela página (mensagem "fotos");
   - PDFs (fichas, catálogos, propostas): só os que a pessoa abriu.
   O que NUNCA passa por aqui: /conta.py (login e preços), /interno/ (site antigo com preço) e outros domínios (Web3Forms, WhatsApp).

   Estratégias: páginas e dados = rede primeiro, cópia guardada se não houver internet (online, sempre o mais novo).
   Fotos = cópia guardada primeiro (o endereço muda com ?v=<hash> quando a foto muda, então nunca fica velha).
   CSS/JS/fontes = cópia guardada na hora e atualização por trás (os HTML publicados levam ?v=<hash> nos CSS/JS). */
const VERSAO = "v1";
const SHELL = "mdtech-shell-" + VERSAO, DADOS = "mdtech-dados-" + VERSAO, FOTOS = "mdtech-fotos-" + VERSAO, PDFS = "mdtech-pdfs-" + VERSAO;
const ESCOPO = new URL(self.registration.scope);
const INICIAIS = ["index.html", "produto.html", "privacidade.html", "manifest.json", "img/logo.png", "img/app/icone-192.png",
  "css/estilo.css", "js/config.js", "js/dados.js", "js/catalogo.js", "js/produto.js", "js/suporte.js", "js/app.js",
  "fonts/Poppins-Regular.woff2", "fonts/Poppins-Medium.woff2", "fonts/Poppins-SemiBold.woff2", "fonts/Poppins-Bold.woff2",
  "fonts/IBMPlexMono-Regular.woff2", "fonts/IBMPlexMono-Medium.woff2"];

self.addEventListener("install", ev => {
  ev.waitUntil(caches.open(SHELL).then(c => Promise.allSettled(INICIAIS.map(u => c.add(new URL(u, ESCOPO)))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", ev => {
  const atuais = [SHELL, DADOS, FOTOS, PDFS];
  ev.waitUntil(caches.keys()
    .then(nomes => Promise.all(nomes.filter(n => n.startsWith("mdtech-") && !atuais.includes(n)).map(n => caches.delete(n))))
    .then(() => self.clients.claim()));
});

// endereço sem a busca (?codigo=, ?esp=): a mesma página guardada serve para todos os produtos e filtros
const semBusca = url => new Request(url.origin + url.pathname);

async function redePrimeiro(req, nome, pagina) {
  const cache = await caches.open(nome), url = new URL(req.url);
  try {
    const r = await fetch(req);
    if (r.ok && !r.redirected) cache.put(pagina ? semBusca(url) : req, r.clone());
    return r;
  } catch (e) {
    const guardada = await cache.match(pagina ? semBusca(url) : req, { ignoreSearch: !!pagina })
      || (pagina && await cache.match(new URL("index.html", ESCOPO).href));
    if (guardada) return guardada;
    throw e;
  }
}

async function guardadaPrimeiro(req, nome) {
  const cache = await caches.open(nome);
  const guardada = await cache.match(req);
  if (guardada) return guardada;
  const r = await fetch(req);
  if (r.ok) cache.put(req, r.clone());
  return r;
}

async function guardadaEAtualiza(ev, req, nome) {
  const cache = await caches.open(nome);
  const guardada = await cache.match(req);
  const rede = fetch(req).then(r => { if (r.ok) cache.put(req, r.clone()); return r; });
  if (guardada) { ev.waitUntil(rede.catch(() => null)); return guardada; }
  try { return await rede; }
  catch (e) {
    // sem internet e sem esta versão exata (?v=): serve a cópia guardada do mesmo arquivo, de qualquer versão
    const qualquer = await cache.match(req, { ignoreSearch: true });
    if (qualquer) return qualquer;
    throw e;
  }
}

self.addEventListener("fetch", ev => {
  const req = ev.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== ESCOPO.origin || !url.pathname.startsWith(ESCOPO.pathname)) return;
  const rel = url.pathname.slice(ESCOPO.pathname.length);
  if (rel.startsWith("interno/") || rel.startsWith("conta.py") || rel === "sw.js") return;   // preços e login: sempre direto
  if (req.mode === "navigate" || rel.endsWith(".html") || rel === "") { ev.respondWith(redePrimeiro(req, SHELL, true)); return; }
  if (rel.endsWith(".json")) { ev.respondWith(redePrimeiro(req, DADOS, false)); return; }
  if (rel.startsWith("fotos/")) { ev.respondWith(guardadaPrimeiro(req, FOTOS)); return; }
  if (rel.toLowerCase().endsWith(".pdf")) { ev.respondWith(redePrimeiro(req, PDFS, false)); return; }
  ev.respondWith(guardadaEAtualiza(ev, req, SHELL));
});

// A página manda a lista das fotos do catálogo atual ({tipo: "fotos", urls: [...]}): baixa as que faltam (só o que mudou,
// porque o endereço leva o hash da foto) e apaga as que saíram do catálogo.
self.addEventListener("message", ev => {
  const m = ev.data || {};
  if (m.tipo !== "fotos" || !Array.isArray(m.urls)) return;
  ev.waitUntil((async () => {
    const cache = await caches.open(FOTOS);
    const quero = new Set(m.urls.map(u => new URL(u, ESCOPO).href));
    for (const req of await cache.keys()) if (!quero.has(req.url)) await cache.delete(req);
    const tenho = new Set((await cache.keys()).map(r => r.url));
    const faltam = [...quero].filter(u => !tenho.has(u));
    for (let i = 0; i < faltam.length; i += 4) {       // 4 por vez: não trava o celular nem a rede
      await Promise.all(faltam.slice(i, i + 4).map(u => fetch(u).then(r => r.ok ? cache.put(u, r) : null).catch(() => null)));
    }
  })());
});
