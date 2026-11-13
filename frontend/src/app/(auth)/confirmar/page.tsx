"use client";

import { authApi } from "@/api/client";
import { AuthCard } from "@/components/AuthCard";
import styles from "@/components/AuthCard.module.css";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

type Status = "pending" | "ok" | "error";

function ConfirmContent() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [status, setStatus] = useState<Status>("pending");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Link inválido: token ausente.");
      return;
    }
    let cancelled = false;
    authApi
      .confirm(token)
      .then((res) => {
        if (cancelled) return;
        setStatus("ok");
        setMessage(res.message);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Erro inesperado.");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <AuthCard title="Confirmação de e-mail" subtitle="Ativando sua conta no SysLink">
      {status === "pending" ? <output className={styles.success}>Confirmando…</output> : null}

      {status === "ok" ? (
        <>
          <output className={styles.success}>{message}</output>
          <Link href="/login" className={styles.button}>
            Ir para o login
          </Link>
        </>
      ) : null}

      {status === "error" ? (
        <>
          <p className={styles.error} role="alert">
            {message}
          </p>
          <div className={styles.links}>
            <Link href="/login">Ir para o login</Link>
            <Link href="/reenviar-confirmacao">Reenviar e-mail</Link>
          </div>
        </>
      ) : null}
    </AuthCard>
  );
}

export default function ConfirmarPage() {
  // useSearchParams exige Suspense para o build estático do Next.
  return (
    <Suspense fallback={null}>
      <ConfirmContent />
    </Suspense>
  );
}
