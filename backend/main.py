import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

import auth
import collector
import database
import retention
from routes import logs as logs_router
from routes import ws as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("DB_PATH", "/data/logs.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    database.set_db_path(db_path)
    database.init_db()

    auth.init_auth()

    await collector.start_collector()
    asyncio.create_task(retention.run_retention_loop(), name="retention")

    logger.info("CrowsNest started")
    yield

    await collector.stop_collector()
    logger.info("CrowsNest stopped")


app = FastAPI(title="CrowsNest", lifespan=lifespan)

# Auth route (public)
@app.post("/api/auth/login", response_model=auth.TokenResponse)
def login(body: auth.LoginRequest):
    if not auth.verify_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return auth.create_token()


app.include_router(logs_router.router)
app.include_router(ws_router.router)

# Serve Vue SPA — html=True makes StaticFiles return index.html for unknown paths
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
