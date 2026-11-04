import { describe, expect, it } from "vitest";
import { resolveRealQuantity } from "./realQuantities";
import type { MoleculeTransferFrom2D } from "./type/3dpage.types";

const cases: Array<[MoleculeTransferFrom2D["unit"],number]> = [
  ["mol/L", .01], ["mmol/L",10], ["µmol/L",10000], ["mol",.001], ["mmol",1],
  ["µmol",1000], ["g/L",2.8838], ["mg/L",2883.8], ["g",.28838], ["mg",288.38],
];
describe("quantidades físicas compartilhadas pelo pedido 3D e painel da solução", () => {
  it.each(cases)("converte %s para quantidade real", (unit,value) => {
    const q=resolveRealQuantity({smiles:"SDS",unit,concentration:value,molarMass:"288.38"},{volume_ml:100});
    expect(q.realAmountMmol).toBeCloseTo(1,8);
    expect(q.realConcentrationMmolL).toBeCloseTo(10,8);
  });
  it("recalcula a concentração quando o volume muda e a quantidade permanece", () => {
    const t={smiles:"O",transferMetadata:{realAmountMmol:1,realConcentrationMmolL:10}};
    expect(resolveRealQuantity(t,{volume_ml:200}).realConcentrationMmolL).toBe(5);
  });
  it("usa concentração explícita nos metadados quando não há quantidade", () => {
    expect(resolveRealQuantity({smiles:"O",transferMetadata:{realConcentrationMmolL:10}},{volume_ml:100}).realAmountMmol).toBe(1);
  });
  it.each([0,-1,Infinity,NaN])("recusa volume inválido %s", volume => {
    expect(resolveRealQuantity({smiles:"O",unit:"mmol",concentration:1},{volume_ml:volume}).realAmountMmol).toBeNull();
  });
  it.each(["partes","% mol","mL",undefined] as const)("não inventa quantidade para %s", unit => {
    expect(resolveRealQuantity({smiles:"O",unit,concentration:50,transferMetadata:{renderCount:100}},{volume_ml:100}).realAmountMmol).toBeNull();
  });
  it("preserva quantidade zero", () => {
    expect(resolveRealQuantity({smiles:"O",unit:"mmol",concentration:0},{volume_ml:100}).realAmountMmol).toBe(0);
  });
  it("recusa conversão de massa sem massa molar", () => {
    expect(resolveRealQuantity({smiles:"O",unit:"g",concentration:1},{volume_ml:100}).realAmountMmol).toBeNull();
  });
});
