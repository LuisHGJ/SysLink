"use client";

import { leadsApi } from "@/api/client";
import { excavate, fetchQuota, toLeadCreate } from "@/api/excavator";
import type { ExcavatedLead, QuotaInfo } from "@/api/excavator";
import { DificuldadeBadge } from "@/components/DificuldadeBadge";
import { useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

type ItemStatus = "pendente" | "aceito" | "rejeitado";

interface ResultItem {
  lead: ExcavatedLead;
  status: ItemStatus;
}

/**
 * Leads por request no "Aceitar todos". Disparar os N de uma vez só
 * enfileira (limite de ~6 conexões por host) e satura o threadpool do
 * backend — 5 por lote mantém a UI responsiva sem prejuízo.
 */
const ACCEPT_CHUNK_SIZE = 5;

/** ISO 8601 da virada da cota → "00:00" no fuso do navegador. */
function formatReset(iso: string | null): string {
  if (!iso) return "meia-noite";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "meia-noite";
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function EscavadorPage() {
  const [nicho, setNicho] = useState("");
  const [quantidade, setQuantidade] = useState(30);
  const [results, setResults] = useState<ResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [quota, setQuota] = useState<QuotaInfo | null>(null);

  // ─── Cota diária ──────────────────────────────────────────────
  // Falha na consulta é só informativa: não pode quebrar a tela.
  const refreshQuota = useCallback(async () => {
    try {
      setQuota(await fetchQuota());
    } catch {
      /* mantém o último valor conhecido */
    }
  }, []);

  useEffect(() => {
    void refreshQuota();
  }, [refreshQuota]);

  const quotaEsgotada = quota?.ativa === true && quota.restante <= 0;

  // ─── Escavar ──────────────────────────────────────────────────
  async function handleExcavate() {
    if (!nicho.trim() || quotaEsgotada) return;
    setLoading(true);
    setError(null);
    setSummary(null);
    setResults([]);
    try {
      const { resultados, cota } = await excavate(nicho.trim(), quantidade);
      setQuota(cota);
      setResults(resultados.map((lead) => ({ lead, status: "pendente" })));
      if (resultados.length === 0) {
        setError(
          "Nenhum perfil encontrado. Verifique se APIFY_API_TOKEN ou TAVILY_API_KEY estão configuradas no .env.",
        );
      } else {
        setSummary(
          `${resultados.length} perfil${resultados.length !== 1 ? "s" : ""} encontrado${resultados.length !== 1 ? "s" : ""} para "${nicho}"`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao escavar");
      // Erro de cota (429) ou de busca: sincroniza o indicador com o servidor.
      void refreshQuota();
    } finally {
      setLoading(false);
    }
  }

  // ─── Aceitar → criar lead ─────────────────────────────────────
  async function handleAccept(index: number) {
    const item = results[index];
    if (!item || item.status !== "pendente") return;
    try {
      await leadsApi.create(toLeadCreate(item.lead));
      setResults((prev) => prev.map((r, i) => (i === index ? { ...r, status: "aceito" } : r)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao adicionar lead");
    }
  }

  // ─── Rejeitar ─────────────────────────────────────────────────
  function handleReject(index: number) {
    setResults((prev) => prev.map((r, i) => (i === index ? { ...r, status: "rejeitado" } : r)));
  }

  // ─── Aceitar todos pendentes ──────────────────────────────────
  // Envia em lotes de ACCEPT_CHUNK_SIZE com Promise.allSettled: um lote
  // falha → os demais continuam, e cards só marcam "aceito" se o POST
  // deu certo (comportamento do loop sequencial, só que ~5x mais rápido).
  async function handleAcceptAll() {
    const pendings = results
      .map((r, i) => ({ ...r, index: i }))
      .filter((r) => r.status === "pendente");
    if (pendings.length === 0 || accepting) return;

    setAccepting(true);
    setError(null);
    let failed = 0;
    try {
      for (let i = 0; i < pendings.length; i += ACCEPT_CHUNK_SIZE) {
        const chunk = pendings.slice(i, i + ACCEPT_CHUNK_SIZE);
        const settled = await Promise.allSettled(
          chunk.map((item) => leadsApi.create(toLeadCreate(item.lead))),
        );

        const okIndexes = new Set(
          chunk.filter((_, j) => settled[j].status === "fulfilled").map((item) => item.index),
        );
        failed += chunk.length - okIndexes.size;

        if (okIndexes.size > 0) {
          setResults((prev) =>
            prev.map((r, idx) => (okIndexes.has(idx) ? { ...r, status: "aceito" as const } : r)),
          );
        }
      }
      if (failed > 0) {
        setError(
          `${failed} de ${pendings.length} lead${pendings.length !== 1 ? "s" : ""} não puderam ser adicionados.`,
        );
      }
    } finally {
      setAccepting(false);
    }
  }

  // ─── Contadores ───────────────────────────────────────────────
  const pendings = results.filter((r) => r.status === "pendente").length;
  const accepted = results.filter((r) => r.status === "aceito").length;
  const rejected = results.filter((r) => r.status === "rejeitado").length;

  // ─── Render ───────────────────────────────────────────────────
  return (
    <main className={styles.container}>
      {/* ── Header ────────────────────────────────────────────── */}
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Escavador</h1>
          <p className={styles.subtitle}>
            Buscador de leads com IA — informe um nicho e encontre perfis do Instagram
          </p>
        </div>
        {quota?.ativa && (
          <span className={quotaEsgotada ? styles.quotaBadgeExhausted : styles.quotaBadge}>
            {quotaEsgotada
              ? `Cota esgotada · renova às ${formatReset(quota.renova_em)}`
              : `Cota: ${quota.usado}/${quota.limite} hoje`}
          </span>
        )}
      </header>

      {/* ── Formulário ────────────────────────────────────────── */}
      <section className={styles.formCard}>
        <div className={styles.formRow}>
          <div className={styles.fieldGrow}>
            <label className={styles.label} htmlFor="nicho">
              Nicho <span className={styles.required}>*</span>
            </label>
            <input
              id="nicho"
              className={styles.input}
              type="text"
              value={nicho}
              onChange={(e) => setNicho(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleExcavate()}
              placeholder="Ex: restaurantes, academias, fotógrafos, dentistas..."
              disabled={loading}
            />
          </div>
          <div className={styles.fieldSmall}>
            <label className={styles.label} htmlFor="qtd">
              Quantidade
            </label>
            <select
              id="qtd"
              className={styles.select}
              value={quantidade}
              onChange={(e) => setQuantidade(Number(e.target.value))}
              disabled={loading}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={30}>30</option>
              <option value={50}>50</option>
            </select>
          </div>
          <button
            type="button"
            className={styles.excavateBtn}
            onClick={handleExcavate}
            disabled={loading || !nicho.trim() || quotaEsgotada}
          >
            {loading ? "Escavando..." : quotaEsgotada ? "⛏ Cota esgotada" : "⛏ Escavar"}
          </button>
        </div>
      </section>

      {/* ── Erro ──────────────────────────────────────────────── */}
      {error && (
        <div className={styles.errorBanner}>
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}>
            ✕
          </button>
        </div>
      )}

      {/* ── Loading ───────────────────────────────────────────── */}
      {loading && (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Buscando perfis no nicho "{nicho}"...</p>
        </div>
      )}

      {/* ── Resumo + ações em massa ───────────────────────────── */}
      {!loading && results.length > 0 && (
        <div className={styles.summaryBar}>
          <span className={styles.summaryText}>
            {summary}
            {accepted > 0 && ` · ${accepted} aceito${accepted !== 1 ? "s" : ""}`}
            {rejected > 0 && ` · ${rejected} rejeitado${rejected !== 1 ? "s" : ""}`}
            {pendings > 0 && ` · ${pendings} pendente${pendings !== 1 ? "s" : ""}`}
          </span>
          {pendings > 0 && (
            <div className={styles.summaryActions}>
              <button
                type="button"
                className={styles.acceptAllBtn}
                onClick={handleAcceptAll}
                disabled={accepting}
              >
                {accepting ? "Adicionando..." : `✓ Aceitar todos (${pendings})`}
              </button>
              <button
                type="button"
                className={styles.rejectAllBtn}
                disabled={accepting}
                onClick={() =>
                  setResults((prev) =>
                    prev.map((r) => (r.status === "pendente" ? { ...r, status: "rejeitado" } : r)),
                  )
                }
              >
                ✕ Rejeitar todos
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Resultados ────────────────────────────────────────── */}
      {!loading && results.length > 0 && (
        <div className={styles.resultsList}>
          {results.map((item, index) => (
            <div
              key={`${item.lead.instagram}-${index}`}
              className={`${styles.resultCard} ${
                item.status === "aceito"
                  ? styles.cardAccepted
                  : item.status === "rejeitado"
                    ? styles.cardRejected
                    : ""
              }`}
            >
              <div className={styles.cardInfo}>
                <div className={styles.cardTop}>
                  <span className={styles.cardName}>{item.lead.nome}</span>
                  {item.lead.verificado && (
                    <span className={styles.verifiedBadge} title="Verificado">
                      ✓
                    </span>
                  )}
                  <a
                    href={
                      item.lead.url ||
                      `https://instagram.com/${item.lead.instagram.replace("@", "").replace("https://instagram.com/", "")}`
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.cardIgLink}
                    title="Abrir perfil no Instagram"
                  >
                    {item.lead.instagram}
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                      <polyline points="15 3 21 3 21 9" />
                      <line x1="10" y1="14" x2="21" y2="3" />
                    </svg>
                  </a>
                </div>
                {item.lead.bio && <p className={styles.cardBio}>{item.lead.bio}</p>}
                <div className={styles.cardMeta}>
                  {item.lead.seguidores > 0 && (
                    <span className={styles.cardFollowers}>
                      {item.lead.seguidores.toLocaleString("pt-BR")} seguidores
                    </span>
                  )}
                  {item.lead.categoria && item.lead.categoria !== "None" && (
                    <span className={styles.cardCategoria}>{item.lead.categoria}</span>
                  )}
                  <span className={styles.cardProduto}>{item.lead.produto}</span>
                  <DificuldadeBadge
                    dificuldade={item.lead.dificuldade as "Fácil" | "Médio" | "Difícil"}
                  />
                  <span className={styles.cardConf}>{Math.round(item.lead.confianca * 100)}%</span>
                </div>
              </div>

              <div className={styles.cardActions}>
                {item.status === "pendente" ? (
                  <>
                    <button
                      type="button"
                      className={styles.acceptBtn}
                      onClick={() => handleAccept(index)}
                      disabled={accepting}
                      title="Adicionar à tabela de leads"
                    >
                      ✓ Aceitar
                    </button>
                    <button
                      type="button"
                      className={styles.rejectBtn}
                      onClick={() => handleReject(index)}
                      disabled={accepting}
                      title="Descartar"
                    >
                      ✕
                    </button>
                  </>
                ) : (
                  <span
                    className={
                      item.status === "aceito" ? styles.statusAccepted : styles.statusRejected
                    }
                  >
                    {item.status === "aceito" ? "✓ Adicionado" : "✕ Rejeitado"}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Vazio ─────────────────────────────────────────────── */}
      {!loading && results.length === 0 && !error && (
        <div className={styles.empty}>
          <p>Informe um nicho e clique em "Escavar" para encontrar leads.</p>
        </div>
      )}
    </main>
  );
}
