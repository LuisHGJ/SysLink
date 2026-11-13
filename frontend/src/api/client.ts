/**
 * Cliente HTTP para a API SysLink.
 * Base URL vem de variável de ambiente (NEXT_PUBLIC_API_URL).
 * Todo request carrega o Bearer token quando há sessão ativa.
 */
import { authHeaders, handleUnauthorized } from "./auth";
import type { Lead, LeadCreate, LeadPatch, LeadUpdate } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const NETWORK_ERROR = "Não foi possível conectar ao servidor. Verifique se a API está no ar.";

/** Mensagem PT-BR por status, quando a API não devolve um detail legível. */
const STATUS_MESSAGES: Record<number, string> = {
  400: "Dados inválidos.",
  401: "Sessão expirada. Entre novamente.",
  403: "Você não tem permissão para isso.",
  404: "Registro não encontrado.",
  405: "Método não permitido.",
  409: "Conflito: este registro já foi alterado.",
  422: "Confira os campos informados.",
  429: "Muitas tentativas. Aguarde um pouco.",
  500: "Erro interno do servidor. Tente novamente.",
  502: "Serviço indisponível no momento.",
  503: "Serviço indisponível. Tente novamente.",
  504: "O servidor demorou para responder. Tente novamente.",
};

type ProblemBody = {
  detail?: unknown;
  errors?: Array<{ field?: string; message?: string }>;
};

type ValidationItem = {
  msg?: string;
  loc?: unknown[];
  field?: string;
  message?: string;
};

/** Formata o corpo de erro (problem+json) em uma única mensagem legível. */
function problemMessage(body: ProblemBody, status: number): string {
  const { detail, errors } = body;

  if (typeof detail === "string" && detail.trim()) return detail;

  // Listas de erro (validação) — object[] vira "[object Object]" se não
  // for formatado, então monta "campo: mensagem".
  const items: ValidationItem[] = Array.isArray(detail)
    ? detail
    : Array.isArray(errors)
      ? errors
      : [];
  const parts = items
    .map((item) => {
      const message = item.message ?? item.msg ?? "";
      const rawLoc = item.loc;
      const field =
        item.field ?? (Array.isArray(rawLoc) ? rawLoc.filter((p) => p !== "body").join(".") : "");
      if (!message) return "";
      return field ? `${field}: ${message}` : message;
    })
    .filter(Boolean);
  if (parts.length > 0) return parts.join("; ");

  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
  }

  return STATUS_MESSAGES[status] ?? `Erro inesperado na API (${status}).`;
}

/**
 * Erro de API com o status HTTP anexado — permitem tratos específicos
 * nas páginas (ex.: 409 no cadastro → sugerir reenvio de confirmação).
 * Estende Error, então `err instanceof Error` continua valendo.
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readError(res: Response): Promise<ApiError> {
  const body = (await res.json().catch(() => ({}))) as ProblemBody;
  return new ApiError(problemMessage(body, res.status), res.status);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
    });
  } catch {
    // fetch só rejeita em falha de rede/servidor (antes: "Failed to fetch")
    throw new Error(NETWORK_ERROR);
  }

  if (!res.ok) {
    // 401 fora dos endpoints de auth = sessão inválida → volta pro login.
    if (res.status === 401 && !path.startsWith("/api/v1/auth/")) {
      handleUnauthorized();
    }
    throw await readError(res);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── CRUD ────────────────────────────────────────────────────────

export const leadsApi = {
  list: () => request<Lead[]>("/api/v1/leads"),

  get: (id: number) => request<Lead>(`/api/v1/leads/${id}`),

  create: (data: LeadCreate) =>
    request<Lead>("/api/v1/leads", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: LeadUpdate) =>
    request<Lead>(`/api/v1/leads/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  patch: (id: number, data: LeadPatch) =>
    request<Lead>(`/api/v1/leads/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  remove: (id: number) => request<void>(`/api/v1/leads/${id}`, { method: "DELETE" }),
};

// ─── Export CSV ──────────────────────────────────────────────────

export async function exportCSV(): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/leads/export`, {
      headers: authHeaders(),
    });
  } catch {
    throw new Error(NETWORK_ERROR);
  }
  if (!res.ok) {
    if (res.status === 401) handleUnauthorized();
    throw await readError(res);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `syslink_leads_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─── Auth ────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface MessageResponse {
  message: string;
}

export const authApi = {
  register: (data: { email: string; password: string }) =>
    request<MessageResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  login: (data: { email: string; password: string }) =>
    request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  confirm: (token: string) =>
    request<MessageResponse>("/api/v1/auth/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  forgot: (email: string) =>
    request<MessageResponse>("/api/v1/auth/forgot", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resendConfirmation: (email: string) =>
    request<MessageResponse>("/api/v1/auth/resend-confirmation", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  reset: (token: string, password: string) =>
    request<MessageResponse>("/api/v1/auth/reset", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
};
