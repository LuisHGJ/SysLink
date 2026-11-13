"use client";

import { authApi } from "@/api/client";
import { AuthCard } from "@/components/AuthCard";
import styles from "@/components/AuthCard.module.css";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function ResetContent() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("As senhas não conferem.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.reset(token, password);
      setSent(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthCard title="Senha redefinida" subtitle="Tudo certo!">
        <output className={styles.success}>{sent}</output>
        <div className={styles.links}>
          <Link href="/login">Ir para o login</Link>
        </div>
      </AuthCard>
    );
  }

  if (!token) {
    return (
      <AuthCard title="Redefinir senha" subtitle="Link inválido">
        <p className={styles.error} role="alert">
          Link inválido: token ausente. Solicite um novo em “Esqueci minha senha”.
        </p>
        <div className={styles.links}>
          <Link href="/esqueci-senha">Solicitar novo link</Link>
          <Link href="/login">Voltar ao login</Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Redefinir senha" subtitle="Escolha uma nova senha para sua conta">
      <form className={styles.form} onSubmit={handleSubmit}>
        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">
            Nova senha
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
            Confirmar nova senha
          </label>
          <input
            id="confirm"
            type="password"
            className={styles.input}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repita a nova senha"
            autoComplete="new-password"
            minLength={8}
            required
          />
        </div>

        <button type="submit" className={styles.button} disabled={loading}>
          {loading ? "Salvando…" : "Redefinir senha"}
        </button>
      </form>

      <div className={styles.links}>
        <Link href="/login">Voltar ao login</Link>
      </div>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  // useSearchParams exige Suspense para o build estático do Next.
  return (
    <Suspense fallback={null}>
      <ResetContent />
    </Suspense>
  );
}
