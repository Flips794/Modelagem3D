import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { InternalMoleculeModel } from "../../2dpage/type/rdkit2d.types";
import type { ChemistryParametersResponse, ParameterValue } from "./chemistryParameters.types";

vi.mock("./chemistryParametersApi", () => ({ analyzeChemistryParameters: vi.fn() }));

import { analyzeChemistryParameters } from "./chemistryParametersApi";
import { ChemistryParametersPanel } from "./ChemistryParametersPanel";

const analyze = vi.mocked(analyzeChemistryParameters);

function pv<T>(value: T | null, extra: Partial<ParameterValue<T>> = {}): ParameterValue<T> {
  return { value, unit: null, source: "teste", available: value !== null, confidence: "high", note: null, ...extra };
}

function molecule(smiles: string): InternalMoleculeModel {
  return { atoms: [], bonds: [], metadata: { canonical_smiles: smiles } } as unknown as InternalMoleculeModel;
}

function response(overrides: Record<string, unknown> = {}): ChemistryParametersResponse {
  return {
    success: true, package_version: "t", source: "t", warnings: [], limitations: [], atoms: [], bonds: [],
    molecule: {
      formula_molecular: "C2H3O2-", peso_molecular: 59.044, massa_exata: 59.013, carga_formal_total: -1,
      smiles_canonico: "CC(=O)[O-]", smiles_isomerico: "CC(=O)[O-]", hash_estrutural: "h",
      ressonancia_numero_estruturas: pv(2, { note: "Estruturas de Lewis formais, sem peso de contribuição; não descreve a distribuição eletrônica real." }),
      sistemas_conjugados: pv(1),
      ressonancia_atomos_deslocalizados: pv([1, 2, 3]),
      carga_liquida_ph: pv(-1, { unit: "e", confidence: "estimated" }),
      especie_predominante_ph: pv({ ph: 7, classe: "anionic", smiles: "CC(=O)[O-]" }, { confidence: "estimated" }),
      sitios_ionizaveis: pv([{ atom_idx: 3, grupo: "ácido carboxílico", tipo: "acid", pka: 4.76, acoplado: false,
        referencia: "Ácido acético 4,76 (CRC)", qualidade_referencia: "consolidada" }], { confidence: "estimated" }),
      energia_homo: pv(null, { unit: "eV", confidence: "unavailable", note: "indisponível: Exige método da etapa 2 (xTB)." }),
      cmc_experimental: pv(8.16, { unit: "mmol/L", confidence: "experimental", note: "Medido em água pura a 25 °C; NSRDS-NBS 36, ref. 66007." }),
      cmc_origem: pv("estimada (âncora experimental + inclinação de homólogos)"),
      classificacao_surfactante: pv({ classe: "anionic", classe_pt: "aniônico", classes_compativeis: ["anionic"],
        papel: "surfactant", confianca: "high", justificativa: "Grupos: sulfato (ácido forte). Regra: somente grupos ácidos → aniônico.",
        regras: [], especie_no_ph: { ph: 7, species: "anionic", net_charge: -1, reference_status: "consolidada", note: "" } }),
      raio_de_giracao: pv(null, { unit: "nm", confidence: "unavailable", note: "indisponível: geometria 3D sob demanda; não solicitada nesta chamada (generate_3d=false)" }),
      ...overrides,
    },
  } as unknown as ChemistryParametersResponse;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

beforeEach(() => analyze.mockReset());
afterEach(() => {
  cleanup();   // o Vitest do projeto não usa globals: sem isto o RTL não desmonta entre testes
  vi.useRealTimers();
});

async function renderPanel(smiles = "CC(=O)[O-]") {
  const view = render(<ChemistryParametersPanel molecule={molecule(smiles)} selectedTarget={null} mode="molecule" />);
  await screen.findByText("Estruturas de ressonância");
  return view;
}

describe("painel químico — novos cálculos", () => {
  it("mostra ressonância e espécie no pH com rótulos legíveis", async () => {
    analyze.mockResolvedValue(response());
    await renderPanel();
    expect(screen.getByTestId("row-ressonancia_numero_estruturas").textContent).toContain("2");
    expect(screen.getByTestId("row-especie_predominante_ph").textContent).toContain("aniônica");
    expect(screen.getByText(/ácido carboxílico/)).toBeTruthy();
    expect(screen.getByText(/Ácido acético 4,76 \(CRC\)/)).toBeTruthy();
  });

  it("indisponível mostra o motivo visível, sem depender de passar o mouse", async () => {
    analyze.mockResolvedValue(response());
    await renderPanel();
    expect(screen.getByText(/Exige método da etapa 2/)).toBeTruthy();
  });

  it("CMC experimental aparece separada, com classe e referência visíveis", async () => {
    analyze.mockResolvedValue(response());
    await renderPanel();
    const row = screen.getByTestId("row-cmc_experimental");
    expect(row.querySelector("strong.experimental")).not.toBeNull();
    expect(row.textContent).toContain("8.16 mmol/L");
    expect(row.textContent).toContain("NSRDS-NBS 36");
    expect(screen.getByTestId("row-cmc_origem").textContent).toContain("estimada");
  });

  it("classificação mostra classe, papel, confiança e justificativa", async () => {
    analyze.mockResolvedValue(response());
    await renderPanel();
    expect(screen.getByTestId("row-classificacao_classe").textContent).toContain("aniônico");
    expect(screen.getByText(/somente grupos ácidos → aniônico/)).toBeTruthy();
  });

  it("valor ausente não aparece com a cor de calculado", async () => {
    analyze.mockResolvedValue(response({ hash_estrutural: null, cmc_experimental: undefined }));
    await renderPanel();
    expect(screen.getByTestId("row-cmc_experimental").querySelector("strong.missing")).not.toBeNull();
    const hashRow = screen.getByText("Hash estrutural").nextElementSibling as HTMLElement;
    expect(hashRow.className).toBe("missing");
    const formulaRow = screen.getByText("Fórmula química").nextElementSibling as HTMLElement;
    expect(formulaRow.className).toBe("available");
  });

  it("classificação indisponível mostra o motivo uma única vez", async () => {
    analyze.mockResolvedValue(response({
      classificacao_surfactante: pv(null, { confidence: "not_applicable", note: "não se aplica: não surfactante" }),
    }));
    await renderPanel();
    expect(screen.getAllByText("não se aplica: não surfactante")).toHaveLength(1);
  });

  it("legenda distingue experimental, calculado, estimado, indisponível e não se aplica", async () => {
    analyze.mockResolvedValue(response());
    await renderPanel();
    const legend = screen.getByTestId("parameter-legend");
    for (const word of ["Experimental", "Calculado", "Estimado", "Indisponível", "Não se aplica"]) {
      expect(legend.textContent).toContain(word);
    }
  });
});

describe("geometria 3D sob demanda", () => {
  it("não pede 3D automaticamente", async () => {
    analyze.mockResolvedValue(response());
    await renderPanel();
    expect(analyze).toHaveBeenCalledTimes(1);
    expect(analyze.mock.calls[0][2]?.generate3d ?? false).toBe(false);
  });

  it("botão pede 3D, mostra carregamento e depois os valores", async () => {
    analyze.mockResolvedValueOnce(response());
    await renderPanel();
    const pending = deferred<ChemistryParametersResponse>();
    analyze.mockReturnValueOnce(pending.promise);
    const button = screen.getByRole("button", { name: "Calcular geometria 3D" });
    fireEvent.click(button);
    expect(analyze.mock.calls[1][2]).toEqual({ generate3d: true });
    const busy = screen.getByRole("button", { name: /Calculando geometria 3D/ });
    expect((busy as HTMLButtonElement).disabled).toBe(true);
    await act(async () => pending.resolve(response({ raio_de_giracao: pv(0.31, { unit: "nm", confidence: "medium", note: "1 confórmero" }) })));
    expect(screen.getByTestId("row-raio_de_giracao").textContent).toContain("0.31 nm");
    expect(screen.getByRole("button", { name: /Geometria 3D calculada/ })).toBeTruthy();
  });

  it("erro do 3D aparece sem apagar o painel 2D", async () => {
    analyze.mockResolvedValueOnce(response());
    await renderPanel();
    analyze.mockRejectedValueOnce(new Error("falha de rede"));
    fireEvent.click(screen.getByRole("button", { name: "Calcular geometria 3D" }));
    await screen.findByText(/falha de rede/);
    expect(screen.getByText("Estruturas de ressonância")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Calcular geometria 3D" })).toBeTruthy();
  });
});

describe("edição rápida no editor", () => {
  it("resposta antiga não sobrescreve a mais nova", async () => {
    const first = deferred<ChemistryParametersResponse>();
    const second = deferred<ChemistryParametersResponse>();
    analyze.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const view = render(<ChemistryParametersPanel molecule={molecule("CCO")} selectedTarget={null} mode="molecule" />);
    await waitFor(() => expect(analyze).toHaveBeenCalledTimes(1));
    view.rerender(<ChemistryParametersPanel molecule={molecule("CCCO")} selectedTarget={null} mode="molecule" />);
    await waitFor(() => expect(analyze).toHaveBeenCalledTimes(2));
    await act(async () => second.resolve(response({ formula_molecular: "C3H8O" })));
    await act(async () => first.resolve(response({ formula_molecular: "C2H6O" })));
    expect(screen.getByText("C3H8O")).toBeTruthy();
    expect(screen.queryByText("C2H6O")).toBeNull();
  });
});
