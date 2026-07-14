from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .version import __version__


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Eval-first observability for report-generating LLM workflows.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


from .routers import dashboard, evaluations, human_reviews, regression, reports, runs  # noqa: E402

app.include_router(runs.router)
app.include_router(evaluations.router)
app.include_router(human_reviews.router)
app.include_router(dashboard.router)
app.include_router(regression.router)
app.include_router(reports.router)
