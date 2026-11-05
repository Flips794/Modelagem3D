import { type CSSProperties, useEffect, useMemo, useState } from "react";

import { API_BASE_URL } from "../../../../config/apiBaseUrl";

import "./periodictable.css";

export type PeriodicElement = {
  id: string;
  atomicNumber: number;
  symbol: string;
  name: string;
  atomicMass?: number | null;
  category?: string | null;
  period?: number | null;
  group?: number | null;
  block?: string | null;
  colorHex?: string | null;
  covalentRadiusPm?: number | null;
  vdwRadiusPm?: number | null;
  isOrganicStandard?: boolean;
  isMetal?: boolean;
  isTransitionMetal?: boolean;
  isHalogen?: boolean;
  isNobleGas?: boolean;
  isLanthanide?: boolean;
  isActinide?: boolean;
};

type BackendElement = {
  id?: string | number;

  atomic_number?: number | string;
  atomicNumber?: number | string;
  number?: number | string;

  symbol?: string;
  name?: string;
  name_pt?: string;

  atomic_mass?: number | string | null;
  atomicMass?: number | string | null;
  mass?: number | string | null;

  category?: string | null;
  element_category?: string | null;

  period?: number | string | null;
  group?: number | string | null;
  group_number?: number | string | null;

  block?: string | null;

  color_hex?: string | null;
  colorHex?: string | null;
  color?: string | null;

  covalent_radius_pm?: number | string | null;
  covalentRadiusPm?: number | string | null;

  vdw_radius_pm?: number | string | null;
  vdwRadiusPm?: number | string | null;

  is_organic_standard?: boolean | string | number | null;
  isOrganicStandard?: boolean | string | number | null;

  is_metal?: boolean | string | number | null;
  isMetal?: boolean | string | number | null;

  is_transition_metal?: boolean | string | number | null;
  isTransitionMetal?: boolean | string | number | null;

  is_halogen?: boolean | string | number | null;
  isHalogen?: boolean | string | number | null;

  is_noble_gas?: boolean | string | number | null;
  isNobleGas?: boolean | string | number | null;

  is_lanthanide?: boolean | string | number | null;
  isLanthanide?: boolean | string | number | null;

  is_actinide?: boolean | string | number | null;
  isActinide?: boolean | string | number | null;
};

type BackendElementsPayload =
  | BackendElement[]
  | {
      success?: boolean;
      source?: string;
      count?: number;
      elements?: BackendElement[];
      items?: BackendElement[];
      data?: BackendElement[];
      results?: BackendElement[];
    };

type Props = {
  isOpen: boolean;
  selectedSymbols: string[];
  onSelectElement: (symbol: string, element: PeriodicElement) => void;
  onClose: () => void;
  onClearSelectedElements?: () => void;

  /**
   * Opcional.
   * Se não passar nada, a tabela mostra todos os elementos.
   * Não passe allowedSymbols se quiser a tabela periódica completa.
   */
  allowedSymbols?: string[];

  endpoint?: string;
};

const LOCAL_PERIODIC_ELEMENTS: BackendElement[] = [{"id":"1","atomicNumber":1,"symbol":"H","name":"Hydrogen","atomicMass":1.008,"category":"nonmetal","period":1,"group":1,"block":"s","colorHex":"#FFFFFF"},{"id":"2","atomicNumber":2,"symbol":"He","name":"Helium","atomicMass":4.0026,"category":"noble-gas","period":1,"group":18,"block":"s","colorHex":"#D9FFFF"},{"id":"3","atomicNumber":3,"symbol":"Li","name":"Lithium","atomicMass":6.94,"category":"alkali-metal","period":2,"group":1,"block":"s","colorHex":"#CC80FF"},{"id":"4","atomicNumber":4,"symbol":"Be","name":"Beryllium","atomicMass":9.0122,"category":"alkaline-earth","period":2,"group":2,"block":"s","colorHex":"#C2FF00"},{"id":"5","atomicNumber":5,"symbol":"B","name":"Boron","atomicMass":10.81,"category":"metalloid","period":2,"group":13,"block":"p","colorHex":"#FFB5B5"},{"id":"6","atomicNumber":6,"symbol":"C","name":"Carbon","atomicMass":12.011,"category":"nonmetal","period":2,"group":14,"block":"p","colorHex":"#303030"},{"id":"7","atomicNumber":7,"symbol":"N","name":"Nitrogen","atomicMass":14.007,"category":"nonmetal","period":2,"group":15,"block":"p","colorHex":"#0000F0"},{"id":"8","atomicNumber":8,"symbol":"O","name":"Oxygen","atomicMass":15.999,"category":"nonmetal","period":2,"group":16,"block":"p","colorHex":"#F00000"},{"id":"9","atomicNumber":9,"symbol":"F","name":"Fluorine","atomicMass":18.998,"category":"halogen","period":2,"group":17,"block":"p","colorHex":"#90E050"},{"id":"10","atomicNumber":10,"symbol":"Ne","name":"Neon","atomicMass":20.18,"category":"noble-gas","period":2,"group":18,"block":"p","colorHex":"#B3E3F5"},{"id":"11","atomicNumber":11,"symbol":"Na","name":"Sodium","atomicMass":22.99,"category":"alkali-metal","period":3,"group":1,"block":"s","colorHex":"#AB5CF2"},{"id":"12","atomicNumber":12,"symbol":"Mg","name":"Magnesium","atomicMass":24.305,"category":"alkaline-earth","period":3,"group":2,"block":"s","colorHex":"#8AFF00"},{"id":"13","atomicNumber":13,"symbol":"Al","name":"Aluminum","atomicMass":26.982,"category":"post-transition-metal","period":3,"group":13,"block":"p","colorHex":"#BFA6A6"},{"id":"14","atomicNumber":14,"symbol":"Si","name":"Silicon","atomicMass":28.085,"category":"metalloid","period":3,"group":14,"block":"p","colorHex":"#F0C8A0"},{"id":"15","atomicNumber":15,"symbol":"P","name":"Phosphorus","atomicMass":30.974,"category":"nonmetal","period":3,"group":15,"block":"p","colorHex":"#FFA500"},{"id":"16","atomicNumber":16,"symbol":"S","name":"Sulfur","atomicMass":32.06,"category":"nonmetal","period":3,"group":16,"block":"p","colorHex":"#FFFF00"},{"id":"17","atomicNumber":17,"symbol":"Cl","name":"Chlorine","atomicMass":35.45,"category":"halogen","period":3,"group":17,"block":"p","colorHex":"#00FF00"},{"id":"18","atomicNumber":18,"symbol":"Ar","name":"Argon","atomicMass":39.948,"category":"noble-gas","period":3,"group":18,"block":"p","colorHex":"#80D1E3"},{"id":"19","atomicNumber":19,"symbol":"K","name":"Potassium","atomicMass":39.098,"category":"alkali-metal","period":4,"group":1,"block":"s","colorHex":"#8F40D4"},{"id":"20","atomicNumber":20,"symbol":"Ca","name":"Calcium","atomicMass":40.078,"category":"alkaline-earth","period":4,"group":2,"block":"s","colorHex":"#3DFF00"},{"id":"21","atomicNumber":21,"symbol":"Sc","name":"Scandium","atomicMass":44.956,"category":"transition-metal","period":4,"group":3,"block":"d","colorHex":"#E6E6E6"},{"id":"22","atomicNumber":22,"symbol":"Ti","name":"Titanium","atomicMass":47.867,"category":"transition-metal","period":4,"group":4,"block":"d","colorHex":"#BFC2C7"},{"id":"23","atomicNumber":23,"symbol":"V","name":"Vanadium","atomicMass":50.942,"category":"transition-metal","period":4,"group":5,"block":"d","colorHex":"#A6A6AB"},{"id":"24","atomicNumber":24,"symbol":"Cr","name":"Chromium","atomicMass":51.996,"category":"transition-metal","period":4,"group":6,"block":"d","colorHex":"#8A99C7"},{"id":"25","atomicNumber":25,"symbol":"Mn","name":"Manganese","atomicMass":54.938,"category":"transition-metal","period":4,"group":7,"block":"d","colorHex":"#9C7AC7"},{"id":"26","atomicNumber":26,"symbol":"Fe","name":"Iron","atomicMass":55.845,"category":"transition-metal","period":4,"group":8,"block":"d","colorHex":"#E06633"},{"id":"27","atomicNumber":27,"symbol":"Co","name":"Cobalt","atomicMass":58.933,"category":"transition-metal","period":4,"group":9,"block":"d","colorHex":"#F090A0"},{"id":"28","atomicNumber":28,"symbol":"Ni","name":"Nickel","atomicMass":58.693,"category":"transition-metal","period":4,"group":10,"block":"d","colorHex":"#50D050"},{"id":"29","atomicNumber":29,"symbol":"Cu","name":"Copper","atomicMass":63.546,"category":"transition-metal","period":4,"group":11,"block":"d","colorHex":"#C88033"},{"id":"30","atomicNumber":30,"symbol":"Zn","name":"Zinc","atomicMass":65.38,"category":"transition-metal","period":4,"group":12,"block":"d","colorHex":"#7D80B0"},{"id":"31","atomicNumber":31,"symbol":"Ga","name":"Gallium","atomicMass":69.723,"category":"post-transition-metal","period":4,"group":13,"block":"p","colorHex":"#C28F8F"},{"id":"32","atomicNumber":32,"symbol":"Ge","name":"Germanium","atomicMass":72.63,"category":"metalloid","period":4,"group":14,"block":"p","colorHex":"#668F8F"},{"id":"33","atomicNumber":33,"symbol":"As","name":"Arsenic","atomicMass":74.922,"category":"metalloid","period":4,"group":15,"block":"p","colorHex":"#BD80E3"},{"id":"34","atomicNumber":34,"symbol":"Se","name":"Selenium","atomicMass":78.971,"category":"nonmetal","period":4,"group":16,"block":"p","colorHex":"#FFA100"},{"id":"35","atomicNumber":35,"symbol":"Br","name":"Bromine","atomicMass":79.904,"category":"halogen","period":4,"group":17,"block":"p","colorHex":"#A52A2A"},{"id":"36","atomicNumber":36,"symbol":"Kr","name":"Krypton","atomicMass":83.798,"category":"noble-gas","period":4,"group":18,"block":"p","colorHex":"#5CB8D1"},{"id":"37","atomicNumber":37,"symbol":"Rb","name":"Rubidium","atomicMass":85.468,"category":"alkali-metal","period":5,"group":1,"block":"s","colorHex":"#702EB0"},{"id":"38","atomicNumber":38,"symbol":"Sr","name":"Strontium","atomicMass":87.62,"category":"alkaline-earth","period":5,"group":2,"block":"s","colorHex":"#00FF00"},{"id":"39","atomicNumber":39,"symbol":"Y","name":"Yttrium","atomicMass":88.906,"category":"transition-metal","period":5,"group":3,"block":"d","colorHex":"#94FFFF"},{"id":"40","atomicNumber":40,"symbol":"Zr","name":"Zirconium","atomicMass":91.224,"category":"transition-metal","period":5,"group":4,"block":"d","colorHex":"#94E0E0"},{"id":"41","atomicNumber":41,"symbol":"Nb","name":"Niobium","atomicMass":92.906,"category":"transition-metal","period":5,"group":5,"block":"d","colorHex":"#73C2C9"},{"id":"42","atomicNumber":42,"symbol":"Mo","name":"Molybdenum","atomicMass":95.95,"category":"transition-metal","period":5,"group":6,"block":"d","colorHex":"#54B5B5"},{"id":"43","atomicNumber":43,"symbol":"Tc","name":"Technetium","atomicMass":98.0,"category":"transition-metal","period":5,"group":7,"block":"d","colorHex":"#3B9E9E"},{"id":"44","atomicNumber":44,"symbol":"Ru","name":"Ruthenium","atomicMass":101.07,"category":"transition-metal","period":5,"group":8,"block":"d","colorHex":"#248F8F"},{"id":"45","atomicNumber":45,"symbol":"Rh","name":"Rhodium","atomicMass":102.906,"category":"transition-metal","period":5,"group":9,"block":"d","colorHex":"#0A7D8C"},{"id":"46","atomicNumber":46,"symbol":"Pd","name":"Palladium","atomicMass":106.42,"category":"transition-metal","period":5,"group":10,"block":"d","colorHex":"#006985"},{"id":"47","atomicNumber":47,"symbol":"Ag","name":"Silver","atomicMass":107.868,"category":"transition-metal","period":5,"group":11,"block":"d","colorHex":"#C0C0C0"},{"id":"48","atomicNumber":48,"symbol":"Cd","name":"Cadmium","atomicMass":112.414,"category":"transition-metal","period":5,"group":12,"block":"d","colorHex":"#FFD98F"},{"id":"49","atomicNumber":49,"symbol":"In","name":"Indium","atomicMass":114.818,"category":"post-transition-metal","period":5,"group":13,"block":"p","colorHex":"#A67573"},{"id":"50","atomicNumber":50,"symbol":"Sn","name":"Tin","atomicMass":118.71,"category":"post-transition-metal","period":5,"group":14,"block":"p","colorHex":"#668080"},{"id":"51","atomicNumber":51,"symbol":"Sb","name":"Antimony","atomicMass":121.76,"category":"metalloid","period":5,"group":15,"block":"p","colorHex":"#9E63B5"},{"id":"52","atomicNumber":52,"symbol":"Te","name":"Tellurium","atomicMass":127.6,"category":"metalloid","period":5,"group":16,"block":"p","colorHex":"#D47A00"},{"id":"53","atomicNumber":53,"symbol":"I","name":"Iodine","atomicMass":126.9,"category":"halogen","period":5,"group":17,"block":"p","colorHex":"#9400D3"},{"id":"54","atomicNumber":54,"symbol":"Xe","name":"Xenon","atomicMass":131.293,"category":"noble-gas","period":5,"group":18,"block":"p","colorHex":"#429EB0"},{"id":"55","atomicNumber":55,"symbol":"Cs","name":"Cesium","atomicMass":132.905,"category":"alkali-metal","period":6,"group":1,"block":"s","colorHex":"#57178F"},{"id":"56","atomicNumber":56,"symbol":"Ba","name":"Barium","atomicMass":137.327,"category":"alkaline-earth","period":6,"group":2,"block":"s","colorHex":"#00C900"},{"id":"57","atomicNumber":57,"symbol":"La","name":"Lanthanum","atomicMass":138.905,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#70D4FF"},{"id":"58","atomicNumber":58,"symbol":"Ce","name":"Cerium","atomicMass":140.116,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#FFFFC7"},{"id":"59","atomicNumber":59,"symbol":"Pr","name":"Praseodymium","atomicMass":140.908,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#D9FFC7"},{"id":"60","atomicNumber":60,"symbol":"Nd","name":"Neodymium","atomicMass":144.242,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#C7FFC7"},{"id":"61","atomicNumber":61,"symbol":"Pm","name":"Promethium","atomicMass":145.0,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#A3FFC7"},{"id":"62","atomicNumber":62,"symbol":"Sm","name":"Samarium","atomicMass":150.36,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#8FFFC7"},{"id":"63","atomicNumber":63,"symbol":"Eu","name":"Europium","atomicMass":151.964,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#61FFC7"},{"id":"64","atomicNumber":64,"symbol":"Gd","name":"Gadolinium","atomicMass":157.25,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#45FFC7"},{"id":"65","atomicNumber":65,"symbol":"Tb","name":"Terbium","atomicMass":158.925,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#30FFC7"},{"id":"66","atomicNumber":66,"symbol":"Dy","name":"Dysprosium","atomicMass":162.5,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#1FFFC7"},{"id":"67","atomicNumber":67,"symbol":"Ho","name":"Holmium","atomicMass":164.93,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#00FF9C"},{"id":"68","atomicNumber":68,"symbol":"Er","name":"Erbium","atomicMass":167.259,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#00E675"},{"id":"69","atomicNumber":69,"symbol":"Tm","name":"Thulium","atomicMass":168.934,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#00D452"},{"id":"70","atomicNumber":70,"symbol":"Yb","name":"Ytterbium","atomicMass":173.045,"category":"lanthanide","period":6,"group":null,"block":"f","colorHex":"#00BF38"},{"id":"71","atomicNumber":71,"symbol":"Lu","name":"Lutetium","atomicMass":174.967,"category":"lanthanide","period":6,"group":3,"block":"d","colorHex":"#00AB24"},{"id":"72","atomicNumber":72,"symbol":"Hf","name":"Hafnium","atomicMass":178.49,"category":"transition-metal","period":6,"group":4,"block":"d","colorHex":"#4DC2FF"},{"id":"73","atomicNumber":73,"symbol":"Ta","name":"Tantalum","atomicMass":180.948,"category":"transition-metal","period":6,"group":5,"block":"d","colorHex":"#4DA6FF"},{"id":"74","atomicNumber":74,"symbol":"W","name":"Tungsten","atomicMass":183.84,"category":"transition-metal","period":6,"group":6,"block":"d","colorHex":"#2194D6"},{"id":"75","atomicNumber":75,"symbol":"Re","name":"Rhenium","atomicMass":186.207,"category":"transition-metal","period":6,"group":7,"block":"d","colorHex":"#267DAB"},{"id":"76","atomicNumber":76,"symbol":"Os","name":"Osmium","atomicMass":190.23,"category":"transition-metal","period":6,"group":8,"block":"d","colorHex":"#266696"},{"id":"77","atomicNumber":77,"symbol":"Ir","name":"Iridium","atomicMass":192.217,"category":"transition-metal","period":6,"group":9,"block":"d","colorHex":"#175487"},{"id":"78","atomicNumber":78,"symbol":"Pt","name":"Platinum","atomicMass":195.084,"category":"transition-metal","period":6,"group":10,"block":"d","colorHex":"#D0D0E0"},{"id":"79","atomicNumber":79,"symbol":"Au","name":"Gold","atomicMass":196.967,"category":"transition-metal","period":6,"group":11,"block":"d","colorHex":"#FFD123"},{"id":"80","atomicNumber":80,"symbol":"Hg","name":"Mercury","atomicMass":200.592,"category":"transition-metal","period":6,"group":12,"block":"d","colorHex":"#B8B8D0"},{"id":"81","atomicNumber":81,"symbol":"Tl","name":"Thallium","atomicMass":204.38,"category":"post-transition-metal","period":6,"group":13,"block":"p","colorHex":"#A6544D"},{"id":"82","atomicNumber":82,"symbol":"Pb","name":"Lead","atomicMass":207.2,"category":"post-transition-metal","period":6,"group":14,"block":"p","colorHex":"#575961"},{"id":"83","atomicNumber":83,"symbol":"Bi","name":"Bismuth","atomicMass":208.98,"category":"post-transition-metal","period":6,"group":15,"block":"p","colorHex":"#9E4FB5"},{"id":"84","atomicNumber":84,"symbol":"Po","name":"Polonium","atomicMass":209.0,"category":"metalloid","period":6,"group":16,"block":"p","colorHex":"#AB5C00"},{"id":"85","atomicNumber":85,"symbol":"At","name":"Astatine","atomicMass":210.0,"category":"halogen","period":6,"group":17,"block":"p","colorHex":"#754F45"},{"id":"86","atomicNumber":86,"symbol":"Rn","name":"Radon","atomicMass":222.0,"category":"noble-gas","period":6,"group":18,"block":"p","colorHex":"#428296"},{"id":"87","atomicNumber":87,"symbol":"Fr","name":"Francium","atomicMass":223.0,"category":"alkali-metal","period":7,"group":1,"block":"s","colorHex":"#420066"},{"id":"88","atomicNumber":88,"symbol":"Ra","name":"Radium","atomicMass":226.0,"category":"alkaline-earth","period":7,"group":2,"block":"s","colorHex":"#007D00"},{"id":"89","atomicNumber":89,"symbol":"Ac","name":"Actinium","atomicMass":227.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#70ABFA"},{"id":"90","atomicNumber":90,"symbol":"Th","name":"Thorium","atomicMass":232.038,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#00BAFF"},{"id":"91","atomicNumber":91,"symbol":"Pa","name":"Protactinium","atomicMass":231.036,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#00A1FF"},{"id":"92","atomicNumber":92,"symbol":"U","name":"Uranium","atomicMass":238.029,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#008FFF"},{"id":"93","atomicNumber":93,"symbol":"Np","name":"Neptunium","atomicMass":237.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#0080FF"},{"id":"94","atomicNumber":94,"symbol":"Pu","name":"Plutonium","atomicMass":244.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#006BFF"},{"id":"95","atomicNumber":95,"symbol":"Am","name":"Americium","atomicMass":243.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#545CF2"},{"id":"96","atomicNumber":96,"symbol":"Cm","name":"Curium","atomicMass":247.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#785CE3"},{"id":"97","atomicNumber":97,"symbol":"Bk","name":"Berkelium","atomicMass":247.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#8A4FE3"},{"id":"98","atomicNumber":98,"symbol":"Cf","name":"Californium","atomicMass":251.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#A136D4"},{"id":"99","atomicNumber":99,"symbol":"Es","name":"Einsteinium","atomicMass":252.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#B31FD4"},{"id":"100","atomicNumber":100,"symbol":"Fm","name":"Fermium","atomicMass":257.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#B31FBA"},{"id":"101","atomicNumber":101,"symbol":"Md","name":"Mendelevium","atomicMass":258.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#B30DA6"},{"id":"102","atomicNumber":102,"symbol":"No","name":"Nobelium","atomicMass":259.0,"category":"actinide","period":7,"group":null,"block":"f","colorHex":"#BD0D87"},{"id":"103","atomicNumber":103,"symbol":"Lr","name":"Lawrencium","atomicMass":266.0,"category":"actinide","period":7,"group":3,"block":"d","colorHex":"#C70066"},{"id":"104","atomicNumber":104,"symbol":"Rf","name":"Rutherfordium","atomicMass":267.0,"category":"transition-metal","period":7,"group":4,"block":"d","colorHex":"#CC0059"},{"id":"105","atomicNumber":105,"symbol":"Db","name":"Dubnium","atomicMass":268.0,"category":"transition-metal","period":7,"group":5,"block":"d","colorHex":"#D1004F"},{"id":"106","atomicNumber":106,"symbol":"Sg","name":"Seaborgium","atomicMass":269.0,"category":"transition-metal","period":7,"group":6,"block":"d","colorHex":"#D90045"},{"id":"107","atomicNumber":107,"symbol":"Bh","name":"Bohrium","atomicMass":270.0,"category":"transition-metal","period":7,"group":7,"block":"d","colorHex":"#E00038"},{"id":"108","atomicNumber":108,"symbol":"Hs","name":"Hassium","atomicMass":277.0,"category":"transition-metal","period":7,"group":8,"block":"d","colorHex":"#E6002E"},{"id":"109","atomicNumber":109,"symbol":"Mt","name":"Meitnerium","atomicMass":278.0,"category":"transition-metal","period":7,"group":9,"block":"d","colorHex":"#EB0026"},{"id":"110","atomicNumber":110,"symbol":"Ds","name":"Darmstadtium","atomicMass":281.0,"category":"transition-metal","period":7,"group":10,"block":"d","colorHex":"#F00026"},{"id":"111","atomicNumber":111,"symbol":"Rg","name":"Roentgenium","atomicMass":282.0,"category":"transition-metal","period":7,"group":11,"block":"d","colorHex":"#F50026"},{"id":"112","atomicNumber":112,"symbol":"Cn","name":"Copernicium","atomicMass":285.0,"category":"transition-metal","period":7,"group":12,"block":"d","colorHex":"#F80026"},{"id":"113","atomicNumber":113,"symbol":"Nh","name":"Nihonium","atomicMass":286.0,"category":"post-transition-metal","period":7,"group":13,"block":"p","colorHex":"#FA0030"},{"id":"114","atomicNumber":114,"symbol":"Fl","name":"Flerovium","atomicMass":289.0,"category":"post-transition-metal","period":7,"group":14,"block":"p","colorHex":"#FB0038"},{"id":"115","atomicNumber":115,"symbol":"Mc","name":"Moscovium","atomicMass":290.0,"category":"post-transition-metal","period":7,"group":15,"block":"p","colorHex":"#FC0040"},{"id":"116","atomicNumber":116,"symbol":"Lv","name":"Livermorium","atomicMass":293.0,"category":"post-transition-metal","period":7,"group":16,"block":"p","colorHex":"#FD0048"},{"id":"117","atomicNumber":117,"symbol":"Ts","name":"Tennessine","atomicMass":294.0,"category":"halogen","period":7,"group":17,"block":"p","colorHex":"#FE0050"},{"id":"118","atomicNumber":118,"symbol":"Og","name":"Oganesson","atomicMass":294.0,"category":"noble-gas","period":7,"group":18,"block":"p","colorHex":"#FF0058"}];

const SERIES_PLACEHOLDERS = [
  {
    id: "lanthanide-placeholder",
    label: "57–71",
    title: "Lantanídeos",
    gridColumn: 3,
    gridRow: 6,
  },
  {
    id: "actinide-placeholder",
    label: "89–103",
    title: "Actinídeos",
    gridColumn: 3,
    gridRow: 7,
  },
];

const SERIES_LABELS = [
  {
    id: "lanthanide-label",
    label: "Lantanídeos",
    gridColumn: "2 / span 2",
    gridRow: 8,
  },
  {
    id: "actinide-label",
    label: "Actinídeos",
    gridColumn: "2 / span 2",
    gridRow: 9,
  },
];

const POLYATOMIC_NONMETALS = new Set(["C", "P", "S", "Se"]);
const DIATOMIC_NONMETALS = new Set(["H", "N", "O", "F", "Cl", "Br", "I"]);
const UNKNOWN_CHEMICAL_PROPERTIES = new Set([
  "Mt",
  "Ds",
  "Rg",
  "Cn",
  "Nh",
  "Fl",
  "Mc",
  "Lv",
  "Ts",
  "Og",
]);

const CLASSIFICATION_LEGEND = [
  { id: "alkali-metals", label: "Metais alcalinos" },
  { id: "alkaline-earth-metals", label: "Metais alcalinoterrosos" },
  { id: "transition-metals", label: "Metais de transição" },
  { id: "post-transition-metals", label: "Metais pós-transição" },
  { id: "metalloids", label: "Semimetais" },
  { id: "polyatomic-nonmetals", label: "Não metais poliatômicos" },
  { id: "diatomic-nonmetals", label: "Não metais diatômicos" },
  { id: "noble-gases", label: "Gases nobres" },
  {
    id: "unknown-chemical-properties",
    label: "Propriedades químicas desconhecidas",
  },
  { id: "lanthanides", label: "Lantanídeos" },
  { id: "actinides", label: "Actinídeos" },
];

function normalizeClassificationText(value?: string | null) {
  if (!value) return "";

  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/_/g, "-")
    .replace(/\s+/g, "-");
}

function getElementClassification(element: PeriodicElement) {
  const symbol = normalizeSymbol(element.symbol);
  const category = normalizeClassificationText(element.category);

  if (element.isLanthanide || category === "lanthanide") {
    return "lanthanides";
  }

  if (element.isActinide || category === "actinide") {
    return "actinides";
  }

  if (UNKNOWN_CHEMICAL_PROPERTIES.has(symbol) || category === "unknown") {
    return "unknown-chemical-properties";
  }

  if (category === "alkali-metal" || category === "alkali-metals") {
    return "alkali-metals";
  }

  if (
    category === "alkaline-earth" ||
    category === "alkaline-earth-metal" ||
    category === "alkaline-earth-metals"
  ) {
    return "alkaline-earth-metals";
  }

  if (category === "transition-metal" || category === "transition-metals") {
    return "transition-metals";
  }

  if (
    category === "post-transition-metal" ||
    category === "post-transition-metals"
  ) {
    return "post-transition-metals";
  }

  if (category === "metalloid" || category === "semimetal") {
    return "metalloids";
  }

  if (category === "noble-gas" || category === "noble-gases") {
    return "noble-gases";
  }

  if (DIATOMIC_NONMETALS.has(symbol) || category === "halogen") {
    return "diatomic-nonmetals";
  }

  if (POLYATOMIC_NONMETALS.has(symbol) || category === "nonmetal") {
    return "polyatomic-nonmetals";
  }

  return "unknown-chemical-properties";
}


function getApiBaseUrl() {
  return API_BASE_URL;
}

function getDefaultEndpoint() {
  return `${getApiBaseUrl()}/reference-data/elements`;
}

function getFallbackEndpoints(endpoint: string) {
  const baseUrl = getApiBaseUrl();

  return Array.from(
    new Set([
      endpoint,
      `${baseUrl}/reference-data/elements`,
      `${baseUrl}/chemical-parameters/elements`,
      `${baseUrl}/reference-data/elements/raw`,
      `${baseUrl}/chemical-parameters/elements/raw`,
    ])
  );
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;

  const parsed = Number(String(value).replace(",", "."));

  return Number.isFinite(parsed) ? parsed : null;
}

function toBoolean(value: unknown): boolean {
  if (typeof value === "boolean") return value;

  if (typeof value === "number") return value !== 0;

  if (typeof value === "string") {
    return ["true", "1", "yes", "sim"].includes(value.trim().toLowerCase());
  }

  return false;
}

function normalizeSymbol(value: string) {
  const trimmed = value.trim();

  if (!trimmed) return "";

  if (trimmed.length === 1) return trimmed.toUpperCase();

  return `${trimmed.charAt(0).toUpperCase()}${trimmed
    .slice(1)
    .toLowerCase()}`;
}

function normalizeHexColor(value: unknown): string | null {
  if (typeof value !== "string") return null;

  const trimmed = value.trim();

  if (!trimmed) return null;

  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) return trimmed.toUpperCase();

  if (/^[0-9a-fA-F]{6}$/.test(trimmed)) return `#${trimmed.toUpperCase()}`;

  return null;
}

function normalizeElement(item: BackendElement): PeriodicElement | null {
  const atomicNumber = toNumber(
    item.atomicNumber ?? item.atomic_number ?? item.number
  );

  const symbol = normalizeSymbol(String(item.symbol ?? ""));
  const name = String(item.name ?? item.name_pt ?? item.symbol ?? "").trim();

  if (!atomicNumber || !symbol || !name) {
    return null;
  }

  const atomicMass = toNumber(item.atomicMass ?? item.atomic_mass ?? item.mass);
  const group = toNumber(item.group ?? item.group_number);
  const period = toNumber(item.period);

  return {
    id: String(item.id ?? atomicNumber),
    atomicNumber,
    symbol,
    name,
    atomicMass,
    category: item.category ?? item.element_category ?? null,
    period,
    group,
    block: item.block ?? null,
    colorHex: normalizeHexColor(item.colorHex ?? item.color_hex ?? item.color),
    covalentRadiusPm: toNumber(
      item.covalentRadiusPm ?? item.covalent_radius_pm
    ),
    vdwRadiusPm: toNumber(item.vdwRadiusPm ?? item.vdw_radius_pm),
    isOrganicStandard: toBoolean(
      item.isOrganicStandard ?? item.is_organic_standard
    ),
    isMetal: toBoolean(item.isMetal ?? item.is_metal),
    isTransitionMetal: toBoolean(
      item.isTransitionMetal ?? item.is_transition_metal
    ),
    isHalogen: toBoolean(item.isHalogen ?? item.is_halogen),
    isNobleGas: toBoolean(item.isNobleGas ?? item.is_noble_gas),
    isLanthanide:
      toBoolean(item.isLanthanide ?? item.is_lanthanide) ||
      (atomicNumber >= 57 && atomicNumber <= 71),
    isActinide:
      toBoolean(item.isActinide ?? item.is_actinide) ||
      (atomicNumber >= 89 && atomicNumber <= 103),
  };
}

function extractRawElements(payload: BackendElementsPayload): BackendElement[] {
  if (Array.isArray(payload)) return payload;

  return (
    payload.elements ??
    payload.items ??
    payload.data ??
    payload.results ??
    []
  );
}

function getPeriodicPosition(element: PeriodicElement): CSSProperties {
  if (element.atomicNumber >= 57 && element.atomicNumber <= 71) {
    return {
      gridColumn: String(element.atomicNumber - 53),
      gridRow: "8",
    };
  }

  if (element.atomicNumber >= 89 && element.atomicNumber <= 103) {
    return {
      gridColumn: String(element.atomicNumber - 85),
      gridRow: "9",
    };
  }

  return {
    gridColumn: String(element.group ?? 1),
    gridRow: String(element.period ?? 1),
  };
}

function getCategoryClass(category?: string | null) {
  if (!category) return "unknown";

  return category
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/_/g, "-")
    .replace(/\s+/g, "-");
}

function getTextColor(background?: string | null) {
  if (!background || !background.startsWith("#")) return undefined;

  const hex = background.replace("#", "");

  if (hex.length !== 6) return undefined;

  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  return luminance > 0.58 ? "#020617" : "#f8fafc";
}

function sortElements(elements: PeriodicElement[]) {
  return [...elements].sort((a, b) => a.atomicNumber - b.atomicNumber);
}

function formatValue(value: string | number | null | undefined, unit = "") {
  if (value === null || value === undefined || value === "") return "—";

  return `${value}${unit}`;
}

async function fetchJson(endpoint: string) {
  const response = await fetch(endpoint, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`${endpoint} retornou HTTP ${response.status}`);
  }

  return response.json() as Promise<BackendElementsPayload>;
}

function makeMissingSelectedElement(symbol: string): PeriodicElement {
  return {
    id: `selected-${symbol}`,
    atomicNumber: 0,
    symbol,
    name: "Elemento selecionado",
    atomicMass: null,
    category: null,
    period: null,
    group: null,
    block: null,
    colorHex: null,
  };
}

export function PeriodicTable({
  isOpen,
  selectedSymbols,
  onSelectElement,
  onClose,
  onClearSelectedElements,
  allowedSymbols,
  endpoint = getDefaultEndpoint(),
}: Props) {
  const [elements, setElements] = useState<PeriodicElement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState("");
  const [inspectedSymbol, setInspectedSymbol] = useState<string | null>(null);

  const selectedSet = useMemo(
    () => new Set(selectedSymbols.map(normalizeSymbol)),
    [selectedSymbols]
  );

  const allowedSet = useMemo(() => {
    if (!allowedSymbols || allowedSymbols.length === 0) return null;

    return new Set(allowedSymbols.map(normalizeSymbol));
  }, [allowedSymbols]);

  const elementBySymbol = useMemo(() => {
    const map = new Map<string, PeriodicElement>();

    elements.forEach((element) => {
      map.set(normalizeSymbol(element.symbol), element);
    });

    return map;
  }, [elements]);

  const selectedElements = useMemo(() => {
    return selectedSymbols
      .map(normalizeSymbol)
      .filter(Boolean)
      .map((symbol) => elementBySymbol.get(symbol) ?? makeMissingSelectedElement(symbol));
  }, [elementBySymbol, selectedSymbols]);

  const visibleElements = useMemo(() => {
    if (!allowedSet) return elements;

    return elements.filter((element) => allowedSet.has(element.symbol));
  }, [allowedSet, elements]);

  const inspectedElement = useMemo(() => {
    if (inspectedSymbol) {
      const inspected = elementBySymbol.get(normalizeSymbol(inspectedSymbol));

      if (inspected) return inspected;
    }

    if (selectedElements.length > 0) {
      return selectedElements[selectedElements.length - 1];
    }

    return visibleElements[0] ?? null;
  }, [elementBySymbol, inspectedSymbol, selectedElements, visibleElements]);

  useEffect(() => {
    if (!isOpen) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;

    let active = true;

    async function loadElements() {
      setLoading(true);
      setError("");

      const errors: string[] = [];

      for (const currentEndpoint of getFallbackEndpoints(endpoint)) {
        try {
          const payload = await fetchJson(currentEndpoint);
          const rawElements = extractRawElements(payload);

          const normalized = rawElements
            .map(normalizeElement)
            .filter((item): item is PeriodicElement => Boolean(item));

          if (normalized.length < 100) {
            throw new Error(
              `${currentEndpoint} retornou apenas ${normalized.length} elemento(s).`
            );
          }

          if (!active) return;

          setElements(sortElements(normalized));
          setSource(currentEndpoint);
          setError("");
          setLoading(false);
          return;
        } catch (loadError) {
          errors.push(
            loadError instanceof Error
              ? loadError.message
              : String(loadError)
          );
        }
      }

      const fallbackElements = LOCAL_PERIODIC_ELEMENTS
        .map(normalizeElement)
        .filter((item): item is PeriodicElement => Boolean(item));

      if (!active) return;

      setElements(sortElements(fallbackElements));
      setSource("fallback_local_frontend");
      setError(
        `Backend indisponível ou incompleto. Usando fallback local com ${fallbackElements.length} elementos. ${errors.join(
          " | "
        )}`
      );
      setLoading(false);
    }

    void loadElements();

    return () => {
      active = false;
    };
  }, [endpoint, isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="periodic-table-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Tabela periódica"
    >
      <section className="periodic-table-window">
        <header className="periodic-table-header">
          <div>
            <strong>Tabela periódica completa</strong>
            <span>
              118 elementos · clique para adicionar à barra de átomos.
            </span>
          </div>

          <button
            className="periodic-table-close"
            type="button"
            onClick={onClose}
            aria-label="Fechar tabela periódica"
          >
            ×
          </button>
        </header>

        {loading && (
          <div className="periodic-table-state">Carregando elementos...</div>
        )}

        {!loading && error && (
          <div className="periodic-table-warning">
            <strong>Aviso</strong>
            <span>{error}</span>
          </div>
        )}

        {!loading && visibleElements.length > 0 && (
          <div
            className="periodic-classification-legend"
            aria-label="Legenda das classificações químicas"
          >
            {CLASSIFICATION_LEGEND.map((item) => (
              <div
                key={item.id}
                className={`periodic-classification-item periodic-class-${item.id}`}
              >
                <span className="periodic-classification-dot" />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        )}

        <div className="periodic-table-body">
          <aside className="periodic-selected-panel">
            <div className="periodic-panel-title">
              <strong>Barra de elementos</strong>
              <span>
                {selectedElements.length} selecionado
                {selectedElements.length === 1 ? "" : "s"}
              </span>
            </div>

            <div className="periodic-selected-list">
              {selectedElements.length === 0 && (
                <div className="periodic-empty-selection">
                  Nenhum elemento adicionado ainda.
                </div>
              )}

              {selectedElements.map((element) => {
                const textColor = getTextColor(element.colorHex);

                return (
                  <button
                    key={element.symbol}
                    type="button"
                    className="periodic-selected-chip"
                    style={{
                      background: element.colorHex ?? undefined,
                      color: textColor,
                    }}
                    onClick={() => onSelectElement(element.symbol, element)}
                    onMouseEnter={() => setInspectedSymbol(element.symbol)}
                    onFocus={() => setInspectedSymbol(element.symbol)}
                  >
                    <span>{element.symbol}</span>
                    <small>{element.name}</small>
                  </button>
                );
              })}
            </div>

            <div className="periodic-info-card">
              <div className="periodic-info-card-header">
                <strong>{inspectedElement?.symbol ?? "—"}</strong>
                <span>{inspectedElement?.name ?? "Passe o mouse em um elemento"}</span>
              </div>

              <dl>
                <div>
                  <dt>Nº atômico</dt>
                  <dd>{formatValue(inspectedElement?.atomicNumber || null)}</dd>
                </div>
                <div>
                  <dt>Massa</dt>
                  <dd>{formatValue(inspectedElement?.atomicMass, " u")}</dd>
                </div>
                <div>
                  <dt>Categoria</dt>
                  <dd>{formatValue(inspectedElement?.category)}</dd>
                </div>
                <div>
                  <dt>Período</dt>
                  <dd>{formatValue(inspectedElement?.period)}</dd>
                </div>
                <div>
                  <dt>Grupo</dt>
                  <dd>{formatValue(inspectedElement?.group)}</dd>
                </div>
                <div>
                  <dt>Bloco</dt>
                  <dd>{formatValue(inspectedElement?.block)}</dd>
                </div>
                <div>
                  <dt>Raio covalente</dt>
                  <dd>{formatValue(inspectedElement?.covalentRadiusPm, " pm")}</dd>
                </div>
                <div>
                  <dt>Raio vdW</dt>
                  <dd>{formatValue(inspectedElement?.vdwRadiusPm, " pm")}</dd>
                </div>
                <div>
                  <dt>Cor</dt>
                  <dd>{formatValue(inspectedElement?.colorHex)}</dd>
                </div>
              </dl>
            </div>
          </aside>

          <section className="periodic-table-main">
            {!loading && visibleElements.length === 0 && (
              <div className="periodic-table-error">
                <strong>Nenhum elemento disponível.</strong>
                <span>
                  Verifique se /api/v1/reference-data/elements está retornando
                  elements, items, data ou array direto.
                </span>
              </div>
            )}

            {!loading && visibleElements.length > 0 && (
              <div className="periodic-table-grid">
                {SERIES_PLACEHOLDERS.map((placeholder) => (
                  <div
                    key={placeholder.id}
                    className="periodic-series-placeholder"
                    style={{
                      gridColumn: placeholder.gridColumn,
                      gridRow: placeholder.gridRow,
                    }}
                    title={placeholder.title}
                  >
                    <strong>{placeholder.label}</strong>
                    <span>{placeholder.title}</span>
                  </div>
                ))}

                {SERIES_LABELS.map((label) => (
                  <div
                    key={label.id}
                    className="periodic-series-label"
                    style={{
                      gridColumn: label.gridColumn,
                      gridRow: label.gridRow,
                    }}
                  >
                    {label.label}
                  </div>
                ))}

                {visibleElements.map((element) => {
                  const selected = selectedSet.has(element.symbol);
                  const textColor = getTextColor(element.colorHex);
                  const classification = getElementClassification(element);

                  return (
                    <button
                      key={element.id ?? element.symbol}
                      className={`periodic-element ${getCategoryClass(
                        element.category
                      )} periodic-class-${classification} ${
                        selected ? "selected" : ""
                      }`}
                      type="button"
                      style={{
                        ...getPeriodicPosition(element),
                        background: element.colorHex ?? undefined,
                        color: textColor,
                      }}
                      onClick={() => onSelectElement(element.symbol, element)}
                      onMouseEnter={() => setInspectedSymbol(element.symbol)}
                      onFocus={() => setInspectedSymbol(element.symbol)}
                      title={`${element.atomicNumber} · ${element.name} (${element.symbol}) · massa: ${formatValue(
                        element.atomicMass,
                        " u"
                      )} · período: ${formatValue(
                        element.period
                      )} · grupo: ${formatValue(element.group)}`}
                    >
                      <span className="periodic-atomic-number">
                        {element.atomicNumber}
                      </span>
                      <strong>{element.symbol}</strong>
                      <span className="periodic-name">{element.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        <footer className="periodic-table-footer">
          <span>
            {visibleElements.length} elementos disponíveis · fonte: {source || "—"}
          </span>

          <button
            className="periodic-clear-button"
            type="button"
            onClick={onClearSelectedElements}
            disabled={!onClearSelectedElements || selectedSymbols.length === 0}
          >
            Apagar barra de elementos
          </button>
        </footer>
      </section>
    </div>
  );
}

export default PeriodicTable;


