"use client";

import { authApi } from "@/api/client";
import { AuthCard } from "@/components/AuthCard";
import styles from "@/components/AuthCard.module.css";
import Link from "next/link";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.forgot(email);
      setSent(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthCard title="Verifique seu e-mail" subtitle="Recuperação de senha">
        <output className={styles.success}>{sent}</output>
        <div className={styles.links}>
          <Link href="/login">Voltar ao login</Link>
          <Link href="/cadastro">Criar conta</Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Esqueci minha senha"
      subtitle="Enviaremos um link de redefinição para o seu e-mail"
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
          {loading ? "Enviando…" : "Enviar link"}
        </button>
      </form>

      <div className={styles.links}>
        <Link href="/login">Voltar ao login</Link>
      </div>
    </AuthCard>
  );
}
