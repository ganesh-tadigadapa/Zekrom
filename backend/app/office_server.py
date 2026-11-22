"""A long-running LibreOffice, driven through unoserver.

Starting LibreOffice costs seconds (tens of seconds on a small cloud CPU) while converting a
typical document takes a fraction of that, so one instance is kept running and fed files over
XML-RPC. If it can't start or dies, `ready` goes False and callers fall back to launching
LibreOffice per job (app.engines.office), so conversions never depend on this.

unoserver's server half has to run under a Python that can `import uno` (Debian's python3-uno,
or LibreOffice's bundled Python on macOS). That is usually not the app's Python, so it gets a
PYTHONPATH holding only the unoserver package.
"""
from __future__ import annotations

import asyncio
import os
import signal
import socket
import sys
import time
import xmlrpc.client
from pathlib import Path

from .config import settings
from .engines.office import FILTERS

UNO_PYTHON_CANDIDATES = (
    "/usr/bin/python3",                                           # Debian/Ubuntu + python3-uno
    "/usr/lib/libreoffice/program/python",                        # LibreOffice's own Python on Linux
    "/opt/libreoffice/program/python",
    "/Applications/LibreOffice.app/Contents/Resources/python",    # macOS
)


class _TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout: float) -> None:
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def supports(src_format: str | None, dst: str | None) -> bool:
    """Targets whose LibreOffice filter needs option tokens (txt, html, csv) and CSV input keep
    the command-line path, which already handles them."""
    return bool(dst in FILTERS and FILTERS[dst].count(":") <= 1 and src_format != "csv")


class OfficeServer:
    def __init__(self) -> None:
        self.ready = False
        self._proc: asyncio.subprocess.Process | None = None
        self._port = 0
        self._python: str | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> bool:
        """Start (or restart) the server. Returns True once it answers requests."""
        async with self._lock:
            if self.ready:
                return True
            await self._kill()
            if not settings.soffice or not settings.use_unoserver:
                return False
            if self._python is None:
                self._python = await self._find_uno_python() or ""
            if not self._python:
                return False
            try:
                import unoserver  # noqa: F401  (only needed to locate the package)
            except ImportError:
                return False
            root = settings.storage_dir / "unoserver"
            pypath = root / "pypath"
            pypath.mkdir(parents=True, exist_ok=True)
            # The package plus its dist-info (unoserver reads its own version from it at import).
            for src in (Path(unoserver.__file__).resolve().parent, _dist_info("unoserver")):
                link = pypath / src.name if src else None
                if link and not link.exists():
                    link.symlink_to(src, target_is_directory=True)
            profile = root / "profile"
            self._port = _free_port()
            env = {**os.environ, "PYTHONPATH": str(pypath), "SAL_USE_VCLPLUGIN": "svp", "HOME": str(profile)}
            env.pop("PYTHONHOME", None)
            self._proc = await asyncio.create_subprocess_exec(
                self._python, "-m", "unoserver.server",
                "--interface", "127.0.0.1", "--port", str(self._port), "--uno-port", str(_free_port()),
                "--executable", settings.soffice, "--user-installation", str(profile.resolve()),
                "--conversion-timeout", str(settings.conversion_timeout_s),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, env=env,
                start_new_session=True,  # own process group: stop() takes LibreOffice down with it
                preexec_fn=_limit_file_size if sys.platform != "win32" else None,
            )
            deadline = time.monotonic() + settings.unoserver_start_timeout_s
            while time.monotonic() < deadline and self._proc.returncode is None:
                if await asyncio.to_thread(self._ping):
                    self.ready = True
                    print(f"[zekrom] LibreOffice server ready on port {self._port}", file=sys.stderr)
                    return True
                await asyncio.sleep(0.5)
            print("[zekrom] LibreOffice server did not start; converting with one launch per job", file=sys.stderr)
            await self._kill()
            return False

    async def stop(self) -> None:
        async with self._lock:
            await self._kill()

    async def convert(self, src: Path, dest: Path, dst: str) -> bool:
        """Convert src into dest. False means "not converted"; the caller should fall back."""
        if not self.ready:
            return False
        spec = FILTERS[dst]
        filtername = spec.split(":", 1)[1] if ":" in spec else None
        try:
            await asyncio.to_thread(self._call, str(src), str(dest), dest.suffix.lstrip("."), filtername)
        except xmlrpc.client.Fault:
            return False  # LibreOffice rejected this file; the server itself is fine
        except Exception:
            # Connection refused, timeout, or the server died mid-conversion: restart it in the
            # background and let this file go through the fallback path.
            self.ready = False
            asyncio.get_running_loop().create_task(self.start())
            return False
        return dest.exists() and dest.stat().st_size > 0

    # ---- internals ----------------------------------------------------------------------------
    def _proxy(self, timeout: float) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"http://127.0.0.1:{self._port}", allow_none=True,
                                         transport=_TimeoutTransport(timeout))

    def _ping(self) -> bool:
        try:
            self._proxy(5).info()
            return True
        except Exception:
            return False

    def _call(self, src: str, dest: str, convert_to: str, filtername: str | None) -> None:
        # Positional, matching unoserver's XML-RPC `convert`: inpath, indata, outpath, convert_to,
        # filtername, filter_options, update_index, infiltername, password.
        self._proxy(settings.conversion_timeout_s + 15).convert(src, None, dest, convert_to, filtername, [], False, None, None)

    async def _kill(self) -> None:
        self.ready = False
        proc, self._proc = self._proc, None
        if proc is None or proc.returncode is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            await asyncio.wait_for(proc.wait(), timeout=10)
        except (ProcessLookupError, PermissionError):
            pass
        except asyncio.TimeoutError:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            await proc.wait()

    @staticmethod
    async def _find_uno_python() -> str | None:
        candidates = [settings.uno_python] if settings.uno_python else list(UNO_PYTHON_CANDIDATES)
        for py in candidates:
            if not py or not Path(py).exists():
                continue
            try:
                proc = await asyncio.create_subprocess_exec(
                    py, "-c", "import uno", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                if await asyncio.wait_for(proc.wait(), timeout=30) == 0:
                    return py
            except (OSError, asyncio.TimeoutError):
                continue
        return None


def _dist_info(name: str) -> Path | None:
    from importlib import metadata

    try:
        meta = next(f for f in metadata.distribution(name).files or [] if f.name == "METADATA")
        return Path(meta.locate()).resolve().parent
    except (metadata.PackageNotFoundError, StopIteration):
        return None


def _limit_file_size() -> None:
    """No CPU limit here: it counts total CPU over the server's whole life, not per conversion
    (unoserver's --conversion-timeout covers runaway conversions instead)."""
    import resource

    try:
        two_gb = 2 * 1024 ** 3
        resource.setrlimit(resource.RLIMIT_FSIZE, (two_gb, two_gb))
    except (ValueError, OSError):
        pass


office_server = OfficeServer()
