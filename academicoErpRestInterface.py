import os
import time
import threading
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

# Load .env automatically (recommended)
from dotenv import load_dotenv
load_dotenv()

# ----------------------------
# Config helpers
# ----------------------------
def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def getenv_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def redact(s: Optional[str]) -> str:
    if not s:
        return "***"
    if len(s) <= 6:
        return "***REDACTED***"
    return s[:3] + "...***REDACTED***"

# ----------------------------
# Logging
# ----------------------------
logger = logging.getLogger("erp_facade")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

# ----------------------------
# Environment configuration
# ----------------------------
ERP_TOKEN_URL = require_env("ERP_TOKEN_URL")  # e.g. https://crosscutting.preunir.net/token
ERP_API_BASE = require_env("ERP_API_BASE")    # e.g. https://erpacademico.preunir.net/api/v1/public

ERP_USERNAME = require_env("ERP_USERNAME")
ERP_PASSWORD = require_env("ERP_PASSWORD")
ERP_CLIENT_ID = require_env("ERP_CLIENT_ID")
ERP_CLIENT_SECRET = require_env("ERP_CLIENT_SECRET")

HTTP_TIMEOUT_SECONDS = getenv_int("ERP_HTTP_TIMEOUT_SECONDS", 20)
TOKEN_SAFETY_SECONDS = getenv_int("ERP_TOKEN_SAFETY_SECONDS", 60)

# ----------------------------
# Token cache (thread-safe)
# ----------------------------
_token_lock = threading.Lock()
_access_token: Optional[str] = None
_token_expiry_epoch: float = 0.0  # epoch seconds (already safety-adjusted)

def _token_is_valid() -> bool:
    return _access_token is not None and time.time() < _token_expiry_epoch

async def _fetch_token(client: httpx.AsyncClient) -> str:
    """
    Fetch token using password grant. Uses application/x-www-form-urlencoded.
    """
    global _access_token, _token_expiry_epoch

    data = {
        "grant_type": "password",
        "username": ERP_USERNAME,
        "password": ERP_PASSWORD,
        "client_id": ERP_CLIENT_ID,
        "client_secret": ERP_CLIENT_SECRET,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    logger.info(
        "Fetching token from %s (username=%s, client_id=%s, client_secret=%s)",
        ERP_TOKEN_URL,
        ERP_USERNAME,
        ERP_CLIENT_ID,
        redact(ERP_CLIENT_SECRET),
    )

    r = await client.post(ERP_TOKEN_URL, data=data, headers=headers)
    if r.status_code < 200 or r.status_code >= 300:
        logger.error("Token request failed: status=%s body=%s", r.status_code, r.text[:500])
        raise HTTPException(status_code=502, detail=f"Token request failed ({r.status_code})")

    j = r.json()
    token = j.get("access_token")
    expires_in = int(j.get("expires_in", 0))

    if not token or expires_in <= 0:
        logger.error("Token response missing access_token or expires_in. keys=%s", list(j.keys()))
        raise HTTPException(status_code=502, detail="Token response invalid")

    expiry = time.time() + max(0, expires_in - TOKEN_SAFETY_SECONDS)

    _access_token = token
    _token_expiry_epoch = expiry

    logger.info(
        "Token acquired. expires_in=%s safety=%s valid_for~%ss",
        expires_in, TOKEN_SAFETY_SECONDS, int(_token_expiry_epoch - time.time())
    )
    return token

async def get_token(client: httpx.AsyncClient) -> str:
    """
    Get cached token or fetch a new one. Uses a lock to prevent token stampede.
    """
    global _access_token

    if _token_is_valid():
        return _access_token  # type: ignore

    with _token_lock:
        # Double-check inside lock
        if _token_is_valid():
            return _access_token  # type: ignore

        # Mark invalid and fetch outside lock to avoid await within lock
        _access_token = None

    # Fetch without holding the lock (fine; lock reduces stampede; not perfect but practical)
    return await _fetch_token(client)

async def erp_post_json(
    path: str,
    payload: Dict[str, Any],
    accept_json: bool = True,
    retry_on_401: bool = True,
) -> Any:
    """
    POST JSON to ERP API with Bearer token. If 401, refresh token once and retry.
    """
    url = ERP_API_BASE.rstrip("/") + "/" + path.lstrip("/")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        token = await get_token(client)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if accept_json:
            headers["Accept"] = "application/json"

        logger.info("POST %s", url)
        r = await client.post(url, json=payload, headers=headers)

        if r.status_code == 401 and retry_on_401:
            logger.warning("ERP returned 401. Refreshing token and retrying once.")
            await _fetch_token(client)
            token2 = _access_token
            headers["Authorization"] = f"Bearer {token2}"
            r = await client.post(url, json=payload, headers=headers)

        if r.status_code < 200 or r.status_code >= 300:
            logger.error("ERP call failed: status=%s url=%s body=%s", r.status_code, url, r.text[:800])
            raise HTTPException(status_code=502, detail=f"ERP call failed ({r.status_code})")

        return r.json()

# ----------------------------
# Normalizers
# ----------------------------
def iso_date_only(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return s.split("T", 1)[0]

def normalize_alumno(item: dict) -> dict:
    persona = item.get("Persona") or {}

    id_alumno = str(item.get("IdIntegracion") or "")
    nombre = str(persona.get("Nombre") or "")

    a1 = str(persona.get("Apellido1") or "").strip()
    a2 = str(persona.get("Apellido2") or "").strip()
    apellidos = " ".join([p for p in [a1, a2] if p])

    email_personal = str(persona.get("Email") or "")
    id_seguridad = str(persona.get("IdSeguridad") or "")
    telefono = str(persona.get("Celular") or "")

    territorio = str(persona.get("IdRefTerritorioDomicilio") or "")
    id_pais = territorio.split("-", 1)[0] if territorio else ""

    return {
        "IdAlumno": id_alumno,
        "Nombre": nombre,
        "Apellidos": apellidos,
        "EmailPersonal": email_personal,
        "IdSeguridad": id_seguridad,
        "Telefono": telefono,
        "IdPais": id_pais
    }


def normalize_matricula(m: dict) -> dict:
    plan = m.get("Plan") or {}
    estado = m.get("EstadoMatricula") or {}
    alumno = m.get("Alumno") or {}
    doc = m.get("DocumentoIdentificacionAlumno") or {}

    # Defensive: ensure dicts
    if not isinstance(plan, dict): plan = {}
    if not isinstance(estado, dict): estado = {}
    if not isinstance(alumno, dict): alumno = {}
    if not isinstance(doc, dict): doc = {}

    return {
        # idIntegración (matrícula)
        "IdIntegracionMatricula": str(m.get("IdIntegracion") or ""),

        # idPlan
        "IdPlan": str(plan.get("Id") or ""),

        # cEstadoMatricula (code) + optional human-readable
        "cEstadoMatricula": str(estado.get("Id") or ""),          # preferred “code”
        "EstadoMatriculaNombre": str(estado.get("Nombre") or ""), # optional, very useful

        # sEstadoMatricula (not available yet)
        "sEstadoMatricula": "",

        # IdAlumno (from nested Alumno)
        "IdAlumno": str(alumno.get("IdIntegracion") or ""),

        # Documento
        "TipoDocumento": str(doc.get("IdRefTipoDocumentoIdentificacionPais") or ""),
        "NumeroDocumento": str(doc.get("Numero") or ""),
    }

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="ERP Academico Facade", version="1.0.1")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tokenCached": _token_is_valid(),
        "tokenExpiresInSeconds": int(max(0, _token_expiry_epoch - time.time())) if _access_token else 0,
    }

@app.get("/aic/alumnos")
async def aic_alumnos(
    idAlumno: str = Query(..., description="IdAlumno / IdIntegracion alumno (from PingOne AIC)"),
    itemsPerPage: int = Query(10, ge=1, le=200),
):
    # Validate idAlumno
    id_str = (idAlumno or "").strip()
    if not id_str.isdigit():
        raise HTTPException(status_code=400, detail="idAlumno must be a numeric string")

    payload = {
        "filterIdPlanoOfertado": 0,
        "filterHasActiveMatriculas": True,  # keep if desired; set False if you want all alumnos regardless
        "filterIdsIntegracion": [int(id_str)],
        "orderColumnName": "",
        "orderColumnPosition": 0,
        "orderDirection": "",
        "pageIndex": 1,
        "itemsPerPage": itemsPerPage,
    }

    data = await erp_post_json("/alumnos/search-list", payload, accept_json=True)

    if not isinstance(data, list) or len(data) == 0:
        return JSONResponse(status_code=404, content={"detail": "Alumno not found"})

    # If ERP ever returns multiple, we take the first but it's useful to know
    item = data[0]
    if not isinstance(item, dict):
        raise HTTPException(status_code=502, detail="Unexpected alumnos response format")

    return normalize_alumno(item)

@app.get("/aic/matriculas")
async def aic_matriculas(
    idAlumno: str = Query(..., description="IdAlumno used for FilterIdsIntegracionAlumnos"),
    onlyActive: bool = Query(True),
    itemsPerPage: int = Query(50, ge=1, le=500),
    pageIndex: int = Query(1, ge=1, le=100000),
    # Optional backward compatibility: allow old param name alumnoId too
    alumnoId: Optional[str] = Query(None, description="DEPRECATED: use idAlumno"),
):
    # Backward compatible: if caller still sends alumnoId, accept it
    effective_id = (idAlumno or "").strip()
    if (not effective_id) and alumnoId:
        effective_id = alumnoId.strip()

    if not effective_id:
        raise HTTPException(status_code=400, detail="Missing required parameter: idAlumno")

    payload = {
        "FilterIdsIntegracionMatriculas": [],
        "FilterIdsIntegracionAlumnos": [int(effective_id)],
        "ProjectAlumno": True,
        "ProjectDocumentoIdentificacionAlumno": True,
        "ProjectPlan": True,
        "PageIndex": int(pageIndex),
        "ItemsPerPage": int(itemsPerPage),
    }

    data = await erp_post_json("/matriculas/search-list", payload, accept_json=True)

    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Unexpected matriculas response format")

    out: List[Dict[str, Any]] = []
    for m in data:
        if not isinstance(m, dict):
            continue

        estado = m.get("EstadoMatricula") or {}
        estado_nombre = str(estado.get("Nombre") or "") if isinstance(estado, dict) else ""

        if onlyActive and estado_nombre != "Alta":
            continue

        out.append(normalize_matricula(m))

    return out

