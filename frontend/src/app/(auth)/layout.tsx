import { GuestGuard } from "@/components/AuthGuard";
import type { ReactNode } from "react";
import styles from "./layout.module.css";

/**
 * Layout das telas de autenticação (login, cadastro, etc.).
 * Sem sidebar e centralizado; com sessão ativa o GuestGuard
 * redireciona para /leads.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <GuestGuard>{children}</GuestGuard>
    </div>
  );
}
