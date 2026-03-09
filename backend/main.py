"""FastAPI application for GhostProtocol — NHI Security Auditing Platform.

Exposes REST endpoints consumed by the Next.js dashboard to scan,
analyse, and quarantine Non-Human Identities in AWS.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from pythonjsonlogger import jsonlogger

from config import LOG_LEVEL, CORS_ORIGINS, API_KEY
from database import get_all_identities, get_identity
from scanner import get_nhi_profiles, quarantine_identity
from analyzer import generate_least_privilege_policy

# ---------------------------------------------------------------------------
# Structured JSON Logging
# ---------------------------------------------------------------------------
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(
    jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[_log_handler],
)
logger = logging.getLogger("ghostprotocol.app")

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GhostProtocol backend starting")
    yield
    logger.info("GhostProtocol backend shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="GhostProtocol API",
    description="Non-Human Identity (NHI) Security Auditing Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request-ID Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# API-Key Authentication (optional — only enforced when GHOSTPROTOCOL_API_KEY is set)
# ---------------------------------------------------------------------------
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)):
    """Validate the API key if one is configured."""
    if not API_KEY:  # auth disabled
        return
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class QuarantineRequest(BaseModel):
    arn: str


class AnalyzeRequest(BaseModel):
    arn: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
@limiter.limit("120/minute")
def health(request: Request):
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/scan")
@limiter.limit("10/minute")
def scan_identities(request: Request, _: None = Depends(verify_api_key)):
    """Trigger an AWS scan and persist discovered NHI profiles to Supabase."""
    try:
        profiles = get_nhi_profiles()
        return {"scanned": len(profiles), "profiles": profiles}
    except Exception as exc:
        logger.exception("Scan failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/identities")
@limiter.limit("60/minute")
def list_identities(request: Request, _: None = Depends(verify_api_key)):
    """Return all audited identities from Supabase, ordered by risk."""
    try:
        return get_all_identities()
    except Exception as exc:
        logger.exception("Failed to fetch identities")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/identities/{arn:path}")
@limiter.limit("60/minute")
def get_single_identity(arn: str, request: Request, _: None = Depends(verify_api_key)):
    """Fetch a single identity by its ARN."""
    identity = get_identity(arn)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity not found")
    return identity


@app.post("/analyze")
@limiter.limit("10/minute")
def analyze_identity(req: AnalyzeRequest, request: Request, _: None = Depends(verify_api_key)):
    """Run AI analysis on an identity to generate a least-privilege policy."""
    identity = get_identity(req.arn)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity not found")

    try:
        result = generate_least_privilege_policy(
            current_policy=identity.get("allowed_actions", {}),
            used_actions=identity.get("used_actions", []),
        )
        return result
    except Exception as exc:
        logger.exception("Analysis failed for %s", req.arn)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/quarantine")
@limiter.limit("5/minute")
def quarantine(req: QuarantineRequest, request: Request, _: None = Depends(verify_api_key)):
    """Quarantine an identity by attaching a Deny-All permissions boundary."""
    try:
        result = quarantine_identity(req.arn)
        return result
    except Exception as exc:
        logger.exception("Quarantine failed for %s", req.arn)
        raise HTTPException(status_code=500, detail=str(exc))
