import type { ReactNode } from "react";
import styles from "./AuthCard.module.css";

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

/**
 * Cartão central usado por todas as telas de autenticação
 * (login, cadastro, confirmação, recuperação de senha).
 */
export function AuthCard({ title, subtitle, children }: AuthCardProps) {
  return (
    <div className={styles.card}>
      <img src="/logo.png" alt="SysLink" className={styles.logo} width={40} height={40} />
      <h1 className={styles.title}>{title}</h1>
      {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
      {children}
    </div>
  );
}
