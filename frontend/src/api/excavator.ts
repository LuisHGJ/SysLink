/**
 * Cliente da API do Escavador — busca de leads via IA.
 */
import { authHeaders, handleUnauthorized } from "./auth";
import type { LeadCreate } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ExcavatedLead {
  instagram: string;
  nome: string;
  empresa: string | null;
  contato: string | null;
  produto: string;
  dificuldade: string;
  confianca: number;
  // Dados reais da fonte (Apify e/ou Tavily)
  seguidores: number;
  bio: string;
  categoria: string;
  verificado: boolean;
  negocio: boolean;
  url: string;
}

/** Cota diária de perfis escavados do usuário autenticado. */
export interface QuotaInfo {
  ativa: boolean;
  limite: number;
  usado: number;
  restante: number;
  /** Próxima meia-noite BRT em ISO 8601 (null quando a cota está desativada). */
  renova_em: string | null;
}

export interface ExcavateResponse {
  resultados: ExcavatedLead[];
  cota: QuotaInfo;
}

/** Consulta a cota do dia — usada ao abrir a tela e após erros. */
export async function fetchQuota(): Promise<QuotaInfo> {
  const res = await fetch(`${API_BASE}/api/v1/excavate/quota`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    if (res.status === 401) handleUnauthorized();
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erro ao consultar a cota: ${res.status}`);
  }
  return (await res.json()) as QuotaInfo;
}

export async function excavate(nicho: string, quantidade = 30): Promise<ExcavateResponse> {
  const res = await fetch(`${API_BASE}/api/v1/excavate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ nicho, quantidade }),
  });

  if (!res.ok) {
    if (res.status === 401) handleUnauthorized();
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erro ao escavar: ${res.status}`);
  }

  return (await res.json()) as ExcavateResponse;
}

/** Converte resultado escavado para formato aceito pela API de leads. */
export function toLeadCreate(excavated: ExcavatedLead): LeadCreate {
  return {
    nome: excavated.nome,
    empresa: excavated.empresa,
    contato: excavated.contato,
    instagram: excavated.instagram,
    produto: excavated.produto as LeadCreate["produto"],
    dificuldade: excavated.dificuldade as LeadCreate["dificuldade"],
    status: "Não contatado",
    motivo_perda: null,
    ultimo_contato: null,
    arquivos: [],
  };
}
