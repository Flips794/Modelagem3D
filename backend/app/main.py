from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, settings
from app.core.request_limits import BodySizeLimitMiddleware


def create_app(app_settings: Settings | None = None) -> FastAPI:
    config = app_settings or settings
    # Documentação interativa só em desenvolvimento: em produção não expõe o esquema da API.
    docs_enabled = not config.is_production

    application = FastAPI(
        title=config.app_name,
        version=config.app_version,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # add_middleware põe cada novo middleware por fora: CORS → limite de corpo → gzip → rotas.
    # /micelium/simulate devolve JSON grande (quadros da animação); respostas < 1 KB não são compactadas.
    application.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
    application.add_middleware(BodySizeLimitMiddleware, max_bytes=config.max_request_bytes)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.backend_cors_origins,
        # A API não usa cookies nem autenticação.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api/v1")

    if config.demo_routes_enabled:
        # Import tardio: em produção o OpenMM nem é carregado.
        from app.modules.simulation.router import router as simulation_router

        application.include_router(simulation_router, prefix="/api/v1")

    @application.get("/")
    def root():
        return {
            "message": "Molecular Micelle Reality Engine API",
            "version": config.app_version,
            "environment": config.app_env,
        }

    return application


app = create_app()
