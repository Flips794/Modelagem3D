import type { MoleculeTransferFrom2D } from "./type/3dpage.types";

export function finiteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(String(value).replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

/** Physical quantities only; renderCount never enters a chemical calculation. */
export function resolveRealQuantity(transfer: MoleculeTransferFrom2D, environment: { volume_ml: number }) {
  const volumeL = environment.volume_ml / 1000;
  const empty = { realAmountMmol: null, realConcentrationMmolL: null, realAmountUnit: null };
  if (!Number.isFinite(volumeL) || volumeL <= 0) return empty;
  const metadataAmount = finiteNumber(transfer.transferMetadata?.realAmountMmol);
  const metadataConcentration = finiteNumber(transfer.transferMetadata?.realConcentrationMmolL);
  // An amount survives volume changes; concentration must be recomputed.
  if (metadataAmount !== null && metadataAmount >= 0) {
    return { realAmountMmol: metadataAmount, realConcentrationMmolL: metadataAmount / volumeL, realAmountUnit: "mmol" };
  }
  if (metadataConcentration !== null && metadataConcentration >= 0) {
    return { realAmountMmol: metadataConcentration * volumeL, realConcentrationMmolL: metadataConcentration, realAmountUnit: "mmol/L" };
  }
  const value = finiteNumber(transfer.concentration);
  const unit = String(transfer.unit ?? "").trim().replace(/μ/g, "µ").replace(/^u(?=mol)/, "µ");
  if (value === null || value < 0) return empty;
  const mass = finiteNumber(transfer.molarMass);
  const concentrationFactors: Record<string, number> = { "mol/L": 1000, "mmol/L": 1, "µmol/L": .001 };
  const amountFactors: Record<string, number> = { "mol": 1000, "mmol": 1, "µmol": .001 };
  if (mass !== null && mass > 0) {
    concentrationFactors["g/L"] = 1000 / mass;
    concentrationFactors["mg/L"] = 1 / mass;
    amountFactors.g = 1000 / mass;
    amountFactors.mg = 1 / mass;
  }
  if (unit in concentrationFactors) {
    const concentration = value * concentrationFactors[unit];
    return { realAmountMmol: concentration * volumeL, realConcentrationMmolL: concentration, realAmountUnit: unit };
  }
  if (unit in amountFactors) {
    const amount = value * amountFactors[unit];
    return { realAmountMmol: amount, realConcentrationMmolL: amount / volumeL, realAmountUnit: unit };
  }
  return empty;
}
