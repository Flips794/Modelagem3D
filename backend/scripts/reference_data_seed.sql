INSERT INTO elements (
    id,
    symbol,
    name,
    atomic_number,
    atomic_mass,
    electronegativity,
    covalent_radius,
    van_der_waals_radius,
    default_valence,
    allowed_valences,
    is_metal
)
VALUES
    (gen_random_uuid(), 'H', 'Hydrogen', 1, 1.008, 2.20, 31, 120, 1, '[1]'::jsonb, false),
    (gen_random_uuid(), 'C', 'Carbon', 6, 12.011, 2.55, 76, 170, 4, '[4]'::jsonb, false),
    (gen_random_uuid(), 'N', 'Nitrogen', 7, 14.007, 3.04, 71, 155, 3, '[3,5]'::jsonb, false),
    (gen_random_uuid(), 'O', 'Oxygen', 8, 15.999, 3.44, 66, 152, 2, '[2]'::jsonb, false),
    (gen_random_uuid(), 'S', 'Sulfur', 16, 32.06, 2.58, 105, 180, 2, '[2,4,6]'::jsonb, false),
    (gen_random_uuid(), 'P', 'Phosphorus', 15, 30.974, 2.19, 107, 180, 3, '[3,5]'::jsonb, false),
    (gen_random_uuid(), 'Na', 'Sodium', 11, 22.990, 0.93, 166, 227, 1, '[1]'::jsonb, true),
    (gen_random_uuid(), 'Cl', 'Chlorine', 17, 35.45, 3.16, 102, 175, 1, '[1,3,5,7]'::jsonb, false)
ON CONFLICT DO NOTHING;


INSERT INTO functional_groups (
    id,
    code,
    name,
    description,
    smarts_pattern,
    polarity_class,
    reactivity_hint
)
VALUES
    (gen_random_uuid(), 'alcohol', 'Alcohol', 'Grupo hidroxila ligado a carbono saturado.', '[OX2H]', 'polar', 'Pode doar e aceitar ligação de hidrogênio.'),
    (gen_random_uuid(), 'carboxylic_acid', 'Carboxylic Acid', 'Grupo ácido carboxílico.', 'C(=O)[OX2H1]', 'strongly_polar', 'Pode atuar como ácido de Brønsted.'),
    (gen_random_uuid(), 'amine', 'Amine', 'Grupo amina.', '[NX3;H2,H1,H0]', 'polar_basic', 'Pode atuar como base ou nucleófilo.'),
    (gen_random_uuid(), 'ester', 'Ester', 'Grupo éster.', 'C(=O)O[#6]', 'polar', 'Pode sofrer hidrólise em condições adequadas.')
ON CONFLICT DO NOTHING;

