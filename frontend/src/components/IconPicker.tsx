"use client";

import {
  Award,
  BookOpen,
  Calendar,
  Camera,
  Clock,
  Coffee,
  Dumbbell,
  FileText,
  Gift,
  Globe,
  Heart,
  Link as LinkIcon,
  type LucideIcon,
  Mail,
  MapPin,
  MessageCircle,
  Mic,
  Phone,
  Play,
  Scissors,
  ShoppingBag,
  ShoppingCart,
  Star,
  Tag,
  Users,
  Utensils,
  Video,
  Wallet,
  Zap,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { renderToStaticMarkup } from "react-dom/server";
import {
  siDiscord,
  siFacebook,
  siGithub,
  siGmail,
  siInstagram,
  siPaypal,
  siPinterest,
  siShopify,
  siSpotify,
  siTelegram,
  siTiktok,
  siTwitch,
  siWhatsapp,
  siX,
  siYoutube,
} from "simple-icons";
import styles from "./IconPicker.module.css";

export type IconColor = "accent" | "white" | "black";

export interface IconValue {
  type: "generic" | "brand";
  key: string;
  color: IconColor;
}

export const DEFAULT_ICON: IconValue = { type: "generic", key: "link", color: "accent" };

interface GenericDef {
  key: string;
  label: string;
  Icon: LucideIcon;
}

interface BrandDef {
  key: string;
  label: string;
  path: string;
}

// ─── Ícones genéricos — lucide-react ─────────────────────────────────────────
const GENERICS: GenericDef[] = [
  { key: "link", label: "Link", Icon: LinkIcon },
  { key: "cart", label: "Carrinho", Icon: ShoppingCart },
  { key: "tag", label: "Preço", Icon: Tag },
  { key: "star", label: "Estrela", Icon: Star },
  { key: "calendar", label: "Agenda", Icon: Calendar },
  { key: "phone", label: "Telefone", Icon: Phone },
  { key: "mail", label: "E-mail", Icon: Mail },
  { key: "map", label: "Localização", Icon: MapPin },
  { key: "video", label: "Vídeo", Icon: Video },
  { key: "book", label: "Curso", Icon: BookOpen },
  { key: "gift", label: "Presente", Icon: Gift },
  { key: "scissors", label: "Beleza", Icon: Scissors },
  { key: "dumbbell", label: "Fitness", Icon: Dumbbell },
  { key: "utensils", label: "Comida", Icon: Utensils },
  { key: "heart", label: "Coração", Icon: Heart },
  { key: "globe", label: "Website", Icon: Globe },
  { key: "clock", label: "Horário", Icon: Clock },
  { key: "play", label: "Reproduzir", Icon: Play },
  { key: "camera", label: "Foto", Icon: Camera },
  { key: "mic", label: "Áudio", Icon: Mic },
  { key: "wallet", label: "Pagamento", Icon: Wallet },
  { key: "chat", label: "Mensagem", Icon: MessageCircle },
  { key: "bag", label: "Loja", Icon: ShoppingBag },
  { key: "coffee", label: "Café", Icon: Coffee },
  { key: "award", label: "Prêmio", Icon: Award },
  { key: "users", label: "Comunidade", Icon: Users },
  { key: "file", label: "Arquivo", Icon: FileText },
  { key: "zap", label: "Destaque", Icon: Zap },
];

// ─── Marcas — simple-icons ───────────────────────────────────────────────────
// O simple-icons não distribui mais a marca LinkedIn, então o path fica local.
const LINKEDIN_PATH =
  "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z";

const BRANDS: BrandDef[] = [
  { key: "whatsapp", label: "WhatsApp", path: siWhatsapp.path },
  { key: "facebook", label: "Facebook", path: siFacebook.path },
  { key: "instagram", label: "Instagram", path: siInstagram.path },
  { key: "tiktok", label: "TikTok", path: siTiktok.path },
  { key: "youtube", label: "YouTube", path: siYoutube.path },
  { key: "spotify", label: "Spotify", path: siSpotify.path },
  { key: "x", label: "X (Twitter)", path: siX.path },
  { key: "linkedin", label: "LinkedIn", path: LINKEDIN_PATH },
  { key: "telegram", label: "Telegram", path: siTelegram.path },
  { key: "discord", label: "Discord", path: siDiscord.path },
  { key: "github", label: "GitHub", path: siGithub.path },
  { key: "gmail", label: "Gmail", path: siGmail.path },
  { key: "pinterest", label: "Pinterest", path: siPinterest.path },
  { key: "shopify", label: "Shopify", path: siShopify.path },
  { key: "paypal", label: "PayPal", path: siPaypal.path },
  { key: "twitch", label: "Twitch", path: siTwitch.path },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────
function resolveColor(color: IconColor, accent: string): string {
  if (color === "accent") return accent;
  return color === "white" ? "#ffffff" : "#000000";
}

function brandSvg(path: string, color: string): string {
  return `<svg width="16" height="16" viewBox="0 0 24 24" fill="${color}"><path d="${path}"/></svg>`;
}

function genericSvg(key: string, color: string): string {
  const def = GENERICS.find((g) => g.key === key) ?? GENERICS[0];
  const { Icon } = def;
  return renderToStaticMarkup(<Icon size={16} color={color} strokeWidth={2} />);
}

/** SVG (string) do ícone — usado no HTML estático gerado pelo Gerador. */
export function getIconSvg(icon: IconValue, accentColor = "currentColor"): string {
  const color = resolveColor(icon.color, accentColor);
  if (icon.type === "brand") {
    const brand = BRANDS.find((b) => b.key === icon.key);
    return brandSvg(brand?.path ?? LINKEDIN_PATH, color);
  }
  return genericSvg(icon.key, color);
}

/** Elemento React do ícone — usado na UI do seletor. */
function IconElement({
  icon,
  color,
  size = 16,
}: { icon: IconValue; color: string; size?: number }) {
  if (icon.type === "brand") {
    const brand = BRANDS.find((b) => b.key === icon.key) ?? BRANDS[0];
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true">
        <path d={brand.path} />
      </svg>
    );
  }
  const def = GENERICS.find((g) => g.key === icon.key) ?? GENERICS[0];
  const { Icon } = def;
  return <Icon size={size} color={color} strokeWidth={2} aria-hidden="true" />;
}

// ─── Componente ──────────────────────────────────────────────────────────────
interface Props {
  value: IconValue;
  onChange: (v: IconValue) => void;
  accentColor?: string;
}

const DROPDOWN_WIDTH = 280;
const DROPDOWN_HEIGHT = 360;

export function IconPicker({ value, onChange, accentColor = "#10b981" }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Abre já com o foco na busca (sem causar scroll da página).
  useEffect(() => {
    if (open) searchRef.current?.focus({ preventScroll: true });
  }, [open]);

  // Fecha ao clicar fora, ao apertar Esc ou ao rolar o formulário.
  useEffect(() => {
    if (!open) return;

    function onDown(e: MouseEvent) {
      const target = e.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (dropdownRef.current?.contains(target)) return;
      setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onScroll(e: Event) {
      const target = e.target as Node | null;
      // A lista interna do dropdown pode rolar sem fechar.
      if (target && dropdownRef.current?.contains(target)) return;
      setOpen(false);
    }

    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    document.addEventListener("scroll", onScroll, true);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  function toggle() {
    if (!open) {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (rect) {
        const margin = 8;
        let left = rect.left;
        if (left + DROPDOWN_WIDTH > window.innerWidth - margin) {
          left = Math.max(margin, window.innerWidth - DROPDOWN_WIDTH - margin);
        }
        let top = rect.bottom + 6;
        if (top + DROPDOWN_HEIGHT > window.innerHeight - margin) {
          top = Math.max(margin, rect.top - DROPDOWN_HEIGHT - 6);
        }
        setPos({ top, left });
      }
      setSearch("");
    }
    setOpen(!open);
  }

  const q = search.trim().toLowerCase();
  const filtG = GENERICS.filter(
    (x) => !q || x.key.includes(q) || x.label.toLowerCase().includes(q),
  );
  const filtB = BRANDS.filter((x) => !q || x.key.includes(q) || x.label.toLowerCase().includes(q));

  const color = resolveColor(value.color, accentColor);

  const dropdown =
    open &&
    createPortal(
      <div
        ref={dropdownRef}
        className={styles.dropdown}
        style={{ top: pos.top, left: pos.left }}
        aria-label="Selecionar ícone"
      >
        <div className={styles.searchWrap}>
          <input
            ref={searchRef}
            className={styles.search}
            placeholder="Buscar ícone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className={styles.colorRow}>
          <span className={styles.colorLabel}>Cor:</span>
          {(["accent", "white", "black"] as IconColor[]).map((c) => (
            <button
              key={c}
              type="button"
              className={styles.colorChip + (value.color === c ? ` ${styles.colorChipActive}` : "")}
              style={{
                background: resolveColor(c, accentColor),
                border: c === "white" ? "1px solid #555" : "none",
              }}
              title={c === "accent" ? "Destaque" : c === "white" ? "Branco" : "Preto"}
              onClick={() => onChange({ ...value, color: c })}
            />
          ))}
        </div>

        <div className={styles.scroll}>
          {filtG.length > 0 && (
            <>
              <div className={styles.groupLabel}>Geral</div>
              <div className={styles.grid}>
                {filtG.map((g) => {
                  const { Icon } = g;
                  const active = value.type === "generic" && value.key === g.key;
                  return (
                    <button
                      key={g.key}
                      type="button"
                      className={styles.item + (active ? ` ${styles.itemActive}` : "")}
                      title={g.label}
                      onClick={() => {
                        onChange({ type: "generic", key: g.key, color: value.color });
                        setOpen(false);
                      }}
                    >
                      <Icon size={16} color={color} strokeWidth={2} aria-hidden="true" />
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {filtB.length > 0 && (
            <>
              <div className={styles.groupLabel}>Marcas</div>
              <div className={styles.grid}>
                {filtB.map((b) => {
                  const active = value.type === "brand" && value.key === b.key;
                  return (
                    <button
                      key={b.key}
                      type="button"
                      className={styles.item + (active ? ` ${styles.itemActive}` : "")}
                      title={b.label}
                      onClick={() => {
                        onChange({ type: "brand", key: b.key, color: value.color });
                        setOpen(false);
                      }}
                    >
                      <svg
                        width={16}
                        height={16}
                        viewBox="0 0 24 24"
                        fill={color}
                        aria-hidden="true"
                      >
                        <path d={b.path} />
                      </svg>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {filtG.length === 0 && filtB.length === 0 && (
            <div className={styles.empty}>Nenhum ícone encontrado</div>
          )}
        </div>
      </div>,
      document.body,
    );

  return (
    <div className={styles.root} ref={rootRef}>
      <button
        type="button"
        ref={triggerRef}
        className={styles.trigger}
        onClick={toggle}
        title="Selecionar ícone"
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <span className={styles.preview}>
          <IconElement icon={value} color={color} size={16} />
        </span>
        <svg
          className={styles.chevron}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {dropdown}
    </div>
  );
}
