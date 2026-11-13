"use client";

import { exportCSV, leadsApi } from "@/api/client";
import type { Lead, LeadCreate, LeadPatch } from "@/api/types";
import { ConfirmModal } from "@/components/ConfirmModal";
import { DificuldadeBadge } from "@/components/DificuldadeBadge";
import { EditIcon, TrashIcon } from "@/components/Icons";
import { LeadModal } from "@/components/LeadModal";
import { StatusBadge } from "@/components/StatusBadge";
import { useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

type SortKey = keyof Pick<
  Lead,
  "id" | "nome" | "empresa" | "produto" | "dificuldade" | "status" | "ultimo_contato"
>;

interface SortableThProps {
  field: SortKey;
  label: string;
  current: SortKey;
  asc: boolean;
  onSort: (key: SortKey) => void;
}

/** Cabeçalho de coluna ordenável — botão nativo (teclado) + aria-sort no th. */
function SortableTh({ field, label, current, asc, onSort }: SortableThProps) {
  const active = current === field;
  return (
    <th aria-sort={active ? (asc ? "ascending" : "descending") : "none"}>
      <button type="button" className={styles.thSort} onClick={() => onSort(field)}>
        {label}
        {active ? (asc ? " ↑" : " ↓") : ""}
      </button>
    </th>
  );
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [sortAsc, setSortAsc] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Lead | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  // ─── Carregar leads ───────────────────────────────────────────
  const loadLeads = useCallback(async () => {
    try {
      setLoading(true);
      const data = await leadsApi.list();
      setLeads(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar leads");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  // ─── Copiar contato no duplo-clique ───────────────────────────
  async function handleCopyContact(lead: Lead) {
    if (!lead.contato) return;
    try {
      await navigator.clipboard.writeText(lead.contato);
      setCopied(lead.id);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      // Fallback para browsers sem clipboard API
      const ta = document.createElement("textarea");
      ta.value = lead.contato;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(lead.id);
      setTimeout(() => setCopied(null), 1500);
    }
  }

  // ─── CRUD handlers ────────────────────────────────────────────
  async function handleSave(data: LeadCreate | LeadPatch, id?: number) {
    if (id) {
      await leadsApi.update(id, data as LeadCreate);
    } else {
      await leadsApi.create(data as LeadCreate);
    }
    await loadLeads();
  }

  async function handleConfirmDelete() {
    if (!confirmDelete) return;
    setDeleting(confirmDelete.id);
    try {
      await leadsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao excluir");
      setConfirmDelete(null);
    } finally {
      setDeleting(null);
    }
  }

  function openCreate() {
    setEditingLead(null);
    setModalOpen(true);
  }

  function openEdit(lead: Lead) {
    setEditingLead(lead);
    setModalOpen(true);
  }

  // ─── Sort ─────────────────────────────────────────────────────
  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  // ─── Filtros ──────────────────────────────────────────────────
  const filtered = leads
    .filter((l) => {
      const q = search.toLowerCase();
      const matchSearch =
        !q ||
        l.nome.toLowerCase().includes(q) ||
        (l.empresa ?? "").toLowerCase().includes(q) ||
        (l.contato ?? "").toLowerCase().includes(q) ||
        (l.instagram ?? "").toLowerCase().includes(q);
      const matchStatus = !statusFilter || l.status === statusFilter;
      return matchSearch && matchStatus;
    })
    .sort((a, b) => {
      const va = String(a[sortKey] ?? "");
      const vb = String(b[sortKey] ?? "");
      return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    });

  // ─── Export ───────────────────────────────────────────────────
  async function handleExport() {
    try {
      await exportCSV();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao exportar");
    }
  }

  // ─── Render ───────────────────────────────────────────────────
  return (
    <main className={styles.container}>
      {/* ── Header ────────────────────────────────────────────── */}
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Leads</h1>
          <p className={styles.subtitle}>
            {leads.length} lead{leads.length !== 1 ? "s" : ""} no total
          </p>
        </div>
        <div className={styles.headerActions}>
          <button type="button" className={styles.exportBtn} onClick={handleExport}>
            ↓ Exportar CSV
          </button>
          <button type="button" className={styles.createBtn} onClick={openCreate}>
            + Novo Lead
          </button>
        </div>
      </header>

      {/* ── Filtros ───────────────────────────────────────────── */}
      <div className={styles.filters}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Buscar por nome, empresa, contato..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className={styles.filterSelect}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">Todos os status</option>
          <option value="Não contatado">Não contatado</option>
          <option value="Aguardando resposta">Aguardando resposta</option>
          <option value="Negociando">Negociando</option>
          <option value="Negado">Negado</option>
          <option value="Fechado">Fechado</option>
          <option value="Em desenvolvimento">Em desenvolvimento</option>
          <option value="Finalizado">Finalizado</option>
        </select>
      </div>

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
      {loading && <div className={styles.loading}>Carregando leads...</div>}

      {/* ── Tabela ────────────────────────────────────────────── */}
      {!loading && (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortableTh
                  field="nome"
                  label="Nome"
                  current={sortKey}
                  asc={sortAsc}
                  onSort={handleSort}
                />
                <SortableTh
                  field="empresa"
                  label="Empresa"
                  current={sortKey}
                  asc={sortAsc}
                  onSort={handleSort}
                />
                <th>Contato</th>
                <th>Instagram</th>
                <SortableTh
                  field="produto"
                  label="Produto"
                  current={sortKey}
                  asc={sortAsc}
                  onSort={handleSort}
                />
                <SortableTh
                  field="dificuldade"
                  label="Dificuldade"
                  current={sortKey}
                  asc={sortAsc}
                  onSort={handleSort}
                />
                <SortableTh
                  field="status"
                  label="Status"
                  current={sortKey}
                  asc={sortAsc}
                  onSort={handleSort}
                />
                <th>Motivo da perda</th>
                <SortableTh
                  field="ultimo_contato"
                  label="Último contato"
                  current={sortKey}
                  asc={sortAsc}
                  onSort={handleSort}
                />
                <th>Arquivos</th>
                <th className={styles.actionsCol}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={11} className={styles.empty}>
                    {leads.length === 0
                      ? 'Nenhum lead cadastrado. Clique em "+ Novo Lead" para começar.'
                      : "Nenhum lead encontrado com esses filtros."}
                  </td>
                </tr>
              )}
              {filtered.map((lead) => (
                <tr key={lead.id} className={styles.row}>
                  <td className={styles.cellNome}>{lead.nome}</td>
                  <td>{lead.empresa || "—"}</td>
                  <td
                    className={`${styles.cellContato} ${
                      lead.contato ? styles.copyable : ""
                    } ${copied === lead.id ? styles.copied : ""}`}
                    onDoubleClick={() => handleCopyContact(lead)}
                    title={
                      lead.contato
                        ? copied === lead.id
                          ? "Copiado!"
                          : "Duplo clique para copiar"
                        : undefined
                    }
                  >
                    {copied === lead.id ? (
                      <span className={styles.copiedTag}>✓ Copiado</span>
                    ) : (
                      lead.contato || "—"
                    )}
                  </td>
                  <td className={styles.cellInstagram}>
                    {lead.instagram ? (
                      <a
                        href={`https://instagram.com/${lead.instagram.replace("@", "")}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.link}
                      >
                        {lead.instagram}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>{lead.produto}</td>
                  <td>
                    <DificuldadeBadge dificuldade={lead.dificuldade} />
                  </td>
                  <td>
                    <StatusBadge status={lead.status} />
                  </td>
                  <td className={styles.cellMotivo}>{lead.motivo_perda || "—"}</td>
                  <td className={styles.cellData}>
                    {lead.ultimo_contato
                      ? new Date(lead.ultimo_contato).toLocaleDateString("pt-BR")
                      : "—"}
                  </td>
                  <td>
                    {lead.arquivos.length > 0 ? (
                      <span className={styles.fileCount}>📎 {lead.arquivos.length}</span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className={styles.actionsCell}>
                    <button
                      type="button"
                      className={styles.actionBtn}
                      onClick={() => openEdit(lead)}
                      aria-label="Editar lead"
                      title="Editar"
                    >
                      <EditIcon size={18} />
                    </button>
                    <button
                      type="button"
                      className={`${styles.actionBtn} ${styles.deleteAction}`}
                      onClick={() => setConfirmDelete(lead)}
                      disabled={deleting === lead.id}
                      aria-label="Excluir lead"
                      title="Excluir"
                    >
                      <TrashIcon size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Modal criar/editar ────────────────────────────────── */}
      {modalOpen && (
        <LeadModal lead={editingLead} onSave={handleSave} onClose={() => setModalOpen(false)} />
      )}

      {/* ── Modal confirmar exclusão ──────────────────────────── */}
      {confirmDelete && (
        <ConfirmModal
          title="Excluir lead"
          message={`Tem certeza que deseja excluir "${confirmDelete.nome}"? Essa ação não pode ser desfeita.`}
          onConfirm={handleConfirmDelete}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </main>
  );
}
