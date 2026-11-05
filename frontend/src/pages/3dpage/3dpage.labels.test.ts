import { describe, expect, it } from "vitest";

import { buildDocumentedExampleRows, buildObservationRows, buildPredictionRows } from "./3dpage";
import { REPRESENTATION_LABEL, pinchDistance, viewerSealText } from "./components/render/SimulationViewer3D";
import type { MiceliumAnalysis3D } from "./type/3dpage.types";

function analysis(updates: Partial<MiceliumAnalysis3D> = {}): MiceliumAnalysis3D {
  return {
    total_particles: 160, molecule_count: 40, surfactant_count: 40, solvent_count: 0, solute_count: 0,
    micelle_probability: 0.64, average_cluster_size: 4.8, cluster_count: 5, largest_cluster_size: 14,
    stability_score: 0.6, warnings: [],
    c_over_cmc_proxy: 3.0, critical_amount_mmol: 0.775, real_amount_mmol: 2.325,
    predicted_morphology: "micela esférica", dominant_morphology: "micela esférica",
    predicted_regime: "micelização estabelecida", formation_phase: "organização mesoscópica",
    measured_morphology: "agregado orientado", micellized_fraction: 0.62,
    morphology_basis: "CPP médio = 0.292; c/CMC = 3",
    validation_status: "não validado experimentalmente: …",
    representation_label: REPRESENTATION_LABEL,
    independent_shape_distribution: { "agregado orientado": 2, "agregado aproximadamente esférico": 1 },
    ignored_components: [], prediction_note: null, c_over_cmc_parcial: null,
    ...updates,
  };
}

const valueOf = (rows: { label: string; value: string }[], label: string) => rows.find((row) => row.label === label)?.value;

describe("Previsto pelos cálculos", () => {
  it("mostra CMC da mistura, C/CMC, morfologia prevista, base e validação", () => {
    const { rows, partialNote } = buildPredictionRows(analysis(), 100);
    expect(valueOf(rows, "CMC da mistura (Clint)")).toBe("7.75 mmol/L");
    expect(valueOf(rows, "C/CMC")).toBe("3.00");
    expect(valueOf(rows, "Morfologia prevista")).toBe("micela esférica");
    expect(valueOf(rows, "Base da previsão")).toContain("CPP");
    expect(valueOf(rows, "Validação")).toContain("não validado");
    expect(rows.some((row) => row.label.startsWith("C/CMC parcial"))).toBe(false);
    expect(partialNote).toBeNull();
  });

  it("informa claramente quando a mistura usa C/CMC parcial", () => {
    const { rows, partialNote } = buildPredictionRows(analysis({
      c_over_cmc_proxy: null, critical_amount_mmol: null, c_over_cmc_parcial: 3.0,
      ignored_components: ["m1 (sem CMC no domínio de aplicação)"],
      prediction_note: "visualização aproximada: ignora m1 (sem CMC no domínio de aplicação) no cálculo de c/CMC",
    }), 100);
    expect(valueOf(rows, "C/CMC")).toBe("— (total desconhecido)");
    expect(valueOf(rows, "C/CMC parcial (só visualização)")).toBe("3.00");
    expect(valueOf(rows, "CMC da mistura (Clint)")).toBe("—");
    expect(valueOf(rows, "Componentes fora do C/CMC")).toContain("m1");
    expect(partialNote).toContain("visualização aproximada");
  });

  it("sem análise mostra traços, sem inventar valores", () => {
    const { rows } = buildPredictionRows(null, 100);
    expect(rows.every((row) => row.value === "—")).toBe(true);
  });
});

describe("Observado na visualização", () => {
  it("separa forma medida sem a previsão, rótulo da cena e agregados", () => {
    const rows = buildObservationRows(analysis());
    expect(valueOf(rows, "Forma dominante medida (sem usar a previsão)")).toBe("agregado orientado");
    expect(valueOf(rows, "Rótulo dos agregados na cena")).toBe("micela esférica");
    expect(valueOf(rows, "Fase observada na cena")).toBe("organização mesoscópica");
    // O rótulo do molde previsto não pode aparecer como observação independente.
    expect(rows.some((row) => row.label === "Morfologia observada")).toBe(false);
    expect(valueOf(rows, "Clusters")).toBe("5");
    expect(valueOf(rows, "Maior agregado")).toBe("14 moléculas");
    expect(valueOf(rows, "Fração organizada na amostra 3D")).toBe("62.0%");
    expect(valueOf(rows, "Distribuição das formas medidas")).toBe("agregado orientado ×2; agregado aproximadamente esférico ×1");
    expect(valueOf(rows, "Índice micelar (heurístico)")).toBe("0.64");
  });
});

describe("preserva o funcionamento anterior", () => {
  it("sem morfologia na análise usa a do primeiro cluster e a contagem da topologia", () => {
    const rows = buildObservationRows(analysis({ dominant_morphology: null }), { clusterMorphology: "micela esférica", clusterCount: 7 });
    expect(valueOf(rows, "Rótulo dos agregados na cena")).toBe("micela esférica");
    expect(valueOf(rows, "Clusters")).toBe("7");
    expect(valueOf(buildObservationRows(null, { clusterMorphology: null, clusterCount: 0 }), "Clusters")).toBe("0");
  });

  it("regime previsto vem do plano (c/CMC), não das coordenadas", () => {
    const { rows } = buildPredictionRows(analysis(), 100);
    expect(valueOf(rows, "Regime de concentração (c/CMC)")).toBe("micelização estabelecida");
    expect(rows.some((row) => row.value === "organização mesoscópica")).toBe(false);
  });
});

describe("visualizador", () => {
  it("selo é permanente, com ou sem análise", () => {
    expect(viewerSealText(null)).toBe("Visualização representativa — não é simulação física");
    expect(viewerSealText(analysis({ representation_label: null }))).toBe(REPRESENTATION_LABEL);
  });

  it("pinça aproxima ao afastar os dedos e respeita os limites", () => {
    expect(pinchDistance(100, 100, 200)).toBeCloseTo(50);
    expect(pinchDistance(100, 200, 100)).toBeCloseTo(200);
    expect(pinchDistance(10, 100, 1000)).toBe(8);
    expect(pinchDistance(200, 100, 10)).toBe(220);
  });
});


describe("exemplo documentado no card Previsto", () => {
  const report = (updates: Record<string, unknown> = {}) => ({
    id: "dppc_vesicula_extrusao", title: "DPPC — vesícula unilamelar (extrusão)", kind: "representative_demo" as const,
    example_version: "1.0.0", last_reviewed_at: "2026-11-05", documented_morphology: "vesícula/bicamada fechada",
    within_range: true, out_of_range_reasons: [] as string[],
    conditions: [
      { parameter: "temperature_c", label: "temperatura de extrusão 51–61 °C", basis: "protocol" as const, source: "ref" },
      { parameter: "method", label: "método: extrusão por 100 nm", basis: "experimental" as const, source: "ref" },
      { parameter: "temperature_c", label: "temperatura < 100 °C", basis: "technical" as const, source: "limite" },
    ],
    protocol: "Extrusão por 100 nm a 55 °C.", references: [{ label: "Hope et al. 1985", url: null }, { label: "Tm 41 °C", url: null }],
    notes: [], w0: null, ...updates,
  });

  it("demonstração: origem 'exemplo documentado', condições com a natureza e referências", () => {
    const rows = buildDocumentedExampleRows(analysis({ morphology_source: "documented_example", documented_example: report() }));
    expect(valueOf(rows, "Origem da forma")).toBe("exemplo documentado (demonstração representativa)");
    expect(valueOf(rows, "Exemplo")).toBe("DPPC — vesícula unilamelar (extrusão) · v1.0.0 · revisão 2026-11-05");
    expect(valueOf(rows, "Condição: temperatura de extrusão 51–61 °C")).toBe("protocolo");
    expect(valueOf(rows, "Condição: método: extrusão por 100 nm")).toBe("experimental");
    expect(valueOf(rows, "Condição: temperatura < 100 °C")).toBe("limite técnico");
    expect(valueOf(rows, "Protocolo")).toBe("Extrusão por 100 nm a 55 °C.");
    expect(valueOf(rows, "Referências")).toBe("Hope et al. 1985; Tm 41 °C");
    expect(valueOf(rows, "Fora das condições documentadas")).toBeUndefined();
    expect(valueOf(rows, "w0")).toBeUndefined();
  });

  it("SDS: origem 'calculada'", () => {
    const rows = buildDocumentedExampleRows(analysis({ morphology_source: "calculated",
      documented_example: report({ id: "sds_esferica", kind: "validated_prediction", title: "SDS" }) }));
    expect(valueOf(rows, "Origem da forma")).toBe("calculada (previsão validada)");
  });

  it("fora das condições: aviso com os motivos e origem calculada", () => {
    const rows = buildDocumentedExampleRows(analysis({ morphology_source: "calculated",
      documented_example: report({ within_range: false, out_of_range_reasons: ["temperatura = 45 fora de: 51–61 °C"] }) }));
    expect(valueOf(rows, "Origem da forma")).toBe("calculada (fora das condições do exemplo)");
    expect(valueOf(rows, "Fora das condições documentadas")).toBe("temperatura = 45 fora de: 51–61 °C");
  });

  it("w0 só no AOT; sem exemplo, nenhuma linha", () => {
    const rows = buildDocumentedExampleRows(analysis({ morphology_source: "documented_example",
      documented_example: report({ id: "aot_inversa_isooctano", w0: 10 }) }));
    expect(valueOf(rows, "w0")).toBe("10");
    expect(buildDocumentedExampleRows(analysis())).toEqual([]);
    expect(buildDocumentedExampleRows(null)).toEqual([]);
  });
});
