"""ZEKROM HTTP API."""
from __future__ import annotations

import asyncio
import json
import shlex
import shutil
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from . import registry
from .config import settings
from .formats import FORMATS, format_for_filename
from .jobs import FAILED, SKIPPED, InputFile, Task, manager
from .validation import ValidationError, safe_filename, validate_file

CHUNK = 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.start()
    yield
    await manager.stop()


app = FastAPI(title="ZEKROM API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-Batch-Token", "Content-Type"],
    expose_headers=["Content-Disposition"],
)


# ---- middleware: security headers, request size, rate limit -------------------------------

_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def guard(request: Request, call_next):
    if request.method == "POST":
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_batch_bytes + 4 * 1024 * 1024:
            return JSONResponse({"detail": f"Upload exceeds the {settings.max_batch_mb} MB batch limit"}, status_code=413)
        ip = _client_ip(request)
        window = _hits[ip]
        now = time.monotonic()
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            retry = int(60 - (now - window[0])) + 1
            return JSONResponse({"detail": "Too many conversions. Please wait a moment."}, status_code=429,
                                headers={"Retry-After": str(retry)})
        window.append(now)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


# ---- helpers ------------------------------------------------------------------------------

async def _scan(path: Path) -> str | None:
    """Optional malware scan hook. Returns an error message if the file must be rejected."""
    if not settings.scan_command:
        return None
    proc = await asyncio.create_subprocess_exec(
        *shlex.split(settings.scan_command), str(path),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    code = await proc.wait()
    if code == 1:
        return "File was flagged by the malware scanner"
    if code != 0:
        return "File could not be scanned for malware"
    return None


async def _receive_files(request: Request, batch_dir: Path) -> tuple[list[InputFile], dict]:
    form = await request.form(max_files=settings.max_files_per_batch + 1, max_fields=50)
    uploads = [v for k, v in form.multi_items() if k == "files" and isinstance(v, StarletteUploadFile)]
    if not uploads:
        raise HTTPException(400, "No files were uploaded")
    if len(uploads) > settings.max_files_per_batch:
        raise HTTPException(400, f"A batch can contain at most {settings.max_files_per_batch} files")
    fields = {k: v for k, v in form.multi_items() if isinstance(v, str)}

    files: list[InputFile] = []
    total = 0
    for upload in uploads:
        name = safe_filename(upload.filename or "file")
        fmt = format_for_filename(name)
        file_id = uuid.uuid4().hex[:12]
        rec = InputFile(file_id, name, fmt, 0, None)
        files.append(rec)
        if fmt is None:
            rec.error = "Unsupported file type"
            await upload.close()
            continue
        # Server-chosen disk name: user input never touches the filesystem path.
        dest = batch_dir / "in" / f"{file_id}.{FORMATS[fmt].extensions[0]}"
        size = 0
        too_big = False
        with dest.open("wb") as fh:
            while chunk := await upload.read(CHUNK):
                size += len(chunk)
                if size > settings.max_file_bytes:
                    too_big = True
                    break
                fh.write(chunk)
        await upload.close()
        rec.size = size
        total += size
        if total > settings.max_batch_bytes:
            raise HTTPException(413, f"Upload exceeds the {settings.max_batch_mb} MB batch limit")
        if too_big:
            dest.unlink(missing_ok=True)
            rec.error = f"File is larger than {settings.max_file_mb} MB"
            continue
        try:
            validate_file(dest, fmt)
        except ValidationError as exc:
            dest.unlink(missing_ok=True)
            rec.error = str(exc)
            continue
        scan_error = await _scan(dest)
        if scan_error:
            dest.unlink(missing_ok=True)
            rec.error = scan_error
            continue
        rec.path = dest
    return files, fields


def _parse_json(fields: dict, key: str, default):
    raw = fields.get(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"'{key}' must be valid JSON") from exc


def _stem(name: str) -> str:
    return name.rsplit(".", 1)[0] if "." in name else name


def _rejected_task(f: InputFile, target: str | None, op: str = "convert") -> Task:
    t = Task(uuid.uuid4().hex[:12], op, [f], target, _stem(f.name), status=FAILED, error=f.error)
    t.finished_at = time.time()
    return t


def _token(request: Request) -> str | None:
    return request.headers.get("x-batch-token") or request.query_params.get("token")


def _batch_or_404(batch_id: str, request: Request):
    batch = manager.get(batch_id, _token(request))
    if batch is None:
        raise HTTPException(404, "Batch not found or expired")
    return batch


def _created(batch) -> JSONResponse:
    body = manager.to_dict(batch)
    body["token"] = batch.token
    return JSONResponse(body, status_code=201)


# ---- routes -------------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "libreoffice": settings.soffice is not None,
            "workers": settings.max_workers, "office_workers": settings.office_workers}


@app.get("/api/formats")
async def formats():
    return {
        **registry.describe(),
        "limits": {
            "max_files": settings.max_files_per_batch,
            "max_file_mb": settings.max_file_mb,
            "max_batch_mb": settings.max_batch_mb,
            "retention_minutes": settings.retention_s // 60,
        },
        "tools": TOOLS_PUBLIC,
    }


@app.post("/api/conversions", status_code=201)
async def create_conversion(request: Request):
    """Multipart form: `files` (repeated) + `targets` (JSON list aligned with files) or `target` (one format for all)."""
    batch_id, batch_dir = manager.new_batch_dir()
    try:
        files, fields = await _receive_files(request, batch_dir)
        targets = _parse_json(fields, "targets", None)
        single = fields.get("target")
        if targets is None and not single:
            raise HTTPException(400, "Choose an output format")
        if targets is not None and (not isinstance(targets, list) or len(targets) != len(files)):
            raise HTTPException(400, "'targets' must list one output format per file")
        tasks: list[Task] = []
        for i, f in enumerate(files):
            target = (targets[i] if targets is not None else single) or None
            if f.error:
                tasks.append(_rejected_task(f, target))
                continue
            task = Task(uuid.uuid4().hex[:12], "convert", [f], target, _stem(f.name))
            conv = registry.get(f.format, target) if target else None
            task.office = bool(conv and conv.engine.startswith("office:"))
            if conv is None:
                task.status = SKIPPED
                task.error = f"{FORMATS[f.format].label} cannot be converted to {target.upper() if target else 'that format'}"
            tasks.append(task)
        batch = manager.create(batch_id, batch_dir, "convert", tasks)
        return _created(batch)
    except Exception:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise


@app.get("/api/conversions/{batch_id}")
async def get_conversion(batch_id: str, request: Request):
    return manager.to_dict(_batch_or_404(batch_id, request))


@app.get("/api/conversions/{batch_id}/files/{file_id}")
async def download_file(batch_id: str, file_id: str, request: Request):
    batch = _batch_or_404(batch_id, request)
    for t in batch.tasks:
        if t.output and t.output.id == file_id and t.output.path.exists():
            return FileResponse(
                t.output.path, filename=t.output.filename, media_type="application/octet-stream",
                headers={"Content-Security-Policy": "default-src 'none'; sandbox"},
            )
    raise HTTPException(404, "File not found")


@app.get("/api/conversions/{batch_id}/download-zip")
async def download_zip(batch_id: str, request: Request):
    batch = _batch_or_404(batch_id, request)
    path = await asyncio.to_thread(manager.build_zip, batch)
    if path is None:
        raise HTTPException(404, "No converted files are available yet")
    return FileResponse(path, filename=f"zekrom-{batch.id[:8]}.zip", media_type="application/zip")


@app.post("/api/conversions/{batch_id}/cancel")
async def cancel_conversion(batch_id: str, request: Request):
    batch = _batch_or_404(batch_id, request)
    manager.cancel(batch)
    return manager.to_dict(batch)


@app.delete("/api/conversions/{batch_id}", status_code=204)
async def delete_conversion(batch_id: str, request: Request):
    _batch_or_404(batch_id, request)
    await manager.delete(batch_id)
    return None


# ---- tools --------------------------------------------------------------------------------

RASTER = {"jpg", "png", "webp", "bmp", "tiff", "gif"}
TOOLS = {
    # tool id: (op, accepted input formats, combine all inputs into one task?, min files)
    "merge-pdf": ("merge_pdf", {"pdf"}, True, 2),
    "split-pdf": ("split_pdf", {"pdf"}, False, 1),
    "compress-pdf": ("compress_pdf", {"pdf"}, False, 1),
    "images-to-pdf": ("images_to_pdf", RASTER | {"svg"}, True, 1),
    "resize-images": ("resize_image", RASTER, False, 1),
    "compress-images": ("compress_image", {"jpg", "png", "webp"}, False, 1),
}
TOOLS_PUBLIC = {k: {"accepts": sorted(v[1]), "combine": v[2], "min_files": v[3]} for k, v in TOOLS.items()}


def _validate_tool_options(tool: str, options: dict) -> dict:
    clean: dict = {}
    try:
        if tool == "split-pdf":
            clean["mode"] = options.get("mode", "pages")
            if clean["mode"] not in ("pages", "ranges", "extract"):
                raise ValueError
            if clean["mode"] != "pages":
                clean["ranges"] = str(options.get("ranges", ""))[:500]
        elif tool == "compress-pdf":
            clean["level"] = options.get("level", "medium")
            if clean["level"] not in ("low", "medium", "high"):
                raise ValueError
        elif tool == "resize-images":
            if options.get("percent"):
                clean["percent"] = float(options["percent"])
                if not 1 <= clean["percent"] <= 400:
                    raise ValueError
            else:
                for k in ("width", "height"):
                    if options.get(k):
                        clean[k] = int(options[k])
                        if not 1 <= clean[k] <= 20000:
                            raise ValueError
                if not clean:
                    raise ValueError
            clean["keep_aspect"] = bool(options.get("keep_aspect", True))
        elif tool == "compress-images":
            clean["quality"] = int(options.get("quality", 75))
            if not 10 <= clean["quality"] <= 95:
                raise ValueError
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, "Invalid tool options") from exc
    return clean


@app.post("/api/tools/{tool}", status_code=201)
async def run_tool(tool: str, request: Request):
    if tool not in TOOLS:
        raise HTTPException(404, "Unknown tool")
    op, accepts, combine, min_files = TOOLS[tool]
    batch_id, batch_dir = manager.new_batch_dir()
    try:
        files, fields = await _receive_files(request, batch_dir)
        options = _validate_tool_options(tool, _parse_json(fields, "options", {}) or {})
        tasks: list[Task] = []
        good: list[InputFile] = []
        for f in files:
            if not f.error and f.format not in accepts:
                f.error = f"This tool does not accept {FORMATS[f.format].label} files" if f.format else "Unsupported file type"
            if f.error:
                tasks.append(_rejected_task(f, None, op))
            else:
                good.append(f)
        if combine:
            if len(good) < min_files:
                raise HTTPException(400, f"This tool needs at least {min_files} valid files")
            name = "merged" if tool == "merge-pdf" else "images"
            tasks.insert(0, Task(uuid.uuid4().hex[:12], op, good, "pdf", name, options))
        else:
            for f in good:
                tasks.append(Task(uuid.uuid4().hex[:12], op, [f], None, _stem(f.name), options))
        batch = manager.create(batch_id, batch_dir, tool, tasks)
        return _created(batch)
    except Exception:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise


# Serve the built frontend in production (single-origin deployment).
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
