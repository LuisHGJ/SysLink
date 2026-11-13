// ─── Enums do CRM ────────────────────────────────────────────────

export const STATUS_OPTIONS = [
  "Não contatado",
  "Aguardando resposta",
  "Negociando",
  "Negado",
  "Fechado",
  "Em desenvolvimento",
  "Finalizado",
] as const;

export const DIFICULDADE_OPTIONS = ["Fácil", "Médio", "Difícil"] as const;

export const PRODUTO_OPTIONS = ["Portfólio", "Página de vendas", "Sistema", "Link Tree"] as const;

// ─── Tipos ───────────────────────────────────────────────────────

export type Status = (typeof STATUS_OPTIONS)[number];
export type Dificuldade = (typeof DIFICULDADE_OPTIONS)[number];
export type Produto = (typeof PRODUTO_OPTIONS)[number];

export interface Lead {
  id: number;
  nome: string;
  empresa: string | null;
  contato: string | null;
  instagram: string | null;
  produto: Produto;
  dificuldade: Dificuldade;
  status: Status;
  motivo_perda: string | null;
  ultimo_contato: string | null;
  arquivos: string[];
}

export type LeadCreate = Omit<Lead, "id">;
export type LeadUpdate = LeadCreate;
export type LeadPatch = Partial<LeadCreate>;
