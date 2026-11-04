# Micelium Engine

Motor coarse-grained inicial para micelas e múltiplas moléculas.

## Endpoints

```txt
POST /api/v1/micelium/simulate
POST /api/v1/micelium/environment/apply
```

## Integração no router v1

Em `backend/app/api/v1/router.py`, garanta algo equivalente a:

```python
from app.modules.micelium.routes import router as micelium_router

api_router.include_router(micelium_router)
```

Se o seu projeto usa `router = APIRouter()` em vez de `api_router`, use:

```python
router.include_router(micelium_router)
```

## Observação científica

Este motor é uma camada supramolecular simplificada/coarse-grained. Ele serve para visualização, pré-organização micelar e resposta qualitativa a ambiente. Não substitui dinâmica molecular atomística, GROMACS/OpenMM completo ou modelos experimentais calibrados de CMC.


