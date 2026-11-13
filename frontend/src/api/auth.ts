/**
 * Sessão do usuário (JWT) no navegador.
 * O token fica no localStorage e é anexado por todos os clients HTTP.
 */
const TOKEN_KEY = "syslink-token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

/** Headers de Authorization quando há sessão ativa (vazio caso contrário). */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * 401 em rota protegida = sessão inválida/expirada: limpa o token e
 * volta para o login. Chamado pelos clients HTTP.
 */
export function handleUnauthorized(): void {
  clearToken();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}
