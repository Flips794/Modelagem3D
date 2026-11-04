import type {
  InternalMoleculeModel,
  SelectedMoleculeTarget,
} from "../../2dpage/type/rdkit2d.types";

export type ParameterValue<T = unknown> = {
  value: T | null;
  unit: string | null;
  source: string;
  available: boolean;
  confidence?: "high" | "medium" | "low" | "estimated" | "proxy" | string;
  note?: string | null;
};

export type AtomInteraction = {
  atomo_alvo_idx: number;
  elemento_alvo: string;
  distancia_angstrom: number;
  carga_origem?: number | null;
  carga_alvo?: number | null;
  energia_coulomb_kcal_mol: number | null;
  forca_coulomb_aproximada: number | null;
  energia_vdw_kcal_mol: number | null;
  forca_vdw_aproximada: number | null;
  energia_total_kcal_mol: number;
  tipo_interacao: "atração" | "repulsão" | "quase_neutra" | string;
  mesmo_fragmento?: boolean;
  ligacao_direta?: boolean;
  coordinate_source?: string;
};

export type AtomParameterData = {
  id_interno: string | null;
  rdkit_idx: number;
  elemento: string;
  numero_atomico: number;
  massa_exata: ParameterValue<number>;
  is_isotopo: boolean;

  grau_ligacao_explicito: number;
  ordem_ligacao_total?: ParameterValue<number>;
  valencia_total: ParameterValue<number>;
  hidrogenios_totais?: number;
  hidrogenios_implicitos: number;
  hidrogenios_explicitos: number;
  carga_formal: number;
  carga_gasteiger?: ParameterValue<number>;
  carga_quantica_ou_proxy?: ParameterValue<number>;
  eletrons_radicais: number;
  pares_livres: ParameterValue<number>;
  hibridizacao?: string;
  hibridizacao_rdkit?: string;
  hibridizacao_estimativa: ParameterValue<{
    rdkit?: string;
    estimada?: string;
    dominios_eletronicos?: number;
    grau_sigma_aproximado?: number;
    pares_livres_estimados?: number;
    geometria_eletronica?: string;
  }>;
  geometria_eletronica?: ParameterValue<string>;
  is_aromatico: boolean;
  is_no_anel: boolean;
  tamanho_do_anel: number | null;

  chiral_tag: string;
  configuracao_absoluta: ParameterValue<string>;
  posicao_2d: { x: number; y: number } | null;
  posicao_3d: ParameterValue<{ x: number; y: number; z: number }>;

  carga_parcial?: ParameterValue<number>;
  raio_vdw: ParameterValue<number>;
  raio_covalente?: ParameterValue<number>;
  sasa_local: ParameterValue<number>;
  tipo_campo_de_forca: ParameterValue<number | string>;
  indices_fukui?: ParameterValue<unknown>;
  fukui_aproximado?: ParameterValue<unknown>;
  interacoes_atomicas: ParameterValue<AtomInteraction[]>;
  reatividade_local?: ParameterValue<unknown>;
};

export type BondParameterData = {
  id_interno: string | null;
  rdkit_idx: number;
  atomo_origem_idx: number;
  atomo_destino_idx: number;
  ordem: number;
  tipo_rdkit?: string;
  is_conjugada: boolean;
  is_aromatica?: boolean;
  is_no_anel: boolean;
  estereoquimica: string;
  direcao_visual: string;
  comprimento_ideal: ParameterValue<number>;
  polaridade_ligacao?: ParameterValue<unknown>;
};

export type MoleculeParameterData = {
  id_snapshot: string;
  hash_estrutural: string;
  smiles_canonico: string;
  smiles_isomerico: string;
  inchi: ParameterValue<string>;
  inchikey: ParameterValue<string>;
  nome_comum?: ParameterValue<string>;
  formula_molecular: string;

  peso_molecular: number;
  massa_exata: number;

  total_atomos: number;
  total_atomos_pesados: number;
  total_ligacoes: number;
  total_ligacoes_pesadas?: number;

  atom_count_total?: number;
  bond_count_total?: number;
  heavy_atom_count?: number;
  heavy_bond_count?: number;

  total_hidrogenios?: ParameterValue<number>;
  hydrogen_atom_count?: number;
  ligacoes_com_hidrogenio?: ParameterValue<number>;
  hydrogen_bond_count?: number;
  ligacoes_c_h?: ParameterValue<number>;
  carbon_hydrogen_bond_count?: number;
  ligacoes_n_h?: ParameterValue<number>;
  ligacoes_o_h?: ParameterValue<number>;
  ligacoes_s_h?: ParameterValue<number>;
  ligacoes_hetero_h?: ParameterValue<number>;
  ligacoes_sigma?: ParameterValue<number>;
  sigma_bond_count?: number;
  ligacoes_pi?: ParameterValue<number>;
  pi_bond_count?: number;
  ligacoes_sigma_pesadas?: ParameterValue<number>;
  ligacoes_pi_pesadas?: ParameterValue<number>;
  ligacoes_sigma_com_hidrogenio?: ParameterValue<number>;
  contagem_ligacoes_por_tipo?: ParameterValue<Record<string, number>>;

  carga_formal_total: number;

  logp: ParameterValue<number>;
  logd?: ParameterValue<number>;
  pka?: ParameterValue<number>;
  logs?: ParameterValue<number>;
  tpsa: ParameterValue<number>;

  hbd: ParameterValue<number>;
  hba: ParameterValue<number>;
  rotatable_bonds: ParameterValue<number>;
  total_aneis: ParameterValue<number>;
  aneis_aromaticos: ParameterValue<number>;
  fracao_csp3: ParameterValue<number>;
  qed?: ParameterValue<number>;
  complexidade_bertz?: ParameterValue<number>;
  refratividade_molar?: ParameterValue<number>;

  indice_wiener?: ParameterValue<number>;
  indice_randic?: ParameterValue<number>;

  densidade?: ParameterValue<number>;
  ponto_fusao?: ParameterValue<number>;
  ponto_ebulicao?: ParameterValue<number>;
  pressao_vapor?: ParameterValue<number>;
  tensao_superficial?: ParameterValue<number>;
  viscosidade?: ParameterValue<number>;
  energia_livre_gibbs_solvacao?: ParameterValue<number>;

  is_surfactante: ParameterValue<boolean>;
  classe_surfactante?: ParameterValue<string>;
  indice_anfifilico: ParameterValue<number>;
  comprimento_cauda: ParameterValue<number>;
  comprimento_cauda_efetivo?: ParameterValue<number>;
  numero_caudas_hidrofobicas?: ParameterValue<number>;
  volume_cauda?: ParameterValue<number>;
  area_cabeca_micela: ParameterValue<number>;
  hlb?: ParameterValue<number>;
  hlb_estimado?: ParameterValue<number>;
  cmc_estimada: ParameterValue<number>;
  cmc_ambiente_estimada?: ParameterValue<number>;
  cmc_klevens_mol_l?: ParameterValue<number>;
  cmc_klevens_mmol_l?: ParameterValue<number>;
  cmc_corrigida_mol_l?: ParameterValue<number>;
  cmc_corrigida_mmol_l?: ParameterValue<number>;
  x_cmc?: ParameterValue<number>;
  delta_g_micelizacao?: ParameterValue<number>;
  hlb_griffin?: ParameterValue<number>;
  hlb_davies?: ParameterValue<number>;
  hlb_engine_bruto?: ParameterValue<number>;
  cpp?: ParameterValue<number>;
  cpp_ideal?: ParameterValue<number>;
  hld?: ParameterValue<number>;
  nac?: ParameterValue<number>;
  tipo_cabeca_polar?: ParameterValue<string>;
  tipo_carga_surfactante?: ParameterValue<string>;
  area_cabeca_ideal?: ParameterValue<number>;
  area_cabeca_efetiva?: ParameterValue<number>;
  comprimento_maximo_cauda?: ParameterValue<number>;
  parametros_micela?: ParameterValue<Record<string, unknown>>;
  numero_agregacao_estimado?: ParameterValue<number>;
  raio_micela_esferica?: ParameterValue<number>;
  raio_nucleo_hidrofobico?: ParameterValue<number>;
  faixa_raio_micela?: ParameterValue<number[]>;
  raio_micela_cilindrica?: ParameterValue<number>;
  perfil_calibracao_literatura?: ParameterValue<Record<string, unknown> | null>;
  carga_residual_micela?: ParameterValue<number>;
  contraions_ligados_micela?: ParameterValue<number>;
  densidade_carga_superficial?: ParameterValue<number>;
  confianca_cmc?: ParameterValue<Record<string, unknown>>;
  miriam2_identity?: ParameterValue<Record<string, unknown>>;
  miriam2_calculation_plan?: ParameterValue<Array<Record<string, unknown>>>;
  miriam2_physical_validation?: ParameterValue<Record<string, unknown>>;
  miriam2_applicability?: ParameterValue<Record<string, unknown>>;
  miriam2_audit?: ParameterValue<Record<string, unknown>>;
  miriam2_structural_features?: ParameterValue<Record<string, unknown>>;
  parametro_empacotamento: ParameterValue<{
    valor: number | null;
    classe: string | null;
  }>;
  comportamento_micelar_previsto?: ParameterValue<string>;

  raio_de_giracao: ParameterValue<number>;
  npr1: ParameterValue<number>;
  npr2: ParameterValue<number>;
  volume_vdw_total: ParameterValue<number>;
  sasa_total: ParameterValue<number>;
  vetor_momento_dipolo: ParameterValue<{
    x: number;
    y: number;
    z: number;
    magnitude: number;
  }>;

  energia_conformacional: ParameterValue<number>;
  energia_homo: ParameterValue<number>;
  energia_lumo: ParameterValue<number>;
  gap_homo_lumo: ParameterValue<number>;
  calor_de_formacao: ParameterValue<number>;
  potencial_ionizacao?: ParameterValue<number>;
  afinidade_eletronica?: ParameterValue<number>;

  ambiente_fisico_quimico?: ParameterValue<unknown>;

  biblioteca_status?: Record<
    string,
    {
      name: string;
      installed: boolean;
      purpose: string;
      import_error?: string | null;
    }
  > | unknown;
};

export type ChemistryParametersResponse = {
  success: boolean;
  package_version: string;
  source: string;
  molecule: MoleculeParameterData;
  atoms: AtomParameterData[];
  bonds: BondParameterData[];
  warnings: string[];
  limitations?: string[];
  snapshot_dados_completos?: {
    molecule: MoleculeParameterData;
    atoms: AtomParameterData[];
    bonds: BondParameterData[];
  };
};

export type ChemistryParametersPanelMode = "molecule" | "atom" | "bond";

export type ChemistryParametersPanelProps = {
  molecule: InternalMoleculeModel | null;
  selectedTarget: SelectedMoleculeTarget;
  mode: ChemistryParametersPanelMode;
};


