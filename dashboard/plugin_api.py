"""Hermes-owned HTTP namespace. Only plugin-owned source is loaded here."""

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool


def _own_service_module():
    # Hermes loads API files as standalone modules, not children of the agent package.
    root = Path(__file__).resolve().parents[1]
    name = "network_xray_adapter_" + hashlib.sha256(str(root).encode()).hexdigest()[:12]
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, root / "__init__.py", submodule_search_locations=[str(root)]
        )
        if spec is None or spec.loader is None:
            raise ImportError("Network X-ray package cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(name, module)
        spec.loader.exec_module(module)
    return importlib.import_module(name + ".service")


_service_module = _own_service_module()
router = APIRouter()
_slots = threading.BoundedSemaphore(4)
MAX_BODY_BYTES = 262144


def get_service():
    return _service_module.Service()


def _id(value):
    try:
        parsed = uuid.UUID(value)
        if parsed.version != 4 or str(parsed) != value:
            raise ValueError()
    except (ValueError, AttributeError):
        raise HTTPException(400, "A canonical probe UUID is required") from None
    return value


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite number")


def _check_origin(request):
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not accepted")
    if origin:
        parsed = urlsplit(origin)
        expected = urlsplit(str(request.url))
        if origin == "null" or parsed.scheme != expected.scheme or parsed.netloc != expected.netloc:
            raise HTTPException(403, "Cross-origin requests are not accepted")


async def _body(request, required, optional=()):
    _check_origin(request)
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/json"
    ):
        raise HTTPException(415, "Use application/json")
    buffer = bytearray()
    async for chunk in request.stream():
        if len(buffer) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "Request exceeds 256 KiB")
        buffer.extend(chunk)
    try:
        value = json.loads(buffer, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
        if not isinstance(value, dict):
            raise ValueError()
        if set(required) - set(value) or set(value) - set(required) - set(optional):
            raise ValueError()
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(400, "Invalid JSON or unexpected fields") from None
    return value


def _string(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise HTTPException(400, "Invalid field type or length")
    return value


def _call(operation):
    try:
        return operation()
    except (ValueError, TypeError):
        raise HTTPException(
            400, "Invalid input: check URL, fields, bundle schema/digest, and matching targets"
        ) from None
    except (FileNotFoundError, KeyError):
        raise HTTPException(404, "Probe not found in the active profile") from None
    except (OSError, RuntimeError):
        raise HTTPException(
            503, "Operation failed; check local storage and retry. No success is implied"
        ) from None


def _collect(service, values):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Four probes are already running; retry after they finish")
    try:
        return _call(lambda: service.collect(**values))
    finally:
        _slots.release()


@router.get("/health")
def health():
    return {"ok": True, "version": _service_module.VERSION}


@router.get("/probes")
def list_probes(service=Depends(get_service)):
    return _call(service.list_probes)


@router.post("/probe")
async def probe(request: Request, service=Depends(get_service)):
    values = await _body(request, ("url", "label"), ("connect_ip",))
    _string(values["url"], 2048)
    _string(values["label"], 48)
    if values.get("connect_ip") is not None:
        _string(values["connect_ip"], 45)
    return await run_in_threadpool(_collect, service, values)


@router.post("/import")
async def import_probe(request: Request, service=Depends(get_service)):
    values = await _body(request, ("bundle",))
    if not isinstance(values["bundle"], dict):
        raise HTTPException(400, "Bundle must be a JSON object")
    return await run_in_threadpool(_call, lambda: service.import_probe(values["bundle"]))


@router.get("/probes/{probe_id}")
def get_probe(probe_id: str, service=Depends(get_service)):
    return _call(lambda: service.get_probe(_id(probe_id)))


@router.post("/compare")
async def compare(request: Request, service=Depends(get_service)):
    values = await _body(request, ("left_id", "right_id"))
    left, right = _id(values["left_id"]), _id(values["right_id"])
    return await run_in_threadpool(_call, lambda: service.compare_probes(left, right))


@router.get("/collector")
def collector(service=Depends(get_service)):
    return {"filename": "network-xray-collector.py", "source": _call(service.collector_source)}


@router.get("/collector.py", response_class=PlainTextResponse)
def collector_download(service=Depends(get_service)):
    return PlainTextResponse(
        _call(service.collector_source),
        media_type="text/x-python",
        headers={
            "Content-Disposition": 'attachment; filename="network-xray-collector.py"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/export/{left_id}/{right_id}")
def export_report(left_id: str, right_id: str, service=Depends(get_service)):
    left, right = _id(left_id), _id(right_id)
    return {
        "filename": "network-xray-report.html",
        "html": _call(lambda: service.export_report(left, right)),
    }
