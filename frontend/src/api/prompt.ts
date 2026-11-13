/**
 * Template do prompt para geração de páginas link-in-bio.
 * Placeholders: {{INSTAGRAM}}, {{NOME}}, {{BIO}}, {{LINKS}},
 * {{TIKTOK}}, {{VIDEO}}, {{FOTO}}, {{FAVICON}}, {{COR}}, {{TEMA}}
 */

export const PROMPT_TEMPLATE = `Você é um desenvolvedor front-end que cria páginas de "link na bio" (estilo Linktree) para clientes do Instagram.

## TAREFA

Receba os DADOS DO CLIENTE (no final deste texto) e CRIE um arquivo HTML completo e funcional na pasta de trabalho atual.

Para isso, copie o MODELO abaixo por inteiro e altere somente o que as regras mandarem: os dados do cliente no objeto PROFILE, o nome no <title> e nas metas do <head>, as cores do :root e o favicon. Não reescreva o modelo do zero, não reorganize as seções, não troque fontes, não adicione bibliotecas nem frameworks.

## REGRAS OBRIGATÓRIAS

1. **Título da página.** <title> e og:title recebem APENAS o nome de exibição do Instagram (ex.: Maria Silva). Sem @, sem bio, sem traço, sem "Links de". O mesmo nome vai no campo nome do PROFILE.

2. **Botões.** Nunca use degradê nem fundo colorido nos botões. A única exceção é o PRIMEIRO botão, que tem fundo sólido na cor de destaque. Todos os outros são neutros: fundo --btn-bg (quase preto no tema escuro, quase branco no claro), borda fina --btn-border, texto --btn-text e ícone na cor de destaque. Isso já está no CSS do modelo: não altere essas regras.

3. **Hover dos botões.** O botão sobe de leve (translateY(-3px)) e a borda passa para a cor de destaque (--accent). Não clareie nem escureça o fundo e não use filter.

4. **Ícones de Instagram, TikTok e outras redes.** Mesmo padrão dos botões neutros: fundo --btn-bg, borda fina --btn-border, ícone na cor de destaque. No hover, borda na cor de destaque. Nunca fundo colorido.

5. **Cores (:root).** Altere somente estas variáveis:
   - --accent, --accent-rgb (o mesmo valor em R,G,B decimais) e --accent-2 (no tema escuro, uma versão um pouco mais clara do --accent; no tema claro, igual ao --accent).
   - No tema escuro: --bg, --bg-rgb, --bg-deep, --bg-end e --surface, em tons MUITO escuros do mesmo matiz da cor de destaque.
   - Se a cor de destaque for clara (rosa claro, dourado, nude), troque --btn-primary-text para #161112.

6. **Tema.** O padrão é o escuro. Se o cliente pedir tema claro, ou a marca for claramente clara (visual rosé/nude, por exemplo), coloque data-theme="light" na tag <html> e não mexa nos valores do bloco html[data-theme="light"].

7. **Ícone da aba do navegador.** Use o campo "Ícone da aba" dos dados do cliente (link direto da imagem ou nome de um arquivo na mesma pasta). Coloque exatamente esse valor no href das duas tags do <head>: <link rel="icon"> e <link rel="apple-touch-icon">. Se o cliente não enviar ícone, use o link da foto de perfil nas duas tags. Se não houver nem um nem outro, apague as duas tags. Nunca invente o endereço do ícone. Coloque em theme-color o valor de --bg. Se mantiver o padrão do fundo (.bg::after), troque %23E01E37 pela cor de destaque, mantendo o %23 na frente.

8. **Padrão decorativo do fundo (.bg::after).** O desenho do modelo é um halter, só para nicho fitness. Para outro nicho (estética, unhas, culinária etc.), apague o bloco .bg::after inteiro.

9. **Links.** O primeiro item de links é o principal e vira o botão colorido. Mantenha a ordem informada pelo cliente. Instagram e TikTok vão nos campos instagram e tiktok, nunca em links.

10. **Dados.** Use somente os dados do cliente. Não invente links, cupons, preços, textos nem redes. Campo sem dado fica "" (texto) ou [] (lista). Remova qualquer texto de exemplo do modelo ("Nome do Cliente", "exemplo.com").

11. **Animações.** Mantenha todas as animações do modelo (@keyframes, a classe .reveal e as transições de hover), sem remover nem simplificar. Ao abrir a página, a foto, o nome, a bio, cada botão, o vídeo, os ícones sociais e o rodapé aparecem em cascata com subida suave. Isso depende da classe reveal e do --i crescente em cada item gerado pelo script: não tire nenhum dos dois.

12. **Sem comentários.** O arquivo final não pode ter nenhum comentário: nem <!-- --> no HTML, nem /* */ no CSS ou no JS, nem // no JS. O modelo abaixo já está sem comentários; não escreva nenhum.

13. **Saída.** Crie o arquivo index.html na pasta de trabalho atual, usando a ferramenta de criar ou escrever arquivos, com o HTML completo do <!DOCTYPE html> ao </html>. NÃO cole o código na resposta. Depois de criar o arquivo, responda só com uma linha dizendo o nome do arquivo criado.

## CONFIRA ANTES DE RESPONDER

- <title> e og:title têm só o nome, sem @.
- Só o primeiro botão tem a cor de destaque; os demais são neutros.
- Não existe linear-gradient em .btn nem em .social a.
- O hover sobe o botão de leve e muda a borda para --accent.
- As animações do modelo estão inteiras e todos os itens têm reveal com --i.
- O arquivo não tem nenhum comentário (<!-- -->, /* */, //).
- O código foi gravado em index.html na pasta de trabalho, não colado na resposta.
- O href do ícone da aba é o valor informado (ou a foto de perfil), nas duas tags.
- Nenhum texto de exemplo do modelo sobrou.
- O arquivo está completo e termina em </html>.

## MODELO

\`\`\`html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Nome do Cliente</title>
<meta name="description" content="Links de Nome do Cliente — frase curta da bio.">
<meta property="og:type" content="profile">
<meta property="og:title" content="Nome do Cliente">
<meta property="og:description" content="Links de Nome do Cliente.">
<meta property="og:image" content="https://exemplo.com/foto.jpg">
<meta name="twitter:card" content="summary_large_image">

<meta name="theme-color" content="#140507">

<link rel="icon" href="https://exemplo.com/icone.png">
<link rel="apple-touch-icon" href="https://exemplo.com/icone.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
:root{

  --accent:#E01E37;
  --accent-rgb:224,30,55;
  --accent-2:#FF5A5F;

  --bg:#140507;
  --bg-rgb:20,5,7;
  --bg-deep:#080203;
  --bg-end:#050505;
  --surface:#1E080C;

  --text:#FFFFFF;
  --muted:rgba(255,255,255,.62);
  --faint:rgba(255,255,255,.35);
  --grid:rgba(255,255,255,.035);
  --name-shadow:0 4px 18px rgba(0,0,0,.6);

  --btn-bg:#161112;
  --btn-border:rgba(255,255,255,.10);
  --btn-text:#FFFFFF;
  --btn-primary-text:#FFFFFF;
  --display:'Outfit',sans-serif;
  --body:'Inter',system-ui,-apple-system,sans-serif;
  --ease:cubic-bezier(.16,1,.3,1);
}

html[data-theme="light"]{
  --bg:#FBF8F7;
  --bg-rgb:251,248,247;
  --bg-deep:#EFEAE8;
  --bg-end:#F7F3F2;
  --surface:#FFFFFF;
  --text:#161112;
  --muted:rgba(22,17,18,.62);
  --faint:rgba(22,17,18,.40);
  --grid:rgba(0,0,0,.04);
  --name-shadow:none;
  --btn-bg:#F5F1F0;
  --btn-border:rgba(0,0,0,.10);
  --btn-text:#161112;
}

*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  font-family:var(--body);
  color:var(--text);
  background:var(--bg-deep);
  min-height:100vh;
  display:flex;
  justify-content:center;
  padding:32px 16px;
}

.wrap{
  width:100%;
  max-width:420px;
  border-radius:28px;
  overflow:hidden;
  position:relative;
  z-index:1;
  background:var(--surface);
  box-shadow:0 24px 60px rgba(0,0,0,.55);
}

.hero{
  position:relative;
  height:62vh;
  min-height:420px;
  background:center top/cover no-repeat;
}
.hero::after{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(to bottom,
    rgba(var(--bg-rgb),0) 0%,
    rgba(var(--bg-rgb),0) 35%,
    rgba(var(--bg-rgb),.35) 55%,
    rgba(var(--bg-rgb),.75) 78%,
    rgba(var(--bg-rgb),1) 100%);
}

.content{
  position:relative;
  z-index:2;
  margin-top:-90px;
  padding:0 22px 30px;
  display:flex;
  flex-direction:column;
  align-items:stretch;
}

.handle{
  font-size:12px;
  font-weight:700;
  letter-spacing:.22em;
  text-transform:uppercase;
  color:var(--accent-2);
  margin-bottom:6px;
}

.name{
  position:relative;
  z-index:2;
  font-family:var(--display);
  font-weight:600;
  font-size:clamp(34px,9vw,46px);
  line-height:1.05;
  letter-spacing:-.01em;
  text-transform:uppercase;
  color:var(--text);
  text-shadow:var(--name-shadow);
}

.bio{
  margin-top:10px;
  font-size:15px;
  line-height:1.5;
  color:var(--muted);
}

.links{margin-top:22px;display:flex;flex-direction:column;gap:12px}
.btn{
  display:flex;
  align-items:center;
  gap:12px;
  width:100%;
  min-height:56px;
  border-radius:999px;
  text-decoration:none;
  color:var(--btn-text);
  background:var(--btn-bg);
  border:1px solid var(--btn-border);
}
.btn .btn-ico{flex:0 0 20px;display:flex;align-items:center;justify-content:center;color:var(--accent-2)}
.btn .btn-ico svg{width:20px;height:20px}
.btn .labels{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;justify-content:center}
.btn .title{
  font-size:14.5px;
  font-weight:700;
  line-height:1.25;
  word-break:break-word;
}
.btn .subtitle{font-size:11.5px;font-weight:500;opacity:.85;margin-top:2px}
.btn .arrow{flex:0 0 18px;display:flex;align-items:center;justify-content:center;color:var(--muted)}
.btn .arrow svg{width:18px;height:18px}

.btn.primary{
  color:var(--btn-primary-text);
  background:var(--accent);
  border-color:var(--accent);
  box-shadow:0 6px 18px rgba(var(--accent-rgb),.28);
}
.btn.primary .btn-ico,
.btn.primary .arrow{color:var(--btn-primary-text)}

.video-card{
  margin-top:14px;
  border-radius:20px;
  overflow:hidden;
  position:relative;
  background:#000;
  cursor:pointer;
  aspect-ratio:16/9;
}
.video-card img{width:100%;height:100%;object-fit:cover;display:block}
.video-card .play{
  position:absolute;
  inset:0;
  margin:auto;
  width:58px;height:58px;
  border-radius:50%;
  background:rgba(var(--accent-rgb),.92);
  display:flex;align-items:center;justify-content:center;
}
.video-card .play svg{width:22px;height:22px}
.video-card .caption{
  position:absolute;
  left:0;right:0;bottom:0;
  padding:26px 14px 10px;
  font-size:12.5px;
  font-weight:600;
  color:#fff;
  background:linear-gradient(to top,rgba(0,0,0,.8),transparent);
}
.video-card iframe{width:100%;height:100%;border:0;display:block}

.social{
  margin-top:26px;
  display:flex;
  justify-content:center;
  gap:16px;
}
.social a{
  width:48px;height:48px;
  border-radius:50%;
  border:1.5px solid var(--btn-border);
  background:var(--btn-bg);
  display:flex;align-items:center;justify-content:center;
  color:var(--accent-2);
  text-decoration:none;
}
.social a svg{width:22px;height:22px}

.footer{
  margin-top:26px;
  text-align:center;
  font-size:11px;
  letter-spacing:.08em;
  color:var(--faint);
  text-decoration:none;
}

@media (max-width:480px){
  body{padding:0}
  .wrap{max-width:100%;border-radius:0;box-shadow:none;min-height:100vh}
  .content{padding:0 18px 28px}
}

.bg{position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(60% 55% at 100% 0%,rgba(var(--accent-rgb),.22) 0%,rgba(var(--accent-rgb),0) 70%),radial-gradient(45% 45% at 0% 100%,rgba(var(--accent-rgb),.08) 0%,rgba(var(--accent-rgb),0) 70%),linear-gradient(135deg,var(--bg-deep) 0%,var(--bg-end) 100%)}
.bg::before{content:"";position:absolute;inset:0;background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);background-size:96px 96px;-webkit-mask-image:radial-gradient(ellipse at center,#000 25%,transparent 85%);mask-image:radial-gradient(ellipse at center,#000 25%,transparent 85%)}

.bg::after{content:"";position:absolute;inset:0;opacity:.09;background-size:96px 96px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'%3E%3Cg fill='none' stroke='%23E01E37' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M38 48h20M34 41v14M62 41v14M40 43v10M56 43v10'/%3E%3C/g%3E%3C/svg%3E")}

@keyframes pageIn{from{opacity:0}to{opacity:1}}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes heroIn{from{opacity:0;transform:scale(1.05)}to{opacity:1;transform:scale(1)}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
body{animation:pageIn 1.4s ease both}
.hero{animation:heroIn 2.4s var(--ease) both}

.reveal{animation:fadeUp 1.3s var(--ease) backwards;animation-delay:calc(var(--i)*150ms + 700ms)}

.btn{transition:transform .5s var(--ease),border-color .45s var(--ease),box-shadow .55s var(--ease)}
.btn:hover{transform:translateY(-3px);border-color:var(--accent)}
.btn:active{transform:translateY(0) scale(.985)}
.btn.primary:hover{box-shadow:0 10px 26px rgba(var(--accent-rgb),.42)}
.btn .arrow{transition:transform .55s var(--ease)}
.btn:hover .arrow{transform:translateX(4px)}

.social a{transition:transform .5s var(--ease),border-color .4s var(--ease)}
.social a:hover{transform:translateY(-2px) scale(1.08);border-color:var(--accent)}
.video-card img{transition:transform .9s var(--ease)}
.video-card:hover img{transform:scale(1.03)}
.play{animation:pulse 3.6s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.reveal{opacity:1}}
</style>
</head>
<body>

<div class="bg"></div>

<main class="wrap" id="wrap">
  <div class="hero" id="hero"></div>
  <div class="content" id="content"></div>
</main>

<script>

const PROFILE = {
  nome: "Nome do Cliente",
  handle: "@usuario",
  bio: "Frase curta da bio",
  links: [
    { title: "Título do botão 1 (principal)", url: "https://exemplo.com/1" },
    { title: "Título do botão 2", subtitle: "texto opcional", url: "https://exemplo.com/2" },
    { title: "Título do botão 3", url: "https://exemplo.com/3" }
  ],
  instagram: "https://www.instagram.com/usuario/",
  tiktok: "",
  outros: [],
  video: "",
  foto: "https://exemplo.com/foto.jpg"
};

const ICONS = {
  link:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.07 0l3-3A5 5 0 0 0 13 3l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3A5 5 0 0 0 11 21l1.5-1.5"/></svg>',
  cart:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="20" r="1.5"/><circle cx="17" cy="20" r="1.5"/><path d="M3 4h2l2.5 11h10L20 7H6"/></svg>',
  clock:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>',
  tag:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12l-8 8-8-8 8-8h8v8z"/><circle cx="15.5" cy="8.5" r="1.3"/></svg>',
  arrow:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  instagram:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="3.8"/><circle cx="16.9" cy="7.1" r="1" fill="currentColor" stroke="none"/></svg>',
  tiktok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13.5 3v11.6a3.6 3.6 0 1 1-3.1-3.57"/><path d="M13.5 3c.4 2.6 2.2 4.2 4.8 4.4"/></svg>',
  youtube:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10.5 9.5l5 2.5-5 2.5z"/></svg>',
  spotify:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M7.5 9.7c3-.9 6.2-.6 8.8.9M8 12.7c2.4-.7 5-.4 7 .8M8.5 15.5c1.9-.5 3.8-.3 5.4.6"/></svg>',
  whatsapp:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20l1.3-4A8 8 0 1 1 8 18.7L4 20z"/><path d="M9 9.5c.5 2 1.8 3.4 3.8 4l1.2-1 1.8.8-.4 1.5c-2.6.4-5.8-2.3-6.7-5.6L10.4 8 9.6 9.8z" fill="currentColor" stroke="none"/></svg>',
  x:      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M20 4L4 20"/></svg>'
};

const SOCIAIS = ["instagram","tiktok","youtube","spotify","whatsapp","x"];

function hostOf(url){
  try { return new URL(url).hostname.replace(/^www\./,"").toLowerCase(); }
  catch(e){ return ""; }
}

function normalizeLink(item){
  if (typeof item === "string"){
    const md = item.match(/^\[(.+?)\]\((https?:\/\/\S+)\)$/);
    if (md) return { title: md[1], subtitle: "", url: md[2] };
    const parts = item.split("|").map(function(p){return p.trim()});
    if (parts.length >= 3) return { title: parts[0], subtitle: parts[1], url: parts[2] };
    if (parts.length === 2 && parts[1].startsWith("http")) return { title: parts[0], subtitle: "", url: parts[1] };
    return { title: item, subtitle: "", url: "" };
  }
  return { title: item.title || "", subtitle: item.subtitle || "", url: item.url || "" };
}

function linkIconFor(url){
  const h = hostOf(url);
  if (h.includes("kiwify") || h.includes("hotmart") || h.includes("pay")) return ICONS.tag;
  if (h.includes("loja") || h.includes("shop") || h.includes("suplement") ||
      h.includes("goodliftpower") || h.includes("4climb") || h.includes("darklab")) return ICONS.cart;
  if (h.includes("netlify") || h.includes("linktr")) return ICONS.clock;
  return ICONS.link;
}

function moveSocialsToIcons(){
  PROFILE.links = PROFILE.links.filter(function(l){
    const h = hostOf(normalizeLink(l).url);
    return !h.includes("instagram.com") && !h.includes("tiktok.com");
  });
}

function getVideoEmbed(url){
  if(!url) return null;
  let m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/i);
  if (m) return "https://www.youtube.com/embed/" + m[1];
  m = url.match(/vimeo\.com\/(\d+)/i);
  if (m) return "https://player.vimeo.com/video/" + m[1];
  return null;
}

function buildPage(){
  document.title = PROFILE.nome;
  moveSocialsToIcons();
  let i = 0;
  let n = 0;

  const hero = document.getElementById("hero");
  if (PROFILE.foto){
    const probe = new Image();
    probe.onload = function(){ hero.style.backgroundImage = "url('" + PROFILE.foto + "')"; };
    probe.onerror = function(){
      hero.style.backgroundImage =
        "linear-gradient(to bottom, var(--accent) 0%, var(--bg) 100%)";
    };
    probe.src = PROFILE.foto;
  } else {
    hero.style.backgroundImage = "linear-gradient(to bottom, var(--accent) 0%, var(--bg) 100%)";
  }

  const content = document.getElementById("content");
  let html = "";

  html += '<div class="handle reveal" style="--i:'+(i++)+'">'+PROFILE.handle+'</div>';

  html += '<h1 class="name reveal" style="--i:'+(i++)+'">'+PROFILE.nome+'</h1>';

  if (PROFILE.bio) html += '<p class="bio reveal" style="--i:'+(i++)+'">'+PROFILE.bio+'</p>';

  html += '<div class="links">';
  PROFILE.links.forEach(function(item){
    const l = normalizeLink(item);
    if (!l.url) return;
    html += '<a class="btn'+(n++ === 0 ? ' primary' : '')+' reveal" style="--i:'+(i++)+'" href="'+l.url+'" target="_blank" rel="noopener noreferrer">'
          +   '<span class="btn-ico">'+linkIconFor(l.url)+'</span>'
          +   '<span class="labels"><span class="title">'+l.title+'</span>'
          +   (l.subtitle ? '<span class="subtitle">'+l.subtitle+'</span>' : '')
          +   '</span>'
          +   '<span class="arrow">'+ICONS.arrow+'</span>'
          + '</a>';
  });
  html += '</div>';

  if (PROFILE.video){
    const embed = getVideoEmbed(PROFILE.video);
    const thumb = embed && embed.indexOf("youtube.com/embed/") === 0
      ? "https://img.youtube.com/vi/" + embed.split("/embed/")[1] + "/hqdefault.jpg"
      : "";
    html += '<div class="video-card reveal" style="--i:'+(i++)+'" '
          + (embed
              ? 'data-embed="'+embed+'">'
                + (thumb ? '<img src="'+thumb+'" alt="Vídeo" loading="lazy">' : '')
              : 'onclick="window.open(\''+PROFILE.video+'\',\'_blank\')">'
                + '<img src="'+(thumb||"")+'" alt="Vídeo" loading="lazy" style="background:#000">')
          + '<span class="play"><svg viewBox="0 0 24 24" fill="#fff"><path d="M8 5l12 7-12 7z"/></svg></span>'
          + '<span class="caption">Assistir ao vídeo</span>'
          + '</div>';
  }

  let socialHtml = "";
  const extras = (PROFILE.outros || []).filter(Boolean);
  const fila = [];
  if (PROFILE.instagram) fila.push({url: PROFILE.instagram, key: "instagram"});
  if (PROFILE.tiktok)    fila.push({url: PROFILE.tiktok,    key: "tiktok"});
  extras.forEach(function(u){
    const h = hostOf(u);
    const key = SOCIAIS.find(function(s){ return h.includes(s) || (s === "x" && (h.includes("twitter.com") || h === "x.com")); });
    if (key && !fila.some(function(f){return f.key === key;})) fila.push({url: u, key: key});
  });
  fila.forEach(function(f){
    socialHtml += '<a href="'+f.url+'" target="_blank" rel="noopener noreferrer" aria-label="'+f.key+'">'+ICONS[f.key]+'</a>';
  });
  if (socialHtml) html += '<div class="social reveal" style="--i:'+(i++)+'">'+socialHtml+'</div>';

  html += '<div class="footer reveal" style="--i:'+(i++)+'">© '+new Date().getFullYear()+' '+PROFILE.handle+'</div>';

  content.innerHTML = html;

  const card = content.querySelector(".video-card[data-embed]");
  if (card){
    card.addEventListener("click", function(){
      card.innerHTML = '<iframe src="'+card.dataset.embed+'?autoplay=1" title="Vídeo" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
      card.style.cursor = "default";
    });
  }
}

buildPage();

</script>
</body>
</html>
\`\`\`

## DADOS DO CLIENTE

- Nome de exibição no Instagram (sem @): {{NOME}}
- @ do Instagram: {{INSTAGRAM}}
- Bio (frase curta): {{BIO}}
- Links, do mais importante ao menos importante (título | url | subtítulo opcional): {{LINKS}}
- TikTok e outras redes (url): {{TIKTOK}}
- Vídeo (url do YouTube, opcional): {{VIDEO}}
- Foto de perfil (url): {{FOTO}}
- Ícone da aba do navegador (link direto da imagem ou nome do arquivo na pasta; se vazio, usa a foto de perfil): {{FAVICON}}
- Cor de destaque (hex) ou estilo da marca: {{COR}}
- Tema: escuro ou claro

Agora crie o arquivo index.html na pasta de trabalho seguindo as regras. Não cole o código na resposta.`;

/**
 * Substitui os placeholders do template pelos valores informados.
 */
export function buildPrompt(fields: {
  instagram: string;
  nome: string;
  bio: string;
  links: string;
  tiktok: string;
  video: string;
  foto: string;
  favicon: string;
  cor: string;
  tema: string;
}): string {
  return PROMPT_TEMPLATE.replace("{{INSTAGRAM}}", fields.instagram.trim() || "@usuario")
    .replace("{{NOME}}", fields.nome.trim() || "Nome do Cliente")
    .replace("{{BIO}}", fields.bio.trim() || "Frase curta da bio")
    .replace("{{LINKS}}", fields.links.trim() || "Título | https://exemplo.com | subtítulo")
    .replace("{{TIKTOK}}", fields.tiktok.trim() || "")
    .replace("{{VIDEO}}", fields.video.trim() || "")
    .replace("{{FOTO}}", fields.foto.trim() || "")
    .replace("{{FAVICON}}", fields.favicon.trim() || "")
    .replace("{{COR}}", fields.cor.trim() || "#E01E37")
    .replace("{{TEMA}}", fields.tema.trim() || "escuro");
}
