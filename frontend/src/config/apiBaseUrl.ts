// Base única das chamadas à API.
// Padrão relativo: em produção o Caddy serve a interface e encaminha /api/* ao backend no mesmo domínio.
// Desenvolvimento local: VITE_API_URL absoluta (ver frontend/.env.example e backend/docker-compose.yml).
export const DEFAULT_API_BASE_URL = "/api/v1";

export function resolveApiBaseUrl(raw: string | undefined): string {
  const value = (raw ?? "").trim();
  return (value || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_URL);
