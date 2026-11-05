import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "../../config/apiBaseUrl";
import {
  deriveCoreWaterMmol,
  exampleToMixture,
  fetchDocumentedExamples,
  type DocumentedExampleDto,
} from "./documentedExamples";

function component(updates: Partial<DocumentedExampleDto["components"][number]>) {
  return {
    key: "x", name: "X", smiles: "C", role: "reagent" as const, amount_mmol: 1, formula: "CH4", molar_mass: 16.04,
    is_surfactant: null, tail_carbon_count: null, tail_chain_count: null, example_role: null, derived_from_w0: false,
    ...updates,
  };
}

const AOT: DocumentedExampleDto = {
  id: "aot_inversa_isooctano", title: "AOT em isooctano", kind: "representative_demo",
  example_version: "1.0.0", last_reviewed_at: "2026-11-05", documented_morphology: "micela inversa",
  components: [
    component({ key: "aot", name: "AOT", smiles: "CCCCC(CC)COC(=O)CC(C(=O)OCC(CC)CCCC)S(=O)(=O)[O-].[Na+]", amount_mmol: 10,
      formula: "C20H37NaO7S", molar_mass: 444.56, is_surfactant: true, tail_carbon_count: 8, tail_chain_count: 2 }),
    component({ key: "agua", name: "Água (núcleo, derivada de w0)", smiles: "O", amount_mmol: 100, formula: "H2O",
      molar_mass: 18.015, example_role: "core_water", derived_from_w0: true }),
    component({ key: "isooctano", name: "Isooctano", smiles: "CC(C)CC(C)(C)C", role: "solvent", amount_mmol: null,
      formula: "C8H18", molar_mass: 114.23 }),
  ],
  environment: { volume_ml: 100, temperature_k: 298.15, ionic_strength_mol_l: 0, solvent_name: "isooctano", dielectric_constant: 1.94 },
  conditions: [], protocol: "AOT 0,1 M", references: [{ label: "ref", url: null }], notes: [], w0: 10,
};

const VESICLE: DocumentedExampleDto = {
  ...AOT, id: "dppc_vesicula_extrusao", title: "DPPC vesícula", documented_morphology: "vesícula/bicamada fechada", w0: null,
  components: [component({ key: "dppc", name: "DPPC", amount_mmol: 1 }), component({ key: "agua", name: "Água", smiles: "O", role: "solvent", amount_mmol: null })],
  environment: { volume_ml: 100, temperature_k: 328.15, ionic_strength_mol_l: 0.01, solvent_name: "água", dielectric_constant: 78.5, solvent_polarity_index: 1 },
};

afterEach(() => vi.unstubAllGlobals());

describe("exemplos documentados no painel 2D→3D", () => {
  it("AOT: água derivada de w0 e w0 no estado do exemplo", () => {
    const { items, state } = exampleToMixture(AOT);
    const water = items.find((item) => item.key === "agua");
    expect(water?.derivedFromW0).toBe(true);
    expect(water?.amountMmol).toBe(100);
    expect(state).toEqual({ id: "aot_inversa_isooctano", w0: 10, aotKey: "aot", waterKey: "agua" });
    expect(items.find((item) => item.key === "isooctano")?.role).toBe("solvent");
  });

  it("água do núcleo = w0 × AOT", () => {
    expect(deriveCoreWaterMmol(15, 10)).toBe(150);
    expect(deriveCoreWaterMmol(10, 2.5)).toBe(25);
  });

  it("carrega o meio do exemplo nas chaves do painel", () => {
    const { environment, state } = exampleToMixture(VESICLE);
    expect(environment.temperatureK).toBe("328.15");
    expect(environment.solventName).toBe("água");
    expect(environment.volumeMl).toBe("100");
    expect(state).toEqual({ id: "dppc_vesicula_extrusao", w0: null, aotKey: null, waterKey: null });
  });

  it("busca o catálogo na rota da API", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [AOT] });
    vi.stubGlobal("fetch", fetchMock);
    const examples = await fetchDocumentedExamples();
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE_URL}/micelium/documented-examples`);
    expect(examples[0].id).toBe("aot_inversa_isooctano");
  });

  it("falha de rede vira erro com mensagem", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }));
    await expect(fetchDocumentedExamples()).rejects.toThrow("503");
  });
});
