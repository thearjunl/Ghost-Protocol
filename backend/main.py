"""FastAPI application for GhostProtocol — NHI Security Auditing Platform.

Exposes REST endpoints consumed by the Next.js dashboard to scan,
analyse, and quarantine Non-Human Identities in AWS.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import LOG_LEVEL
from database import get_all_identities, get_identity
from scanner import get_nhi_profiles, quarantine_identity
from analyzer import generate_least_privilege_policy

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ghostprotocol.app")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
def health():
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/scan")
def scan_identities():
    """Trigger an AWS scan and persist discovered NHI profiles to Supabase."""
    try:
        profiles = get_nhi_profiles()
        return {"scanned": len(profiles), "profiles": profiles}
    except Exception as exc:
        logger.exception("Scan failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/identities")
def list_identities():
    """Return all audited identities from Supabase, ordered by risk."""
    try:
        return get_all_identities()
    except Exception as exc:
        logger.exception("Failed to fetch identities")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/identities/{arn:path}")
def get_single_identity(arn: str):
    """Fetch a single identity by its ARN."""
    identity = get_identity(arn)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity not found")
    return identity


@app.post("/analyze")
def analyze_identity(req: AnalyzeRequest):
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
def quarantine(req: QuarantineRequest):
    """Quarantine an identity by attaching a Deny-All permissions boundary."""
    try:
        result = quarantine_identity(req.arn)
        return result
    except Exception as exc:
        logger.exception("Quarantine failed for %s", req.arn)
        raise HTTPException(status_code=500, detail=str(exc))
