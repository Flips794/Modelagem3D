import { describe, expect, it } from "vitest";
import { buildMiceliumRequest } from "./3dpage";
import type { MoleculeTransferFrom2D } from "./type/3dpage.types";

function transfer(updates: Partial<MoleculeTransferFrom2D> = {}): MoleculeTransferFrom2D {
  return {
    id: "sds", name: "SDS", smiles: "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    concentration: 3, unit: "mmol", ...updates,
  };
}

describe("dados químicos enviados ao motor 3D", () => {
  it("preserva 3 mmol em 100 mL, inclusive com metadados nulos", () => {
    const request = buildMiceliumRequest([transfer({transferMetadata: {
      realAmountMmol: null, realConcentrationMmolL: null, renderCount: 48,
    }})]);
    expect(request.molecules[0].real_concentration_mmol_l).toBe(30);
    expect(request.molecules[0].real_amount_mmol).toBe(3);
    expect(request.molecules[0].cmc_mmol_l).toBeNull();
  });

  it("não trata uma classificação textual inconclusiva como negativa química", () => {
    const request = buildMiceliumRequest([transfer({name: "anfifílico insaturado", smiles: "OCCCCCC=CCCCCC"})]);
    expect(request.molecules[0].is_surfactant).toBeNull();
    expect(request.molecules[0].tail_carbon_count).toBeNull();
  });

  it("contagem visual não altera a concentração real", () => {
    const low = buildMiceliumRequest([transfer({transferMetadata: {renderCount: 8}})]);
    const high = buildMiceliumRequest([transfer({transferMetadata: {renderCount: 800}})]);
    expect(low.molecules[0].count).not.toBe(high.molecules[0].count);
    expect(low.molecules[0].real_concentration_mmol_l).toBe(high.molecules[0].real_concentration_mmol_l);
  });

  it("solvente permanece separado da quantidade molar de reagente", () => {
    const request = buildMiceliumRequest([transfer(), transfer({id: "water", name: "Água", smiles: "O", transferMetadata: {role: "solvent", renderCount: 28}})]);
    expect(request.molecules[1].role).toBe("solvent");
    expect(request.molecules[1].real_amount_mmol).toBeNull();
    expect(request.molecules[0].real_concentration_mmol_l).toBe(30);
  });
});

describe("exemplo documentado no pedido 3D", () => {
  const marked = (id: string | null) => ({ documentedExampleId: id });

  it("envia o id quando todos os transfers trazem o mesmo exemplo", () => {
    const request = buildMiceliumRequest([
      transfer({ transferMetadata: marked("sds_esferica") }),
      transfer({ id: "water", name: "Água", smiles: "O", transferMetadata: { role: "solvent", ...marked("sds_esferica") } }),
    ]);
    expect(request.documented_example_id).toBe("sds_esferica");
  });

  it("sem marcação ou com marcações diferentes, não envia exemplo", () => {
    expect(buildMiceliumRequest([transfer()]).documented_example_id).toBeNull();
    const mixed = buildMiceliumRequest([
      transfer({ transferMetadata: marked("sds_esferica") }),
      transfer({ id: "b", smiles: "CCO", transferMetadata: marked(null) }),
    ]);
    expect(mixed.documented_example_id).toBeNull();
  });
});

describe("papel explícito do painel", () => {
  it("água marcada como reagente (núcleo do AOT) continua reagente com a quantidade real", () => {
    const request = buildMiceliumRequest([
      transfer({ id: "aot", name: "AOT", smiles: "CCCCC(CC)COC(=O)CC(C(=O)OCC(CC)CCCC)S(=O)(=O)[O-].[Na+]", concentration: 10,
        transferMetadata: { role: "reagent", realAmountMmol: 10, documentedExampleId: "aot_inversa_isooctano" } }),
      transfer({ id: "agua", name: "Água (núcleo, derivada de w0)", smiles: "O", concentration: 100,
        transferMetadata: { role: "reagent", realAmountMmol: 100, documentedExampleId: "aot_inversa_isooctano" } }),
      transfer({ id: "isooctano", name: "Isooctano", smiles: "CC(C)CC(C)(C)C",
        transferMetadata: { role: "solvent", renderCount: 80, documentedExampleId: "aot_inversa_isooctano" } }),
    ]);
    const water = request.molecules.find((molecule) => molecule.name?.startsWith("Água"));
    expect(water?.role).toBe("reagent");
    expect(water?.real_amount_mmol).toBe(100);
    expect(request.molecules.find((molecule) => molecule.name === "Isooctano")?.role).toBe("solvent");
  });

  it("mistura comum: água marcada como reagente continua tratada como solvente (comportamento anterior)", () => {
    const request = buildMiceliumRequest([transfer(), transfer({ id: "w", name: "Água", smiles: "O", transferMetadata: { role: "reagent" } })]);
    expect(request.molecules.find((molecule) => molecule.smiles === "O")?.role).toBe("solvent");
  });

  it("sem papel marcado, a água continua sendo reconhecida como solvente", () => {
    const request = buildMiceliumRequest([transfer(), transfer({ id: "w", name: "Água", smiles: "O" })]);
    expect(request.molecules.find((molecule) => molecule.smiles === "O")?.role).toBe("solvent");
  });
});
