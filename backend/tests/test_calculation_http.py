"""Real HTTP routes without opening a database or using external lookup."""
import json
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://validation:validation@127.0.0.1/validation')
from app.modules.chemistry.routes import router as chemistry_router
from app.modules.micelium.routes import router as cg_router
from app.modules.micelium.IA.routes import router as ai_router

app=FastAPI()
for router in [chemistry_router, cg_router, ai_router]: app.include_router(router,prefix='/api/v1')
client=TestClient(app)
SDS='CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]'

@pytest.mark.parametrize('smiles',['O','CCO',SDS,'c1cc[nH]c1','CC(=O)N'])
def test_http_svg_panel_and_identity_agree(smiles):
    drawing=client.post('/api/v1/chemistry/rdkit/parse-2d',json={'identifier':smiles})
    panel=client.post('/api/v1/chemistry/parameters/analyze',json={'smiles':smiles})
    ai=client.post('/api/v1/micelium-ai/predict',json={'smiles':smiles})
    assert drawing.status_code==panel.status_code==ai.status_code==200
    d,m,p=drawing.json(),panel.json()['molecule'],ai.json()['molecule']
    assert d['formula']==m['formula_molecular']==p['descriptors']['formula']
    assert d['molecular_weight']==pytest.approx(m['peso_molecular'])
    assert '<svg' in d['svg']
    assert len(d['atoms'])==d['internal_molecule']['metadata']['atom_count']
    assert len(d['bonds'])==d['internal_molecule']['metadata']['bond_count']
    assert m['energia_homo']['available'] is False
    json.dumps(panel.json(),allow_nan=False)

@pytest.mark.parametrize('field,bad',[('temperature_k',0),('ph',15),('volume_ml',0),('ionic_strength_mol_l',-1),('temperature_k','NaN')])
def test_http_invalid_environment_returns_422_not_fabricated_default(field,bad):
    assert client.post('/api/v1/chemistry/parameters/analyze',json={'smiles':SDS,'environment':{field:bad}}).status_code==422
    assert client.post('/api/v1/micelium-ai/predict',json={'smiles':SDS,'environment':{field:bad}}).status_code==422

@pytest.mark.parametrize('url,payload',[('/chemistry/parameters/analyze',{'smiles':'C('}),('/micelium-ai/predict',{'smiles':'C('}),
 ('/micelium-ai/analyze',{'smiles':'C('}),('/micelium-ai/predict',{'smiles':SDS,'concentration':3,'unit':'partes'})])
def test_http_caller_error_is_not_an_internal_server_error(url,payload):
    assert client.post('/api/v1'+url,json=payload).status_code==400

@pytest.mark.parametrize('solvent',['water','ethanol','hexane'])
def test_http_cg_metrics_use_shared_prediction_in_selected_solvent(solvent):
    two=client.post('/api/v1/chemistry/parameters/analyze',json={'smiles':SDS,'environment':{'solvent_name':solvent}}).json()['molecule']
    three=client.post('/api/v1/micelium/simulate',json={'molecules':[{'smiles':SDS,'count':8,'real_concentration_mmol_l':30}],
        'environment':{'solvent_name':solvent},'steps':2,'max_particles':64})
    assert three.status_code==200,three.text
    result=three.json();cmc=two['cmc_estimada']['value']
    if cmc is None:
        assert result['analysis']['c_over_cmc_proxy'] is None
    else:
        assert result['analysis']['c_over_cmc_proxy']==pytest.approx(30/cmc,rel=1e-6)
    json.dumps(result,allow_nan=False)
    assert result['frames']
    assert all(len(f['coordinates'])==len(result['particles']) for f in result['frames'])
