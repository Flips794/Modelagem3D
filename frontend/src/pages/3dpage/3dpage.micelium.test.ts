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
