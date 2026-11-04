import { useMemo, useState } from "react";

import "./fastmol.css";

type FastMolCategory =
  | "Comuns"
  | "Solventes"
  | "Ácidos e bases"
  | "Orgânicos"
  | "Cotensoativos"
  | "Hidrótropos"
  | "Siloxanos de referência"
  | "Surfactantes aniônicos"
  | "Surfactantes catiônicos"
  | "Surfactantes não iônicos"
  | "Surfactantes anfóteros"
  | "Biossurfactantes"
  | "Surfactantes fluorados"
  | "Surfactantes siliconados";

export type FastMolItem = {
  id: string;
  name: string;
  formula: string;
  smiles: string;
  category: FastMolCategory;
  description: string;
  tags: string[];
};

type FastMolProps = {
  isOpen: boolean;
  onClose: () => void;
  onSelectSmiles: (smiles: string, molecule: FastMolItem) => void;
};

const fastMolecules: FastMolItem[] = [
  {
    "id": "water",
    "name": "Água",
    "formula": "H2O",
    "smiles": "O",
    "category": "Comuns",
    "description": "Molécula polar básica para testar pares livres no oxigênio.",
    "tags": [
      "polar",
      "pares livres",
      "solvente"
    ]
  },
  {
    "id": "ammonia",
    "name": "Amônia",
    "formula": "NH3",
    "smiles": "N",
    "category": "Comuns",
    "description": "Base simples; útil para testar par livre no nitrogênio.",
    "tags": [
      "base",
      "nitrogênio",
      "par livre"
    ]
  },
  {
    "id": "ammonium",
    "name": "Íon amônio",
    "formula": "NH4+",
    "smiles": "[NH4+]",
    "category": "Comuns",
    "description": "Cátion simples para testar carga formal positiva.",
    "tags": [
      "cátion",
      "carga formal",
      "nitrogênio"
    ]
  },
  {
    "id": "hydroxide",
    "name": "Íon hidróxido",
    "formula": "OH-",
    "smiles": "[OH-]",
    "category": "Ácidos e bases",
    "description": "Ânion comum para testar carga negativa em oxigênio.",
    "tags": [
      "ânion",
      "base",
      "carga formal"
    ]
  },
  {
    "id": "acetate",
    "name": "Íon acetato",
    "formula": "C2H3O2-",
    "smiles": "CC(=O)[O-]",
    "category": "Ácidos e bases",
    "description": "Ânion carboxilato; útil para testar ressonância e carga.",
    "tags": [
      "carboxilato",
      "ressonância",
      "ânion"
    ]
  },
  {
    "id": "acetic-acid",
    "name": "Ácido acético",
    "formula": "C2H4O2",
    "smiles": "CC(=O)O",
    "category": "Ácidos e bases",
    "description": "Ácido carboxílico pequeno e estável.",
    "tags": [
      "ácido carboxílico",
      "polar"
    ]
  },
  {
    "id": "ethanol",
    "name": "Etanol",
    "formula": "C2H6O",
    "smiles": "CCO",
    "category": "Solventes",
    "description": "Álcool simples para testar grupo hidroxila.",
    "tags": [
      "álcool",
      "solvente",
      "polar"
    ]
  },
  {
    "id": "acetone",
    "name": "Acetona",
    "formula": "C3H6O",
    "smiles": "CC(=O)C",
    "category": "Solventes",
    "description": "Cetona simples para testar carbonila.",
    "tags": [
      "cetona",
      "carbonila",
      "solvente"
    ]
  },
  {
    "id": "benzene",
    "name": "Benzeno",
    "formula": "C6H6",
    "smiles": "c1ccccc1",
    "category": "Orgânicos",
    "description": "Anel aromático padrão.",
    "tags": [
      "aromático",
      "anel",
      "ressonância"
    ]
  },
  {
    "id": "phenol",
    "name": "Fenol",
    "formula": "C6H6O",
    "smiles": "Oc1ccccc1",
    "category": "Orgânicos",
    "description": "Aromático com hidroxila.",
    "tags": [
      "fenol",
      "aromático",
      "polar"
    ]
  },
  {
    "id": "aniline",
    "name": "Anilina",
    "formula": "C6H7N",
    "smiles": "Nc1ccccc1",
    "category": "Orgânicos",
    "description": "Amina aromática.",
    "tags": [
      "amina",
      "aromático",
      "nitrogênio"
    ]
  },
  {
    "id": "sodium-c6-sulfate",
    "name": "Hexil sulfato de sódio",
    "formula": "C6H13NaO4S",
    "smiles": "CCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C6.",
    "tags": [
      "aniônico",
      "sulfato",
      "C6",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c6-sulfonate",
    "name": "Hexano-1-sulfonato de sódio",
    "formula": "C6H13NaO3S",
    "smiles": "CCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C6.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C6",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c6-carboxylate",
    "name": "Hexanoato de sódio",
    "formula": "C6H11NaO2",
    "smiles": "CCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C6.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C6"
    ]
  },
  {
    "id": "sodium-c8-sulfate",
    "name": "Octil sulfato de sódio",
    "formula": "C8H17NaO4S",
    "smiles": "CCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C8.",
    "tags": [
      "aniônico",
      "sulfato",
      "C8",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c8-sulfonate",
    "name": "Octano-1-sulfonato de sódio",
    "formula": "C8H17NaO3S",
    "smiles": "CCCCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C8.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C8",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c8-carboxylate",
    "name": "Octanoato de sódio",
    "formula": "C8H15NaO2",
    "smiles": "CCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C8.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C8"
    ]
  },
  {
    "id": "sodium-c10-sulfate",
    "name": "Decil sulfato de sódio",
    "formula": "C10H21NaO4S",
    "smiles": "CCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C10.",
    "tags": [
      "aniônico",
      "sulfato",
      "C10",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c10-sulfonate",
    "name": "Decano-1-sulfonato de sódio",
    "formula": "C10H21NaO3S",
    "smiles": "CCCCCCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C10.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C10",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c10-carboxylate",
    "name": "Decanoato de sódio",
    "formula": "C10H19NaO2",
    "smiles": "CCCCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C10.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C10"
    ]
  },
  {
    "id": "sodium-c12-sulfate",
    "name": "Dodecil sulfato de sódio",
    "formula": "C12H25NaO4S",
    "smiles": "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C12.",
    "tags": [
      "aniônico",
      "sulfato",
      "C12",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c12-sulfonate",
    "name": "Dodecano-1-sulfonato de sódio",
    "formula": "C12H25NaO3S",
    "smiles": "CCCCCCCCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C12.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C12",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c12-carboxylate",
    "name": "Dodecanoato de sódio / laurato de sódio",
    "formula": "C12H23NaO2",
    "smiles": "CCCCCCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C12.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C12"
    ]
  },
  {
    "id": "sodium-c14-sulfate",
    "name": "Tetradecil sulfato de sódio",
    "formula": "C14H29NaO4S",
    "smiles": "CCCCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C14.",
    "tags": [
      "aniônico",
      "sulfato",
      "C14",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c14-sulfonate",
    "name": "Tetradecano-1-sulfonato de sódio",
    "formula": "C14H29NaO3S",
    "smiles": "CCCCCCCCCCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C14.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C14",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c14-carboxylate",
    "name": "Tetradecanoato de sódio / miristato de sódio",
    "formula": "C14H27NaO2",
    "smiles": "CCCCCCCCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C14.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C14"
    ]
  },
  {
    "id": "sodium-c16-sulfate",
    "name": "Hexadecil sulfato de sódio",
    "formula": "C16H33NaO4S",
    "smiles": "CCCCCCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C16.",
    "tags": [
      "aniônico",
      "sulfato",
      "C16",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c16-sulfonate",
    "name": "Hexadecano-1-sulfonato de sódio",
    "formula": "C16H33NaO3S",
    "smiles": "CCCCCCCCCCCCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C16.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C16",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c16-carboxylate",
    "name": "Hexadecanoato de sódio / palmitato de sódio",
    "formula": "C16H31NaO2",
    "smiles": "CCCCCCCCCCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C16.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C16"
    ]
  },
  {
    "id": "sodium-c18-sulfate",
    "name": "Octadecil sulfato de sódio",
    "formula": "C18H37NaO4S",
    "smiles": "CCCCCCCCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alquil sulfato com cauda C18.",
    "tags": [
      "aniônico",
      "sulfato",
      "C18",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c18-sulfonate",
    "name": "Octadecano-1-sulfonato de sódio",
    "formula": "C18H37NaO3S",
    "smiles": "CCCCCCCCCCCCCCCCCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico tipo alcano sulfonato com cauda C18.",
    "tags": [
      "aniônico",
      "sulfonato",
      "C18",
      "série homóloga"
    ]
  },
  {
    "id": "sodium-c18-carboxylate",
    "name": "Octadecanoato de sódio / estearato de sódio",
    "formula": "C18H35NaO2",
    "smiles": "CCCCCCCCCCCCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Sabão/carboxilato de cadeia C18.",
    "tags": [
      "aniônico",
      "carboxilato",
      "sabão",
      "C18"
    ]
  },
  {
    "id": "sds",
    "name": "SDS / SLS — dodecil sulfato de sódio",
    "formula": "C12H25NaO4S",
    "smiles": "CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico clássico; cauda C12 e cabeça sulfato.",
    "tags": [
      "aniônico",
      "sulfato",
      "C12",
      "micela"
    ]
  },
  {
    "id": "sles-eo1",
    "name": "SLES EO1 — lauril éter sulfato de sódio",
    "formula": "C14H29NaO5S",
    "smiles": "CCCCCCCCCCCCOCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Lauril éter sulfato com uma unidade etoxilada.",
    "tags": [
      "aniônico",
      "sulfato",
      "etoxilado"
    ]
  },
  {
    "id": "sles-eo2",
    "name": "SLES EO2 — lauril éter sulfato de sódio",
    "formula": "C16H33NaO6S",
    "smiles": "CCCCCCCCCCCCOCCOCCOS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Lauril éter sulfato com duas unidades etoxiladas.",
    "tags": [
      "aniônico",
      "sulfato",
      "etoxilado"
    ]
  },
  {
    "id": "sdbs",
    "name": "4-n-dodecilbenzenossulfonato de sódio — isômero de referência",
    "formula": "C18H29NaO3S",
    "smiles": "CCCCCCCCCCCCc1ccc(S(=O)(=O)[O-])cc1.[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Alquilbenzenossulfonato linear com substituição para e cadeia n-dodecil. Representante estrutural definido do SDBS.",
    "tags": [
      "aniônico",
      "sulfonato",
      "aromático",
      "SDBS",
      "isômero definido"
    ]
  },
  {
    "id": "sodium-toluene-sulfonate",
    "name": "p-toluenossulfonato de sódio",
    "formula": "C7H7NaO3S",
    "smiles": "Cc1ccc(S(=O)(=O)[O-])cc1.[Na+]",
    "category": "Hidrótropos",
    "description": "4-Metilbenzenossulfonato de sódio; hidrótropo aromático de cadeia curta.",
    "tags": [
      "aniônico",
      "hidrotropo",
      "sulfonato"
    ]
  },
  {
    "id": "sodium-xylene-sulfonate",
    "name": "2,4-dimetilbenzenossulfonato de sódio — isômero de xilenossulfonato",
    "formula": "C8H9NaO3S",
    "smiles": "Cc1cc(C)ccc1S(=O)(=O)[O-].[Na+]",
    "category": "Hidrótropos",
    "description": "Isômero 2,4 definido do xilenossulfonato de sódio; referência de hidrótropo aromático.",
    "tags": [
      "aniônico",
      "hidrotropo",
      "sulfonato"
    ]
  },
  {
    "id": "sodium-cocoyl-isethionate-simplified",
    "name": "Lauroil isetionato de sódio — homólogo C12",
    "formula": "C14H27NaO5S",
    "smiles": "CCCCCCCCCCCC(=O)OCCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "2-(Dodecanoiloxi)etanossulfonato de sódio. Homólogo C12 definido de isetionatos de coco; preserva o grupo acila e o contraíon sódio.",
    "tags": [
      "aniônico",
      "isetionato",
      "suave"
    ]
  },
  {
    "id": "sodium-lauroyl-sarcosinate",
    "name": "Lauroil sarcosinato de sódio",
    "formula": "C15H28NNaO3",
    "smiles": "CCCCCCCCCCCC(=O)N(C)CC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Aminoácido surfactante aniônico derivado de sarcosina.",
    "tags": [
      "aniônico",
      "aminoácido",
      "sarcosinato"
    ]
  },
  {
    "id": "sodium-methyl-lauroyl-taurate",
    "name": "Metil lauroil taurato de sódio",
    "formula": "C15H30NNaO4S",
    "smiles": "CCCCCCCCCCCC(=O)N(C)CCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico do tipo taurato.",
    "tags": [
      "aniônico",
      "taurato",
      "suave"
    ]
  },
  {
    "id": "sodium-lauryl-sulfoacetate",
    "name": "Lauril sulfoacetato de sódio",
    "formula": "C14H27NaO5S",
    "smiles": "CCCCCCCCCCCCOC(=O)CS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico sulfoacetato.",
    "tags": [
      "aniônico",
      "sulfoacetato",
      "C12"
    ]
  },
  {
    "id": "sodium-lauryl-phosphate",
    "name": "Lauril fosfato de sódio",
    "formula": "C12H26NaO4P",
    "smiles": "CCCCCCCCCCCCOP(=O)(O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Monoéster fosfato de álcool graxo.",
    "tags": [
      "aniônico",
      "fosfato",
      "C12"
    ]
  },
  {
    "id": "aot",
    "name": "AOT / docusato de sódio — bis(2-etilhexil) sulfosuccinato de sódio",
    "formula": "C20H37NaO7S",
    "smiles": "CCCCC(CC)COC(=O)CC(S(=O)(=O)[O-])C(=O)OCC(CC)CCCC.[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico ramificado clássico em microemulsões.",
    "tags": [
      "aniônico",
      "sulfosuccinato",
      "microemulsão"
    ]
  },
  {
    "id": "sodium-oleate",
    "name": "Oleato de sódio — 9Z (cis)",
    "formula": "C18H33NaO2",
    "smiles": "CCCCCCCC/C=C\\CCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Surfactante aniônico insaturado derivado de ácido graxo.",
    "tags": [
      "aniônico",
      "insaturado",
      "ácido graxo"
    ]
  },
  {
    "id": "sodium-linoleate",
    "name": "Linoleato de sódio — 9Z,12Z (cis,cis)",
    "formula": "C18H31NaO2",
    "smiles": "CCCCC/C=C\\C/C=C\\CCCCCCCC(=O)[O-].[Na+]",
    "category": "Surfactantes aniônicos",
    "description": "Carboxilato insaturado com duas duplas ligações.",
    "tags": [
      "aniônico",
      "insaturado",
      "ácido graxo"
    ]
  },
  {
    "id": "c8tab",
    "name": "OTAB — brometo de octiltrimetilamônio",
    "formula": "C11H26BrN",
    "smiles": "CCCCCCCC[N+](C)(C)C.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C8 e contraíon brometo.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C8",
      "brometo"
    ]
  },
  {
    "id": "c8tac",
    "name": "OTAC — cloreto de octiltrimetilamônio",
    "formula": "C11H26ClN",
    "smiles": "CCCCCCCC[N+](C)(C)C.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C8 e contraíon cloreto.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C8",
      "cloreto"
    ]
  },
  {
    "id": "c8-amine-hcl",
    "name": "Cloreto de octilamônio",
    "formula": "C8H20ClN",
    "smiles": "CCCCCCCC[NH3+].[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Amina graxa protonada com cauda C8.",
    "tags": [
      "catiônico",
      "amina protonada",
      "C8"
    ]
  },
  {
    "id": "c10tab",
    "name": "DeTAB — brometo de deciltrimetilamônio",
    "formula": "C13H30BrN",
    "smiles": "CCCCCCCCCC[N+](C)(C)C.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C10 e contraíon brometo.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C10",
      "brometo"
    ]
  },
  {
    "id": "c10tac",
    "name": "DeTAC — cloreto de deciltrimetilamônio",
    "formula": "C13H30ClN",
    "smiles": "CCCCCCCCCC[N+](C)(C)C.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C10 e contraíon cloreto.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C10",
      "cloreto"
    ]
  },
  {
    "id": "c10-amine-hcl",
    "name": "Cloreto de decilamônio",
    "formula": "C10H24ClN",
    "smiles": "CCCCCCCCCC[NH3+].[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Amina graxa protonada com cauda C10.",
    "tags": [
      "catiônico",
      "amina protonada",
      "C10"
    ]
  },
  {
    "id": "c12tab",
    "name": "DTAB — brometo de dodeciltrimetilamônio",
    "formula": "C15H34BrN",
    "smiles": "CCCCCCCCCCCC[N+](C)(C)C.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C12 e contraíon brometo.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C12",
      "brometo"
    ]
  },
  {
    "id": "c12tac",
    "name": "DTAC — cloreto de dodeciltrimetilamônio",
    "formula": "C15H34ClN",
    "smiles": "CCCCCCCCCCCC[N+](C)(C)C.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C12 e contraíon cloreto.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C12",
      "cloreto"
    ]
  },
  {
    "id": "c12-amine-hcl",
    "name": "Cloreto de dodecilamônio",
    "formula": "C12H28ClN",
    "smiles": "CCCCCCCCCCCC[NH3+].[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Amina graxa protonada com cauda C12.",
    "tags": [
      "catiônico",
      "amina protonada",
      "C12"
    ]
  },
  {
    "id": "c14tab",
    "name": "TTAB — brometo de tetradeciltrimetilamônio",
    "formula": "C17H38BrN",
    "smiles": "CCCCCCCCCCCCCC[N+](C)(C)C.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C14 e contraíon brometo.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C14",
      "brometo"
    ]
  },
  {
    "id": "c14tac",
    "name": "TTAC — cloreto de tetradeciltrimetilamônio",
    "formula": "C17H38ClN",
    "smiles": "CCCCCCCCCCCCCC[N+](C)(C)C.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C14 e contraíon cloreto.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C14",
      "cloreto"
    ]
  },
  {
    "id": "c14-amine-hcl",
    "name": "Cloreto de tetradecilamônio",
    "formula": "C14H32ClN",
    "smiles": "CCCCCCCCCCCCCC[NH3+].[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Amina graxa protonada com cauda C14.",
    "tags": [
      "catiônico",
      "amina protonada",
      "C14"
    ]
  },
  {
    "id": "c16tab",
    "name": "CTAB — brometo de cetiltrimetilamônio",
    "formula": "C19H42BrN",
    "smiles": "CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C16 e contraíon brometo.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C16",
      "brometo"
    ]
  },
  {
    "id": "c16tac",
    "name": "CTAC — cloreto de cetiltrimetilamônio",
    "formula": "C19H42ClN",
    "smiles": "CCCCCCCCCCCCCCCC[N+](C)(C)C.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C16 e contraíon cloreto.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C16",
      "cloreto"
    ]
  },
  {
    "id": "c16-amine-hcl",
    "name": "Cloreto de hexadecilamônio",
    "formula": "C16H36ClN",
    "smiles": "CCCCCCCCCCCCCCCC[NH3+].[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Amina graxa protonada com cauda C16.",
    "tags": [
      "catiônico",
      "amina protonada",
      "C16"
    ]
  },
  {
    "id": "c18tab",
    "name": "STAB — brometo de esteariltrimetilamônio",
    "formula": "C21H46BrN",
    "smiles": "CCCCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C18 e contraíon brometo.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C18",
      "brometo"
    ]
  },
  {
    "id": "c18tac",
    "name": "STAC — cloreto de esteariltrimetilamônio",
    "formula": "C21H46ClN",
    "smiles": "CCCCCCCCCCCCCCCCCC[N+](C)(C)C.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio com cauda C18 e contraíon cloreto.",
    "tags": [
      "catiônico",
      "amônio quaternário",
      "C18",
      "cloreto"
    ]
  },
  {
    "id": "c18-amine-hcl",
    "name": "Cloreto de octadecilamônio",
    "formula": "C18H40ClN",
    "smiles": "CCCCCCCCCCCCCCCCCC[NH3+].[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Amina graxa protonada com cauda C18.",
    "tags": [
      "catiônico",
      "amina protonada",
      "C18"
    ]
  },
  {
    "id": "benzalkonium-c12",
    "name": "Cloreto de benzalcônio C12 — homólogo dodecil",
    "formula": "C21H38ClN",
    "smiles": "CCCCCCCCCCCC[N+](C)(C)Cc1ccccc1.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário benzílico simplificado com cauda C12.",
    "tags": [
      "catiônico",
      "benzalcônio",
      "C12"
    ]
  },
  {
    "id": "benzalkonium-c14",
    "name": "Cloreto de benzalcônio C14 — homólogo tetradecil",
    "formula": "C23H42ClN",
    "smiles": "CCCCCCCCCCCCCC[N+](C)(C)Cc1ccccc1.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário benzílico simplificado com cauda C14.",
    "tags": [
      "catiônico",
      "benzalcônio",
      "C14"
    ]
  },
  {
    "id": "cetylpyridinium-chloride",
    "name": "Cloreto de cetilpiridínio",
    "formula": "C21H38ClN",
    "smiles": "CCCCCCCCCCCCCCCC[n+]1ccccc1.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Surfactante catiônico piridínico.",
    "tags": [
      "catiônico",
      "piridínio",
      "C16"
    ]
  },
  {
    "id": "didecyldimethylammonium-chloride",
    "name": "Cloreto de didecildimetilamônio",
    "formula": "C22H48ClN",
    "smiles": "CCCCCCCCCC[N+](C)(C)CCCCCCCCCC.[Cl-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário de amônio dialquílico.",
    "tags": [
      "catiônico",
      "dialquil",
      "amônio quaternário"
    ]
  },
  {
    "id": "dioctyldimethylammonium-bromide",
    "name": "Brometo de dioctildimetilamônio",
    "formula": "C18H40BrN",
    "smiles": "CCCCCCCC[N+](C)(C)CCCCCCCC.[Br-]",
    "category": "Surfactantes catiônicos",
    "description": "Quaternário dialquílico com duas caudas C8.",
    "tags": [
      "catiônico",
      "dialquil",
      "brometo"
    ]
  },
  {
    "id": "c8-alcohol",
    "name": "1-octanol / álcool octílico",
    "formula": "C8H18O",
    "smiles": "CCCCCCCCO",
    "category": "Cotensoativos",
    "description": "Álcool primário linear C8; referência de álcool graxo e cotensoativo.",
    "tags": [
      "não iônico",
      "álcool graxo",
      "C8"
    ]
  },
  {
    "id": "c8-alcohol-eo2",
    "name": "Octeth-2 — álcool octílico etoxilado EO2",
    "formula": "C12H26O3",
    "smiles": "CCCCCCCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C8EO2, com exatamente 2 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C8",
      "EO2",
      "homólogo definido"
    ]
  },
  {
    "id": "c8-alcohol-eo3",
    "name": "Octeth-3 — álcool octílico etoxilado EO3",
    "formula": "C14H30O4",
    "smiles": "CCCCCCCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C8EO3, com exatamente 3 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C8",
      "EO3",
      "homólogo definido"
    ]
  },
  {
    "id": "c8-alcohol-eo4",
    "name": "Octeth-4 — álcool octílico etoxilado EO4",
    "formula": "C16H34O5",
    "smiles": "CCCCCCCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C8EO4, com exatamente 4 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C8",
      "EO4",
      "homólogo definido"
    ]
  },
  {
    "id": "c8-alcohol-eo6",
    "name": "Octeth-6 — álcool octílico etoxilado EO6",
    "formula": "C20H42O7",
    "smiles": "CCCCCCCCOCCOCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C8EO6, com exatamente 6 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C8",
      "EO6",
      "homólogo definido"
    ]
  },
  {
    "id": "c8-glucoside",
    "name": "Octil β-D-glucopiranosídeo",
    "formula": "C14H28O6",
    "smiles": "CCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "β-D-Glucopiranosídeo de n-alquila C8; anômero e configuração dos cinco centros do açúcar definidos.",
    "tags": [
      "não iônico",
      "glicosídeo",
      "C8",
      "APG",
      "β-D",
      "estereoquímica definida"
    ]
  },
  {
    "id": "c10-alcohol",
    "name": "1-decanol / álcool decílico",
    "formula": "C10H22O",
    "smiles": "CCCCCCCCCCO",
    "category": "Cotensoativos",
    "description": "Álcool primário linear C10; referência de álcool graxo e cotensoativo.",
    "tags": [
      "não iônico",
      "álcool graxo",
      "C10"
    ]
  },
  {
    "id": "c10-alcohol-eo2",
    "name": "Deceth-2 — álcool decílico etoxilado EO2",
    "formula": "C14H30O3",
    "smiles": "CCCCCCCCCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C10EO2, com exatamente 2 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C10",
      "EO2",
      "homólogo definido"
    ]
  },
  {
    "id": "c10-alcohol-eo3",
    "name": "Deceth-3 — álcool decílico etoxilado EO3",
    "formula": "C16H34O4",
    "smiles": "CCCCCCCCCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C10EO3, com exatamente 3 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C10",
      "EO3",
      "homólogo definido"
    ]
  },
  {
    "id": "c10-alcohol-eo4",
    "name": "Deceth-4 — álcool decílico etoxilado EO4",
    "formula": "C18H38O5",
    "smiles": "CCCCCCCCCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C10EO4, com exatamente 4 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C10",
      "EO4",
      "homólogo definido"
    ]
  },
  {
    "id": "c10-alcohol-eo6",
    "name": "Deceth-6 — álcool decílico etoxilado EO6",
    "formula": "C22H46O7",
    "smiles": "CCCCCCCCCCOCCOCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C10EO6, com exatamente 6 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C10",
      "EO6",
      "homólogo definido"
    ]
  },
  {
    "id": "c10-glucoside",
    "name": "Decil β-D-glucopiranosídeo",
    "formula": "C16H32O6",
    "smiles": "CCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "β-D-Glucopiranosídeo de n-alquila C10; anômero e configuração dos cinco centros do açúcar definidos.",
    "tags": [
      "não iônico",
      "glicosídeo",
      "C10",
      "APG",
      "β-D",
      "estereoquímica definida"
    ]
  },
  {
    "id": "c12-alcohol",
    "name": "1-dodecanol / álcool laurílico",
    "formula": "C12H26O",
    "smiles": "CCCCCCCCCCCCO",
    "category": "Cotensoativos",
    "description": "Álcool primário linear C12; referência de álcool graxo e cotensoativo.",
    "tags": [
      "não iônico",
      "álcool graxo",
      "C12"
    ]
  },
  {
    "id": "c12-alcohol-eo2",
    "name": "Laureth-2 — álcool laurílico etoxilado EO2",
    "formula": "C16H34O3",
    "smiles": "CCCCCCCCCCCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C12EO2, com exatamente 2 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C12",
      "EO2",
      "homólogo definido"
    ]
  },
  {
    "id": "c12-alcohol-eo3",
    "name": "Laureth-3 — álcool laurílico etoxilado EO3",
    "formula": "C18H38O4",
    "smiles": "CCCCCCCCCCCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C12EO3, com exatamente 3 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C12",
      "EO3",
      "homólogo definido"
    ]
  },
  {
    "id": "c12-alcohol-eo4",
    "name": "Laureth-4 — álcool laurílico etoxilado EO4",
    "formula": "C20H42O5",
    "smiles": "CCCCCCCCCCCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C12EO4, com exatamente 4 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C12",
      "EO4",
      "homólogo definido"
    ]
  },
  {
    "id": "c12-alcohol-eo6",
    "name": "Laureth-6 — álcool laurílico etoxilado EO6",
    "formula": "C24H50O7",
    "smiles": "CCCCCCCCCCCCOCCOCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C12EO6, com exatamente 6 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C12",
      "EO6",
      "homólogo definido"
    ]
  },
  {
    "id": "c12-glucoside",
    "name": "Dodecil β-D-glucopiranosídeo",
    "formula": "C18H36O6",
    "smiles": "CCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "β-D-Glucopiranosídeo de n-alquila C12; anômero e configuração dos cinco centros do açúcar definidos.",
    "tags": [
      "não iônico",
      "glicosídeo",
      "C12",
      "APG",
      "β-D",
      "estereoquímica definida"
    ]
  },
  {
    "id": "c14-alcohol",
    "name": "1-tetradecanol / álcool miristílico",
    "formula": "C14H30O",
    "smiles": "CCCCCCCCCCCCCCO",
    "category": "Cotensoativos",
    "description": "Álcool primário linear C14; referência de álcool graxo e cotensoativo.",
    "tags": [
      "não iônico",
      "álcool graxo",
      "C14"
    ]
  },
  {
    "id": "c14-alcohol-eo2",
    "name": "Myreth-2 — álcool miristílico etoxilado EO2",
    "formula": "C18H38O3",
    "smiles": "CCCCCCCCCCCCCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C14EO2, com exatamente 2 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C14",
      "EO2",
      "homólogo definido"
    ]
  },
  {
    "id": "c14-alcohol-eo3",
    "name": "Myreth-3 — álcool miristílico etoxilado EO3",
    "formula": "C20H42O4",
    "smiles": "CCCCCCCCCCCCCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C14EO3, com exatamente 3 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C14",
      "EO3",
      "homólogo definido"
    ]
  },
  {
    "id": "c14-alcohol-eo4",
    "name": "Myreth-4 — álcool miristílico etoxilado EO4",
    "formula": "C22H46O5",
    "smiles": "CCCCCCCCCCCCCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C14EO4, com exatamente 4 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C14",
      "EO4",
      "homólogo definido"
    ]
  },
  {
    "id": "c14-alcohol-eo6",
    "name": "Myreth-6 — álcool miristílico etoxilado EO6",
    "formula": "C26H54O7",
    "smiles": "CCCCCCCCCCCCCCOCCOCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C14EO6, com exatamente 6 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C14",
      "EO6",
      "homólogo definido"
    ]
  },
  {
    "id": "c14-glucoside",
    "name": "Tetradecil β-D-glucopiranosídeo",
    "formula": "C20H40O6",
    "smiles": "CCCCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "β-D-Glucopiranosídeo de n-alquila C14; anômero e configuração dos cinco centros do açúcar definidos.",
    "tags": [
      "não iônico",
      "glicosídeo",
      "C14",
      "APG",
      "β-D",
      "estereoquímica definida"
    ]
  },
  {
    "id": "c16-alcohol",
    "name": "1-hexadecanol / álcool cetílico",
    "formula": "C16H34O",
    "smiles": "CCCCCCCCCCCCCCCCO",
    "category": "Cotensoativos",
    "description": "Álcool primário linear C16; referência de álcool graxo e cotensoativo.",
    "tags": [
      "não iônico",
      "álcool graxo",
      "C16"
    ]
  },
  {
    "id": "c16-alcohol-eo2",
    "name": "Ceteth-2 — álcool cetílico etoxilado EO2",
    "formula": "C20H42O3",
    "smiles": "CCCCCCCCCCCCCCCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C16EO2, com exatamente 2 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C16",
      "EO2",
      "homólogo definido"
    ]
  },
  {
    "id": "c16-alcohol-eo3",
    "name": "Ceteth-3 — álcool cetílico etoxilado EO3",
    "formula": "C22H46O4",
    "smiles": "CCCCCCCCCCCCCCCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C16EO3, com exatamente 3 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C16",
      "EO3",
      "homólogo definido"
    ]
  },
  {
    "id": "c16-alcohol-eo4",
    "name": "Ceteth-4 — álcool cetílico etoxilado EO4",
    "formula": "C24H50O5",
    "smiles": "CCCCCCCCCCCCCCCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C16EO4, com exatamente 4 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C16",
      "EO4",
      "homólogo definido"
    ]
  },
  {
    "id": "c16-alcohol-eo6",
    "name": "Ceteth-6 — álcool cetílico etoxilado EO6",
    "formula": "C28H58O7",
    "smiles": "CCCCCCCCCCCCCCCCOCCOCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C16EO6, com exatamente 6 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C16",
      "EO6",
      "homólogo definido"
    ]
  },
  {
    "id": "c16-glucoside",
    "name": "Hexadecil β-D-glucopiranosídeo",
    "formula": "C22H44O6",
    "smiles": "CCCCCCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "β-D-Glucopiranosídeo de n-alquila C16; anômero e configuração dos cinco centros do açúcar definidos.",
    "tags": [
      "não iônico",
      "glicosídeo",
      "C16",
      "APG",
      "β-D",
      "estereoquímica definida"
    ]
  },
  {
    "id": "c18-alcohol",
    "name": "1-octadecanol / álcool estearílico",
    "formula": "C18H38O",
    "smiles": "CCCCCCCCCCCCCCCCCCO",
    "category": "Cotensoativos",
    "description": "Álcool primário linear C18; referência de álcool graxo e cotensoativo.",
    "tags": [
      "não iônico",
      "álcool graxo",
      "C18"
    ]
  },
  {
    "id": "c18-alcohol-eo2",
    "name": "Steareth-2 — álcool estearílico etoxilado EO2",
    "formula": "C22H46O3",
    "smiles": "CCCCCCCCCCCCCCCCCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C18EO2, com exatamente 2 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C18",
      "EO2",
      "homólogo definido"
    ]
  },
  {
    "id": "c18-alcohol-eo3",
    "name": "Steareth-3 — álcool estearílico etoxilado EO3",
    "formula": "C24H50O4",
    "smiles": "CCCCCCCCCCCCCCCCCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C18EO3, com exatamente 3 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C18",
      "EO3",
      "homólogo definido"
    ]
  },
  {
    "id": "c18-alcohol-eo4",
    "name": "Steareth-4 — álcool estearílico etoxilado EO4",
    "formula": "C26H54O5",
    "smiles": "CCCCCCCCCCCCCCCCCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C18EO4, com exatamente 4 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C18",
      "EO4",
      "homólogo definido"
    ]
  },
  {
    "id": "c18-alcohol-eo6",
    "name": "Steareth-6 — álcool estearílico etoxilado EO6",
    "formula": "C30H62O7",
    "smiles": "CCCCCCCCCCCCCCCCCCOCCOCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido C18EO6, com exatamente 6 unidades de óxido de etileno. O nome INCI pode designar uma distribuição de homólogos.",
    "tags": [
      "não iônico",
      "etoxilado",
      "C18",
      "EO6",
      "homólogo definido"
    ]
  },
  {
    "id": "c18-glucoside",
    "name": "Octadecil β-D-glucopiranosídeo",
    "formula": "C24H48O6",
    "smiles": "CCCCCCCCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "β-D-Glucopiranosídeo de n-alquila C18; anômero e configuração dos cinco centros do açúcar definidos.",
    "tags": [
      "não iônico",
      "glicosídeo",
      "C18",
      "APG",
      "β-D",
      "estereoquímica definida"
    ]
  },
  {
    "id": "triton-x100-simplified",
    "name": "4-terc-octilfenol EO10 — homólogo de referência",
    "formula": "C34H62O11",
    "smiles": "CC(C)(C)CC(C)(C)c1ccc(OCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO)cc1",
    "category": "Surfactantes não iônicos",
    "description": "Homólogo definido com grupo 1,1,3,3-tetrametilbutil e dez EO. Referência para Triton X-100, cuja mistura comercial apresenta aproximadamente 9–10 EO em média.",
    "tags": [
      "não iônico",
      "Triton X-100",
      "EO10",
      "homólogo definido"
    ]
  },
  {
    "id": "nonoxynol-9-simplified",
    "name": "4-n-nonilfenol EO9 — referência de nonoxinol-9",
    "formula": "C33H60O10",
    "smiles": "CCCCCCCCCc1ccc(OCCOCCOCCOCCOCCOCCOCCOCCOCCO)cc1",
    "category": "Surfactantes não iônicos",
    "description": "Éter nonilfenílico de nonaetilenoglicol, com cadeia n-nonil para e exatamente nove EO; estrutura definida de referência.",
    "tags": [
      "não iônico",
      "nonoxinol-9",
      "EO9",
      "isômero definido"
    ]
  },
  {
    "id": "span-20-simplified",
    "name": "Monolaurato de 1,4-sorbitano — referência do Span 20",
    "formula": "C18H34O6",
    "smiles": "CCCCCCCCCCCC(=O)OC[C@H]([C@@H]1[C@@H]([C@H](CO1)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "Molécula completa de monolaurato de 1,4-sorbitano, com configuração do isômero de referência definida; produtos comerciais podem conter outros isômeros.",
    "tags": [
      "não iônico",
      "Span 20",
      "sorbitano",
      "estrutura completa"
    ]
  },
  {
    "id": "span-80-simplified",
    "name": "Monooleato de 1,4-sorbitano (9Z) — referência do Span 80",
    "formula": "C24H44O6",
    "smiles": "CCCCCCCC/C=C\\CCCCCCCC(=O)OC[C@H]([C@@H]1[C@@H]([C@H](CO1)O)O)O",
    "category": "Surfactantes não iônicos",
    "description": "Monooleato de 1,4-sorbitano completo, com dupla cis e centros do sorbitano definidos; isômero de referência do Span 80.",
    "tags": [
      "não iônico",
      "Span 80",
      "sorbitano",
      "9Z",
      "estrutura completa"
    ]
  },
  {
    "id": "tween-20-simplified",
    "name": "Polissorbato 20 — modelo molecular EO20 (5/5/5/5)",
    "formula": "C58H114O26",
    "smiles": "CCCCCCCCCCCC(=O)OCCOCCOCCOCCOCCOC[C@H]([C@@H]1[C@@H]([C@H](CO1)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Modelo molecular de referência para Tween 20: sorbitano completo, monoéster e vinte EO. Distribuição 5/5/5/5 escolhida para visualização; o produto comercial é uma mistura.",
    "tags": [
      "não iônico",
      "Tween 20",
      "polysorbate 20",
      "modelo definido",
      "EO20"
    ]
  },
  {
    "id": "tween-80-simplified",
    "name": "Polissorbato 80 — modelo molecular EO20 (5/5/5/5)",
    "formula": "C64H124O26",
    "smiles": "CCCCCCCC/C=C\\CCCCCCCC(=O)OCCOCCOCCOCCOCCOC[C@H]([C@@H]1[C@@H]([C@H](CO1)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Modelo molecular de referência para Tween 80: sorbitano completo, monoéster e vinte EO. Distribuição 5/5/5/5 escolhida para visualização; o produto comercial é uma mistura.",
    "tags": [
      "não iônico",
      "Tween 80",
      "polysorbate 80",
      "modelo definido",
      "EO20"
    ]
  },
  {
    "id": "cocamide-mea-simplified",
    "name": "Lauramida MEA — homólogo C12 da cocamida MEA",
    "formula": "C14H29NO2",
    "smiles": "CCCCCCCCCCCC(=O)NCCO",
    "category": "Surfactantes não iônicos",
    "description": "Modelo C12 para cocamida monoetanolamina; representa a fração lauroil de misturas cocoyl.",
    "tags": [
      "não iônico",
      "amida",
      "MEA"
    ]
  },
  {
    "id": "cocamide-dea-simplified",
    "name": "Lauramida DEA — homólogo C12 da cocamida DEA",
    "formula": "C16H33NO3",
    "smiles": "CCCCCCCCCCCC(=O)N(CCO)CCO",
    "category": "Surfactantes não iônicos",
    "description": "Modelo C12 para cocamida dietanolamina; representa a fração lauroil de misturas cocoyl.",
    "tags": [
      "não iônico",
      "amida",
      "DEA"
    ]
  },
  {
    "id": "poloxamer-fragment",
    "name": "Oligômero EO2–PO2–EO1 — modelo tipo poloxâmero",
    "formula": "C12H26O6",
    "smiles": "OCCOCCOCC(C)OCC(C)OCCO",
    "category": "Surfactantes não iônicos",
    "description": "Oligômero com blocos EO2–PO2–EO1 e terminações hidroxila; modelo definido de arquitetura, com centros dos PO sem configuração R/S especificada.",
    "tags": [
      "não iônico",
      "poloxamer",
      "poloxâmero",
      "modelo de blocos"
    ]
  },
  {
    "id": "peg-monolaurate-simplified",
    "name": "Monolaurato de trietilenoglicol — PEG3 definido",
    "formula": "C18H36O5",
    "smiles": "CCCCCCCCCCCC(=O)OCCOCCOCCO",
    "category": "Surfactantes não iônicos",
    "description": "Monoéster de ácido láurico e trietilenoglicol, com exatamente três unidades EO.",
    "tags": [
      "não iônico",
      "PEG",
      "laurato"
    ]
  },
  {
    "id": "c8-betaine",
    "name": "Octil dimetil betaína",
    "formula": "C12H25NO2",
    "smiles": "CCCCCCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Betaína zwitteriônica com cauda C8.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína",
      "C8"
    ]
  },
  {
    "id": "c8-sulfobetaine",
    "name": "Octil dimetil sulfopropil betaína",
    "formula": "C13H29NO3S",
    "smiles": "CCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Sulfobetaína zwitteriônica com cauda C8.",
    "tags": [
      "anfótero",
      "zwitterion",
      "sulfobetaína",
      "C8"
    ]
  },
  {
    "id": "c8-amine-oxide",
    "name": "Óxido de N,N-dimetiloctilamina",
    "formula": "C10H23NO",
    "smiles": "CCCCCCCC[N+](C)(C)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amina óxido com cauda C8.",
    "tags": [
      "anfótero",
      "amina óxido",
      "C8"
    ]
  },
  {
    "id": "c8-amidopropyl-betaine",
    "name": "Caprilamidopropil betaína",
    "formula": "C15H30N2O3",
    "smiles": "CCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amidopropil betaína simplificada com cauda acila C8.",
    "tags": [
      "anfótero",
      "amidopropil betaína",
      "C8"
    ]
  },
  {
    "id": "c10-betaine",
    "name": "Decil dimetil betaína",
    "formula": "C14H29NO2",
    "smiles": "CCCCCCCCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Betaína zwitteriônica com cauda C10.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína",
      "C10"
    ]
  },
  {
    "id": "c10-sulfobetaine",
    "name": "Decil dimetil sulfopropil betaína",
    "formula": "C15H33NO3S",
    "smiles": "CCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Sulfobetaína zwitteriônica com cauda C10.",
    "tags": [
      "anfótero",
      "zwitterion",
      "sulfobetaína",
      "C10"
    ]
  },
  {
    "id": "c10-amine-oxide",
    "name": "Óxido de N,N-dimetildecilamina",
    "formula": "C12H27NO",
    "smiles": "CCCCCCCCCC[N+](C)(C)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amina óxido com cauda C10.",
    "tags": [
      "anfótero",
      "amina óxido",
      "C10"
    ]
  },
  {
    "id": "c10-amidopropyl-betaine",
    "name": "Capramidopropil betaína",
    "formula": "C17H34N2O3",
    "smiles": "CCCCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amidopropil betaína simplificada com cauda acila C10.",
    "tags": [
      "anfótero",
      "amidopropil betaína",
      "C10"
    ]
  },
  {
    "id": "c12-betaine",
    "name": "Lauril dimetil betaína",
    "formula": "C16H33NO2",
    "smiles": "CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Betaína zwitteriônica com cauda C12.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína",
      "C12"
    ]
  },
  {
    "id": "c12-sulfobetaine",
    "name": "Lauril dimetil sulfopropil betaína",
    "formula": "C17H37NO3S",
    "smiles": "CCCCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Sulfobetaína zwitteriônica com cauda C12.",
    "tags": [
      "anfótero",
      "zwitterion",
      "sulfobetaína",
      "C12"
    ]
  },
  {
    "id": "c12-amine-oxide",
    "name": "Óxido de N,N-dimetildodecilamina / lauramina óxido",
    "formula": "C14H31NO",
    "smiles": "CCCCCCCCCCCC[N+](C)(C)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amina óxido com cauda C12.",
    "tags": [
      "anfótero",
      "amina óxido",
      "C12"
    ]
  },
  {
    "id": "c12-amidopropyl-betaine",
    "name": "Lauroamidopropil betaína",
    "formula": "C19H38N2O3",
    "smiles": "CCCCCCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amidopropil betaína simplificada com cauda acila C12.",
    "tags": [
      "anfótero",
      "amidopropil betaína",
      "C12"
    ]
  },
  {
    "id": "c14-betaine",
    "name": "Miristil dimetil betaína",
    "formula": "C18H37NO2",
    "smiles": "CCCCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Betaína zwitteriônica com cauda C14.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína",
      "C14"
    ]
  },
  {
    "id": "c14-sulfobetaine",
    "name": "Miristil dimetil sulfopropil betaína",
    "formula": "C19H41NO3S",
    "smiles": "CCCCCCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Sulfobetaína zwitteriônica com cauda C14.",
    "tags": [
      "anfótero",
      "zwitterion",
      "sulfobetaína",
      "C14"
    ]
  },
  {
    "id": "c14-amine-oxide",
    "name": "Óxido de N,N-dimetiltetradecilamina",
    "formula": "C16H35NO",
    "smiles": "CCCCCCCCCCCCCC[N+](C)(C)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amina óxido com cauda C14.",
    "tags": [
      "anfótero",
      "amina óxido",
      "C14"
    ]
  },
  {
    "id": "c14-amidopropyl-betaine",
    "name": "Miristamidopropil betaína",
    "formula": "C21H42N2O3",
    "smiles": "CCCCCCCCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amidopropil betaína simplificada com cauda acila C14.",
    "tags": [
      "anfótero",
      "amidopropil betaína",
      "C14"
    ]
  },
  {
    "id": "c16-betaine",
    "name": "Cetil dimetil betaína",
    "formula": "C20H41NO2",
    "smiles": "CCCCCCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Betaína zwitteriônica com cauda C16.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína",
      "C16"
    ]
  },
  {
    "id": "c16-sulfobetaine",
    "name": "Cetil dimetil sulfopropil betaína",
    "formula": "C21H45NO3S",
    "smiles": "CCCCCCCCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Sulfobetaína zwitteriônica com cauda C16.",
    "tags": [
      "anfótero",
      "zwitterion",
      "sulfobetaína",
      "C16"
    ]
  },
  {
    "id": "c16-amine-oxide",
    "name": "Óxido de N,N-dimetilhexadecilamina",
    "formula": "C18H39NO",
    "smiles": "CCCCCCCCCCCCCCCC[N+](C)(C)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amina óxido com cauda C16.",
    "tags": [
      "anfótero",
      "amina óxido",
      "C16"
    ]
  },
  {
    "id": "c16-amidopropyl-betaine",
    "name": "Palmitamidopropil betaína",
    "formula": "C23H46N2O3",
    "smiles": "CCCCCCCCCCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amidopropil betaína simplificada com cauda acila C16.",
    "tags": [
      "anfótero",
      "amidopropil betaína",
      "C16"
    ]
  },
  {
    "id": "c18-betaine",
    "name": "Estearil dimetil betaína",
    "formula": "C22H45NO2",
    "smiles": "CCCCCCCCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Betaína zwitteriônica com cauda C18.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína",
      "C18"
    ]
  },
  {
    "id": "c18-sulfobetaine",
    "name": "Estearil dimetil sulfopropil betaína",
    "formula": "C23H49NO3S",
    "smiles": "CCCCCCCCCCCCCCCCCC[N+](C)(C)CCCS(=O)(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Sulfobetaína zwitteriônica com cauda C18.",
    "tags": [
      "anfótero",
      "zwitterion",
      "sulfobetaína",
      "C18"
    ]
  },
  {
    "id": "c18-amine-oxide",
    "name": "Óxido de N,N-dimetiloctadecilamina",
    "formula": "C20H43NO",
    "smiles": "CCCCCCCCCCCCCCCCCC[N+](C)(C)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amina óxido com cauda C18.",
    "tags": [
      "anfótero",
      "amina óxido",
      "C18"
    ]
  },
  {
    "id": "c18-amidopropyl-betaine",
    "name": "Estearamidopropil betaína",
    "formula": "C25H50N2O3",
    "smiles": "CCCCCCCCCCCCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Amidopropil betaína simplificada com cauda acila C18.",
    "tags": [
      "anfótero",
      "amidopropil betaína",
      "C18"
    ]
  },
  {
    "id": "cocamidopropyl-betaine-simplified",
    "name": "Cocamidopropil betaína — modelo lauroamidopropil C12",
    "formula": "C19H38N2O3",
    "smiles": "CCCCCCCCCCCC(=O)NCCC[N+](C)(C)CC(=O)[O-]",
    "category": "Surfactantes anfóteros",
    "description": "Zwitterion anfótero simplificado com amônio e carboxilato.",
    "tags": [
      "anfótero",
      "zwitterion",
      "betaína"
    ]
  },
  {
    "id": "cocoamphoacetate-simplified",
    "name": "Lauroamfoacetato de sódio — homólogo C12 de cadeia aberta",
    "formula": "C18H35N2NaO4",
    "smiles": "CCCCCCCCCCCC(=O)NCCN(CCO)CC(=O)[O-].[Na+]",
    "category": "Surfactantes anfóteros",
    "description": "N-(2-hidroxietil)-N-[2-(dodecanoilamino)etil]glicinato de sódio; representante C12 de cadeia aberta do cocoamfoacetato, na forma carboxilato com amina não protonada.",
    "tags": [
      "anfótero",
      "cocoamphoacetate",
      "cadeia aberta",
      "C12",
      "espécie definida"
    ]
  },
  {
    "id": "lecithin-fragment",
    "name": "DPPC — 1,2-dipalmitoil-sn-glicero-3-fosfocolina",
    "formula": "C40H80NO8P",
    "smiles": "CCCCCCCCCCCCCCCC(=O)OC[C@H](COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC",
    "category": "Surfactantes anfóteros",
    "description": "Fosfatidilcolina completa com duas cadeias palmitoil e configuração sn definida. Representante molecular específico da classe presente em lecitinas.",
    "tags": [
      "zwitteriônico",
      "DPPC",
      "lecitina",
      "fosfolipídio",
      "bicamada"
    ]
  },
  {
    "id": "rhamnose",
    "name": "α-L-ramnopiranose",
    "formula": "C6H12O5",
    "smiles": "C[C@H]1[C@@H]([C@H]([C@H]([C@@H](O1)O)O)O)O",
    "category": "Orgânicos",
    "description": "Monossacarídeo com estereoquímica α-L definida; unidade de referência de ramnolipídeos.",
    "tags": [
      "carboidrato",
      "ramnose",
      "α-L",
      "referência estrutural"
    ]
  },
  {
    "id": "mono-rhamnolipid-simplified",
    "name": "Monorramnolipídeo Rha-C10-C10 — forma ácida de referência",
    "formula": "C26H48O9",
    "smiles": "CCCCCCCC(CC(=O)O)OC(=O)CC(CCCCCCC)O[C@H]1[C@@H]([C@@H]([C@H]([C@@H](O1)C)O)O)O",
    "category": "Biossurfactantes",
    "description": "Estrutura completa do registro CID 162246, com α-L-ramnose e duas unidades C10. Os dois centros β das caudas permanecem sem configuração R/S especificada, como nesse registro.",
    "tags": [
      "biossurfactante",
      "ramnolipídeo",
      "Rha-C10-C10",
      "estereoquímica parcial"
    ]
  },
  {
    "id": "sophorolipid-simplified",
    "name": "Soforolipídeo ácido diacetilado — referência 9E",
    "formula": "C34H58O15",
    "smiles": "CC(CCCCCC/C=C/CCCCCCCC(=O)O)O[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)COC(=O)C)O)O)O[C@H]2[C@@H]([C@H]([C@@H]([C@H](O2)COC(=O)C)O)O)O",
    "category": "Biossurfactantes",
    "description": "Estrutura completa do CID 11856871: forma ácida diacetilada, dupla 9E e soforose com estereoquímica definida. A configuração R/S de C17 não está especificada; não representa todos os congêneres naturais.",
    "tags": [
      "biossurfactante",
      "soforolipídeo",
      "ácido diacetilado",
      "9E",
      "estereoquímica parcial"
    ]
  },
  {
    "id": "surfactin-fragment",
    "name": "Surfactina C — lipo-heptapeptídeo cíclico completo",
    "formula": "C53H93N7O13",
    "smiles": "CC(C)CCCCCCCCC[C@@H]1CC(=O)N[C@H](C(=O)N[C@H](C(=O)N[C@@H](C(=O)N[C@H](C(=O)N[C@H](C(=O)N[C@@H](C(=O)N[C@H](C(=O)O1)CC(C)C)CC(C)C)CC(=O)O)C(C)C)CC(C)C)CC(C)C)CCC(=O)O",
    "category": "Biossurfactantes",
    "description": "Estrutura completa do CID 443592, com sete resíduos de aminoácidos, lactona de fechamento e cadeia lipídica ramificada; centros estereogênicos definidos.",
    "tags": [
      "biossurfactante",
      "surfactina C",
      "lipopeptídeo",
      "macrociclo",
      "estrutura completa"
    ]
  },
  {
    "id": "pfoa-sodium",
    "name": "PFOA-Na — perfluorooctanoato de sódio",
    "formula": "C8F15NaO2",
    "smiles": "C(F)(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(=O)[O-].[Na+]",
    "category": "Surfactantes fluorados",
    "description": "Perfluorocarboxilato C8 incluído como referência estrutural PFAS.",
    "tags": [
      "fluorado",
      "PFAS",
      "carboxilato"
    ]
  },
  {
    "id": "pfos-potassium",
    "name": "PFOS-K — perfluorooctanossulfonato de potássio",
    "formula": "C8F17KO3S",
    "smiles": "C(F)(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)S(=O)(=O)[O-].[K+]",
    "category": "Surfactantes fluorados",
    "description": "Perfluorossulfonato C8 incluído como referência estrutural PFAS.",
    "tags": [
      "fluorado",
      "PFAS",
      "sulfonato"
    ]
  },
  {
    "id": "fluorotelomer-sulfonate-simplified",
    "name": "4:2 fluorotelômero sulfonato de sódio — modelo simplificado",
    "formula": "C6H4F9NaO3S",
    "smiles": "C(F)(F)(F)C(F)(F)C(F)(F)C(F)(F)CCS(=O)(=O)[O-].[Na+]",
    "category": "Surfactantes fluorados",
    "description": "Modelo 4:2 de fluorotelômero sulfonado.",
    "tags": [
      "fluorado",
      "sulfonato",
      "simplificado"
    ]
  },
  {
    "id": "pdms-fragment",
    "name": "Octametiltrissiloxano (MDM)",
    "formula": "C8H24O2Si3",
    "smiles": "C[Si](C)(O[Si](C)(C)O[Si](C)(C)C)C",
    "category": "Siloxanos de referência",
    "description": "Trissiloxano definido com oito grupos metila. Referência de segmento siloxânico para comparação com silicones e PDMS.",
    "tags": [
      "siloxano",
      "MDM",
      "PDMS",
      "referência estrutural"
    ]
  },
  {
    "id": "silicone-polyether-fragment",
    "name": "Dissiloxano com éter de dietilenoglicol — modelo definido",
    "formula": "C9H24O4Si2",
    "smiles": "C[Si](C)(OCCOCCO)O[Si](C)(C)C",
    "category": "Surfactantes siliconados",
    "description": "Modelo definido de dissiloxano metilado ligado por Si–O–C a um éter de dietilenoglicol; contém dois EO e uma hidroxila terminal.",
    "tags": [
      "silicone poliéter",
      "dissiloxano",
      "EO2",
      "modelo definido"
    ]
  }
];

const categoryOrder: FastMolCategory[] = [
  "Comuns",
  "Solventes",
  "Ácidos e bases",
  "Orgânicos",
  "Cotensoativos",
  "Hidrótropos",
  "Siloxanos de referência",
  "Surfactantes aniônicos",
  "Surfactantes catiônicos",
  "Surfactantes não iônicos",
  "Surfactantes anfóteros",
  "Biossurfactantes",
  "Surfactantes fluorados",
  "Surfactantes siliconados",
];

export function FastMol({ isOpen, onClose, onSelectSmiles }: FastMolProps) {
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<FastMolCategory | "Todos">(
    "Todos"
  );

  const filteredMolecules = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return fastMolecules.filter((molecule) => {
      const matchesCategory =
        activeCategory === "Todos" || molecule.category === activeCategory;

      if (!matchesCategory) return false;

      if (!normalizedQuery) return true;

      return [
        molecule.name,
        molecule.formula,
        molecule.smiles,
        molecule.category,
        molecule.description,
        ...molecule.tags,
      ]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    });
  }, [activeCategory, query]);

  if (!isOpen) return null;

  return (
    <div
      className="fastmol-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Moléculas rápidas"
    >
      <section className="fastmol-window">
        <header className="fastmol-header">
          <div>
            <strong>Moléculas rápidas</strong>
            <span>
              Compostos comuns, séries homólogas e surfactantes de várias
              classes. Clique em uma molécula para renderizar no ambiente 2D via
              SMILES/RDKit.
            </span>
          </div>

          <button
            className="fastmol-close"
            type="button"
            onClick={onClose}
            aria-label="Fechar moléculas rápidas"
          >
            ×
          </button>
        </header>

        <div className="fastmol-controls">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por nome, SMILES, categoria ou tag..."
            aria-label="Buscar molécula rápida"
          />

          <div className="fastmol-category-row">
            <button
              type="button"
              className={activeCategory === "Todos" ? "active" : ""}
              onClick={() => setActiveCategory("Todos")}
            >
              Todos
            </button>

            {categoryOrder.map((category) => (
              <button
                key={category}
                type="button"
                className={activeCategory === category ? "active" : ""}
                onClick={() => setActiveCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        <div className="fastmol-grid">
          {filteredMolecules.map((molecule) => (
            <button
              key={molecule.id}
              className="fastmol-card"
              type="button"
              onClick={() => onSelectSmiles(molecule.smiles, molecule)}
              title={`Carregar ${molecule.name}`}
            >
              <span className="fastmol-category">{molecule.category}</span>

              <strong>{molecule.name}</strong>

              <span className="fastmol-formula">{molecule.formula}</span>

              <code>{molecule.smiles}</code>

              <p>{molecule.description}</p>

              <span className="fastmol-tags">
                {molecule.tags.map((tag) => `#${tag}`).join(" ")}
              </span>
            </button>
          ))}

          {filteredMolecules.length === 0 && (
            <div className="fastmol-empty">
              Nenhuma molécula encontrada para esse filtro.
            </div>
          )}
        </div>

        <footer className="fastmol-footer">
          <span>{filteredMolecules.length} moléculas disponíveis</span>
          <span>
            Homólogos, isômeros de referência e modelos moleculares estão
            identificados em cada cartão.
          </span>
        </footer>
      </section>
    </div>
  );
}

export default FastMol;


