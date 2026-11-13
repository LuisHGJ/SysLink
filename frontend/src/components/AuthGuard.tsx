"use client";

import { getToken } from "@/api/auth";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

/**
 * Protege rotas autenticadas: sem token → /login.
 * Os filhos só montam depois da checagem — evita disparar chamadas
 * de API que cairiam em 401 logo no carregamento da página.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (getToken()) {
      setChecked(true);
    } else {
      router.replace("/login");
    }
  }, [router]);

  if (!checked) return null;
  return <>{children}</>;
}

/**
 * Protege telas de auth: quem já tem sessão vai para /leads.
 * Renderiza na hora (caso comum = visitante sem token) e só redireciona
 * se existir sessão ativa.
 */
export function GuestGuard({ children }: { children: ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (getToken()) router.replace("/leads");
  }, [router]);

  return <>{children}</>;
}
