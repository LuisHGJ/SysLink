"use client";

import { clearToken } from "@/api/auth";
import { LogOut, Moon, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import styles from "./Sidebar.module.css";

/** Chave do tema persistida no navegador (mesma usada no script do layout). */
const THEME_KEY = "syslink-theme";
type Theme = "dark" | "light";

const NAV_ITEMS = [
  {
    href: "/leads",
    label: "Leads",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    href: "/escavador",
    label: "Escavador",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
        <path d="M11 8v6" />
        <path d="M8 11h6" />
      </svg>
    ),
  },
  {
    href: "/gerador",
    label: "Gerador",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [theme, setTheme] = useState<Theme>("dark");

  // O script do layout já aplicou o tema salvo antes da hidratação;
  // aqui só lemos o atributo para o ícone ficar coerente.
  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
  }, []);

  const toggleTheme = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    // data-theme só existe no modo claro; o escuro é o padrão sem atributo.
    if (next === "light") {
      document.documentElement.dataset.theme = "light";
    } else {
      delete document.documentElement.dataset.theme;
    }
    window.localStorage.setItem(THEME_KEY, next);
  };

  const isDark = theme === "dark";
  const toggleLabel = isDark ? "Ativar modo claro" : "Ativar modo escuro";

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <img src="/logo.png" alt="SysLink" className={styles.logo} width={32} height={32} />
        <span className={styles.brandName}>SysLink</span>
      </div>

      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${active ? styles.active : ""}`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className={styles.footer}>
        <span className={styles.version}>v0.1.0</span>
        <div className={styles.footerActions}>
          <button
            type="button"
            className={styles.themeBtn}
            onClick={toggleTheme}
            aria-label={toggleLabel}
            aria-pressed={!isDark}
            title={toggleLabel}
          >
            {isDark ? <Sun size={15} aria-hidden="true" /> : <Moon size={15} aria-hidden="true" />}
          </button>
          <button
            type="button"
            className={styles.themeBtn}
            onClick={handleLogout}
            aria-label="Sair da conta"
            title="Sair da conta"
          >
            <LogOut size={15} aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  );
}
