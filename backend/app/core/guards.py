"""Proteções da versão pública: escrita no banco, tamanho de simulação e mensagens de erro."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request

from app.core.config import settings_for

logger = logging.getLogger("modelagem3d")


def require_db_writes(request: Request) -> None:
    if not settings_for(request).db_writes_enabled:
        raise HTTPException(status_code=403, detail="Gravação no banco desativada nesta instalação (ENABLE_DB_WRITES).")


def check_simulation_size(request: Request, *, molecules: int, max_particles: int, steps: int) -> None:
    config = settings_for(request)
    if not config.is_production:
        return
    if molecules > config.public_max_molecules:
        raise HTTPException(status_code=422, detail=f"Acima do limite da versão web: no máximo {config.public_max_molecules} moléculas por mistura.")
    if max_particles > config.public_max_particles:
        raise HTTPException(status_code=422, detail=f"Acima do limite da versão web: max_particles até {config.public_max_particles}.")
    if steps > config.public_max_steps:
        raise HTTPException(status_code=422, detail=f"Acima do limite da versão web: steps até {config.public_max_steps} por trecho.")


def public_error_detail(request: Request, exc: Exception, development_detail: str, public_message: str) -> str:
    """Em produção não devolve mensagem nem traceback internos; o detalhe vai para o log do servidor."""
    if settings_for(request).is_production:
        logger.exception("erro interno em %s", request.url.path, exc_info=exc)
        return f"{public_message} ({type(exc).__name__}). O detalhe ficou no log do servidor."
    return development_detail
