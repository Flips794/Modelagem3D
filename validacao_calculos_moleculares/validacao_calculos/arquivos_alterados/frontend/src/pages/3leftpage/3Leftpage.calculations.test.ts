import { beforeEach, describe, expect, it } from "vitest";
import { clintCmcMixMmolL, collectStoredMolecules, formatValue, getFirstValue, weightedRawValue } from "./3Leftpage";

function item(cmc: number|null, amount: number|null=1, count=10) {
  return {id:"a",name:"surfactant",smiles:"S",formula:"",count,amountMmol:amount,role:"reagent" as const,
    metadata:{},backend:{is_surfactante:{value:true},cmc_corrigida_mmol_l:{value:cmc,available:cmc!==null,unit:"mmol/L"}}};
}
beforeEach(()=>localStorage.clear());
describe("cálculos apresentados para uma solução",()=>{
  it("usa fração molar real na equação de Clint",()=>{
    expect(clintCmcMixMmolL([item(10,1,800),item(20,3,2)])).toBe("16 mmol/L");
    expect(clintCmcMixMmolL([item(10,1,2),item(20,3,800)])).toBe("16 mmol/L");
  });
  it("quantidade visual não substitui quantidade real ausente",()=>{
    expect(clintCmcMixMmolL([item(10,null,800),item(20,3,2)])).toBe("—");
  });
  it("CMC ausente de um surfactante não é descartada da mistura",()=>{
    expect(clintCmcMixMmolL([item(10),item(null)])).toBe("—");
  });
  it("exclui solvente e solutos declaradamente não surfactantes",()=>{
    const solvent={...item(null),role:"solvent" as const};
    const solute={...item(null),backend:{is_surfactante:{value:false}}};
    expect(clintCmcMixMmolL([item(10),solvent,solute])).toBe("10 mmol/L");
  });
  it("converte mol/L para mmol/L antes da equação",()=>{
    const a={...item(1),backend:{is_surfactante:{value:true},cmc_corrigida_mol_l:{value:.01,unit:"mol/L"}}};
    expect(clintCmcMixMmolL([a])).toBe("10 mmol/L");
  });
  it("não usa CMC de referência quando CMC no ambiente está indisponível",()=>{
    const a=item(null);a.metadata={cmc_corrigida_mmol_l:8.2};
    expect(clintCmcMixMmolL([a])).toBe("—");
  });
  it("não calcula logP médio pela quantidade de desenhos",()=>{
    expect(weightedRawValue([item(10),item(20)],["logp"])).toBe("—");
  });
  it("indisponibilidade atual prevalece sobre metadado antigo",()=>{
    const unavailable={value:null,available:false};
    expect(getFirstValue([{homo:unavailable},{homo:-7}],["homo"])).toBe(unavailable);
  });
  it.each([[1,"nm"," Å","10 Å"],[10,"Angstrom"," nm","1 nm"],[4.184,"kJ/mol"," kcal/mol","1 kcal/mol"],
    [1,"kcal/mol"," kJ/mol","4.184 kJ/mol"],[2,"Angstrom^2"," Å²","2 Å²"],
    [3,"mN/m","", "3 mN/m"]])("respeita unidade de %s %s",(value,unit,suffix,expected)=>{
    expect(formatValue({value,unit},String(suffix))).toBe(expected);
  });
  it("não muda unidade sem conversão conhecida",()=>{
    expect(formatValue({value:1,unit:"Pa"}," atm")).toBe("1 Pa");
  });
  it("não mostra NaN ou Infinity",()=>{
    expect(formatValue(NaN)).toBe("—");expect(formatValue(Infinity)).toBe("—");
  });
  it("não soma cinco snapshots da mesma solução",()=>{
    localStorage.setItem("modelagem3d:environment3d:molecules",JSON.stringify({molecules:[{smiles:"O",count:5}]}));
    localStorage.setItem("modelagem3d:2dto3d:solution",JSON.stringify([{smiles:"O",count:500}]));
    expect(collectStoredMolecules()).toEqual([{smiles:"O",count:5}]);
  });
  it("ausência da composição 3D não transforma um rascunho antigo em solução ativa",()=>{
    localStorage.setItem("modelagem3d:2dto3d:solution",JSON.stringify([{smiles:"O",count:500}]));
    expect(collectStoredMolecules()).toEqual([]);
  });
  it("uma solução limpa não ressuscita snapshots antigos",()=>{
    localStorage.setItem("modelagem3d:environment3d:molecules",JSON.stringify({molecules:[]}));
    localStorage.setItem("modelagem3d:2dto3d:solution",JSON.stringify([{smiles:"O",count:500}]));
    expect(collectStoredMolecules()).toEqual([]);
  });
});
