"use client";

import { DIFICULDADE_OPTIONS, PRODUTO_OPTIONS, STATUS_OPTIONS } from "@/api/types";
import type { Lead, LeadCreate, LeadPatch } from "@/api/types";
import { useEffect, useState } from "react";
import styles from "./LeadModal.module.css";

interface Props {
  lead?: Lead | null; // null = criar, Lead = editar
  onSave: (data: LeadCreate | LeadPatch, id?: number) => Promise<void>;
  onClose: () => void;
}

const EMPTY: LeadCreate = {
  nome: "",
  empresa: "",
  contato: "",
  instagram: "",
  produto: "Portfólio",
  dificuldade: "Médio",
  status: "Não contatado",
  motivo_perda: "",
  ultimo_contato: "",
  arquivos: [],
};

export function LeadModal({ lead, onSave, onClose }: Props) {
  const [form, setForm] = useState<LeadCreate>(() => {
    if (!lead) return EMPTY;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { id: _id, ...rest } = lead;
    return rest;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Bloqueia scroll do body enquanto modal aberto
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  function set<K extends keyof LeadCreate>(key: K, value: LeadCreate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(form, lead?.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className={styles.overlay}
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
      role="presentation"
    >
      <div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            onClose();
          }
        }}
        // biome-ignore lint/a11y/useSemanticElements: <dialog> nativo aplica UA styles (position/padding/margin) que quebram o layout do overlay em flex — o div com role="dialog" + aria-modal é o padrão ARIA de modal.
        role="dialog"
        aria-modal="true"
        aria-label={lead ? "Editar lead" : "Novo lead"}
      >
        <div className={styles.header}>
          <h2 className={styles.title}>{lead ? "Editar Lead" : "Novo Lead"}</h2>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Fechar">
            ✕
          </button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.grid}>
            {/* ── Nome ─────────────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="nome">
                Nome *
              </label>
              <input
                id="nome"
                className={styles.input}
                type="text"
                value={form.nome}
                onChange={(e) => set("nome", e.target.value)}
                required
                maxLength={255}
                placeholder="Nome do contato"
              />
            </div>

            {/* ── Empresa ──────────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="empresa">
                Empresa
              </label>
              <input
                id="empresa"
                className={styles.input}
                type="text"
                value={form.empresa ?? ""}
                onChange={(e) => set("empresa", e.target.value)}
                maxLength={255}
                placeholder="Nome da empresa"
              />
            </div>

            {/* ── Contato ──────────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="contato">
                Contato
              </label>
              <input
                id="contato"
                className={styles.input}
                type="text"
                value={form.contato ?? ""}
                onChange={(e) => set("contato", e.target.value)}
                maxLength={255}
                placeholder="E-mail ou telefone"
              />
            </div>

            {/* ── Instagram ────────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="instagram">
                Instagram
              </label>
              <input
                id="instagram"
                className={styles.input}
                type="text"
                value={form.instagram ?? ""}
                onChange={(e) => set("instagram", e.target.value)}
                maxLength={255}
                placeholder="@usuario"
              />
            </div>

            {/* ── Produto ──────────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="produto">
                Produto *
              </label>
              <select
                id="produto"
                className={styles.select}
                value={form.produto}
                onChange={(e) => set("produto", e.target.value as LeadCreate["produto"])}
                required
              >
                {PRODUTO_OPTIONS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            {/* ── Dificuldade ──────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="dificuldade">
                Dificuldade *
              </label>
              <select
                id="dificuldade"
                className={styles.select}
                value={form.dificuldade}
                onChange={(e) => set("dificuldade", e.target.value as LeadCreate["dificuldade"])}
                required
              >
                {DIFICULDADE_OPTIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* ── Status ───────────────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="status">
                Status *
              </label>
              <select
                id="status"
                className={styles.select}
                value={form.status}
                onChange={(e) => set("status", e.target.value as LeadCreate["status"])}
                required
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* ── Último contato ───────────────────────────────── */}
            <div className={styles.field}>
              <label className={styles.label} htmlFor="ultimo_contato">
                Último contato
              </label>
              <input
                id="ultimo_contato"
                className={styles.input}
                type="datetime-local"
                value={(form.ultimo_contato ?? "").slice(0, 16)}
                onChange={(e) =>
                  set("ultimo_contato", e.target.value ? `${e.target.value}:00` : "")
                }
              />
            </div>
          </div>

          {/* ── Motivo da perda ────────────────────────────────── */}
          <div className={`${styles.field} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="motivo_perda">
              Motivo da perda
            </label>
            <textarea
              id="motivo_perda"
              className={styles.textarea}
              value={form.motivo_perda ?? ""}
              onChange={(e) => set("motivo_perda", e.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="Descreva o motivo (se aplicável)"
            />
          </div>

          {/* ── Arquivos ───────────────────────────────────────── */}
          <div className={`${styles.field} ${styles.fullWidth}`}>
            <label className={styles.label} htmlFor="arquivos">
              Arquivos (URLs separadas por vírgula)
            </label>
            <input
              id="arquivos"
              className={styles.input}
              type="text"
              value={(form.arquivos ?? []).join(", ")}
              onChange={(e) =>
                set(
                  "arquivos",
                  e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                )
              }
              placeholder="https://arquivo1.pdf, https://arquivo2.png"
            />
          </div>

          {/* ── Erro ───────────────────────────────────────────── */}
          {error && <p className={styles.error}>{error}</p>}

          {/* ── Ações ──────────────────────────────────────────── */}
          <div className={styles.actions}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className={styles.saveBtn} disabled={saving}>
              {saving ? "Salvando..." : lead ? "Salvar" : "Criar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
