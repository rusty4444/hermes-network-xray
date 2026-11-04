"""Loopback-only development workbench using the real plugin router and UI."""

import argparse
import importlib.util
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

ROOT = Path(__file__).resolve().parents[1]


def create_app(data_root):
    spec = importlib.util.spec_from_file_location(
        "network_xray_dev_api", ROOT / "dashboard" / "plugin_api.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Plugin router missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    app = FastAPI(title="Network X-ray local workbench", docs_url=None, redoc_url=None)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"]
    )
    app.include_router(module.router, prefix="/api/plugins/network-xray")
    app.dependency_overrides[module.get_service] = lambda: module._service_module.Service(data_root)
    app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="workbench")
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="Explicit private data directory")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    uvicorn.run(create_app(args.data), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
