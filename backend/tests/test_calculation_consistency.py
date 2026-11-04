"""Reproducible chemistry checks: numerical consistency is not experimental validation."""
from __future__ import annotations

from functools import lru_cache
import json
import math
import re
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError
from rdkit import Chem, RDLogger
from rdkit.Chem import Crippen

from app.modules.chemistry.parameters import validated_calculations as v
from app.modules.chemistry.parameters.router import make_response
from app.modules.chemistry.parameters.schemas import ChemistryParametersRequest, ChemistryEnvironmentRequest
from app.modules.chemistry.parameters.service import analyze_parameters
from app.modules.chemistry.rdkit_service import RDKitService
from app.modules.chemistry.rdkit_engine.parse_2d.service import Parse2DService
from app.modules.micelium.IA.prediction_service import MiceliumAIService
from app.modules.micelium.IA.schemas import MiceliumAIPredictionRequest, MiceliumAIEnvironment
from app.modules.micelium.IA.model_registry import ModelRegistry
from app.modules.micelium.IA.feature_builder import build_feature_vector, number_or_zero
from app.modules.micelium.ai_bridge import enrich_molecules_with_ai
from app.modules.micelium.engine import calculate_micellization_metrics, infer_solvent_profile, estimate_cpp_from_molecule
from app.modules.micelium.schemas import MiceliumEnvironment, MiceliumMoleculeInput, MiceliumSimulationRequest

RDLogger.DisableLog("rdApp.warning")
CATALOG = json.loads((Path(__file__).parent / 'fixtures/molecular_catalog.json').read_text())
SDS = 'CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]'
CTAB = 'CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]'

@lru_cache(maxsize=200)
def response(smiles):
    return make_response(ChemistryParametersRequest(smiles=smiles))

@lru_cache(maxsize=200)
def prediction(smiles):
    return MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=smiles))

@pytest.mark.parametrize('item', CATALOG, ids=lambda x: x['id'])
def test_catalog_formula_charge_and_complete_bond_inventory(item):
    m = response(item['smiles'])['molecule']
    # NH3/H3N and OH-/HO- are valid alternative element orderings.
    def composition(formula):
        counts = Counter()
        for element, count in re.findall(r"([A-Z][a-z]?)([0-9]*)", formula):
            counts[element] += int(count or 1)
        return counts
    assert composition(m['formula_molecular']) == composition(item['formula'])
    assert m['carga_formal_total'] == item['formal_charge']
    assert m['atom_count_total'] == m['heavy_atom_count'] + m['hydrogen_atom_count']
    assert m['bond_count_total'] == m['heavy_bond_count'] + m['hydrogen_bond_count']
    assert m['sigma_bond_count'] == m['bond_count_total']
    assert m['pi_bond_count'] == int(m['pi_bond_count'])
    assert m['peso_molecular'] > 0 and m['massa_exata'] > 0

@pytest.mark.parametrize('item', CATALOG, ids=lambda x: x['id'])
def test_catalog_identical_2d_ai_identity_descriptors_and_predictions(item):
    m, ai = response(item['smiles'])['molecule'], prediction(item['smiles'])
    d, p = ai.molecule.descriptors, ai.prediction
    assert m['smiles_fragmento_ativo']['value'] == d.active_component_smiles
    assert m['formula_molecular'] == d.formula
    assert m['peso_molecular'] == pytest.approx(d.molar_mass)
    assert m['massa_exata'] == pytest.approx(d.exact_mass)
    assert m['tpsa']['value'] == pytest.approx(d.tpsa, abs=1e-5)
    assert m['logp']['value'] == pytest.approx(d.logp, abs=1e-5)
    assert m['comprimento_cauda']['value'] == d.tail_carbon_count
    assert m['numero_caudas_hidrofobicas']['value'] == d.tail_count
    expected_cpp=d.raw_descriptors.get('packing_estimate',{}).get('cpp')
    assert m['cpp']['value']==pytest.approx(expected_cpp,abs=1e-5) if expected_cpp is not None else m['cpp']['value'] is None
    assert m['is_surfactante']['value'] == ai.molecule.is_surfactant
    assert m['classe_surfactante']['value'] == v.CLASS_PT[ai.molecule.surfactant_class]
    for expected, actual in [(m['hlb']['value'],p.predicted_hlb), (m['cmc_estimada']['value'],p.predicted_cmc_mmol_l)]:
        assert expected == pytest.approx(actual, abs=1e-5) if actual is not None else expected is None
    assert len(build_feature_vector(ai.molecule, ai.environment)) == 27

@pytest.mark.parametrize('item', CATALOG, ids=lambda x: x['id'])
def test_catalog_no_fabricated_quantum_results_or_false_physical_approval(item):
    result, ai = response(item['smiles']), prediction(item['smiles'])
    json.dumps(result, allow_nan=False)
    json.dumps(ai.model_dump(), allow_nan=False)
    m = result['molecule']
    for key in ['energia_homo','energia_lumo','gap_homo_lumo','potencial_ionizacao','afinidade_eletronica',
                'densidade','ponto_ebulicao','calor_de_formacao']:
        assert m[key]['available'] is False
        assert m[key]['value'] is None and m[key]['note']
    # Web Lite v1 (tarefa 3): dipolo e energia conformacional passam a vir do campo de força
    # MMFF94 (não quântico) quando há geometria 3D; continuam proibidos como valor inventado.
    for key in ['vetor_momento_dipolo', 'energia_conformacional']:
        field = m[key]
        if field['available']:
            assert 'MMFF94' in field['source'] and field['confidence'] in {'low', 'medium'}
            assert '1 confórmero' in field['note']
        else:
            assert field['value'] is None and field['note']
    assert m['miriam2_physical_validation']['value']['passed'] is None
    assert m['calculation_provenance']['value']['experimental_validation'] is False
    assert all(a['carga_quantica_ou_proxy']['available'] is False for a in result['atoms'])

@pytest.mark.parametrize('item', CATALOG, ids=lambda x: x['id'])
def test_catalog_2d_svg_and_parameter_panel_use_same_molecule(item):
    svg = RDKitService().parse_smiles_2d(item['smiles'])
    m = response(item['smiles'])['molecule']
    assert '<svg' in svg['svg']
    assert svg['formula'] == m['formula_molecular']
    assert svg['atom_count_total'] == m['atom_count_total']
    assert svg['bond_count_total'] == m['bond_count_total']
    assert svg['active_component_smiles'] == m['smiles_fragmento_ativo']['value']
    assert svg['logp'] == pytest.approx(m['logp']['value'], abs=1e-5)
    assert svg['tpsa'] == pytest.approx(m['tpsa']['value'], abs=1e-5)
    assert all(math.isfinite(a['x']) and math.isfinite(a['y']) for a in svg['atoms'])

@pytest.mark.parametrize('item', CATALOG, ids=lambda x: x['id'])
def test_catalog_active_parse_route_svg_and_internal_graph(item):
    drawing = Parse2DService().execute(item['smiles'])
    m = response(item['smiles'])['molecule']
    internal = drawing['internal_molecule']
    if hasattr(internal, 'model_dump'):
        internal = internal.model_dump()
    assert drawing['formula'] == m['formula_molecular']
    assert drawing['molecular_weight'] == pytest.approx(m['peso_molecular'])
    assert drawing['exact_molecular_weight'] == pytest.approx(m['massa_exata'])
    assert len(drawing['atoms']) == len(internal['atoms'])
    assert len(drawing['bonds']) == len(internal['bonds'])
    assert internal['metadata']['canonical_smiles'] == drawing['canonical_smiles']
    assert '<svg' in drawing['svg']
    assert all(math.isfinite(a['x']) and math.isfinite(a['y']) for a in drawing['atoms'])

# Hand-counted expected formulas, molecular atoms/bonds, sigma and pi bonds.
MANUAL = [
 ('O','H2O',3,2,2,0,18.015),('N','H3N',4,3,3,0,17.031),('C','CH4',5,4,4,0,16.043),
 ('CC','C2H6',8,7,7,0,30.070),('C=C','C2H4',6,5,5,1,28.054),('C#C','C2H2',4,3,3,2,26.038),
 ('CO','CH4O',6,5,5,0,32.042),('CCO','C2H6O',9,8,8,0,46.069),('O=C=O','CO2',3,2,2,2,44.009),
 ('c1ccccc1','C6H6',12,12,12,3,78.114),('c1ccncc1','C5H5N',11,11,11,3,79.102),
 ('c1cc[nH]c1','C4H5N',10,10,10,2,67.091),('c1ccoc1','C4H4O',9,9,9,2,68.075),
 ('c1ccsc1','C4H4S',9,9,9,2,84.141),('c1ccc2ccccc2c1','C10H8',18,19,19,5,128.174),
 ('CC(=O)O','C2H4O2',8,7,7,1,60.052),('CC(=O)[O-].[Na+]','C2H3NaO2',8,6,6,1,82.034),
 ('[NH4+]','H4N+',5,4,4,0,18.039),('[Na+].[Cl-]','ClNa',2,0,0,0,58.443),
 ('[H][H]','H2',2,1,1,0,2.016),('C1CCCCC1','C6H12',18,18,18,0,84.162),
]
@pytest.mark.parametrize('smiles,formula,atoms,bonds,sigma,pi,mw',MANUAL,ids=[x[0] for x in MANUAL])
def test_manual_stoichiometry_and_molecular_mass(smiles,formula,atoms,bonds,sigma,pi,mw):
    m=response(smiles)['molecule']
    assert (m['formula_molecular'],m['atom_count_total'],m['bond_count_total'],m['sigma_bond_count'],m['pi_bond_count']) == (formula,atoms,bonds,sigma,pi)
    assert m['peso_molecular'] == pytest.approx(mw,abs=.006)

@pytest.mark.parametrize('smiles,expected',[('[13CH4]',13.003354835),('[2H]O[2H]',2.014101778),('C',12.0),('O',15.99491462),('[37Cl-]',36.9659026)])
def test_atomic_mass_is_isotope_mass_not_average(smiles,expected):
    assert response(smiles)['atoms'][0]['massa_exata']['value'] == pytest.approx(expected,abs=1e-5)

@pytest.mark.parametrize('n', range(8,19))
@pytest.mark.parametrize('family',['sulfate','ammonium'])
@pytest.mark.parametrize('ionic',[0,.01,.1])
def test_homolog_cmc_matches_units_environment_and_ai(n,family,ionic):
    smiles='C'*n+('OS(=O)(=O)[O-].[Na+]' if family=='sulfate' else '[N+](C)(C)C.[Br-]')
    env={'ionic_strength_mol_l':ionic}
    two=make_response(ChemistryParametersRequest(smiles=smiles,environment=env))['molecule']
    ai=MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=smiles,environment=MiceliumAIEnvironment(**env)))
    expected=(8.2*10**(.31*(12-n))/(1+5.8*ionic) if family=='sulfate' else .92*10**(.30*(16-n))/(1+4.4*ionic))
    assert two['cmc_estimada']['value'] == pytest.approx(expected,abs=1e-5)
    assert ai.prediction.predicted_cmc_mmol_l == pytest.approx(expected)
    assert two['cmc_corrigida_mol_l']['value']*1000 == pytest.approx(expected,abs=5.1e-6)
    assert two['x_cmc']['value'] == pytest.approx((expected/1000)/(55.5+expected/1000),abs=5.1e-11)

@pytest.mark.parametrize('smiles,cmc_range,hlb',[(SDS,(7,10),40.0),(CTAB,(.92,1),None)])
def test_published_reference_ranges_at_25c_without_added_salt(smiles,cmc_range,hlb):
    # Reference-anchor checks, not an independent external validation dataset.
    m=make_response(ChemistryParametersRequest(smiles=smiles,environment={'ionic_strength_mol_l':0}))['molecule']
    assert cmc_range[0] <= m['cmc_estimada']['value'] <= cmc_range[1]
    assert m['hlb']['value'] == hlb

@pytest.mark.parametrize('env',[{'solvent_name':'hexane'},{'solvent_name':'ethanol'},{'temperature_k':273.15},
 {'temperature_k':330},{'ionic_strength_mol_l':.5},{'dielectric_constant':2},{'solvent_polarity_index':.5}])
def test_cmc_does_not_extrapolate_outside_aqueous_domain(env):
    m=make_response(ChemistryParametersRequest(smiles=SDS,environment=env))['molecule']
    assert m['cmc_estimada']['available'] is False
    ai_env={('solvent' if k=='solvent_name' else k):value for k,value in env.items()}
    assert MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=SDS,environment=MiceliumAIEnvironment(**ai_env))).prediction.predicted_cmc_mmol_l is None

@pytest.mark.parametrize('rpm',[0,100,1000,10000])
@pytest.mark.parametrize('volume',[1,100,1000])
def test_equilibrium_cmc_independent_of_stirring_and_volume(rpm,volume):
    ai=MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=SDS,environment=MiceliumAIEnvironment(agitation_rpm=rpm,volume_ml=volume)))
    assert ai.prediction.predicted_cmc_mmol_l == prediction(SDS).prediction.predicted_cmc_mmol_l

@pytest.mark.parametrize('smiles,chemical,surf',[('CC(=O)O','nonionic',False),('CCCCCCCCCCCC(=O)O','nonionic',True),
 ('CCCCCCCCCCCC(=O)[O-].[Na+]','anionic',True),('CCCCCCCC(=O)[O-].[Na+]','anionic',True),('CCCCCCCCCCCCN','nonionic',True),
 ('CCCCCCCCCCCC[NH3+].[Cl-]','cationic',True),('CCCCCCCCCCCC[N+](C)(C)[O-]','nonionic',True),
 ('CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]','zwitterionic',True),('CCCCCCCCCCCC','nonionic',False),
 ('CC(=O)N','nonionic',False),('CCCCCCCCCCCCOC(=O)C','nonionic',True)])
def test_formal_charge_and_neutral_functional_groups(smiles,chemical,surf):
    p=v.profile(Chem.MolFromSmiles(smiles))
    assert p.chemical_class==chemical and p.is_surfactant==surf
    if not surf: assert response(smiles)['molecule']['cmc_estimada']['value'] is None

@pytest.mark.parametrize('smiles,length,tails',[('CCCCCCCCCCCCO',12,1),('OCCCCCC=CCCCCC',12,1),
 ('CCCCCCCCCCCC(=O)O',11,1),('CCCCCCCCN(CCCCCCCC)CCCCCCCC',8,3),
 ('CCCCCC(C)CCCCCO',11,1),('CCCCCCCCCCCCOCCOCCO',12,1),('C1CCCCC1O',0,0)])
def test_carbon_paths_and_distinct_tails(smiles,length,tails):
    p=v.profile(Chem.MolFromSmiles(smiles))
    assert (p.tail_c,p.tail_count)==(length,tails)

@pytest.mark.parametrize('ph',range(15))
# Web Lite v1 (tarefa 5): pKa referenciados do composto-modelo (CRC) em vez dos valores arredondados
# 4,8 / 10,6 / 10; a verificação de Henderson–Hasselbalch com logP da forma neutra é a mesma.
@pytest.mark.parametrize('smiles,neutral,pka,kind',[('CC(=O)O','CC(=O)O',4.76,'acid'),
 ('CC(=O)[O-].[Na+]','CC(=O)O',4.76,'acid'),('CN','CN',10.66,'base'),
 ('C[NH3+].[Cl-]','CN',10.66,'base'),('Nc1ccccc1','Nc1ccccc1',4.6,'base'),('Oc1ccccc1','Oc1ccccc1',9.99,'acid')])
def test_henderson_hasselbalch_neutral_and_charged_forms(ph,smiles,neutral,pka,kind):
    m=make_response(ChemistryParametersRequest(smiles=smiles,environment={'ph':ph}))['molecule']
    exponent=ph-pka if kind=='acid' else pka-ph
    expected=Crippen.MolLogP(Chem.MolFromSmiles(neutral))-math.log10(1+10**exponent)
    assert m['pka']['value']==pka
    assert m['logd']['value']==pytest.approx(expected,abs=1e-5)

@pytest.mark.parametrize('smiles',['CC(=O)N',CTAB,'O=C(O)CCC(=O)O','NCCN',SDS,'CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]'])
def test_no_generic_amine_pka_for_amides_permanent_ions_or_polyprotic(smiles):
    pka = response(smiles)['molecule']['pka']
    if smiles == 'CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]':
        # Web Lite v1 (tarefa 5): betaína recebe o pKa específico e referenciado da carboxila (1,83),
        # não um pKa genérico de amina/carboxila.
        assert pka['available'] is False or (pka['value'] == 1.83 and 'betaína' in pka['note'].lower())
        return
    assert pka['available'] is False

@pytest.mark.parametrize('smiles,ap,mw,rb',[('c1ccccc1',1,78.114,0),('c1ccc2ccccc2c1',1,128.174,0),('CCO',0,46.069,0),('Oc1ccccc1',6/7,94.113,0)])
def test_esol_uses_aromatic_atom_fraction_not_ring_count(smiles,ap,mw,rb):
    logp=Crippen.MolLogP(Chem.MolFromSmiles(smiles))
    expected=.16-.63*logp-.0062*mw+.066*rb-.74*ap
    assert response(smiles)['molecule']['logs']['value']==pytest.approx(expected,abs=1e-5)

@pytest.mark.parametrize('smiles',[SDS,CTAB,'[Na+]','CC(=O)[O-]','C'*100+'O'])
def test_esol_rejects_ions_and_unsupported_large_molecules(smiles):
    assert response(smiles)['molecule']['logs']['available'] is False

@pytest.mark.parametrize('n',[8,12,16,18])
@pytest.mark.parametrize('eo',[1,3,6,12,23])
def test_griffin_ethoxylated_alcohol_uses_eo_mass_fraction(n,eo):
    smiles='C'*n+'O'+'CCO'*eo
    expected=20*eo*44.053/(14.027*n+18.015+eo*44.053)
    m=response(smiles)['molecule']
    assert m['hlb_griffin']['value']==pytest.approx(expected,abs=1e-5)
    assert 'E/5' in m['hlb']['source']

@pytest.mark.parametrize('smiles',[CTAB,'CCCCCCCCCCCCOC(=O)C','CCCCCCCCCCCCS(=O)(=O)[O-].[Na+]'])
def test_hlb_has_no_invented_groups_for_unsupported_heads(smiles):
    assert response(smiles)['molecule']['hlb']['available'] is False

@pytest.mark.parametrize('equivalent',[SDS,'[Na+].[O-]S(=O)(=O)OCCCCCCCCCCCC'])
def test_equivalent_salt_order_and_canonical_smiles_do_not_change_results(equivalent):
    a=response(SDS)['molecule'];b=response(equivalent)['molecule']
    for k in ['peso_molecular','formula_molecular','massa_exata','hlb','cmc_estimada','logp','tpsa']:
        assert a[k]==b[k]

@pytest.mark.parametrize('counterion',['OCC[NH+](CCO)CCO','[Na+]','[K+]'])
def test_organic_counterion_does_not_replace_amphiphile(counterion):
    smiles='CCCCCCCCCCCCOS(=O)(=O)[O-].'+counterion
    m=response(smiles)['molecule'];ai=prediction(smiles).molecule
    assert m['comprimento_cauda']['value']==12
    assert m['carga_formal_fragmento_ativo']['value']==-1
    assert m['smiles_fragmento_ativo']['value']==ai.descriptors.active_component_smiles
    assert len(m['contraions_detectados']['value'])==1

@pytest.mark.parametrize('unit,value,expected',[('mol/L',.01,10),('mmol/L',10,10),('µmol/L',10000,10),('μmol/L',10000,10),
 ('mol',.001,10),('mmol',1,10),('µmol',1000,10),('g/L',2.8838,10),('mg/L',2883.8,10),('g',.28838,10),('mg',288.38,10)])
@pytest.mark.parametrize('volume',[50,100,1000])
def test_concentration_units_and_real_amounts_are_used(unit,value,expected,volume):
    # Mass fixture rounded independently to manufacturer SDS MW 288.38 g/mol.
    if '/' not in unit: value*=volume/100
    ai=MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=SDS,concentration=value,unit=unit,
        environment=MiceliumAIEnvironment(volume_ml=volume,ionic_strength_mol_l=0)))
    actual=ai.environment.surfactant_concentration_mmol_l
    assert actual==pytest.approx(expected,rel=1e-4)
    assert ai.prediction.c_over_cmc==pytest.approx(actual/8.2)
    assert ai.prediction.critical_amount_mmol==pytest.approx(8.2*volume/1000)
    assert ai.prediction.excess_amount_mmol==pytest.approx(max(0,(actual-8.2)*volume/1000))

@pytest.mark.parametrize('unit',['partes','% m/m','mL','molecules'])
def test_unsupported_unit_is_rejected_not_treated_as_mmol_l(unit):
    with pytest.raises(ValueError):
        MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=SDS,concentration=10,unit=unit))

@pytest.mark.parametrize('model',[ChemistryEnvironmentRequest,MiceliumAIEnvironment,MiceliumEnvironment])
@pytest.mark.parametrize('field,bad',[('temperature_k',0),('temperature_k',float('inf')),('temperature_k',float('nan')),
 ('pressure_atm',-1),('pressure_atm',float('inf')),('ph',-1),('ph',15),('ph',float('nan')),
 ('ionic_strength_mol_l',-1),('ionic_strength_mol_l',float('inf')),('volume_ml',0),('volume_ml',float('nan')),
 ('dielectric_constant',0),('agitation_rpm',-1),('solvent_polarity_index',1.1)])
def test_invalid_physical_environment_never_silently_clamps_or_defaults(model,field,bad):
    with pytest.raises(ValidationError): model(**{field:bad})

@pytest.mark.parametrize('field',['real_amount_mmol','real_concentration_mmol_l','cmc_mmol_l','logp','tpsa'])
@pytest.mark.parametrize('bad',[float('nan'),float('inf'),float('-inf')])
def test_nonfinite_molecular_input_is_rejected(field,bad):
    with pytest.raises(ValidationError): MiceliumMoleculeInput(smiles=SDS,**{field:bad})

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),None,'bad'])
def test_nonfinite_model_feature_never_reaches_estimator(bad):
    assert number_or_zero(bad)==0

@pytest.mark.parametrize('volume',[1,100,1000])
@pytest.mark.parametrize('count',[1,12,800])
def test_engine_mixture_uses_real_moles_not_visual_counts_or_double_salt_correction(volume,count):
    a=MiceliumMoleculeInput(smiles=SDS,is_surfactant=True,cmc_mmol_l=10,real_concentration_mmol_l=6,count=count)
    b=MiceliumMoleculeInput(smiles=CTAB,is_surfactant=True,cmc_mmol_l=20,real_concentration_mmol_l=12,count=801-count)
    request=MiceliumSimulationRequest(molecules=[a,b],environment=MiceliumEnvironment(volume_ml=volume,ionic_strength_mol_l=.1))
    metrics=calculate_micellization_metrics(request.molecules,volume,infer_solvent_profile(request))
    assert metrics.c_over_cmc==pytest.approx(1.2)
    assert metrics.real_amount_mmol==pytest.approx(18*volume/1000)
    assert metrics.critical_amount_mmol==pytest.approx(15*volume/1000)

@pytest.mark.parametrize('missing',['cmc_mmol_l','real_concentration_mmol_l'])
def test_engine_incomplete_mixture_does_not_return_known_subset_as_total(missing):
    data=dict(smiles=SDS,is_surfactant=True,cmc_mmol_l=10,real_concentration_mmol_l=6)
    a=MiceliumMoleculeInput(**data);data[missing]=None;b=MiceliumMoleculeInput(**data)
    assert calculate_micellization_metrics([a,b],100).c_over_cmc is None

@pytest.mark.parametrize('model',[MiceliumEnvironment,MiceliumAIEnvironment])
def test_default_environment_is_compatible_across_modules(model):
    value=model().model_dump()
    two=ChemistryEnvironmentRequest().model_dump()
    assert all(value[k]==two[k] for k in two if k in value)

@pytest.mark.parametrize('volume',[10,100,1000])
def test_conflicting_amount_and_concentration_are_rejected(volume):
    with pytest.raises(ValidationError):
        MiceliumSimulationRequest(molecules=[MiceliumMoleculeInput(smiles=SDS,real_amount_mmol=2,real_concentration_mmol_l=10)],
                                  environment=MiceliumEnvironment(volume_ml=volume))

def test_conflicting_top_level_and_environment_concentration_rejected():
    with pytest.raises(ValueError):
        MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=SDS,concentration=10,unit='mmol/L',environment=MiceliumAIEnvironment(surfactant_concentration_mmol_l=20)))

@pytest.mark.parametrize('smiles',['','C(','C(C)(C)(C)(C)C','not smiles'])
def test_invalid_smiles_never_produces_prediction(smiles):
    with pytest.raises(ValueError): make_response(ChemistryParametersRequest(smiles=smiles))
    with pytest.raises(ValueError): MiceliumAIService().predict(MiceliumAIPredictionRequest(smiles=smiles))

@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),-1,0])
def test_invalid_trained_cmc_falls_back_and_is_not_marked_trained(value):
    class Estimator:
        def predict(self, features): return [value]
    registry=ModelRegistry();registry._cache['anionic_ai:cmc_mmol_l']=Estimator()
    ai=MiceliumAIService(registry).predict(MiceliumAIPredictionRequest(smiles=SDS))
    assert ai.prediction.predicted_cmc_mmol_l==prediction(SDS).prediction.predicted_cmc_mmol_l
    assert ai.prediction.prediction_json['methods']['cmc']!='trained_model'

def test_corrupt_model_file_is_safe_and_does_not_hide_descriptor_results(tmp_path):
    target=tmp_path/'anionic_ai';target.mkdir();(target/'cmc_mmol_l.joblib').write_bytes(b'not a joblib model')
    ai=MiceliumAIService(ModelRegistry(tmp_path)).predict(MiceliumAIPredictionRequest(smiles=SDS))
    assert ai.prediction.predicted_cmc_mmol_l==prediction(SDS).prediction.predicted_cmc_mmol_l

def test_valid_trained_target_is_identified_as_trained_without_claiming_experimental_validation():
    class Estimator:
        def predict(self, features): return [9.125]
    registry=ModelRegistry();registry._cache['anionic_ai:cmc_mmol_l']=Estimator()
    ai=MiceliumAIService(registry).predict(MiceliumAIPredictionRequest(smiles=SDS))
    assert ai.prediction.predicted_cmc_mmol_l==9.125
    assert ai.prediction.prediction_json['methods']['cmc']=='trained_model'
    assert ai.prediction.prediction_json['experimental_validation'] is False

@pytest.mark.parametrize('smiles',[SDS,CTAB,'CCO'])
def test_legacy_service_has_same_results_as_active_route(smiles):
    a=analyze_parameters(ChemistryParametersRequest(smiles=smiles))['molecule'];b=response(smiles)['molecule']
    for k in ['formula_molecular','peso_molecular','hlb','cmc_estimada','energia_homo','pka','logd']: assert a[k]==b[k]

@pytest.mark.parametrize('smiles',[SDS,CTAB,'CCO','CCCCCCCCCCCCO'])
def test_3d_automatic_enrichment_uses_same_2d_values(smiles):
    molecules,_=enrich_molecules_with_ai([MiceliumMoleculeInput(smiles=smiles)],MiceliumEnvironment())
    m=response(smiles)['molecule'];three=molecules[0]
    assert three.is_surfactant==m['is_surfactante']['value']
    assert three.tail_carbon_count==m['comprimento_cauda']['value']
    assert three.hlb==pytest.approx(m['hlb']['value'],abs=1e-5) if m['hlb']['value'] is not None else three.hlb is None
    assert three.cmc_mmol_l==pytest.approx(m['cmc_estimada']['value'],abs=1e-5) if m['cmc_estimada']['value'] is not None else three.cmc_mmol_l is None

@pytest.mark.parametrize('ionic,expected',[(.001,9.61),(.01,3.04),(.1,.961)])
def test_debye_screening_matches_si_formula_reference(ionic,expected):
    assert v.debye_nm({'ionic_strength_mol_l':ionic})==pytest.approx(expected,rel=.002)


@pytest.mark.parametrize('smiles',[SDS,CTAB,'CCCCCCCCCCCCO','CCCCCCCCCCCCN','CCCCCCCCCCCC(=O)O',
 'CCCCCCCCN(CCCCCCCC)CCCCCCCC','CCCCCC(C)CCCCCO','OCCCCCC=CCCCCC'])
def test_packing_parameter_has_same_formula_and_domain_in_2d_and_3d(smiles):
    two=response(smiles)['molecule']
    enriched,_=enrich_molecules_with_ai([MiceliumMoleculeInput(smiles=smiles)],MiceliumEnvironment())
    cpp=estimate_cpp_from_molecule(enriched[0])
    if two['cpp']['value'] is None:
        assert cpp is None
    else:
        assert cpp==pytest.approx(two['cpp']['value'],abs=1e-5)
        volume=two['volume_cauda']['value'];area=two['area_cabeca_micela']['value'];length=two['comprimento_maximo_cauda']['value']
        assert cpp==pytest.approx(volume/(area*length))
        assert enriched[0].head_area_a2==area
        assert enriched[0].tail_volume_a3==pytest.approx(volume,abs=5.1e-6)


def test_user_head_area_and_volume_override_is_preserved():
    molecule=MiceliumMoleculeInput(smiles=SDS,head_area_a2=80,tail_volume_a3=320)
    enriched,_=enrich_molecules_with_ai([molecule],MiceliumEnvironment())
    assert enriched[0].packing_parameter==pytest.approx(320/(80*(1.5+1.265*12)))


@pytest.mark.parametrize('volume',[1,100,1000])
def test_zero_concentration_has_zero_ratio_with_known_single_cmc(volume):
    molecule=MiceliumMoleculeInput(smiles=SDS,is_surfactant=True,cmc_mmol_l=10,real_concentration_mmol_l=0)
    metrics=calculate_micellization_metrics([molecule],volume)
    assert metrics.c_over_cmc==0 and metrics.real_amount_mmol==0
    assert metrics.critical_amount_mmol==pytest.approx(10*volume/1000)


def test_neutral_other_fragment_is_not_reported_as_counterion():
    result=response('CCCCCCCCCCCCO.CCO')['molecule']
    assert result['contraions_detectados']['value']==[]


@pytest.mark.parametrize('smiles,expected',[
 ('CCCCCCCCCCCC[N+](=O)[O-]','nonionic'),
 ('CCCCCCCCCCCC[S+](C)[O-]','nonionic'),
 ('CCCCCCCCCCCC[P+](C)(C)[O-]','nonionic'),
 ('[O-][n+]1ccccc1CCCCCCCCCCCC','nonionic'),
 ('CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]','zwitterionic'),
])
def test_resonance_charge_pairs_are_not_confused_with_independent_zwitterionic_sites(smiles,expected):
    structure=v.profile(Chem.MolFromSmiles(smiles))
    assert structure.chemical_class==expected and structure.is_surfactant
    assert prediction(smiles).molecule.surfactant_class==expected
