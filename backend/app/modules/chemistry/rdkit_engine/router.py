from fastapi import APIRouter

try:
    from app.modules.chemistry.rdkit_engine.graph_to_smiles.routes import (
        router as graph_to_smiles_router,
    )
except ModuleNotFoundError:
    from app.modules.chemistry.rdkit_engine.graph_to_smiles.router import (
        router as graph_to_smiles_router,
    )

try:
    from app.modules.chemistry.rdkit_engine.parse_2d.routes import (
        router as parse_2d_router,
    )
except ModuleNotFoundError:
    from app.modules.chemistry.rdkit_engine.parse_2d.router import (
        router as parse_2d_router,
    )

from app.modules.chemistry.rdkit_engine.optimize_2d.router import (
    router as optimize_2d_router,
)

from app.modules.chemistry.rdkit_engine.hydrogens_2d.router import (
    router as hydrogens_2d_router,
)


router = APIRouter(prefix="/rdkit", tags=["Chemistry / RDKit"])
legacy_router = APIRouter(tags=["Chemistry / RDKit Legacy"])


# Endpoints principais:
# /api/v1/chemistry/rdkit/parse-2d
# /api/v1/chemistry/rdkit/graph-to-smiles
# /api/v1/chemistry/rdkit/optimize-2d
# /api/v1/chemistry/rdkit/hydrogens-2d
router.include_router(parse_2d_router)
router.include_router(graph_to_smiles_router)
router.include_router(optimize_2d_router)
router.include_router(hydrogens_2d_router)


# Endpoints legacy/compatibilidade:
# /api/v1/chemistry/parse-2d
# /api/v1/chemistry/graph-to-smiles
# /api/v1/chemistry/optimize-2d
# /api/v1/chemistry/hydrogens-2d
legacy_router.include_router(parse_2d_router)
legacy_router.include_router(graph_to_smiles_router)
legacy_router.include_router(optimize_2d_router)
legacy_router.include_router(hydrogens_2d_router)

