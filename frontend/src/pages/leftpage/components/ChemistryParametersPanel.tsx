import { useEffect, useMemo, useRef, useState } from "react";

import { analyzeChemistryParameters } from "./chemistryParametersApi";
import type {
  AtomInteraction,
  AtomParameterData,
  BondParameterData,
  ChemistryParametersPanelProps,
  ChemistryParametersResponse,
  IonizableSiteData,
  MoleculeParameterData,
  ParameterValue,
  ResonanceRange,
  SpeciesAtPh,
  SurfactantClassificationData,
} from "./chemistryParameters.types";

type GeometryStatus = "idle" | "loading" | "done" | "error";

const SPECIES_PT: Record<string, string> = {
  anionic: "aniônica", cationic: "catiônica", nonionic: "não iônica", zwitterionic: "zwitteriônica",
};
const CLASS_PT: Record<string, string> = {
  anionic: "aniônico", cationic: "catiônico", nonionic: "não iônico", zwitterionic: "zwitteriônico",
  amphoteric: "anfotérico", unknown: "não surfactante",
};
const ROLE_PT: Record<string, string> = {
  surfactant: "surfactante", surfactant_or_cosurfactant: "surfactante ou cossurfactante (cabeça fraca)", none: "não surfactante",
};
const CONFIDENCE_PT: Record<string, string> = { high: "alta", medium: "média", low: "baixa" };

type StandardEnvironmentSpec = {
  temperatureK: number;
  temperatureC: number;
  pressureAtm: number;
  ph: number;
  ionicStrengthMolL: number;
  solventLabel: string;
  solventPolarityIndex: number;
  dielectricConstant: number;
  agitationRpm: number;
  referenceVolumeMl: number;
};

const STANDARD_ISOLATED_ENVIRONMENT: StandardEnvironmentSpec = {
  temperatureK: 298.15,
  temperatureC: 25,
  pressureAtm: 1,
  ph: 7,
  ionicStrengthMolL: 0.01,
  solventLabel: "meio aquoso polar idealizado",
  solventPolarityIndex: 1,
  dielectricConstant: 78.5,
  agitationRpm: 0,
  referenceVolumeMl: 100,
};

function StandardEnvironmentBox() {
  return (
    <details className="leftpage-standard-environment">
      <summary>Ambiente padrão / dados ideais da molécula individual</summary>

      <div className="leftpage-standard-environment-intro">
        <strong>Ambiente padrão usado nos cálculos individuais</strong>
        <span>
          Esta condição serve como referência estável para estimativas da molécula pura.
          A manipulação real de solvente, quantidade e mistura fica na segunda janela da esquerda.
        </span>
      </div>

      <div className="leftpage-standard-environment-grid">
        <span>Temperatura</span>
        <strong>
          {STANDARD_ISOLATED_ENVIRONMENT.temperatureK} K (
          {STANDARD_ISOLATED_ENVIRONMENT.temperatureC} °C)
        </strong>

        <span>Pressão</span>
        <strong>{STANDARD_ISOLATED_ENVIRONMENT.pressureAtm} atm</strong>

        <span>pH</span>
        <strong>{STANDARD_ISOLATED_ENVIRONMENT.ph} neutro</strong>

        <span>Solvente de referência</span>
        <strong>{STANDARD_ISOLATED_ENVIRONMENT.solventLabel}</strong>

        <span>Polaridade do solvente</span>
        <strong>{STANDARD_ISOLATED_ENVIRONMENT.solventPolarityIndex} / 1</strong>

        <span>Constante dielétrica</span>
        <strong>
          {STANDARD_ISOLATED_ENVIRONMENT.dielectricConstant} (
          água a 25 °C)
        </strong>

        <span>Força iônica</span>
        <strong>
          {STANDARD_ISOLATED_ENVIRONMENT.ionicStrengthMolL} mol/L
        </strong>

        <span>Agitação</span>
        <strong>{STANDARD_ISOLATED_ENVIRONMENT.agitationRpm} rpm</strong>

        <span>Volume de referência</span>
        <strong>{STANDARD_ISOLATED_ENVIRONMENT.referenceVolumeMl} mL</strong>
      </div>

      <p>
        Interpretação: os valores físico-químicos desta primeira tabela são
        estimativas ideais da molécula individual em um meio aquoso padrão,
        sem mistura real entre várias moléculas. Quando você selecionar
        solvente, reagentes e quantidades e clicar em Misturar, os dados
        dependentes da solução devem ser lidos na 3LeftPage.
      </p>
    </details>
  );
}

function makeUnavailable<T = unknown>(
  label: string,
  note = "Campo ausente na resposta do backend."
): ParameterValue<T> {
  return {
    value: null,
    unit: null,
    source: "frontend_fallback",
    available: false,
    confidence: "low",
    note: `${label}: ${note}`,
  };
}

function coalesceParameter<T>(
  parameter: ParameterValue<T> | undefined,
  label: string
): ParameterValue<T> {
  return parameter ?? makeUnavailable<T>(label);
}

function formatPrimitive(value: unknown): string {
  if (value === null || value === undefined) return "—";

  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(5)));
  }

  if (typeof value === "boolean") {
    return value ? "sim" : "não";
  }

  if (Array.isArray(value) && value.every((item) => typeof item === "number")) {
    return value.length ? value.map((item) => formatPrimitive(item)).join(", ") : "nenhum";
  }

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if ("min" in record && "max" in record && "varia" in record) {
      const range = record as unknown as ResonanceRange;
      return range.min === range.max
        ? `${formatPrimitive(range.min)} (não varia)`
        : `${formatPrimitive(range.min)} a ${formatPrimitive(range.max)} (varia)`;
    }
    if (["x", "y", "z"].every((key) => typeof record[key] === "number")) {
      const vector = `${formatPrimitive(record.x)}, ${formatPrimitive(record.y)}, ${formatPrimitive(record.z)}`;
      return typeof record.magnitude === "number" ? `${formatPrimitive(record.magnitude)} (vetor ${vector})` : vector;
    }
    try {
      return JSON.stringify(value);
    } catch {
      return "—";
    }
  }

  return String(value);
}

function formatParameter(parameter: ParameterValue | undefined): string {
  if (!parameter) return "—";

  if (parameter.available === false) return "—";

  const value = formatPrimitive(parameter.value);
  if (!parameter.unit) return value;

  const vectorAt = value.indexOf(" (vetor ");
  return vectorAt > 0
    ? `${value.slice(0, vectorAt)} ${parameter.unit}${value.slice(vectorAt)}`
    : `${value} ${parameter.unit}`;
}

function isNotApplicable(parameter: ParameterValue) {
  return parameter.confidence === "not_applicable" || (parameter.note ?? "").startsWith("não se aplica");
}

/** experimental | available (calculado) | estimated | unavailable | not-applicable | missing */
function getParameterClass(parameter: ParameterValue | undefined) {
  if (!parameter) return "missing";

  if (!parameter.available) return isNotApplicable(parameter) ? "not-applicable" : "unavailable";

  if (parameter.confidence === "experimental") return "experimental";

  if (["estimated", "proxy", "medium", "low", "heuristic"].includes(String(parameter.confidence))) {
    return "estimated";
  }

  return "available";
}

function visibleNote(parameter: ParameterValue | undefined, showNote: boolean) {
  if (!parameter?.note) return null;
  const state = getParameterClass(parameter);
  // O motivo/referência fica visível (o title não funciona no toque).
  return showNote || state === "unavailable" || state === "not-applicable" || state === "experimental"
    ? parameter.note
    : null;
}

function ParameterRow({
  label,
  parameter,
  rawValue,
  displayValue,
  testId,
  showNote = false,
}: {
  label: string;
  parameter?: ParameterValue;
  rawValue?: unknown;
  displayValue?: string;
  testId?: string;
  showNote?: boolean;
}) {
  const value = displayValue ?? (parameter ? formatParameter(parameter) : formatPrimitive(rawValue));
  const source = parameter?.source;
  const note = parameter?.note;
  const confidence = parameter?.confidence;
  const shownNote = visibleNote(parameter, showNote);

  return (
    <div className="leftpage-parameter-row" data-testid={testId}>
      <span>{label}</span>
      <strong
        className={parameter ? getParameterClass(parameter) : value === "—" ? "missing" : "available"}
        title={[source, confidence, note].filter(Boolean).join(" | ")}
      >
        {value}
        {shownNote && <small className="leftpage-parameter-note">{shownNote}</small>}
      </strong>
    </div>
  );
}

function ParameterLegend() {
  return (
    <div className="leftpage-parameter-legend" data-testid="parameter-legend">
      <span className="experimental">Experimental</span>
      <span className="available">Calculado</span>
      <span className="estimated">Estimado</span>
      <span className="unavailable">Indisponível</span>
      <span className="not-applicable">Não se aplica</span>
    </div>
  );
}

function ResonanceSection({ molecule }: { molecule: MoleculeParameterData }) {
  return (
    <>
      <h4>Molécula individual — ressonância (estruturas de Lewis formais)</h4>
      <div className="leftpage-data-grid compact">
        <ParameterRow label="Estruturas de ressonância" parameter={molecule.ressonancia_numero_estruturas}
          testId="row-ressonancia_numero_estruturas" showNote />
        <ParameterRow label="Sistemas conjugados" parameter={molecule.sistemas_conjugados} />
        <ParameterRow label="Átomos deslocalizados (índices)" parameter={molecule.ressonancia_atomos_deslocalizados} />
        <ParameterRow label="Ligações deslocalizadas (índices)" parameter={molecule.ressonancia_ligacoes_deslocalizadas} />
      </div>
    </>
  );
}

function speciesLabel(species: SpeciesAtPh | null | undefined) {
  if (!species?.classe) return "—";
  const name = SPECIES_PT[species.classe] ?? species.classe;
  return species.smiles ? `${name} — ${species.smiles}` : name;
}

function IonizationSection({ molecule }: { molecule: MoleculeParameterData }) {
  const sites: IonizableSiteData[] = molecule.sitios_ionizaveis?.value ?? [];
  const species = molecule.especie_predominante_ph;
  const ph = species?.value?.ph;

  return (
    <>
      <h4>Molécula individual — ionização no pH do ambiente{ph !== undefined ? ` (pH ${formatPrimitive(ph)})` : ""}</h4>
      <div className="leftpage-data-grid compact">
        <ParameterRow label="Carga formal do desenho" rawValue={molecule.carga_formal_total} />
        <ParameterRow label="Carga líquida estimada" parameter={molecule.carga_liquida_ph} testId="row-carga_liquida_ph" />
        <ParameterRow label="Espécie predominante" parameter={species}
          displayValue={species?.available ? speciesLabel(species.value) : undefined} testId="row-especie_predominante_ph" />
      </div>
      {sites.length > 0 && (
        <div className="leftpage-interaction-list">
          <h5>Sítios ionizáveis (pKa do composto-modelo)</h5>
          {sites.map((site) => (
            <article className="leftpage-interaction-row" key={`${site.atom_idx}-${site.grupo}`}>
              <strong>
                {site.grupo} — átomo {site.atom_idx}
                {site.pka !== null ? ` · pKa ${formatPrimitive(site.pka)}` : ""}
                {site.pka === null && site.pka_limite_superior != null ? ` · pKa < ${formatPrimitive(site.pka_limite_superior)}` : ""}
                {site.acoplado ? " · acoplado" : ""}
              </strong>
              <span>{site.referencia}</span>
              {site.qualidade_referencia && <span>Qualidade da referência: {site.qualidade_referencia}</span>}
            </article>
          ))}
        </div>
      )}
    </>
  );
}

function ClassificationSection({ molecule }: { molecule: MoleculeParameterData }) {
  const field = molecule.classificacao_surfactante;
  const data: SurfactantClassificationData | null | undefined = field?.value;
  if (!field) return null;

  const title = <h4>Molécula individual — classificação do surfactante (regras químicas, sem IA treinada)</h4>;
  if (!field.available || !data) {
    // Uma linha só: o motivo não se repete em cada campo derivado.
    return (
      <>
        {title}
        <div className="leftpage-data-grid compact">
          <ParameterRow label="Classe estrutural" parameter={field} testId="row-classificacao_classe" />
        </div>
      </>
    );
  }

  const species = data.especie_no_ph;
  return (
    <>
      {title}
      <div className="leftpage-data-grid compact">
        <ParameterRow label="Classe estrutural" parameter={field}
          displayValue={data.classe_pt} testId="row-classificacao_classe" />
        <ParameterRow label="Classes compatíveis" parameter={field}
          displayValue={data.classes_compativeis.map((item) => CLASS_PT[item] ?? item).join(", ") || "—"} />
        <ParameterRow label="Papel anfifílico" parameter={field}
          displayValue={ROLE_PT[data.papel] ?? data.papel} />
        <ParameterRow label="Confiança (qualitativa)" parameter={field}
          displayValue={CONFIDENCE_PT[data.confianca] ?? data.confianca} />
        {species && (
          <ParameterRow label={`Espécie no pH ${formatPrimitive(species.ph)}`} parameter={field}
            displayValue={species.species ? `${SPECIES_PT[species.species] ?? species.species} (referência de pKa: ${species.reference_status})`
              : species.note || "—"} />
        )}
        <ParameterRow label="Justificativa química" parameter={field}
          displayValue={data.justificativa || "—"} />
      </div>
    </>
  );
}

function GeometryAction({
  status,
  error,
  onRequest,
}: {
  status: GeometryStatus;
  error: string;
  onRequest: () => void;
}) {
  const label = status === "loading" ? "Calculando geometria 3D..." : status === "done" ? "Geometria 3D calculada" : "Calcular geometria 3D";
  return (
    <>
      <div className="leftpage-action-row single">
        <button type="button" onClick={onRequest} disabled={status === "loading" || status === "done"}
          aria-busy={status === "loading"}>
          {label}
        </button>
      </div>
      {status === "idle" && (
        <small className="leftpage-parameter-note">
          Sob demanda: ETKDGv3 + MMFF94, um confórmero em fase gasosa (não representa o conjunto em solução).
        </small>
      )}
      {status === "error" && <div className="leftpage-error-box">Geometria 3D não calculada: {error}</div>}
    </>
  );
}

function MessageList({
  title,
  messages,
  variant,
}: {
  title: string;
  messages: string[];
  variant: "warning" | "limitation";
}) {
  if (!messages.length) return null;

  return (
    <details
      className={
        variant === "warning"
          ? "leftpage-warning-box"
          : "leftpage-parameter-unavailable"
      }
    >
      <summary>{title}</summary>
      <div>
        {messages.map((message) => (
          <span key={message}>{message}</span>
        ))}
      </div>
    </details>
  );
}

function LibraryStatus({
  molecule,
}: {
  molecule: MoleculeParameterData;
}) {
  const status = molecule.biblioteca_status ?? {};
  const entries = Object.entries(status);

  if (!entries.length) return null;

  return (
    <details className="leftpage-library-status">
      <summary>Bibliotecas científicas</summary>

      <div className="leftpage-library-grid">
        {entries.map(([key, value]) => (
          <article key={key}>
            <strong className={value.installed ? "available" : "estimated"}>
              {value.name}
            </strong>
            <span>{value.installed ? "instalada" : "não instalada"}</span>
            <small>{value.purpose}</small>
            {value.import_error && <small>{value.import_error}</small>}
          </article>
        ))}
      </div>
    </details>
  );
}

function getTotalAtoms(molecule: MoleculeParameterData) {
  return molecule.atom_count_total ?? molecule.total_atomos;
}

function getTotalBonds(molecule: MoleculeParameterData) {
  return molecule.bond_count_total ?? molecule.total_ligacoes;
}

function getHeavyAtoms(molecule: MoleculeParameterData) {
  return molecule.heavy_atom_count ?? molecule.total_atomos_pesados;
}

function getHeavyBonds(molecule: MoleculeParameterData) {
  return molecule.heavy_bond_count ?? molecule.total_ligacoes_pesadas;
}

function MoleculeParameters({
  parameters,
  geometryStatus,
  geometryError,
  onRequestGeometry,
}: {
  parameters: ChemistryParametersResponse;
  geometryStatus: GeometryStatus;
  geometryError: string;
  onRequestGeometry: () => void;
}) {
  const molecule = parameters.molecule;

  return (
    <div className="leftpage-parameter-section">
      <ParameterLegend />

      <h4>Molécula individual — identidade, topologia e estrutura eletrônica</h4>

      <div className="leftpage-data-grid compact">
        <ParameterRow label="Fórmula química" rawValue={molecule.formula_molecular} />
        <ParameterRow label="Massa molecular média" rawValue={`${molecule.peso_molecular.toFixed(3)} g/mol`} />
        <ParameterRow label="Massa monoisotópica exata" rawValue={molecule.massa_exata} />

        <ParameterRow label="Átomos totais com H" rawValue={getTotalAtoms(molecule)} />
        <ParameterRow label="Átomos pesados" rawValue={getHeavyAtoms(molecule)} />
        <ParameterRow label="Hidrogênios totais" parameter={molecule.total_hidrogenios} />
        <ParameterRow label="Ligações totais com H" rawValue={getTotalBonds(molecule)} />
        <ParameterRow label="Ligações pesadas" rawValue={getHeavyBonds(molecule)} />
        <ParameterRow label="Ligações com hidrogênio" parameter={molecule.ligacoes_com_hidrogenio} />
        <ParameterRow label="Ligações C–H" parameter={molecule.ligacoes_c_h} />
        <ParameterRow label="Ligações N–H" parameter={molecule.ligacoes_n_h} />
        <ParameterRow label="Ligações O–H" parameter={molecule.ligacoes_o_h} />
        <ParameterRow label="Ligações σ totais" parameter={molecule.ligacoes_sigma} />
        <ParameterRow label="Ligações π totais" parameter={molecule.ligacoes_pi} />
        <ParameterRow label="Ligações σ pesadas" parameter={molecule.ligacoes_sigma_pesadas} />
        <ParameterRow label="Ligações π pesadas" parameter={molecule.ligacoes_pi_pesadas} />

        <ParameterRow label="Ligações rotáveis" parameter={molecule.rotatable_bonds} />
        <ParameterRow label="Anéis totais" parameter={molecule.total_aneis} />
        <ParameterRow label="Anéis aromáticos" parameter={molecule.aneis_aromaticos} />
        <ParameterRow label="Fração CSP3" parameter={molecule.fracao_csp3} />
        <ParameterRow label="HBD estrutural" parameter={molecule.hbd} />
        <ParameterRow label="HBA estrutural" parameter={molecule.hba} />
        <ParameterRow label="Carga formal" rawValue={molecule.carga_formal_total} />

        <ParameterRow label="Momento de dipolo no vácuo" parameter={molecule.vetor_momento_dipolo} />
        <ParameterRow label="HOMO" parameter={molecule.energia_homo} />
        <ParameterRow label="LUMO" parameter={molecule.energia_lumo} />
        <ParameterRow label="Gap HOMO-LUMO" parameter={molecule.gap_homo_lumo} />
        <ParameterRow label="Potencial de ionização" parameter={molecule.potencial_ionizacao} />
        <ParameterRow label="Afinidade eletrônica" parameter={molecule.afinidade_eletronica} />

        <ParameterRow label="Complexidade Bertz" parameter={molecule.complexidade_bertz} />
        <ParameterRow label="Índice de Wiener" parameter={molecule.indice_wiener} />
        <ParameterRow label="Índice de Randic" parameter={molecule.indice_randic} />

        <ParameterRow label="SMILES canônico" rawValue={molecule.smiles_canonico} />
        <ParameterRow label="SMILES isomérico" rawValue={molecule.smiles_isomerico} />
        <ParameterRow label="InChI" parameter={molecule.inchi} />
        <ParameterRow label="InChIKey" parameter={molecule.inchikey} />
        <ParameterRow label="Nome comum" parameter={molecule.nome_comum} />
        <ParameterRow label="Hash estrutural" rawValue={molecule.hash_estrutural} />
      </div>

      <ResonanceSection molecule={molecule} />

      <IonizationSection molecule={molecule} />

      <h4>Molécula individual — propriedades físico-químicas ideais/estimadas</h4>

      <GeometryAction status={geometryStatus} error={geometryError} onRequest={onRequestGeometry} />

      <div className="leftpage-data-grid compact">
        <ParameterRow label="LogP" parameter={molecule.logp} />
        <ParameterRow label="LogD" parameter={molecule.logd} />
        <ParameterRow label="pKa" parameter={molecule.pka} />
        <ParameterRow label="LogS" parameter={molecule.logs} />
        <ParameterRow label="TPSA" parameter={molecule.tpsa} />
        <ParameterRow label="QED" parameter={molecule.qed} />

        <ParameterRow label="SASA total (sonda 1,4 Å)" parameter={molecule.sasa_total} />
        <ParameterRow label="Superfície de van der Waals" parameter={molecule.area_superficie_vdw} />
        <ParameterRow label="Raio de giração" parameter={molecule.raio_de_giracao} testId="row-raio_de_giracao" />
        <ParameterRow label="NPR1" parameter={molecule.npr1} />
        <ParameterRow label="NPR2" parameter={molecule.npr2} />
        <ParameterRow label="Volume de Van der Waals" parameter={molecule.volume_vdw_total} />
        <ParameterRow label="Energia conformacional / estérica" parameter={molecule.energia_conformacional} />

        <ParameterRow label="Energia livre de Gibbs de solvatação" parameter={molecule.energia_livre_gibbs_solvacao} />
        <ParameterRow label="Calor de formação" parameter={molecule.calor_de_formacao} />
        <ParameterRow label="Refratividade molar" parameter={molecule.refratividade_molar} />
        <ParameterRow label="Densidade" parameter={molecule.densidade} />
        <ParameterRow label="Ponto de fusão" parameter={molecule.ponto_fusao} />
        <ParameterRow label="Ponto de ebulição" parameter={molecule.ponto_ebulicao} />
        <ParameterRow label="Pressão de vapor" parameter={molecule.pressao_vapor} />
        <ParameterRow label="Tensão superficial" parameter={molecule.tensao_superficial} />
        <ParameterRow label="Viscosidade" parameter={molecule.viscosidade} />
      </div>

      <ClassificationSection molecule={molecule} />

      <h4>Molécula individual — parâmetros micelares ideais</h4>

      <div className="leftpage-data-grid compact">
        <ParameterRow label="É surfactante" parameter={molecule.is_surfactante} />
        <ParameterRow label="Classe surfactante" parameter={molecule.classe_surfactante} />
        <ParameterRow label="Índice anfifílico" parameter={molecule.indice_anfifilico} />
        <ParameterRow label="Comprimento ideal da cauda" parameter={molecule.comprimento_cauda} />
        <ParameterRow label="Comprimento efetivo da cauda" parameter={molecule.comprimento_cauda_efetivo} />
        <ParameterRow label="Número de caudas hidrofóbicas" parameter={molecule.numero_caudas_hidrofobicas} />
        <ParameterRow label="Volume ideal da cauda" parameter={molecule.volume_cauda} />
        <ParameterRow label="Área ideal da cabeça micelar" parameter={molecule.area_cabeca_micela} />
        <ParameterRow label="Tipo de cabeça polar" parameter={molecule.tipo_cabeca_polar} />
        <ParameterRow label="Tipo de carga do surfactante" parameter={molecule.tipo_carga_surfactante} />
        <ParameterRow label="HLB Griffin" parameter={molecule.hlb_griffin} />
        <ParameterRow label="HLB Davies" parameter={molecule.hlb_davies} />
        <ParameterRow label="HLB ideal/estimado" parameter={molecule.hlb_estimado ?? molecule.hlb} />
        <ParameterRow label="HLB bruto do motor" parameter={molecule.hlb_engine_bruto} />

        <ParameterRow label="CMC experimental (NSRDS-NBS 36)" parameter={molecule.cmc_experimental} testId="row-cmc_experimental" />
        <ParameterRow label="Origem da CMC usada" parameter={molecule.cmc_origem} testId="row-cmc_origem" />
        <ParameterRow label="CMC calculada/estimada" parameter={molecule.cmc_estimada} showNote />
        <ParameterRow label="CMC por Klevens" parameter={molecule.cmc_klevens_mmol_l ?? molecule.cmc_estimada} />
        <ParameterRow label="CMC corrigida por ambiente" parameter={molecule.cmc_corrigida_mmol_l ?? molecule.cmc_ambiente_estimada} />
        <ParameterRow label="XCMC" parameter={molecule.x_cmc} />
        <ParameterRow label="ΔG° micelização" parameter={molecule.delta_g_micelizacao} />

        <ParameterRow label="Área ideal da cabeça" parameter={molecule.area_cabeca_ideal} />
        <ParameterRow label="Área efetiva da cabeça" parameter={molecule.area_cabeca_efetiva} />
        <ParameterRow label="Comprimento máximo da cauda" parameter={molecule.comprimento_maximo_cauda} />
        <ParameterRow label="CPP ideal" parameter={molecule.cpp_ideal} />
        <ParameterRow label="CPP efetivo" parameter={molecule.cpp} />
        <ParameterRow label="Packing parameter ideal" parameter={molecule.parametro_empacotamento} />
        <ParameterRow label="Comportamento micelar ideal" parameter={molecule.comportamento_micelar_previsto} />

        <ParameterRow label="Número de agregação estimado" parameter={molecule.numero_agregacao_estimado} />
        <ParameterRow label="Limite geométrico de agregação (esfera, teórico)" parameter={molecule.nagg_maximo_geometrico_esfera} showNote />
        <ParameterRow label="Raio aparente da micela" parameter={molecule.raio_micela_esferica} />
        <ParameterRow label="Faixa de raio da micela" parameter={molecule.faixa_raio_micela} />
        <ParameterRow label="Raio do núcleo hidrofóbico" parameter={molecule.raio_nucleo_hidrofobico} />
        <ParameterRow label="Raio de micela cilíndrica" parameter={molecule.raio_micela_cilindrica} />
        <ParameterRow label="Perfil de calibração aplicado" parameter={molecule.perfil_calibracao_literatura} />
        <ParameterRow label="Carga residual da micela" parameter={molecule.carga_residual_micela} />
        <ParameterRow label="Contraíons ligados" parameter={molecule.contraions_ligados_micela} />
        <ParameterRow label="Densidade de carga superficial" parameter={molecule.densidade_carga_superficial} />
        <ParameterRow label="HLD" parameter={molecule.hld} />
        <ParameterRow label="NAC" parameter={molecule.nac} />
        <ParameterRow label="Confiança da CMC" parameter={molecule.confianca_cmc} />
        <ParameterRow label="Identificação MIRIAM-2.1" parameter={molecule.miriam2_identity} />
        <ParameterRow label="Características estruturais MIRIAM-2.1" parameter={molecule.miriam2_structural_features} />
        <ParameterRow label="Plano de cálculo MIRIAM-2.1" parameter={molecule.miriam2_calculation_plan} />
        <ParameterRow label="Domínio de aplicabilidade" parameter={molecule.miriam2_applicability} />
        <ParameterRow label="Validação física" parameter={molecule.miriam2_physical_validation} />
        <ParameterRow label="Auditoria MIRIAM-2.1" parameter={molecule.miriam2_audit} />
      </div>

      <LibraryStatus molecule={molecule} />

      <StandardEnvironmentBox />

      <MessageList title="Avisos" messages={parameters.warnings} variant="warning" />
      <MessageList
        title="Limitações técnicas"
        messages={parameters.limitations ?? []}
        variant="limitation"
      />
    </div>
  );
}

function AtomInteractionList({ atom }: { atom: AtomParameterData }) {
  const parameter = coalesceParameter<AtomInteraction[]>(
    atom.interacoes_atomicas,
    "interacoes_atomicas"
  );
  const interactions = parameter.value ?? [];

  if (!parameter.available && interactions.length === 0) {
    return (
      <div className="leftpage-warning-box">
        {parameter.note || "Interações átomo-átomo não disponíveis."}
      </div>
    );
  }

  if (interactions.length === 0) {
    return (
      <div className="leftpage-empty">
        Nenhuma interação par-a-par disponível para este átomo.
      </div>
    );
  }

  return (
    <div className="leftpage-interaction-list">
      <h5>Relação deste átomo com cada átomo da molécula</h5>

      {interactions.map((interaction) => (
        <article
          key={`${atom.rdkit_idx}-${interaction.atomo_alvo_idx}`}
          className={`leftpage-interaction-row ${interaction.tipo_interacao}`}
        >
          <strong>
            {atom.elemento}
            {atom.rdkit_idx + 1} ↔ {interaction.elemento_alvo}
            {interaction.atomo_alvo_idx + 1}
          </strong>

          <span>
            {interaction.tipo_interacao} · distância{" "}
            {interaction.distancia_angstrom.toFixed(3)} Å
            {interaction.ligacao_direta ? " · ligação direta" : ""}
            {interaction.mesmo_fragmento === false ? " · outro fragmento" : ""}
          </span>

          <span>
            E total {interaction.energia_total_kcal_mol.toFixed(5)} kcal/mol ·
            Coulomb{" "}
            {interaction.energia_coulomb_kcal_mol === null
              ? "—"
              : interaction.energia_coulomb_kcal_mol.toFixed(5)}
            {" · "}VDW{" "}
            {interaction.energia_vdw_kcal_mol === null
              ? "—"
              : interaction.energia_vdw_kcal_mol.toFixed(5)}
          </span>

          {interaction.coordinate_source && (
            <span>Fonte geométrica: {interaction.coordinate_source}</span>
          )}
        </article>
      ))}
    </div>
  );
}

function AtomParameters({ atom }: { atom: AtomParameterData | null }) {
  if (!atom) {
    return (
      <div className="leftpage-empty">
        Dados avançados de átomo aparecerão aqui após selecionar um átomo.
      </div>
    );
  }

  return (
    <div className="leftpage-parameter-section">
      <h4>Parâmetros do átomo</h4>

      <div className="leftpage-data-grid compact">
        <ParameterRow label="ID interno" rawValue={atom.id_interno} />
        <ParameterRow label="RDKit idx" rawValue={atom.rdkit_idx} />
        <ParameterRow label="Elemento" rawValue={atom.elemento} />
        <ParameterRow label="Número atômico" rawValue={atom.numero_atomico} />
        <ParameterRow label="Massa exata" parameter={atom.massa_exata} />
        <ParameterRow label="Isótopo" rawValue={atom.is_isotopo} />

        <ParameterRow label="Grau explícito" rawValue={atom.grau_ligacao_explicito} />
        <ParameterRow label="Ordem total" parameter={atom.ordem_ligacao_total} />
        <ParameterRow label="Valência total" parameter={atom.valencia_total} />
        <ParameterRow label="H totais" rawValue={atom.hidrogenios_totais} />
        <ParameterRow label="H implícitos" rawValue={atom.hidrogenios_implicitos} />
        <ParameterRow label="H explícitos" rawValue={atom.hidrogenios_explicitos} />
        <ParameterRow label="Carga formal" rawValue={atom.carga_formal} />
        <ParameterRow label="Carga Gasteiger" parameter={atom.carga_gasteiger ?? atom.carga_parcial} />
        <ParameterRow label="Carga quântica/proxy" parameter={atom.carga_quantica_ou_proxy} />
        <ParameterRow label="Radicais" rawValue={atom.eletrons_radicais} />
        <ParameterRow label="Pares livres" parameter={atom.pares_livres} />
        <ParameterRow label="Carga formal entre estruturas de ressonância" parameter={atom.carga_formal_ressonancia} />

        <ParameterRow label="Hibridização RDKit" rawValue={atom.hibridizacao_rdkit ?? atom.hibridizacao} />
        <ParameterRow label="Hibridização estimada" parameter={atom.hibridizacao_estimativa} />
        <ParameterRow label="Geometria eletrônica" parameter={atom.geometria_eletronica} />
        <ParameterRow label="Aromático" rawValue={atom.is_aromatico} />
        <ParameterRow label="Está em anel" rawValue={atom.is_no_anel} />
        <ParameterRow label="Tamanho do anel" rawValue={atom.tamanho_do_anel} />

        <ParameterRow label="Chiral tag" rawValue={atom.chiral_tag} />
        <ParameterRow label="Configuração absoluta" parameter={atom.configuracao_absoluta} />
        <ParameterRow label="Posição 2D" rawValue={atom.posicao_2d} />
        <ParameterRow label="Posição 3D" parameter={atom.posicao_3d} />

        <ParameterRow label="Raio VDW" parameter={atom.raio_vdw} />
        <ParameterRow label="Raio covalente" parameter={atom.raio_covalente} />
        <ParameterRow label="SASA local" parameter={atom.sasa_local} />
        <ParameterRow label="Tipo campo de força" parameter={atom.tipo_campo_de_forca} />
        <ParameterRow label="Fukui/proxy" parameter={atom.fukui_aproximado ?? atom.indices_fukui} />
        <ParameterRow label="Reatividade local" parameter={atom.reatividade_local} />
      </div>

      <AtomInteractionList atom={atom} />
    </div>
  );
}

function BondParameters({ bond }: { bond: BondParameterData | null }) {
  if (!bond) {
    return (
      <div className="leftpage-empty">
        Dados avançados de ligação aparecerão aqui após selecionar uma ligação.
      </div>
    );
  }

  return (
    <div className="leftpage-parameter-section">
      <h4>Parâmetros da ligação</h4>

      <div className="leftpage-data-grid compact">
        <ParameterRow label="ID interno" rawValue={bond.id_interno} />
        <ParameterRow label="RDKit idx" rawValue={bond.rdkit_idx} />
        <ParameterRow label="Átomo origem" rawValue={bond.atomo_origem_idx} />
        <ParameterRow label="Átomo destino" rawValue={bond.atomo_destino_idx} />
        <ParameterRow label="Ordem" rawValue={bond.ordem} />
        <ParameterRow label="Tipo RDKit" rawValue={bond.tipo_rdkit} />
        <ParameterRow label="Conjugada" rawValue={bond.is_conjugada} />
        <ParameterRow label="Aromática" rawValue={bond.is_aromatica} />
        <ParameterRow label="Está em anel" rawValue={bond.is_no_anel} />
        <ParameterRow label="Estereoquímica" rawValue={bond.estereoquimica} />
        <ParameterRow label="Direção visual" rawValue={bond.direcao_visual} />
        <ParameterRow label="Comprimento ideal" parameter={bond.comprimento_ideal} />
        <ParameterRow label="Polaridade" parameter={bond.polaridade_ligacao} />
        <ParameterRow label="Ordem formal entre estruturas de ressonância" parameter={bond.ordem_ressonancia} />
      </div>
    </div>
  );
}

export function ChemistryParametersPanel({
  molecule,
  selectedTarget,
  mode,
}: ChemistryParametersPanelProps) {
  const [parameters, setParameters] =
    useState<ChemistryParametersResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [geometryStatus, setGeometryStatus] = useState<GeometryStatus>("idle");
  const [geometryError, setGeometryError] = useState("");
  const geometryControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Nova molécula: volta ao 2D; o 3D nunca é pedido automaticamente.
    geometryControllerRef.current?.abort();
    setGeometryStatus("idle");
    setGeometryError("");

    if (!molecule?.metadata?.canonical_smiles) {
      setParameters(null);
      setError("");
      setLoading(false);
      return;
    }

    const controller = new AbortController();

    setLoading(true);
    setError("");

    const timeout = window.setTimeout(() => {
      analyzeChemistryParameters(molecule, controller.signal)
        .then((result) => {
          // Resposta de uma molécula anterior que chegou depois do cancelamento.
          if (controller.signal.aborted) return;
          setParameters(result);
        })
        .catch((caughtError) => {
          if (controller.signal.aborted) return;

          setError(
            caughtError instanceof Error
              ? caughtError.message
              : "Erro ao calcular parâmetros químicos no backend."
          );
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
    }, 250);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [molecule]);

  function requestGeometry() {
    if (!molecule || geometryStatus === "loading" || geometryStatus === "done") return;
    const controller = new AbortController();
    geometryControllerRef.current = controller;
    setGeometryStatus("loading");
    setGeometryError("");
    analyzeChemistryParameters(molecule, controller.signal, { generate3d: true })
      .then((result) => {
        if (controller.signal.aborted) return;
        setParameters(result);
        setGeometryStatus("done");
      })
      .catch((caughtError) => {
        if (controller.signal.aborted) return;
        setGeometryError(caughtError instanceof Error ? caughtError.message : "erro desconhecido no backend.");
        setGeometryStatus("error");
      });
  }

  useEffect(() => () => geometryControllerRef.current?.abort(), []);

  const selectedAtom = useMemo(() => {
    if (!molecule || !parameters || selectedTarget?.kind !== "atom") return null;

    const atom = molecule.atoms.find((item) => item.id === selectedTarget.id);

    if (!atom) return null;

    return (
      parameters.atoms.find((item) => item.rdkit_idx === atom.rdkit_index) ??
      parameters.snapshot_dados_completos?.atoms?.find(
        (item) => item.rdkit_idx === atom.rdkit_index
      ) ??
      null
    );
  }, [molecule, parameters, selectedTarget]);

  const selectedBond = useMemo(() => {
    if (!molecule || !parameters || selectedTarget?.kind !== "bond") return null;

    const bond = molecule.bonds.find((item) => item.id === selectedTarget.id);

    if (!bond) return null;

    return (
      parameters.bonds.find((item) => item.rdkit_idx === bond.rdkit_index) ??
      parameters.snapshot_dados_completos?.bonds?.find(
        (item) => item.rdkit_idx === bond.rdkit_index
      ) ??
      null
    );
  }, [molecule, parameters, selectedTarget]);

  if (!molecule) return null;

  if (loading) {
    return (
      <div className="leftpage-parameter-status">
        Calculando parâmetros da molécula individual no backend...
      </div>
    );
  }

  if (error) {
    return <div className="leftpage-error-box">{error}</div>;
  }

  if (!parameters) return null;

  if (mode === "atom") {
    return <AtomParameters atom={selectedAtom} />;
  }

  if (mode === "bond") {
    return <BondParameters bond={selectedBond} />;
  }

  return (
    <MoleculeParameters
      parameters={parameters}
      geometryStatus={geometryStatus}
      geometryError={geometryError}
      onRequestGeometry={requestGeometry}
    />
  );
}

export default ChemistryParametersPanel;


