import os
import time
import secrets
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="Mock ERP Académico API", version="1.1.0")

# ----------------------------
# Mock token store
# ----------------------------
# token -> expiry_epoch
TOKENS: Dict[str, float] = {}

MOCK_EXPIRES_IN = int(os.getenv("MOCK_TOKEN_EXPIRES_IN", "1199"))  # seconds


def _issue_token() -> Dict[str, Any]:
    token = secrets.token_urlsafe(48)
    expires_at = time.time() + MOCK_EXPIRES_IN
    TOKENS[token] = expires_at
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": MOCK_EXPIRES_IN,
        "refresh_token": secrets.token_urlsafe(48),
        "id_token": secrets.token_urlsafe(64),
    }


def _require_bearer(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = auth.split(" ", 1)[1].strip()
    exp = TOKENS.get(token)
    if not exp:
        raise HTTPException(status_code=401, detail="Invalid token")
    if time.time() >= exp:
        TOKENS.pop(token, None)
        raise HTTPException(status_code=401, detail="Token expired")
    return token


def _get_page_params(payload: Dict[str, Any]) -> (int, int):
    """
    Supports both casing styles seen in your samples:
      PageIndex / ItemsPerPage
      pageIndex / itemsPerPage
    PageIndex is 1-based.
    """
    page_index = payload.get("PageIndex", payload.get("pageIndex", 1))
    items_per_page = payload.get("ItemsPerPage", payload.get("itemsPerPage", 10))

    try:
        page_index = int(page_index)
    except Exception:
        page_index = 1

    try:
        items_per_page = int(items_per_page)
    except Exception:
        items_per_page = 10

    if page_index < 1:
        page_index = 1
    if items_per_page < 1:
        items_per_page = 10
    if items_per_page > 500:
        items_per_page = 500

    return page_index, items_per_page


def _paginate(items: List[Any], page_index: int, items_per_page: int) -> List[Any]:
    start = (page_index - 1) * items_per_page
    end = start + items_per_page
    return items[start:end]


# ----------------------------
# Sample data
# ----------------------------
# alumnos/search-list: filterIdsIntegracion: [<idAlumno>]
ALUMNOS_BY_IDINTEGRACION: Dict[int, Dict[str, Any]] = {
    988224: {
        "Id": 300674862,
        "EmailAlumno": "multiofertareserva20011058_psl@yopmail.com",
        "IdIntegracion": "988224",
        "Persona": {
            "Id": 300674862,
            "Nombre": "Multioferta",
            "Apellido1": "Reserva Testpsl",
            "Apellido2": "",
            "Email": "multiofertareserva20011058_psl@yopmail.com",
            "Telefono": "+593-65998855",
            "Celular": "+593-65998855",
            "IdSeguridad": "51c9c98f-1d1a-4971-b2c7-749727090a04",
            "FechaNacimiento": "1987-10-18T00:00:00Z",
            "Sexo": "F",
            "IdRefPaisNacionalidad": "EC",
            "IdRefTerritorioDomicilio": "EC-101-102",
            "DireccionDomicilio": "Direccion Nacional",
            "CodigoPostalDomicilio": "22558",
            "Foto": "Captura de pantalla 2025-02-18 123148.png",
            "FechaSubidaFoto": "2026-01-20T15:42:29.737Z",
            "IdIntegracionDocFoto": "1275726",
            "NombrePaisDomicilio": "Ecuador",
            "IdRefTerritorioNacimiento": "EC-101-102",
        },
    },
    988225: {
        "Id": 300674863,
        "EmailAlumno": "ana.perez@unir.test",
        "IdIntegracion": "988225",
        "Persona": {
            "Id": 300674863,
            "Nombre": "Ana",
            "Apellido1": "Pérez",
            "Apellido2": "Gómez",
            "Email": "ana.perez@unir.test",
            "Telefono": "+34-600000001",
            "Celular": "+34-600000001",
            "IdSeguridad": "11111111-1111-1111-1111-111111111111",
            "FechaNacimiento": "1992-05-03T00:00:00Z",
            "Sexo": "F",
            "IdRefPaisNacionalidad": "ES",
            "IdRefTerritorioDomicilio": "ES-M-28079",
            "DireccionDomicilio": "Calle Mayor 1",
            "CodigoPostalDomicilio": "28013",
            "NombrePaisDomicilio": "España",
        },
    },
    988226: {
        "Id": 300674864,
        "EmailAlumno": "carlos.lopez@unir.test",
        "IdIntegracion": "988226",
        "Persona": {
            "Id": 300674864,
            "Nombre": "Carlos",
            "Apellido1": "López",
            "Apellido2": "",
            "Email": "carlos.lopez@unir.test",
            "Telefono": "+34-600000002",
            "Celular": "+34-600000002",
            "IdSeguridad": "22222222-2222-2222-2222-222222222222",
            "FechaNacimiento": "1989-11-22T00:00:00Z",
            "Sexo": "M",
            "IdRefPaisNacionalidad": "ES",
            "IdRefTerritorioDomicilio": "ES-CT-08001",
            "DireccionDomicilio": "Gran Via 2",
            "CodigoPostalDomicilio": "08002",
            "NombrePaisDomicilio": "España",
        },
    },
    988227: {
        "Id": 300674865,
        "EmailAlumno": "maria.garcia@unir.test",
        "IdIntegracion": "988227",
        "Persona": {
            "Id": 300674865,
            "Nombre": "María",
            "Apellido1": "García",
            "Apellido2": "Ruiz",
            "Email": "maria.garcia@unir.test",
            "Telefono": "+34-600000003",
            "Celular": "+34-600000003",
            "IdSeguridad": "33333333-3333-3333-3333-333333333333",
            "FechaNacimiento": "1995-02-10T00:00:00Z",
            "Sexo": "F",
            "IdRefPaisNacionalidad": "ES",
            "IdRefTerritorioDomicilio": "ES-MD-28001",
            "DireccionDomicilio": "Paseo del Prado 3",
            "CodigoPostalDomicilio": "28014",
            "NombrePaisDomicilio": "España",
        },
    },
}

# matriculas/search-list: FilterIdsIntegracionAlumnos: [<alumnoId>]
# Return can be MANY; we implement paging by PageIndex/ItemsPerPage.
MATRICULAS_BY_ALUMNO_ID: Dict[int, List[Dict[str, Any]]] = {
    1000113: [
        {
            "Id": 308080,
            "IdIntegracion": "5237207",
            "FechaPreMatricula": "2021-04-15T15:46:22.563Z",
            "FechaAlta": "2021-04-16T22:46:03.913Z",
            "FechaCambioEstado": "2021-04-16T22:46:03.913Z",
            "Revisada": False,
            "IdRefExpedienteAlumno": "222724",
            "Parada": False,
            "TipoMatricula": {"Id": 1, "Nombre": "Nuevo ingreso"},
            "RegionEstudio": {"Id": 2, "Nombre": "Internacional"},
            "EstadoMatricula": {"Id": 3, "Nombre": "Alta", "Orden": 3},
            "Alumno": {"Id": 300172917, "EmailAlumno": "300172917@unir.net", "IdIntegracion": "988224"},
            "DocumentoIdentificacionAlumno": {
                "Id": 231870,
                "Numero": "33700053",
                "IdRefTipoDocumentoIdentificacionPais": "CED-CO",
                "EsPrincipal": True,
            },
            "Plan": {
                "Id": 68,
                "Anyo": 2016,
                "Codigo": "0027-2016-01",
                "Nombre": "Máster Universitario en Didáctica (Plan 2016)",
                "EsOficial": True,
                "Creditos": 60.0,
                "EstadoPlan": {"Id": 10, "Nombre": "Extinguido", "Orden": 12},
            },
        },
        {
            # Active
            "Id": 308606,
            "IdIntegracion": "5237781",
            "FechaPreMatricula": "2021-04-15T22:34:08.173Z",
            "FechaAlta": "2021-04-21T21:55:32.847Z",
            "FechaCambioEstado": "2021-04-21T21:55:32.847Z",
            "Revisada": False,
            "IdRefExpedienteAlumno": "223234",
            "Parada": False,
            "TipoMatricula": {"Id": 1, "Nombre": "Nuevo ingreso"},
            "EstadoMatricula": {"Id": 3, "Nombre": "Alta", "Orden": 3},
            "Alumno": {"Id": 300172917, "EmailAlumno": "300172917@unir.net", "IdIntegracion": "1000113"},
            "Plan": {
                "Id": 1354,
                "Anyo": 2018,
                "Codigo": "0267-2018-01",
                "Nombre": "Curso Introducción a la Investigación (TFM)",
                "EsOficial": False,
                "Creditos": 2.0,
                "EstadoPlan": {"Id": 10, "Nombre": "Extinguido", "Orden": 12},
            },
        },
        {
            # Inactive (useful for testing your facade onlyActive filter)
            "Id": 999999,
            "IdIntegracion": "INACTIVA-1",
            "FechaAlta": "2020-01-01T00:00:00Z",
            "EstadoMatricula": {"Id": 2, "Nombre": "Baja", "Orden": 2},
            "TipoMatricula": {"Id": 2, "Nombre": "Renovación"},
            "Alumno": {"Id": 300172917, "EmailAlumno": "300172917@unir.net", "IdIntegracion": "1000113"},
            "Plan": {"Id": 1354, "Codigo": "0267-2018-01", "Nombre": "Curso Introducción a la Investigación (TFM)"},
        },
        # Add more entries so paging is meaningful (mix Alta/Baja)
        *[
            {
                "Id": 700000 + i,
                "IdIntegracion": f"MOCK-{1000113}-{i}",
                "FechaPreMatricula": f"2022-01-{(i%28)+1:02d}T10:00:00Z",
                "FechaAlta": f"2022-02-{(i%28)+1:02d}T12:00:00Z",
                "FechaCambioEstado": f"2022-02-{(i%28)+1:02d}T12:00:00Z",
                "Revisada": False,
                "IdRefExpedienteAlumno": str(240000 + i),
                "Parada": False,
                "TipoMatricula": {"Id": 2, "Nombre": "Renovación" if i % 2 == 0 else "Nuevo ingreso"},
                "EstadoMatricula": {"Id": 3 if i % 3 != 0 else 2, "Nombre": "Alta" if i % 3 != 0 else "Baja", "Orden": 3},
                "Alumno": {"Id": 300172917, "EmailAlumno": "300172917@unir.net", "IdIntegracion": "1000113"},
                "Plan": {
                    "Id": 2000 + (i % 5),
                    "Anyo": 2020 + (i % 4),
                    "Codigo": f"MOCK-PLAN-{i%5}",
                    "Nombre": f"Plan Mock {i%5}",
                    "EsOficial": (i % 2 == 0),
                    "Creditos": float(30 + (i % 4) * 5),
                },
            }
            for i in range(1, 26)  # 25 extra rows
        ],
    ],
    1000114: [
        # This alumno has only inactive matriculas (useful to test empty after onlyActive filter)
        {
            "Id": 810001,
            "IdIntegracion": "MOCK-1000114-1",
            "FechaAlta": "2021-01-01T00:00:00Z",
            "EstadoMatricula": {"Id": 2, "Nombre": "Baja", "Orden": 2},
            "TipoMatricula": {"Id": 1, "Nombre": "Nuevo ingreso"},
            "Alumno": {"Id": 300200000, "EmailAlumno": "alumno1000114@unir.test", "IdIntegracion": "1000114"},
            "Plan": {"Id": 3000, "Codigo": "P-3000", "Nombre": "Plan Inactivo"},
        }
    ],
    1000115: [
        # Small set (paging still works)
        {
            "Id": 820001,
            "IdIntegracion": "MOCK-1000115-1",
            "FechaAlta": "2023-03-10T00:00:00Z",
            "EstadoMatricula": {"Id": 3, "Nombre": "Alta", "Orden": 3},
            "TipoMatricula": {"Id": 1, "Nombre": "Nuevo ingreso"},
            "Alumno": {"Id": 300200001, "EmailAlumno": "alumno1000115@unir.test", "IdIntegracion": "1000115"},
            "Plan": {"Id": 4000, "Codigo": "P-4000", "Nombre": "Plan Activo"},
        },
        {
            "Id": 820002,
            "IdIntegracion": "MOCK-1000115-2",
            "FechaAlta": "2024-01-05T00:00:00Z",
            "EstadoMatricula": {"Id": 3, "Nombre": "Alta", "Orden": 3},
            "TipoMatricula": {"Id": 2, "Nombre": "Renovación"},
            "Alumno": {"Id": 300200001, "EmailAlumno": "alumno1000115@unir.test", "IdIntegracion": "1000115"},
            "Plan": {"Id": 4001, "Codigo": "P-4001", "Nombre": "Plan Activo 2"},
        },
    ],
}

# --- Make matriculas queryable by the same IdAlumno used in alumnos/search-list ---
# In your real system, 988224 is the alumno integration id used across endpoints.
MATRICULAS_BY_ALUMNO_ID[988224] = MATRICULAS_BY_ALUMNO_ID.get(1000113, [])
MATRICULAS_BY_ALUMNO_ID.pop(1000113, None)


# ----------------------------
# Endpoints
# ----------------------------
@app.post("/token")
async def token(_: Request):
    """
    Mock token endpoint. Does NOT validate credentials.
    Accepts x-www-form-urlencoded or any body (ignored).
    """
    return _issue_token()


@app.post("/api/v1/public/alumnos/search-list")
async def alumnos_search_list(request: Request):
    _require_bearer(request)
    payload = await request.json()

    ids = payload.get("filterIdsIntegracion") or []
    if not isinstance(ids, list) or not ids:
        return []

    # Gather results in the same order as requested IDs
    results: List[Dict[str, Any]] = []
    for raw in ids:
        try:
            k = int(raw)
        except Exception:
            continue
        item = ALUMNOS_BY_IDINTEGRACION.get(k)
        if item:
            results.append(item)

    page_index, items_per_page = _get_page_params(payload)
    return _paginate(results, page_index, items_per_page)


@app.post("/api/v1/public/matriculas/search-list")
async def matriculas_search_list(request: Request):
    _require_bearer(request)
    payload = await request.json()

    # Require field present (even if empty), for realism
    require_shape = os.getenv("MOCK_REQUIRE_MATRICULAS_EMPTY_FILTER", "1") == "1"
    if require_shape and "FilterIdsIntegracionMatriculas" not in payload:
        raise HTTPException(
            status_code=400,
            detail="Missing required field: FilterIdsIntegracionMatriculas (must be present, can be empty array)"
        )

    ids = payload.get("FilterIdsIntegracionAlumnos") or []
    if not isinstance(ids, list) or not ids:
        return []

    # Collect matriculas for all requested alumno IDs
    results: List[Dict[str, Any]] = []
    for raw in ids:
        try:
            alumno_id = int(raw)
        except Exception:
            continue

        items = MATRICULAS_BY_ALUMNO_ID.get(alumno_id, [])
        for m in items:
            # Make a shallow copy so we don't mutate global sample data
            if not isinstance(m, dict):
                continue
            m_copy = dict(m)

            # Patch nested Alumno.IdIntegracion to match the request
            alumno_obj = m_copy.get("Alumno")
            if isinstance(alumno_obj, dict):
                alumno_obj = dict(alumno_obj)
                alumno_obj["IdIntegracion"] = str(alumno_id)
                m_copy["Alumno"] = alumno_obj
            else:
                # Ensure Alumno exists
                m_copy["Alumno"] = {"IdIntegracion": str(alumno_id)}

            results.append(m_copy)

    page_index, items_per_page = _get_page_params(payload)
    return _paginate(results, page_index, items_per_page)


@app.get("/health")
async def health():
    now = time.time()
    active_tokens = sum(1 for _, exp in TOKENS.items() if exp > now)
    return {"status": "ok", "activeTokens": active_tokens, "expiresIn": MOCK_EXPIRES_IN}
