"""
site_generator.py — Gerador de página bio a partir de URL do Linktree.

Uso:
    python site_generator.py <url_linktree> [opções]

Opções:
    --cor       #RRGGBB   Cor de destaque (sobrescreve auto-detecção)
    --tema      claro|escuro  Tema (sobrescreve auto-detecção)
    --nicho     fitness|outro  Força o nicho (sobrescreve detecção pela bio)
    --saida     caminho/pasta  Pasta de saída (padrão: ./output)

Exemplo:
    python site_generator.py https://linktr.ee/fulano --cor #E01E37 --saida ./sites/fulano
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

# ── Dependências opcionais ────────────────────────────────────────────────────
try:
    import httpx
except ImportError:
    sys.exit("Instale httpx:  pip install httpx")

try:
    from PIL import Image
except ImportError:
    sys.exit("Instale Pillow:  pip install Pillow")

try:
    from colorthief import ColorThief
except ImportError:
    sys.exit("Instale colorthief:  pip install colorthief")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PARSER DO LINKTREE
# ═══════════════════════════════════════════════════════════════════════════════

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def fetch_linktree(url: str) -> dict:
    """Baixa o HTML do Linktree e extrai os dados do perfil."""
    with httpx.Client(timeout=20, follow_redirects=True, headers=_HEADERS) as c:
        resp = c.get(url)
        resp.raise_for_status()
        html = resp.text

    # O Linktree injeta __NEXT_DATA__ com todos os dados em JSON
    match = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError(
            "Não encontrei __NEXT_DATA__ no HTML. "
            "O perfil pode ser privado ou o Linktree mudou a estrutura."
        )

    data = json.loads(match.group(1))

    # Navega até o objeto do perfil
    try:
        page_props = data["props"]["pageProps"]
    except KeyError:
        raise RuntimeError("Estrutura do __NEXT_DATA__ inesperada.")

    # Suporte a dois formatos que o Linktree usa:
    # 1. pageProps.account  (mais comum)
    # 2. pageProps.profile / pageProps.data.account
    account = (
        page_props.get("account")
        or page_props.get("profile")
        or (page_props.get("data") or {}).get("account")
        or {}
    )

    links_raw = (
        account.get("links")
        or page_props.get("links")
        or (page_props.get("data") or {}).get("links")
        or []
    )

    return {"account": account, "links": links_raw, "page_props": page_props}


def parse_profile(raw: dict) -> dict:
    """Normaliza os dados brutos do Linktree para o formato interno."""
    account = raw["account"]
    links_raw = raw["links"]

    # ── Dados básicos ─────────────────────────────────────────────────────────
    nome = (
        account.get("name")
        or account.get("pageTitle")
        or account.get("username")
        or ""
    )
    nome = _clean_name(nome)

    handle = account.get("username") or ""
    if handle and not handle.startswith("@"):
        handle = f"@{handle}"

    bio = account.get("description") or account.get("bio") or ""
    bio = _clean_bio(bio)

    foto = (
        account.get("profilePictureUrl")
        or account.get("avatar")
        or account.get("picture")
        or ""
    )

    # ── Links ─────────────────────────────────────────────────────────────────
    instagram = ""
    tiktok = ""
    outros: list[str] = []
    links: list[dict] = []

    for lk in links_raw:
        if not isinstance(lk, dict):
            continue
        url = (lk.get("url") or lk.get("link") or "").strip()
        title = (lk.get("title") or lk.get("name") or "").strip()
        subtitle = (lk.get("subtitle") or lk.get("description") or "").strip()

        if not url:
            continue

        # Ícones de redes sociais ficam em campos separados
        lower = url.lower()
        if "instagram.com" in lower:
            instagram = url
            continue
        if "tiktok.com" in lower:
            tiktok = url
            continue

        # Outros links de redes (youtube, twitter, etc.) vão em "outros"
        _SOCIAL_DOMAINS = (
            "youtube.com", "youtu.be", "twitter.com", "x.com",
            "facebook.com", "spotify.com", "linkedin.com", "pinterest.com",
            "whatsapp.com", "t.me",
        )
        if any(d in lower for d in _SOCIAL_DOMAINS):
            outros.append(url)
            continue

        links.append({"title": title, "subtitle": subtitle, "url": url})

    return {
        "nome": nome,
        "handle": handle,
        "bio": bio,
        "foto": foto,
        "links": links,
        "instagram": instagram,
        "tiktok": tiktok,
        "outros": outros,
        "video": "",
    }


def _clean_name(name: str) -> str:
    """Remove @ e espaços extras do nome."""
    name = name.strip().lstrip("@")
    name = re.sub(r"\s{2,}", " ", name)
    return name[:60]


def _clean_bio(bio: str) -> str:
    """Limpa a bio: remove espaços duplicados, limita tamanho."""
    bio = bio.strip()
    bio = re.sub(r"\s{2,}", " ", bio)
    return bio[:220]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. COR DE DESTAQUE
# ═══════════════════════════════════════════════════════════════════════════════

def dominant_accent(foto_url: str) -> Optional[str]:
    """
    Baixa a foto de perfil e retorna a cor mais saturada como hex.
    Retorna None se falhar.
    """
    if not foto_url:
        return None
    try:
        with httpx.Client(timeout=15, headers=_HEADERS) as c:
            resp = c.get(foto_url)
            resp.raise_for_status()
            img_bytes = resp.content

        ct = ColorThief(io.BytesIO(img_bytes))
        palette = ct.get_palette(color_count=8, quality=1)

        best = max(palette, key=lambda rgb: _saturation(*rgb))
        r, g, b = best
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception as exc:
        print(f"[aviso] Não foi possível extrair cor da foto: {exc}", file=sys.stderr)
        return None


def _saturation(r: int, g: int, b: int) -> float:
    """Saturação HSL (0–1)."""
    rf, gf, bf = r / 255, g / 255, b / 255
    cmax = max(rf, gf, bf)
    cmin = min(rf, gf, bf)
    delta = cmax - cmin
    l = (cmax + cmin) / 2
    if delta == 0:
        return 0.0
    return delta / (1 - abs(2 * l - 1))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CONVERSÃO DE CORES
# ═══════════════════════════════════════════════════════════════════════════════

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    rf, gf, bf = r / 255, g / 255, b / 255
    cmax = max(rf, gf, bf)
    cmin = min(rf, gf, bf)
    delta = cmax - cmin
    l = (cmax + cmin) / 2

    if delta == 0:
        h = s = 0.0
    else:
        s = delta / (1 - abs(2 * l - 1))
        if cmax == rf:
            h = 60 * (((gf - bf) / delta) % 6)
        elif cmax == gf:
            h = 60 * (((bf - rf) / delta) + 2)
        else:
            h = 60 * (((rf - gf) / delta) + 4)

    return h, s, l


def hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if 0 <= h < 60:
        rf, gf, bf = c, x, 0
    elif 60 <= h < 120:
        rf, gf, bf = x, c, 0
    elif 120 <= h < 180:
        rf, gf, bf = 0, c, x
    elif 180 <= h < 240:
        rf, gf, bf = 0, x, c
    elif 240 <= h < 300:
        rf, gf, bf = x, 0, c
    else:
        rf, gf, bf = c, 0, x

    r = round((rf + m) * 255)
    g = round((gf + m) * 255)
    b = round((bf + m) * 255)
    return r, g, b


def hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = hsl_to_rgb(h, s, l)
    return f"#{r:02X}{g:02X}{b:02X}"


def build_color_scheme(accent_hex: str) -> dict:
    """
    A partir da cor de destaque, deriva todas as variáveis CSS do :root.
    """
    r, g, b = hex_to_rgb(accent_hex)
    h, s, l = rgb_to_hsl(r, g, b)

    # Tema: claro se luminosidade > 0.65
    is_light = l > 0.65

    # --accent-rgb
    accent_rgb = f"{r},{g},{b}"

    # --accent-2: versão um pouco mais clara (tema escuro) / igual (tema claro)
    if is_light:
        accent_2 = accent_hex
    else:
        l2 = min(l + 0.10, 0.85)
        accent_2 = hsl_to_hex(h, s, l2)

    if is_light:
        bg = "#FBF8F7"
        bg_rgb = "251,248,247"
        bg_deep = "#EFEAE8"
        bg_end = "#F7F3F2"
        surface = "#FFFFFF"
        btn_primary_text = "#161112"
        theme = "light"
    else:
        bg_r, bg_g, bg_b = hsl_to_rgb(h, min(s, 0.6), 0.06)
        bg = f"#{bg_r:02X}{bg_g:02X}{bg_b:02X}"
        bg_rgb = f"{bg_r},{bg_g},{bg_b}"

        deep_r, deep_g, deep_b = hsl_to_rgb(h, min(s, 0.5), 0.03)
        bg_deep = f"#{deep_r:02X}{deep_g:02X}{deep_b:02X}"

        end_r, end_g, end_b = hsl_to_rgb(h, 0.05, 0.03)
        bg_end = f"#{end_r:02X}{end_g:02X}{end_b:02X}"

        surf_r, surf_g, surf_b = hsl_to_rgb(h, min(s, 0.55), 0.08)
        surface = f"#{surf_r:02X}{surf_g:02X}{surf_b:02X}"

        btn_primary_text = "#161112" if l > 0.55 else "#FFFFFF"
        theme = "dark"

    return {
        "accent": accent_hex,
        "accent_rgb": accent_rgb,
        "accent_2": accent_2,
        "bg": bg,
        "bg_rgb": bg_rgb,
        "bg_deep": bg_deep,
        "bg_end": bg_end,
        "surface": surface,
        "btn_primary_text": btn_primary_text,
        "theme": theme,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DETECÇÃO DE NICHO
# ═══════════════════════════════════════════════════════════════════════════════

_FITNESS_KEYWORDS = {
    "fitness", "treino", "academia", "musculação", "musculacao",
    "gym", "crossfit", "personal", "nutrição", "nutricao",
    "dieta", "emagrecer", "hiit", "funcional", "atleta",
    "bodybuilder", "suplemento", "proteina", "proteína",
}


def is_fitness(bio: str) -> bool:
    """Retorna True se a bio tiver palavras-chave de fitness."""
    words = set(re.findall(r"\w+", bio.lower()))
    return bool(words & _FITNESS_KEYWORDS)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TEMPLATE HTML
# ═══════════════════════════════════════════════════════════════════════════════

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR"{{THEME_ATTR}}>
<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{{NOME}}</title>
<meta name="description" content="{{BIO_SHORT}}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{{NOME}}">
<meta property="og:description" content="{{BIO_SHORT}}">
<meta property="og:image" content="{{FOTO}}">
<meta name="twitter:card" content="summary_large_image">

<meta name="theme-color" content="{{BG}}">

<link rel="icon" href="{{ICON}}">
<link rel="apple-touch-icon" href="{{ICON}}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
:root{

  --accent:{{ACCENT}};
  --accent-rgb:{{ACCENT_RGB}};
  --accent-2:{{ACCENT_2}};

  --bg:{{BG}};
  --bg-rgb:{{BG_RGB}};
  --bg-deep:{{BG_DEEP}};
  --bg-end:{{BG_END}};
  --surface:{{SURFACE}};

  --text:#FFFFFF;
  --muted:rgba(255,255,255,.62);
  --faint:rgba(255,255,255,.35);
  --grid:rgba(255,255,255,.035);
  --name-shadow:0 4px 18px rgba(0,0,0,.6);

  --btn-bg:#161112;
  --btn-border:rgba(255,255,255,.10);
  --btn-text:#FFFFFF;
  --btn-primary-text:{{BTN_PRIMARY_TEXT}};
  --display:'Anton',sans-serif;
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
  font-size:clamp(38px,10vw,52px);
  line-height:.95;
  letter-spacing:.01em;
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
  padding:10px 18px;
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
  box-shadow:0 6px 22px rgba(0,0,0,.5);
}
.video-card .play svg{width:22px;height:22px;margin-left:3px}
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

{{BG_AFTER}}

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

const PROFILE = {{PROFILE_JSON}};

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
  try { return new URL(url).hostname.replace(/^www\\./, "").toLowerCase(); }
  catch(e){ return ""; }
}

function normalizeLink(item){
  if (typeof item === "string"){
    const md = item.match(/^\\[(.+?)\\]\\((https?:\\/\\/\\S+)\\)$/);
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
  let m = url.match(/(?:youtube\\.com\\/(?:watch\\?v=|embed\\/|shorts\\/)|youtu\\.be\\/)+([\\w-]{6,})/i);
  if (m) return "https://www.youtube.com/embed/" + m[1];
  m = url.match(/vimeo\\.com\\/(\\d+)/i);
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
                + (thumb ? '<img src="'+thumb+'" alt="Video" loading="lazy">' : '')
              : 'onclick="window.open(\''+PROFILE.video+'\',\'_blank\')">'
                + '<img src="'+(thumb||"")+'" alt="Video" loading="lazy" style="background:#000">')
          + '<span class="play"><svg viewBox="0 0 24 24" fill="#fff"><path d="M8 5l12 7-12 7z"/></svg></span>'
          + '<span class="caption">Assistir ao video</span>'
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

  html += '<div class="footer reveal" style="--i:'+(i++)+'">&#169; '+new Date().getFullYear()+' '+PROFILE.handle+'</div>';

  content.innerHTML = html;

  const card = content.querySelector(".video-card[data-embed]");
  if (card){
    card.addEventListener("click", function(){
      card.innerHTML = '<iframe src="'+card.dataset.embed+'?autoplay=1" title="Video" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
      card.style.cursor = "default";
    });
  }
}

buildPage();
</script>
</body>
</html>
"""

_BG_AFTER_FITNESS = (
    ".bg::after{content:\"\";position:absolute;inset:0;opacity:.09;"
    "background-size:96px 96px;"
    "background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='96' height='96' viewBox='0 0 96 96'%3E%3Cg fill='none' stroke='{{ACCENT_ENCODED}}' "
    "stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'%3E"
    "%3Cpath d='M38 48h20M34 41v14M62 41v14M40 43v10M56 43v10'/%3E"
    "%3C/g%3E%3C/svg%3E\")}"
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MONTAGEM DO HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _url_encode_hex(hex_color: str) -> str:
    """Converte #E01E37 para %23E01E37 para uso em SVG inline."""
    return hex_color.replace("#", "%23")


def build_html(profile: dict, colors: dict, fitness: bool) -> str:
    """Preenche o template com os dados do perfil e o esquema de cores."""
    theme_attr = ' data-theme="light"' if colors["theme"] == "light" else ""

    if fitness:
        bg_after = _BG_AFTER_FITNESS.replace(
            "{{ACCENT_ENCODED}}", _url_encode_hex(colors["accent"])
        )
    else:
        bg_after = ""

    bio_short = profile["bio"][:150] if profile["bio"] else profile["nome"]
    icon = profile["foto"] or ""

    profile_json = json.dumps(
        {
            "nome": profile["nome"],
            "handle": profile["handle"],
            "bio": profile["bio"],
            "links": profile["links"],
            "instagram": profile["instagram"],
            "tiktok": profile["tiktok"],
            "outros": profile["outros"],
            "video": profile["video"],
            "foto": profile["foto"],
        },
        ensure_ascii=False,
        indent=2,
    )

    html = _TEMPLATE
    replacements = {
        "{{THEME_ATTR}}": theme_attr,
        "{{NOME}}": profile["nome"],
        "{{BIO_SHORT}}": bio_short,
        "{{FOTO}}": profile["foto"],
        "{{BG}}": colors["bg"],
        "{{ICON}}": icon,
        "{{ACCENT}}": colors["accent"],
        "{{ACCENT_RGB}}": colors["accent_rgb"],
        "{{ACCENT_2}}": colors["accent_2"],
        "{{BG_RGB}}": colors["bg_rgb"],
        "{{BG_DEEP}}": colors["bg_deep"],
        "{{BG_END}}": colors["bg_end"],
        "{{SURFACE}}": colors["surface"],
        "{{BTN_PRIMARY_TEXT}}": colors["btn_primary_text"],
        "{{BG_AFTER}}": bg_after,
        "{{PROFILE_JSON}}": profile_json,
    }

    for marker, value in replacements.items():
        html = html.replace(marker, value)

    return html


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PONTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_ACCENT = "#E01E37"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera pagina bio a partir de uma URL do Linktree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Exemplos:
              python site_generator.py https://linktr.ee/fulano
              python site_generator.py https://linktr.ee/fulano --cor #9B59B6
              python site_generator.py https://linktr.ee/fulano --tema claro --saida ./sites/fulano
            """
        ),
    )
    parser.add_argument("url", help="URL do Linktree do cliente")
    parser.add_argument(
        "--cor",
        metavar="#RRGGBB",
        help="Cor de destaque (sobrescreve auto-deteccao pela foto)",
    )
    parser.add_argument(
        "--tema",
        choices=["claro", "escuro"],
        help="Tema (sobrescreve auto-deteccao pela luminosidade da cor)",
    )
    parser.add_argument(
        "--nicho",
        choices=["fitness", "outro"],
        help="Nicho (sobrescreve deteccao pela bio)",
    )
    parser.add_argument(
        "--saida",
        metavar="PASTA",
        default="./output",
        help="Pasta de saida (padrao: ./output)",
    )

    args = parser.parse_args()

    print(f"[1/5] Buscando {args.url} ...")
    raw = fetch_linktree(args.url)
    profile = parse_profile(raw)
    print(f"      -> {profile['nome']} ({profile['handle']}), {len(profile['links'])} links")

    if args.cor:
        accent = args.cor if args.cor.startswith("#") else f"#{args.cor}"
        print(f"[2/5] Cor informada: {accent}")
    else:
        print("[2/5] Extraindo cor da foto ...")
        accent = dominant_accent(profile["foto"]) or _DEFAULT_ACCENT
        print(f"      -> {accent}")

    print("[3/5] Calculando esquema de cores ...")
    colors = build_color_scheme(accent)

    if args.tema:
        colors["theme"] = "light" if args.tema == "claro" else "dark"
        if colors["theme"] == "light":
            colors["btn_primary_text"] = "#161112"

    print(f"      -> tema: {colors['theme']}, accent-2: {colors['accent_2']}, bg: {colors['bg']}")

    print("[4/5] Detectando nicho ...")
    if args.nicho:
        fitness = args.nicho == "fitness"
    else:
        fitness = is_fitness(profile["bio"])
    print(f"      -> {'fitness (halter ativo)' if fitness else 'outro nicho (halter removido)'}")

    print("[5/5] Gerando HTML ...")
    html = build_html(profile, colors, fitness)

    out_dir = Path(args.saida)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")

    print(f"\nArquivo gerado: {out_file.resolve()}")
    print("Abra no navegador para visualizar.")


if __name__ == "__main__":
    main()
