import { describe, expect, it } from "vitest";

import { DEFAULT_API_BASE_URL, resolveApiBaseUrl } from "./apiBaseUrl";

describe("URL base da API", () => {
  it("é relativa por padrão, para o mesmo domínio servir interface e API", () => {
    expect(DEFAULT_API_BASE_URL).toBe("/api/v1");
    expect(resolveApiBaseUrl(undefined)).toBe("/api/v1");
  });

  it("valor vazio não gera URLs quebradas", () => {
    expect(resolveApiBaseUrl("")).toBe("/api/v1");
    expect(resolveApiBaseUrl("   ")).toBe("/api/v1");
  });

  it("respeita VITE_API_URL absoluta (desenvolvimento local) e remove a barra final", () => {
    expect(resolveApiBaseUrl("http://127.0.0.1:8000/api/v1/")).toBe("http://127.0.0.1:8000/api/v1");
    expect(resolveApiBaseUrl("/api/v1//")).toBe("/api/v1");
  });
});

describe("todas as chamadas usam a mesma base", () => {
  it("nenhum arquivo do código fixa o endereço local do backend", () => {
    const sources = import.meta.glob(["../**/*.{ts,tsx}", "!../**/*.test.{ts,tsx}"], {
      query: "?raw", import: "default", eager: true,
    }) as Record<string, string>;
    expect(Object.keys(sources).length).toBeGreaterThan(10);
    const offenders = Object.entries(sources)
      .filter(([, text]) => text.includes("127.0.0.1:8000") || text.includes("localhost:8000"))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
