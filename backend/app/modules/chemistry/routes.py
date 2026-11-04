from fastapi import APIRouter
from app.modules.chemistry.parameters.router import router as parameters_router
from app.modules.chemistry.rdkit_engine.router import (
    legacy_router as rdkit_legacy_router,
    router as rdkit_router,
)

router = APIRouter(prefix='/chemistry', tags=['Chemistry'])
router.include_router(rdkit_router)
router.include_router(rdkit_legacy_router)
router.include_router(parameters_router)


