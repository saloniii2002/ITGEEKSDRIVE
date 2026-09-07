from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.bills import router as bills_router
from backend.app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Bill Splitter MVP API",
    version="1.0.0",
    description="Deterministic Bill Splitter backend with AI Vision extraction, human review, and proportional tax/service allocation.",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(bills_router, prefix="")
app.include_router(bills_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "bill-splitter"}


# Mount frontend static build directory if present
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
