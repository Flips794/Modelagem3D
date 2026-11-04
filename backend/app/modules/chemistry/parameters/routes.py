from __future__ import annotations

from fastapi import APIRouter

from app.modules.chemistry.parameters.router import router as parameters_router

router = APIRouter(prefix="/chemistry", tags=["Chemistry"])

router.include_router(parameters_router)

