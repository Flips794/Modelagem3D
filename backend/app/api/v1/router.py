from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine

from app.modules.analysis_packages.routes import router as analysis_packages_router
from app.modules.chemistry.routes import router as chemistry_router
from app.modules.molecules.routes import router as molecules_router
from app.modules.reference_data.routes import (
    legacy_router as chemical_parameters_legacy_router,
    router as reference_data_router,
)
from app.modules.simulation.router import router as simulation_router
from app.modules.micelium.routes import router as micelium_router

try:
    from app.modules.micelium.IA.routes import router as micelium_ai_router
except Exception:
    micelium_ai_router = None


api_router = APIRouter()


@api_router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "Molecular Micelle Reality Engine API",
    }


@api_router.get("/health/database", tags=["Health"])
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }


api_router.include_router(reference_data_router)
api_router.include_router(chemical_parameters_legacy_router)
api_router.include_router(chemistry_router)
api_router.include_router(molecules_router)
api_router.include_router(analysis_packages_router)
api_router.include_router(simulation_router)
api_router.include_router(micelium_router)

if micelium_ai_router is not None:
    api_router.include_router(micelium_ai_router)


