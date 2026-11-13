"use client";

import { authApi } from "@/api/client";
import { AuthCard } from "@/components/AuthCard";
import styles from "@/components/AuthCard.module.css";
import Link from "next/link";
import { useState } from "react";

/**
 * Reenvio do e-mail de CONFIRMAÇÃO de cadastro (não confunde com
 * "esqueci-senha", que reenvia o link de redefinição de senha).
 * Resposta do backend é sempre genérica (anti-enumeração).
 */
export default function ResendConfirmationPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.resendConfirmation(email);
      setSent(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthCard title="Verifique seu e-mail" subtitle="Reenvio de confirmação">
        <output className={styles.success}>{sent}</output>
        <div className={styles.links}>
          <Link href="/login">Ir para o login</Link>
          <Link href="/cadastro">Criar conta</Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Reenviar confirmação"
      subtitle="Enviaremos um novo link de ativação para o seu e-mail"
    >
      <form className={styles.form} onSubmit={handleSubmit}>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="voce@empresa.com"
            autoComplete="email"
            required
          />
        </div>

        <button type="submit" className={styles.button} disabled={loading}>
          {loading ? "Enviando…" : "Reenviar link"}
        </button>
      </form>

      <div className={styles.links}>
        <Link href="/login">Voltar ao login</Link>
      </div>
    </AuthCard>
  );
}
