"""Run pytest without inheriting provider credentials or the live Hermes profile."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="network-xray-tests-") as temporary:
        scratch = Path(temporary)
        (scratch / "home").mkdir()
        environment = {
            key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR") if key in os.environ
        }
        cache_base = Path.home() / ("Library/Caches" if sys.platform == "darwin" else ".cache")
        browsers = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", str(cache_base / "ms-playwright"))
        environment.update(
            {
                "PLAYWRIGHT_BROWSERS_PATH": browsers,
                "HOME": str(scratch / "home"),
                "USERPROFILE": str(scratch / "home"),
                "HERMES_HOME": str(scratch / "hermes"),
                "TMPDIR": str(scratch),
                "TEMP": str(scratch),
                "TMP": str(scratch),
                "HERMES_DISABLE_LAZY_INSTALLS": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "LANG": "en_US.UTF-8",
                "TZ": "UTC",
            }
        )
        command = [
            sys.executable,
            "-E",
            "-B",
            "-m",
            "pytest",
            "--basetemp",
            str(scratch / "cases"),
            *sys.argv[1:],
        ]
        return subprocess.call(command, cwd=root, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
