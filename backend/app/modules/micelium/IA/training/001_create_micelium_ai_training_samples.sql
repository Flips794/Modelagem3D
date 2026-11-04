CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS micelium_ai_training_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    sample_key VARCHAR(180) NOT NULL UNIQUE,
    dataset_role VARCHAR(50) NOT NULL DEFAULT 'reference',
    quality_status VARCHAR(50) NOT NULL DEFAULT 'approved',

    compound_name VARCHAR(255) NOT NULL,
    common_name VARCHAR(255),
    cas_number VARCHAR(80),

    smiles TEXT NOT NULL,
    canonical_smiles TEXT,
    inchikey VARCHAR(80),

    surfactant_class VARCHAR(80) NOT NULL,
    head_group VARCHAR(160),
    ammonium_subtype VARCHAR(120),
    tail_type VARCHAR(120),
    tail_carbon_count INTEGER,
    tail_count INTEGER,
    counterion VARCHAR(80),

    solvent VARCHAR(120) NOT NULL DEFAULT 'water',
    solvent_smiles TEXT,
    temperature_k DOUBLE PRECISION NOT NULL DEFAULT 298.15,
    pressure_atm DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    ph DOUBLE PRECISION,
    ionic_strength_mol_l DOUBLE PRECISION,
    dielectric_constant DOUBLE PRECISION,
    solvent_polarity_index DOUBLE PRECISION,

    cmc_mmol_l DOUBLE PRECISION NOT NULL,
    cmc_unit VARCHAR(40) NOT NULL DEFAULT 'mmol/L',
    log10_cmc_mmol_l DOUBLE PRECISION,
    cmc_original_value DOUBLE PRECISION,
    cmc_original_unit VARCHAR(40),

    hlb DOUBLE PRECISION,
    effective_hlb DOUBLE PRECISION,
    cpp_reference DOUBLE PRECISION,
    preferred_morphology VARCHAR(120),
    aggregation_number DOUBLE PRECISION,
    micelle_radius_nm DOUBLE PRECISION,
    zeta_mv DOUBLE PRECISION,

    source_type VARCHAR(80) NOT NULL DEFAULT 'literature',
    source_title TEXT,
    source_authors TEXT,
    source_year INTEGER,
    source_doi VARCHAR(255),
    source_url TEXT,
    source_notes TEXT,

    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.85,
    feature_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_class
    ON micelium_ai_training_samples (surfactant_class);

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_inchikey
    ON micelium_ai_training_samples (inchikey);

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_compound
    ON micelium_ai_training_samples (LOWER(compound_name));

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_solvent_temp
    ON micelium_ai_training_samples (LOWER(solvent), temperature_k);

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_quality
    ON micelium_ai_training_samples (quality_status, dataset_role);

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_feature_json
    ON micelium_ai_training_samples USING GIN (feature_json);

CREATE INDEX IF NOT EXISTS ix_micelium_ai_training_samples_target_json
    ON micelium_ai_training_samples USING GIN (target_json);

CREATE OR REPLACE FUNCTION set_micelium_ai_training_samples_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_micelium_ai_training_samples_updated_at
ON micelium_ai_training_samples;

CREATE TRIGGER trg_micelium_ai_training_samples_updated_at
BEFORE UPDATE ON micelium_ai_training_samples
FOR EACH ROW
EXECUTE FUNCTION set_micelium_ai_training_samples_updated_at();


