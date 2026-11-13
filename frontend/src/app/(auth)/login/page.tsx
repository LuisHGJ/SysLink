"use client";

import { setToken } from "@/api/auth";
import { ApiError, authApi } from "@/api/client";
import { AuthCard } from "@/components/AuthCard";
import styles from "@/components/AuthCard.module.css";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [unverified, setUnverified] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setUnverified(false);
    setLoading(true);
    try {
      const { access_token } = await authApi.login({ email, password });
      setToken(access_token);
      router.push("/leads");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
      // 403 = conta existe mas o e-mail não foi confirmado → oferece
      // o reenvio do link de ativação.
      setUnverified(err instanceof ApiError && err.status === 403);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard title="Entrar" subtitle="Acesse sua conta no SysLink">
      <form className={styles.form} onSubmit={handleSubmit}>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        {unverified ? (
          <p className={styles.hint}>
            Não recebeu o e-mail de confirmação? <Link href="/reenviar-confirmacao">Reenviar</Link>
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

        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">
            Senha
          </label>
          <input
            id="password"
            type="password"
            className={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
        </div>

        <button type="submit" className={styles.button} disabled={loading}>
          {loading ? "Entrando…" : "Entrar"}
        </button>
      </form>

      <div className={styles.links}>
        <Link href="/esqueci-senha">Esqueci minha senha</Link>
        <Link href="/cadastro">Criar conta</Link>
      </div>
    </AuthCard>
  );
}
