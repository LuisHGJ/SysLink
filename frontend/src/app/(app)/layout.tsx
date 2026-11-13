import { AuthGuard } from "@/components/AuthGuard";
import { Sidebar } from "@/components/Sidebar";
import type { ReactNode } from "react";

/**
 * Layout das rotas AUTENTICADAS (leads, escavador, gerador).
 * Sem sessão → AuthGuard redireciona para /login.
 * Fora do URL: route group "(app)" não altera as rotas.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <Sidebar />
      <div className="appContent">{children}</div>
    </AuthGuard>
  );
}
