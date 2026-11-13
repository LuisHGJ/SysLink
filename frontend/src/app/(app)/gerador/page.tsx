"use client";

import { DEFAULT_ICON, IconPicker, getIconSvg } from "@/components/IconPicker";
import type { IconValue } from "@/components/IconPicker";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import styles from "./page.module.css";

// ═══════════════════════════════════════════════════════════════════════════
// Color math
// ═══════════════════════════════════════════════════════════════════════════

function hexToRgb(hex: string) {
  const h = hex.replace("#", "");
  return {
    r: Number.parseInt(h.slice(0, 2), 16),
    g: Number.parseInt(h.slice(2, 4), 16),
    b: Number.parseInt(h.slice(4, 6), 16),
  };
}

function rgbToHsl(r: number, g: number, b: number) {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const delta = max - min;
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  if (delta !== 0) {
    s = delta / (1 - Math.abs(2 * l - 1));
    if (max === rn) h = 60 * (((gn - bn) / delta) % 6);
    else if (max === gn) h = 60 * ((bn - rn) / delta + 2);
    else h = 60 * ((rn - gn) / delta + 4);
    if (h < 0) h += 360;
  }
  return { h, s, l };
}

function hslToRgb(h: number, s: number, l: number) {
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (h < 60) {
    r = c;
    g = x;
  } else if (h < 120) {
    r = x;
    g = c;
  } else if (h < 180) {
    g = c;
    b = x;
  } else if (h < 240) {
    g = x;
    b = c;
  } else if (h < 300) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }
  return {
    r: Math.round((r + m) * 255),
    g: Math.round((g + m) * 255),
    b: Math.round((b + m) * 255),
  };
}

function toHex(r: number, g: number, b: number) {
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("")}`;
}

function hslToHex(h: number, s: number, l: number) {
  const { r, g, b } = hslToRgb(h, s, l);
  return toHex(r, g, b);
}

interface ColorScheme {
  accent: string;
  accentRgb: string;
  accent2: string;
  bg: string;
  bgRgb: string;
  bgDeep: string;
  bgEnd: string;
  surface: string;
  btnPrimText: string;
  theme: "dark" | "light";
}

function buildScheme(hex: string): ColorScheme {
  const { r, g, b } = hexToRgb(hex);
  const { h, s, l } = rgbToHsl(r, g, b);
  const isLight = l > 0.65;
  const accent2 = isLight ? hex : hslToHex(h, s, Math.min(l + 0.1, 0.85));

  if (isLight) {
    return {
      accent: hex,
      accentRgb: `${r},${g},${b}`,
      accent2,
      bg: "#FBF8F7",
      bgRgb: "251,248,247",
      bgDeep: "#EFEAE8",
      bgEnd: "#F7F3F2",
      surface: "#FFFFFF",
      btnPrimText: "#161112",
      theme: "light",
    };
  }

  const bg_ = hslToRgb(h, Math.min(s, 0.6), 0.06);
  const d_ = hslToRgb(h, Math.min(s, 0.5), 0.03);
  const e_ = hslToRgb(h, 0.05, 0.03);
  const su_ = hslToRgb(h, Math.min(s, 0.55), 0.08);

  return {
    accent: hex,
    accentRgb: `${r},${g},${b}`,
    accent2,
    bg: toHex(bg_.r, bg_.g, bg_.b),
    bgRgb: `${bg_.r},${bg_.g},${bg_.b}`,
    bgDeep: toHex(d_.r, d_.g, d_.b),
    bgEnd: toHex(e_.r, e_.g, e_.b),
    surface: toHex(su_.r, su_.g, su_.b),
    btnPrimText: l > 0.55 ? "#161112" : "#FFFFFF",
    theme: "dark",
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// HTML generation
// ═══════════════════════════════════════════════════════════════════════════
// HTML generation — fully static, no JS required
// ═══════════════════════════════════════════════════════════════════════════

function esc(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function bgAfterFitness(accent: string) {
  const enc = accent.replace("#", "%23");
  return `.bg::after{content:"";position:absolute;inset:0;opacity:.09;background-size:96px 96px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'%3E%3Cg fill='none' stroke='${enc}' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M38 48h20M34 41v14M62 41v14M40 43v10M56 43v10'/%3E%3C/g%3E%3C/svg%3E")}`;
}

interface LinkItem {
  title: string;
  subtitle: string;
  url: string;
  icon: IconValue;
}
interface Profile {
  nome: string;
  handle: string;
  bio: string;
  foto: string;
  favicon: string;
  links: LinkItem[];
  instagram: string;
  tiktok: string;
  outros: string[];
  video: string;
}

const ICONS = {
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.07 0l3-3A5 5 0 0 0 13 3l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3A5 5 0 0 0 11 21l1.5-1.5"/></svg>`,
  cart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="20" r="1.5"/><circle cx="17" cy="20" r="1.5"/><path d="M3 4h2l2.5 11h10L20 7H6"/></svg>`,
  tag: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12l-8 8-8-8 8-8h8v8z"/><circle cx="15.5" cy="8.5" r="1.3"/></svg>`,
  arrow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>`,
  instagram: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="3.8"/><circle cx="16.9" cy="7.1" r="1" fill="currentColor" stroke="none"/></svg>`,
  tiktok: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13.5 3v11.6a3.6 3.6 0 1 1-3.1-3.57"/><path d="M13.5 3c.4 2.6 2.2 4.2 4.8 4.4"/></svg>`,
  youtube: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10.5 9.5l5 2.5-5 2.5z"/></svg>`,
  spotify: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M7.5 9.7c3-.9 6.2-.6 8.8.9M8 12.7c2.4-.7 5-.4 7 .8M8.5 15.5c1.9-.5 3.8-.3 5.4.6"/></svg>`,
  whatsapp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20l1.3-4A8 8 0 1 1 8 18.7L4 20z"/><path d="M9 9.5c.5 2 1.8 3.4 3.8 4l1.2-1 1.8.8-.4 1.5c-2.6.4-5.8-2.3-6.7-5.6L10.4 8 9.6 9.8z" fill="currentColor" stroke="none"/></svg>`,
  x: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M20 4L4 20"/></svg>`,
};

function hostOf(u: string) {
  try {
    return new URL(u).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function linkIconFor(url: string) {
  const h = hostOf(url);
  if (h.includes("kiwify") || h.includes("hotmart") || h.includes("pay")) return ICONS.tag;
  if (h.includes("loja") || h.includes("shop") || h.includes("suplement")) return ICONS.cart;
  return ICONS.link;
}

function socialIconFor(key: string): string {
  return (ICONS as Record<string, string>)[key] ?? ICONS.link;
}

function getYoutubeId(url: string) {
  const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{6,})/i);
  return m ? m[1] : null;
}

function generateHTML(profile: Profile, scheme: ColorScheme, fitness: boolean): string {
  const themeAttr = scheme.theme === "light" ? ' data-theme="light"' : "";
  const bioShort = (profile.bio || profile.nome || "Página Bio").slice(0, 150);
  const icon = profile.favicon || profile.foto || "";
  const bgAfter = fitness ? bgAfterFitness(scheme.accent) : "";
  const year = new Date().getFullYear();

  // hero background
  const heroBg = profile.foto
    ? `background-image:url('${profile.foto.replace(/'/g, "%27")}')`
    : `background-image:linear-gradient(to bottom,${scheme.accent} 0%,${scheme.bg} 100%)`;

  // filter out instagram/tiktok from links
  const filteredLinks = profile.links.filter((l) => {
    const h = hostOf(l.url);
    return !h.includes("instagram.com") && !h.includes("tiktok.com");
  });

  // build link buttons HTML
  let linksHtml = "";
  for (const [i, l] of filteredLinks.entries()) {
    const isPrimary = i === 0;
    const iconSvg = getIconSvg(l.icon, scheme.accent);
    const noUrl = !l.url;
    const hrefAttr = noUrl ? "" : `href="${esc(l.url)}" target="_blank" rel="noopener noreferrer"`;
    const styleAttr = `--i:${i + 3}${noUrl ? ";opacity:.5;cursor:default" : ""}`;
    linksHtml += `<a class="btn${isPrimary ? " primary" : ""} reveal" style="${styleAttr}" ${hrefAttr}><span class="btn-ico">${iconSvg}</span><span class="labels"><span class="title">${esc(l.title || "Sem título")}</span>${l.subtitle ? `<span class="subtitle">${esc(l.subtitle)}</span>` : ""}</span><span class="arrow">${ICONS.arrow}</span></a>\n`;
  }

  // video card
  let videoHtml = "";
  if (profile.video) {
    const ytId = getYoutubeId(profile.video);
    const thumb = ytId ? `https://img.youtube.com/vi/${ytId}/hqdefault.jpg` : "";
    const embedUrl = ytId ? `https://www.youtube.com/embed/${ytId}` : profile.video;
    videoHtml = `<div class="video-card reveal" style="--i:${filteredLinks.length + 3}">${thumb ? `<img src="${esc(thumb)}" alt="Vídeo" loading="lazy">` : ""}<a class="play-link" href="${esc(embedUrl)}" target="_blank" rel="noopener noreferrer" aria-label="Assistir ao vídeo"><span class="play"><svg viewBox="0 0 24 24" fill="#fff"><path d="M8 5l12 7-12 7z"/></svg></span></a><span class="caption">Assistir ao vídeo</span></div>`;
  }

  // social icons
  const SOCIAL_KEYS = ["instagram", "tiktok", "youtube", "spotify", "whatsapp", "x"];
  const socials: { url: string; key: string }[] = [];
  if (profile.instagram) socials.push({ url: profile.instagram, key: "instagram" });
  if (profile.tiktok) socials.push({ url: profile.tiktok, key: "tiktok" });
  for (const u of (profile.outros || []).filter(Boolean)) {
    const h = hostOf(u);
    const key = SOCIAL_KEYS.find(
      (s) => h.includes(s) || (s === "x" && (h.includes("twitter.com") || h === "x.com")),
    );
    if (key && !socials.some((f) => f.key === key)) socials.push({ url: u, key });
  }
  const socialHtml = socials.length
    ? `<div class="social reveal" style="--i:${filteredLinks.length + 4}">${socials
        .map(
          (f) =>
            `<a href="${esc(f.url)}" target="_blank" rel="noopener noreferrer" aria-label="${f.key}">${socialIconFor(f.key)}</a>`,
        )
        .join("")}</div>`
    : "";

  const handle = profile.handle
    ? profile.handle.startsWith("@")
      ? profile.handle
      : `@${profile.handle}`
    : "";

  return `<!DOCTYPE html>
<html lang="pt-BR"${themeAttr}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${esc(profile.nome || "Página Bio")}</title>
<meta name="description" content="${esc(bioShort)}">
<meta property="og:type" content="profile">
<meta property="og:title" content="${esc(profile.nome || "Página Bio")}">
<meta property="og:description" content="${esc(bioShort)}">
<meta property="og:image" content="${esc(profile.foto)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="${scheme.bg}">
<link rel="icon" href="${esc(icon)}">
<link rel="apple-touch-icon" href="${esc(icon)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --accent:${scheme.accent};--accent-rgb:${scheme.accentRgb};--accent-2:${scheme.accent2};
  --bg:${scheme.bg};--bg-rgb:${scheme.bgRgb};--bg-deep:${scheme.bgDeep};
  --bg-end:${scheme.bgEnd};--surface:${scheme.surface};
  --text:#FFFFFF;--muted:rgba(255,255,255,.62);--faint:rgba(255,255,255,.35);
  --grid:rgba(255,255,255,.035);--name-shadow:0 4px 18px rgba(0,0,0,.6);
  --btn-bg:#161112;--btn-border:rgba(255,255,255,.10);--btn-text:#FFFFFF;
  --btn-primary-text:${scheme.btnPrimText};
  --display:'Outfit',sans-serif;--body:'Inter',system-ui,-apple-system,sans-serif;
  --ease:cubic-bezier(.16,1,.3,1);
}
html[data-theme="light"]{
  --bg:#FBF8F7;--bg-rgb:251,248,247;--bg-deep:#EFEAE8;--bg-end:#F7F3F2;--surface:#FFFFFF;
  --text:#161112;--muted:rgba(22,17,18,.62);--faint:rgba(22,17,18,.40);--grid:rgba(0,0,0,.04);
  --name-shadow:none;--btn-bg:#F5F1F0;--btn-border:rgba(0,0,0,.10);--btn-text:#161112;
}
*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{font-family:var(--body);color:var(--text);background:var(--bg-deep);min-height:100vh;display:flex;justify-content:center;padding:32px 16px}
.wrap{width:100%;max-width:420px;border-radius:28px;overflow:hidden;position:relative;z-index:1;background:var(--surface);box-shadow:0 24px 60px rgba(0,0,0,.55)}
.hero{position:relative;height:62vh;min-height:420px;background:center top/cover no-repeat}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(to bottom,rgba(var(--bg-rgb),0) 0%,rgba(var(--bg-rgb),0) 35%,rgba(var(--bg-rgb),.35) 55%,rgba(var(--bg-rgb),.75) 78%,rgba(var(--bg-rgb),1) 100%)}
.content{position:relative;z-index:2;margin-top:-90px;padding:0 22px 30px;display:flex;flex-direction:column;align-items:stretch}
.handle{font-size:12px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:var(--accent-2);margin-bottom:6px}
.name{position:relative;z-index:2;font-family:var(--display);font-weight:600;font-size:clamp(34px,9vw,46px);line-height:1.05;letter-spacing:-.01em;text-transform:uppercase;color:var(--text);text-shadow:var(--name-shadow)}
.bio{margin-top:10px;font-size:15px;line-height:1.5;color:var(--muted)}
.links{margin-top:22px;display:flex;flex-direction:column;gap:12px}
.btn{display:flex;align-items:center;gap:12px;width:100%;min-height:56px;padding:10px 18px;border-radius:999px;text-decoration:none;color:var(--btn-text);background:var(--btn-bg);border:1px solid var(--btn-border)}
.btn .btn-ico{flex:0 0 20px;display:flex;align-items:center;justify-content:center;color:var(--accent-2)}
.btn .btn-ico svg{width:20px;height:20px}
.btn .labels{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;justify-content:center}
.btn .title{font-size:14.5px;font-weight:700;line-height:1.25;word-break:break-word}
.btn .subtitle{font-size:11.5px;font-weight:500;opacity:.85;margin-top:2px}
.btn .arrow{flex:0 0 18px;display:flex;align-items:center;justify-content:center;color:var(--muted)}
.btn .arrow svg{width:18px;height:18px}
.btn.primary{color:var(--btn-primary-text);background:var(--accent);border-color:var(--accent);box-shadow:0 6px 18px rgba(var(--accent-rgb),.28)}
.btn.primary .btn-ico,.btn.primary .arrow{color:var(--btn-primary-text)}
.video-card{margin-top:14px;border-radius:20px;overflow:hidden;position:relative;background:#000;aspect-ratio:16/9}
.video-card img{width:100%;height:100%;object-fit:cover;display:block}
.play-link{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-decoration:none}
.play{width:58px;height:58px;border-radius:50%;background:rgba(var(--accent-rgb),.92);display:flex;align-items:center;justify-content:center;box-shadow:0 6px 22px rgba(0,0,0,.5)}
.play svg{width:22px;height:22px;margin-left:3px}
.video-card .caption{position:absolute;left:0;right:0;bottom:0;padding:26px 14px 10px;font-size:12.5px;font-weight:600;color:#fff;background:linear-gradient(to top,rgba(0,0,0,.8),transparent);pointer-events:none}
.social{margin-top:26px;display:flex;justify-content:center;gap:16px}
.social a{width:48px;height:48px;border-radius:50%;border:1.5px solid var(--btn-border);background:var(--btn-bg);display:flex;align-items:center;justify-content:center;color:var(--accent-2);text-decoration:none}
.social a svg{width:22px;height:22px}
.footer{margin-top:26px;text-align:center;font-size:11px;letter-spacing:.08em;color:var(--faint)}
@media(max-width:480px){body{padding:0}.wrap{max-width:100%;border-radius:0;box-shadow:none;min-height:100vh}.content{padding:0 18px 28px}}
.bg{position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(60% 55% at 100% 0%,rgba(var(--accent-rgb),.22) 0%,rgba(var(--accent-rgb),0) 70%),radial-gradient(45% 45% at 0% 100%,rgba(var(--accent-rgb),.08) 0%,rgba(var(--accent-rgb),0) 70%),linear-gradient(135deg,var(--bg-deep) 0%,var(--bg-end) 100%)}
.bg::before{content:"";position:absolute;inset:0;background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);background-size:96px 96px;-webkit-mask-image:radial-gradient(ellipse at center,#000 25%,transparent 85%);mask-image:radial-gradient(ellipse at center,#000 25%,transparent 85%)}
${bgAfter}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes heroIn{from{opacity:0;transform:scale(1.05)}to{opacity:1;transform:scale(1)}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
.hero{animation:heroIn 1.8s var(--ease) both}
.reveal{animation:fadeUp 1s var(--ease) backwards;animation-delay:calc(var(--i)*120ms + 400ms)}
.btn{transition:transform .4s var(--ease),border-color .3s,box-shadow .4s var(--ease)}
.btn:hover{transform:translateY(-3px);border-color:var(--accent)}
.btn:active{transform:translateY(0) scale(.985)}
.btn.primary:hover{box-shadow:0 10px 26px rgba(var(--accent-rgb),.42)}
.btn .arrow{transition:transform .4s var(--ease)}
.btn:hover .arrow{transform:translateX(4px)}
.social a{transition:transform .4s var(--ease),border-color .3s}
.social a:hover{transform:translateY(-2px) scale(1.08);border-color:var(--accent)}
.play{animation:pulse 3.6s ease-in-out infinite}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.reveal{opacity:1}}
</style>
</head>
<body>
<div class="bg"></div>
<main class="wrap">
  <div class="hero" style="${heroBg}"></div>
  <div class="content">
    ${handle ? `<div class="handle reveal" style="--i:0">${esc(handle)}</div>` : ""}
    <h1 class="name reveal" style="--i:1">${esc(profile.nome || "")}</h1>
    ${profile.bio ? `<p class="bio reveal" style="--i:2">${esc(profile.bio)}</p>` : ""}
    <div class="links">
${linksHtml}    </div>
    ${videoHtml}
    ${socialHtml}
    <div class="footer reveal" style="--i:${filteredLinks.length + 5}">&#169; ${year} ${esc(handle)}</div>
  </div>
</main>
</body>
</html>`;
}

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

type Tema = "auto" | "claro" | "escuro";

interface LinkEntry {
  id: number;
  link: LinkItem;
}

let _lid = 0;
function newEntry(title = "", url = "", subtitle = ""): LinkEntry {
  return { id: _lid++, link: { title, url, subtitle, icon: { ...DEFAULT_ICON } } };
}

// ═══════════════════════════════════════════════════════════════════════════
// LinkRow component
// ═══════════════════════════════════════════════════════════════════════════

interface LinkRowProps {
  id: number;
  index: number;
  link: LinkItem;
  accentColor: string;
  onChange: (id: number, field: keyof LinkItem, value: string | IconValue) => void;
  onRemove: (id: number) => void;
}

function LinkRow({ id, index, link, accentColor, onChange, onRemove }: LinkRowProps) {
  const uid = useId();
  return (
    <div className={`${styles.linkRow} ${index === 0 ? styles.linkRowPrimary : ""}`}>
      <div className={styles.linkRowHead}>
        <span className={`${styles.linkBadge} ${index === 0 ? styles.linkBadgePrimary : ""}`}>
          {index === 0 ? "PRINCIPAL" : `LINK ${index + 1}`}
        </span>
        <button
          className={styles.linkDel}
          onClick={() => onRemove(id)}
          title="Remover link"
          type="button"
        >
          <svg
            width="11"
            height="11"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className={styles.linkFields}>
        <div className={styles.linkTitleRow}>
          <IconPicker
            value={link.icon}
            onChange={(v) => onChange(id, "icon", v)}
            accentColor={accentColor}
          />
          <input
            className={styles.input}
            placeholder="Título do botão"
            value={link.title}
            onChange={(e) => onChange(id, "title", e.target.value)}
            id={`${uid}-title`}
          />
        </div>
        <input
          className={styles.input}
          placeholder="https://..."
          type="url"
          value={link.url}
          onChange={(e) => onChange(id, "url", e.target.value)}
          id={`${uid}-url`}
        />
        <input
          className={styles.input}
          placeholder="Subtítulo (opcional)"
          value={link.subtitle}
          onChange={(e) => onChange(id, "subtitle", e.target.value)}
          id={`${uid}-sub`}
        />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main page
// ═══════════════════════════════════════════════════════════════════════════

const DEFAULT_COLOR = "#E01E37";

export default function GeradorPage() {
  const [nome, setNome] = useState("");
  const [handle, setHandle] = useState("");
  const [bio, setBio] = useState("");
  const [foto, setFoto] = useState("");
  const [favicon, setFavicon] = useState("");
  const [linkEntries, setLinkEntries] = useState<LinkEntry[]>(() => [newEntry()]);
  const [instagram, setInstagram] = useState("");
  const [tiktok, setTiktok] = useState("");
  const [video, setVideo] = useState("");
  const [hexInput, setHexInput] = useState(DEFAULT_COLOR);
  const [activeHex, setActiveHex] = useState(DEFAULT_COLOR);
  const [tema, setTema] = useState<Tema>("auto");
  const [nicho, setNicho] = useState("");
  const [downloaded, setDownloaded] = useState(false);

  const wrapRef = useRef<HTMLDivElement>(null);
  const phoneRef = useRef<HTMLDivElement>(null);
  const [previewDoc, setPreviewDoc] = useState("");

  // ── Derived scheme ────────────────────────────────────────────────────────

  const scheme = (() => {
    const s = buildScheme(activeHex);
    if (tema === "claro") return { ...s, theme: "light" as const, btnPrimText: "#161112" };
    if (tema === "escuro") return { ...s, theme: "dark" as const };
    return s;
  })();

  const swatchChips = [
    { color: scheme.accent, label: "accent" },
    { color: scheme.accent2, label: "accent-2" },
    { color: scheme.surface, label: "surface" },
    { color: scheme.bg, label: "bg" },
    { color: scheme.bgDeep, label: "bg-deep" },
  ];

  // ── Fitness detection ─────────────────────────────────────────────────────

  const FITNESS_KW = new Set([
    "fitness",
    "treino",
    "academia",
    "musculacao",
    "musculação",
    "gym",
    "crossfit",
    "personal",
    "nutricao",
    "nutrição",
    "dieta",
    "emagrecer",
    "hiit",
    "funcional",
    "atleta",
    "bodybuilder",
    "suplemento",
    "proteina",
    "proteína",
  ]);

  const nichoLower = nicho.toLowerCase();
  const fitness = nichoLower
    ? FITNESS_KW.has(nichoLower) || [...FITNESS_KW].some((kw) => nichoLower.includes(kw))
    : false;

  // ── Profile ───────────────────────────────────────────────────────────────

  const profile: Profile = {
    nome,
    handle: handle && !handle.startsWith("@") ? `@${handle}` : handle,
    bio,
    foto,
    favicon,
    links: linkEntries.map((e) => e.link),
    instagram,
    tiktok,
    outros: [],
    video,
  };

  // ── Preview update ────────────────────────────────────────────────────────

  const updatePreview = useCallback(() => {
    const s = buildScheme(activeHex);
    const resolvedScheme: ColorScheme =
      tema === "claro"
        ? { ...s, theme: "light", btnPrimText: "#161112" }
        : tema === "escuro"
          ? { ...s, theme: "dark" }
          : s;
    const nichoL = nicho.toLowerCase();
    const FKW = new Set([
      "fitness",
      "treino",
      "academia",
      "musculacao",
      "musculação",
      "gym",
      "crossfit",
      "personal",
      "nutricao",
      "nutrição",
      "dieta",
      "emagrecer",
      "hiit",
      "funcional",
      "atleta",
      "bodybuilder",
      "suplemento",
      "proteina",
      "proteína",
    ]);
    const isFit = nichoL ? FKW.has(nichoL) || [...FKW].some((kw) => nichoL.includes(kw)) : false;
    const p: Profile = {
      nome,
      bio,
      foto,
      favicon,
      instagram,
      tiktok,
      video,
      outros: [],
      handle: handle && !handle.startsWith("@") ? `@${handle}` : handle,
      links: linkEntries.map((e) => e.link),
    };
    setPreviewDoc(generateHTML(p, resolvedScheme, isFit));
  }, [
    nome,
    handle,
    bio,
    foto,
    favicon,
    linkEntries,
    instagram,
    tiktok,
    video,
    activeHex,
    tema,
    nicho,
  ]);

  useEffect(() => {
    const t = setTimeout(updatePreview, 300);
    return () => clearTimeout(t);
  }, [updatePreview]);

  // ── Preview scaling ───────────────────────────────────────────────────────

  useEffect(() => {
    const wrap = wrapRef.current;
    const phone = phoneRef.current;
    if (!wrap || !phone) return;
    const ro = new ResizeObserver(() => {
      const aw = wrap.clientWidth - 48;
      const ah = wrap.clientHeight - 48;
      const scale = Math.min(aw / 390, ah / 760, 1);
      phone.style.transform = `scale(${scale})`;
    });
    ro.observe(wrap);
    return () => ro.disconnect();
  }, []);

  // ── Color picker ──────────────────────────────────────────────────────────

  function applyHex(raw: string) {
    const hex = raw.startsWith("#") ? raw : `#${raw}`;
    if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
      setActiveHex(hex.toUpperCase());
      setHexInput(hex.toUpperCase());
    }
  }

  function onHexBlur() {
    const hex = hexInput.startsWith("#") ? hexInput : `#${hexInput}`;
    if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) setHexInput(activeHex);
    else applyHex(hexInput);
  }

  // ── Links ─────────────────────────────────────────────────────────────────

  function addLink() {
    setLinkEntries((prev) => [...prev, newEntry()]);
  }
  function removeLink(id: number) {
    setLinkEntries((prev) => prev.filter((e) => e.id !== id));
  }
  function updateLink(id: number, field: keyof LinkItem, value: string | IconValue) {
    setLinkEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, link: { ...e.link, [field]: value } } : e)),
    );
  }

  // ── Download ──────────────────────────────────────────────────────────────

  function downloadHTML() {
    const html = generateHTML(profile, scheme, fitness);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    a.download = "index.html";
    a.click();
    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2200);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={styles.root}>
      {/* ── Form panel ───────────────────────────────────────────── */}
      <aside className={styles.formPanel}>
        <div className={styles.panelHeader}>
          <h1 className={styles.panelTitle}>Gerador de Página Bio</h1>
          <p className={styles.panelSub}>Preencha os dados e baixe o site pronto</p>
        </div>

        <div className={styles.formScroll}>
          {/* Perfil */}
          <section className={styles.section}>
            <div className={styles.sectionLabel}>Perfil</div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-nome">
                Nome de exibição
              </label>
              <input
                id="g-nome"
                className={styles.input}
                placeholder="Maria Silva"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-handle">
                @ do Instagram
              </label>
              <input
                id="g-handle"
                className={styles.input}
                placeholder="@mariasilvafitness"
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-bio">
                Bio
              </label>
              <textarea
                id="g-bio"
                className={styles.textarea}
                rows={3}
                placeholder="Frase curta que aparece abaixo do nome"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-foto">
                URL da foto de perfil
              </label>
              <input
                id="g-foto"
                className={styles.input}
                type="url"
                placeholder="https://..."
                value={foto}
                onChange={(e) => setFoto(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-favicon">
                Ícone da aba <span className={styles.optional}>se vazio, usa a foto</span>
              </label>
              <input
                id="g-favicon"
                className={styles.input}
                type="url"
                placeholder="https://.../icone.png"
                value={favicon}
                onChange={(e) => setFavicon(e.target.value)}
              />
            </div>
          </section>

          {/* Links */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionLabel}>Links</div>
              <span className={styles.sectionHint}>1º vira botão colorido</span>
            </div>
            <div className={styles.linksContainer}>
              {linkEntries.map((entry, idx) => (
                <LinkRow
                  key={entry.id}
                  id={entry.id}
                  index={idx}
                  link={entry.link}
                  accentColor={activeHex}
                  onChange={updateLink}
                  onRemove={removeLink}
                />
              ))}
            </div>
            <button type="button" className={styles.addBtn} onClick={addLink}>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
              Adicionar Link
            </button>
          </section>

          {/* Redes */}
          <section className={styles.section}>
            <div className={styles.sectionLabel}>Redes Sociais</div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-ig">
                Instagram
              </label>
              <input
                id="g-ig"
                className={styles.input}
                type="url"
                placeholder="https://www.instagram.com/..."
                value={instagram}
                onChange={(e) => setInstagram(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-tt">
                TikTok
              </label>
              <input
                id="g-tt"
                className={styles.input}
                type="url"
                placeholder="https://www.tiktok.com/..."
                value={tiktok}
                onChange={(e) => setTiktok(e.target.value)}
              />
            </div>
          </section>

          {/* Mídia */}
          <section className={styles.section}>
            <div className={styles.sectionLabel}>Mídia</div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-video">
                Vídeo YouTube <span className={styles.optional}>opcional</span>
              </label>
              <input
                id="g-video"
                className={styles.input}
                type="url"
                placeholder="https://www.youtube.com/..."
                value={video}
                onChange={(e) => setVideo(e.target.value)}
              />
            </div>
          </section>

          {/* Visual */}
          <section className={styles.section}>
            <div className={styles.sectionLabel}>Visual</div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-hex">
                Cor de destaque
              </label>
              <div className={styles.colorRow}>
                <label className={styles.colorSwatch} style={{ background: activeHex }}>
                  <input
                    type="color"
                    value={activeHex}
                    onChange={(e) => applyHex(e.target.value)}
                    className={styles.srOnly}
                  />
                </label>
                <input
                  id="g-hex"
                  className={`${styles.input} ${styles.hexInput}`}
                  value={hexInput}
                  maxLength={7}
                  spellCheck={false}
                  placeholder="#000000"
                  onChange={(e) => {
                    setHexInput(e.target.value.toUpperCase());
                    applyHex(e.target.value);
                  }}
                  onBlur={onHexBlur}
                />
              </div>
              <div className={styles.swatches}>
                {swatchChips.map((c) => (
                  <div key={c.label} className={styles.chip}>
                    <div
                      className={styles.chipDot}
                      style={{ background: c.color }}
                      title={c.color}
                    />
                    <div className={styles.chipLabel}>{c.label}</div>
                  </div>
                ))}
                <span
                  className={`${styles.themeTag} ${scheme.theme === "light" ? styles.themeTagLight : ""}`}
                >
                  {scheme.theme === "light" ? "Tema Claro" : "Tema Escuro"}
                </span>
              </div>
            </div>

            <div className={styles.field}>
              <span className={styles.label}>Tema</span>
              <div className={styles.toggle}>
                {(["auto", "claro", "escuro"] as Tema[]).map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    className={`${styles.toggleOpt} ${tema === opt ? styles.toggleActive : ""}`}
                    onClick={() => setTema(opt)}
                  >
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="g-nicho">
                Nicho
                {fitness && (
                  <span
                    className={styles.optional}
                    style={{
                      background: "var(--color-primary-muted)",
                      borderColor: "transparent",
                      color: "var(--color-primary-hover)",
                    }}
                  >
                    fitness detectado
                  </span>
                )}
              </label>
              <input
                id="g-nicho"
                className={styles.input}
                placeholder="Ex: fitness, estética, culinária..."
                value={nicho}
                onChange={(e) => setNicho(e.target.value)}
              />
            </div>
          </section>

          {/* Baixar */}
          <section className={styles.section}>
            <button
              type="button"
              className={`${styles.dlBtnFull} ${downloaded ? styles.dlOk : ""}`}
              onClick={downloadHTML}
            >
              {downloaded ? (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                  Baixado!
                </>
              ) : (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Baixar index.html
                </>
              )}
            </button>
          </section>
        </div>
      </aside>

      {/* ── Preview panel ─────────────────────────────────────────── */}
      <div className={styles.previewPanel}>
        <div className={styles.previewBar}>
          <span className={styles.previewDot} />
          Prévia em tempo real
        </div>
        <div className={styles.previewWrap} ref={wrapRef}>
          <div className={styles.previewPhone} ref={phoneRef}>
            <iframe
              className={styles.previewFrame}
              title="Prévia"
              srcDoc={previewDoc}
              sandbox="allow-scripts"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
