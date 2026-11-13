"use client";

import { ApiError, authApi } from "@/api/client";
import { AuthCard } from "@/components/AuthCard";
import styles from "@/components/AuthCard.module.css";
import Link from "next/link";
import { useState } from "react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setConflict(false);
    if (password !== confirm) {
      setError("As senhas não conferem.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.register({ email, password });
      setSent(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
      // 409 = conta já existe (talvez criada num envio que falhou) →
      // oferece o reenvio do link de confirmação como saída.
      setConflict(err instanceof ApiError && err.status === 409);
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthCard title="Confirme seu e-mail" subtitle="Quase lá!">
        <output className={styles.success}>{sent}</output>
        <div className={styles.links}>
          <Link href="/login">Ir para o login</Link>
          <Link href="/reenviar-confirmacao">Reenviar e-mail</Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Criar conta" subtitle="Comece a gerenciar seus leads">
      <form className={styles.form} onSubmit={handleSubmit}>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        {conflict ? (
          <p className={styles.hint}>
            Já existe uma conta com este e-mail?{" "}
            <Link href="/reenviar-confirmacao">Reenviar confirmação</Link>
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
            placeholder="Mínimo de 8 caracteres"
            autoComplete="new-password"
            minLength={8}
            required
          />
          <span className={styles.hint}>Mínimo de 8 caracteres.</span>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="confirm">
            Confirmar senha
          </label>
          <input
            id="confirm"
            type="password"
            className={styles.input}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repita a senha"
            autoComplete="new-password"
            minLength={8}
            required
          />
        </div>

        <button type="submit" className={styles.button} disabled={loading}>
          {loading ? "Criando conta…" : "Criar conta"}
        </button>
      </form>

      <div className={styles.links}>
        <Link href="/login">Já tem conta? Entrar</Link>
      </div>
    </AuthCard>
  );
}
