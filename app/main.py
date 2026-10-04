from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.rate_limit import RateLimiter
from app.routes.cases import router as cases_router
from app.routes.children import router as children_router
from app.routes.events import router as events_router
from app.routes.guardians import router as guardians_router
from app.routes.images import router as images_router
from app.routes.messages import router as messages_router
from app.routes.sessions import router as sessions_router
from app.session import SessionStore
from services.agent_client import AgentClient
from services.child_repository import ChildRepository
from services.event_broker import EventBroker
from services.guardian_repository import GuardianRepository
from services.image_service import ImageService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    app.state.session_store = SessionStore(settings.redis_url)
    app.state.rate_limiter = RateLimiter(
        redis_url=settings.redis_url,
        message_limit=settings.rate_limit_messages_per_minute,
        image_limit=settings.rate_limit_images_per_hour,
    )
    app.state.agent_client = AgentClient(
        base_url=settings.agent_service_url,
        api_key=settings.shelter_backend_api_key,
    )
    app.state.event_broker = EventBroker()
    app.state.image_service = ImageService(settings)
    app.state.child_repository = ChildRepository()
    app.state.guardian_repository = GuardianRepository()
    try:
        yield
    finally:
        await app.state.event_broker.close()
        await app.state.agent_client.close()
        await app.state.rate_limiter.close()
        await app.state.session_store.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="WayFind UI Backend", lifespan=lifespan)
    app.state.settings = settings
    app.state.child_repository = ChildRepository()
    app.state.guardian_repository = GuardianRepository()
    app.state.session_store = SessionStore(settings.redis_url)
    app.state.rate_limiter = RateLimiter(
        redis_url=settings.redis_url,
        message_limit=settings.rate_limit_messages_per_minute,
        image_limit=settings.rate_limit_images_per_hour,
    )
    app.state.agent_client = AgentClient(
        base_url=settings.agent_service_url,
        api_key=settings.shelter_backend_api_key,
    )
    app.state.event_broker = EventBroker()
    app.state.image_service = ImageService(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix="/api")
    api_router.include_router(sessions_router)
    api_router.include_router(messages_router)
    api_router.include_router(events_router)
    api_router.include_router(images_router)
    api_router.include_router(children_router)
    api_router.include_router(cases_router)
    api_router.include_router(guardians_router)
    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok", "service": "wayfind-ui-backend"}

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "The request could not be validated."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

    return app


app = create_app()