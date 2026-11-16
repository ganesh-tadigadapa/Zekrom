"""Batch job management: queueing, bounded parallel execution, retries, cancellation, cleanup.

Jobs live in-process. Concurrency is bounded by a global semaphore shared by all batches, and
each conversion runs in its own OS process (see app.worker). For multi-instance deployments,
swap `JobManager._run_task` dispatch for a Celery/RQ/Arq queue: the Batch/Task model and the
HTTP API do not change.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import secrets
import shutil
import signal
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings
from .formats import mime_for

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Task statuses
WAITING, CONVERTING, COMPLETED, FAILED, CANCELLED, SKIPPED = "waiting", "converting", "completed", "failed", "cancelled", "skipped"
TERMINAL = {COMPLETED, FAILED, CANCELLED, SKIPPED}


@dataclass
class InputFile:
    id: str
    name: str           # sanitised original filename (display only; never used as a disk path)
    format: str | None
    size: int
    path: Path | None   # where the bytes live on disk (None if rejected before storing)
    error: str | None = None


@dataclass
class Output:
    id: str
    filename: str       # unique within the batch
    path: Path
    size: int
    format: str


@dataclass
class Task:
    id: str
    op: str                      # "convert" or a tool op
    inputs: list[InputFile]
    target: str | None           # output format for "convert"
    stem: str
    options: dict = field(default_factory=dict)
    status: str = WAITING
    error: str | None = None
    output: Output | None = None
    attempts: int = 0
    office: bool = False         # runs on a LibreOffice slot (grouped) instead of the fast lane
    solo: bool = False           # retry outside of a group
    started_at: float | None = None
    finished_at: float | None = None


@dataclass
class Batch:
    id: str
    token: str
    kind: str
    dir: Path
    created_at: float
    tasks: list[Task]
    cancelled: bool = False
    procs: dict[str, asyncio.subprocess.Process] = field(default_factory=dict)
    zip_path: Path | None = None
    used_names: set[str] = field(default_factory=set)

    @property
    def expires_at(self) -> float:
        return self.created_at + settings.retention_s

    @property
    def done(self) -> bool:
        return all(t.status in TERMINAL for t in self.tasks)


class JobManager:
    def __init__(self) -> None:
        self.batches: dict[str, Batch] = {}
        self._sem: asyncio.Semaphore | None = None
        self._lo_slots: asyncio.Queue[int] | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._bg: set[asyncio.Task] = set()
        self._office_q: list[tuple[Batch, Task]] = []

    # ---- lifecycle -------------------------------------------------------------------------
    async def start(self) -> None:
        root = settings.storage_dir
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)  # anything left over is from a previous run
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.chmod(root, 0o700)
        (root / "lo-profiles").mkdir(mode=0o700, exist_ok=True)
        self._sem = asyncio.Semaphore(settings.max_workers)
        self._lo_slots = asyncio.Queue()
        for i in range(settings.office_workers):
            self._lo_slots.put_nowait(i)
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        if settings.soffice:
            for _ in range(settings.office_workers):
                self._spawn_bg(self._warm_slot())

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for batch in list(self.batches.values()):
            await self.delete(batch.id)

    # ---- batch creation --------------------------------------------------------------------
    def new_batch_dir(self) -> tuple[str, Path]:
        batch_id = uuid.uuid4().hex
        d = settings.storage_dir / batch_id
        (d / "in").mkdir(parents=True, mode=0o700)
        (d / "out").mkdir(mode=0o700)
        return batch_id, d

    def create(self, batch_id: str, batch_dir: Path, kind: str, tasks: list[Task]) -> Batch:
        batch = Batch(batch_id, secrets.token_urlsafe(24), kind, batch_dir, time.time(), tasks)
        self.batches[batch_id] = batch
        for task in tasks:
            if task.status != WAITING:
                continue
            if task.office:
                self._office_q.append((batch, task))
            else:
                self._spawn_bg(self._run_task(batch, task))
        self._pump_office()
        return batch

    def _spawn_bg(self, coro) -> None:
        t = asyncio.create_task(coro)
        self._bg.add(t)
        t.add_done_callback(self._bg.discard)

    def get(self, batch_id: str, token: str | None) -> Batch | None:
        batch = self.batches.get(batch_id)
        if batch is None or token is None or not secrets.compare_digest(batch.token, token):
            return None
        return batch

    # ---- execution -------------------------------------------------------------------------
    async def _run_task(self, batch: Batch, task: Task) -> None:
        assert self._sem is not None and self._lo_slots is not None
        async with self._sem:
            while task.status == WAITING and not batch.cancelled:
                task.attempts += 1
                task.status = CONVERTING
                task.started_at = task.started_at or time.time()
                result = await self._exec(batch, task)
                if batch.cancelled:
                    task.status = CANCELLED
                    break
                if result.get("ok"):
                    self._finish(batch, task, [Path(p) for p in result["outputs"]])
                elif result.get("recoverable") and task.attempts < settings.max_attempts:
                    task.status = WAITING  # retry
                    shutil.rmtree(batch.dir / "out" / task.id, ignore_errors=True)
                else:
                    task.status = FAILED
                    task.error = result.get("error") or "Conversion failed"
            if batch.cancelled and task.status not in TERMINAL:
                task.status = CANCELLED
            task.finished_at = time.time()

    async def _exec(self, batch: Batch, task: Task) -> dict:
        spec = {
            "op": task.op,
            "inputs": [str(i.path) for i in task.inputs],
            "src_format": task.inputs[0].format,
            "dst": task.target,
            "out_dir": str(batch.dir / "out" / task.id),
            "stem": task.stem,
            "options": {**task.options, "_soffice": settings.soffice, "_timeout": settings.conversion_timeout_s - 5},
        }
        return await self._spawn(batch, task.id, spec, settings.conversion_timeout_s)

    # ---- LibreOffice lane: grouped conversions on warm, persistent profiles ------------------
    def _pump_office(self) -> None:
        """Start office groups while LibreOffice slots are free."""
        assert self._lo_slots is not None
        self._office_q = [(b, t) for b, t in self._office_q if t.status == WAITING and not b.cancelled]
        while self._office_q and not self._lo_slots.empty():
            slot = self._lo_slots.get_nowait()
            batch, head = self._office_q[0]
            if head.solo:
                group = [self._office_q.pop(0)]
            else:
                # Spread work across all slots, then cap the group size.
                size = max(1, min(settings.office_group_size, math.ceil(len(self._office_q) / settings.office_workers)))
                key = (batch.id, head.target, head.inputs[0].format == "csv")
                group, rest = [], []
                for item in self._office_q:
                    b, t = item
                    if len(group) < size and not t.solo and (b.id, t.target, t.inputs[0].format == "csv") == key:
                        group.append(item)
                    else:
                        rest.append(item)
                self._office_q = rest
            self._spawn_bg(self._run_office_group(slot, batch, [t for _, t in group]))

    async def _run_office_group(self, slot: int, batch: Batch, tasks: list[Task]) -> None:
        assert self._lo_slots is not None
        group_id = "g" + uuid.uuid4().hex[:11]
        retry: list[Task] = []
        try:
            if batch.cancelled:
                return
            for t in tasks:
                t.attempts += 1
                t.status = CONVERTING
                t.started_at = t.started_at or time.time()
            timeout = settings.conversion_timeout_s + 30 * (len(tasks) - 1)
            spec = {
                "op": "office_group",
                "dst": tasks[0].target,
                "out_dir": str(batch.dir / "out" / group_id),
                "items": [{"id": t.id, "input": str(t.inputs[0].path), "stem": t.stem, "out_dir": str(batch.dir / "out" / t.id)}
                          for t in tasks],
                "options": {"_soffice": settings.soffice, "_timeout": timeout - 5,
                            "_lo_profile": str(settings.storage_dir / "lo-profiles" / f"slot-{slot}")},
            }
            result = await self._spawn(batch, group_id, spec, timeout)
            shutil.rmtree(batch.dir / "out" / group_id, ignore_errors=True)
            outputs = result.get("outputs") if result.get("ok") else None
            for t in tasks:
                if batch.cancelled:
                    t.status = CANCELLED
                elif outputs and outputs.get(t.id):
                    self._finish(batch, t, [Path(p) for p in outputs[t.id]])
                elif len(tasks) > 1 or (result.get("recoverable") and t.attempts < settings.max_attempts):
                    retry.append(t)  # isolate it: one bad file must not fail the others
                else:
                    t.status = FAILED
                    t.error = (result.get("error") if not result.get("ok") else None) or "LibreOffice could not convert this file"
                if t.status in TERMINAL:
                    t.finished_at = time.time()
        finally:
            for t in retry:
                t.status, t.solo = WAITING, True
            self._office_q[:0] = [(batch, t) for t in retry]
            self._lo_slots.put_nowait(slot)
            self._pump_office()

    async def _warm_slot(self) -> None:
        """Initialise a LibreOffice profile at start-up so the first conversion doesn't pay for it."""
        assert self._lo_slots is not None
        slot = await self._lo_slots.get()
        try:
            profile = settings.storage_dir / "lo-profiles" / f"slot-{slot}"
            proc = await asyncio.create_subprocess_exec(
                settings.soffice, f"-env:UserInstallation={profile.resolve().as_uri()}",
                "--headless", "--norestore", "--nologo", "--terminate_after_init",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                env={**os.environ, "SAL_USE_VCLPLUGIN": "svp", "HOME": str(profile)}, start_new_session=True,
            )
            try:
                await asyncio.wait_for(proc.wait(), timeout=60)
            except asyncio.TimeoutError:
                _kill_group(proc)
        finally:
            self._lo_slots.put_nowait(slot)
            self._pump_office()

    async def _spawn(self, batch: Batch, key: str, spec: dict, timeout: float) -> dict:
        spec_path = batch.dir / f"{key}.spec.json"
        spec_path.write_text(json.dumps(spec))
        proc = await asyncio.create_subprocess_exec(
            settings.python, "-s", "-m", "app.worker", str(spec_path),
            cwd=str(BACKEND_DIR),
            env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(BACKEND_DIR), "HOME": str(batch.dir),
                 "TMPDIR": str(batch.dir), "LANG": "en_US.UTF-8"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,  # own process group so cancel/timeout kills LibreOffice children too
            preexec_fn=_limit_resources if sys.platform != "win32" else None,
        )
        batch.procs[key] = proc
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            _kill_group(proc)
            await proc.wait()
            return {"ok": False, "error": f"Conversion timed out after {int(timeout)}s", "recoverable": False}
        finally:
            batch.procs.pop(key, None)
            spec_path.unlink(missing_ok=True)
        lines = [ln for ln in stdout.decode(errors="replace").splitlines() if ln.startswith("{")]
        if not lines:
            if batch.cancelled:
                return {"ok": False, "error": "Cancelled"}
            return {"ok": False, "error": "Converter crashed while processing this file", "recoverable": True}
        result = json.loads(lines[-1])
        if not result.get("ok") and result.get("trace"):
            print(f"[zekrom] {key} failed:\n{result['trace']}", file=sys.stderr)
        return result

    def _finish(self, batch: Batch, task: Task, files: list[Path]) -> None:
        files = [f for f in files if f.exists()]
        if not files:
            task.status, task.error = FAILED, "Converter produced no output"
            return
        if len(files) == 1:
            path = files[0]
            fmt = path.suffix.lstrip(".").lower()
            desired = path.name
        else:
            # Multi-file result (PDF pages, spreadsheet sheets, split PDF) -> one ZIP per task.
            suffix = task.target or task.op.replace("_", "-")
            path = batch.dir / "out" / task.id / f"{task.stem}-{suffix}.zip"
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, f.name)
            fmt = "zip"
            desired = path.name
        task.output = Output(uuid.uuid4().hex[:12], self._unique_name(batch, desired), path, path.stat().st_size, fmt)
        task.status = COMPLETED

    @staticmethod
    def _unique_name(batch: Batch, name: str) -> str:
        stem, dot, ext = name.rpartition(".")
        if not dot:
            stem, ext = name, ""
        candidate, n = name, 2
        while candidate.lower() in batch.used_names:
            candidate = f"{stem} ({n}).{ext}" if ext else f"{stem} ({n})"
            n += 1
        batch.used_names.add(candidate.lower())
        return candidate

    # ---- control ---------------------------------------------------------------------------
    def cancel(self, batch: Batch) -> None:
        batch.cancelled = True
        for proc in list(batch.procs.values()):
            _kill_group(proc)
        for t in batch.tasks:
            if t.status == WAITING:
                t.status = CANCELLED
                t.finished_at = time.time()
        self._office_q = [(b, t) for b, t in self._office_q if b is not batch]

    async def delete(self, batch_id: str) -> None:
        batch = self.batches.pop(batch_id, None)
        if batch:
            self.cancel(batch)
            await asyncio.sleep(0)  # let killed workers' tasks observe the cancellation
            shutil.rmtree(batch.dir, ignore_errors=True)

    def build_zip(self, batch: Batch) -> Path | None:
        outputs = [t.output for t in batch.tasks if t.status == COMPLETED and t.output]
        if not outputs:
            return None
        key = ",".join(o.id for o in outputs)
        target = batch.dir / f"zekrom-{batch.id[:8]}.zip"
        marker = batch.dir / ".zip-key"
        if target.exists() and marker.exists() and marker.read_text() == key:
            return target
        tmp = target.with_suffix(".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for o in outputs:
                zf.write(o.path, o.filename)
        tmp.replace(target)
        marker.write_text(key)
        return target

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(settings.cleanup_interval_s)
            now = time.time()
            for batch in list(self.batches.values()):
                if now >= batch.expires_at:
                    await self.delete(batch.id)

    # ---- serialisation ---------------------------------------------------------------------
    def to_dict(self, batch: Batch) -> dict:
        counts = {s: 0 for s in (WAITING, CONVERTING, COMPLETED, FAILED, CANCELLED, SKIPPED)}
        for t in batch.tasks:
            counts[t.status] += 1
        actionable = [t for t in batch.tasks if t.status != SKIPPED]
        finished = [t for t in actionable if t.status in TERMINAL]
        durations = [t.finished_at - t.started_at for t in batch.tasks
                     if t.status == COMPLETED and t.started_at and t.finished_at]
        remaining = len(actionable) - len(finished)
        eta = None
        if len(durations) >= 3 and remaining and not batch.cancelled:
            avg = sum(durations) / len(durations)
            eta = round(avg * remaining / max(1, min(settings.max_workers, remaining)))
        if batch.cancelled:
            status = "cancelled"
        elif batch.done:
            status = "completed" if counts[COMPLETED] else "failed"
        elif counts[CONVERTING] or finished:
            status = "processing"
        else:
            status = "queued"
        current = next((t for t in batch.tasks if t.status == CONVERTING), None)
        return {
            "id": batch.id,
            "kind": batch.kind,
            "status": status,
            "created_at": batch.created_at,
            "expires_at": batch.expires_at,
            "total": len(actionable),
            "finished": len(finished),
            "counts": counts,
            "progress": round(100 * len(finished) / len(actionable)) if actionable else 100,
            "current": current.inputs[0].name if current else None,
            "eta_seconds": eta,
            "tasks": [
                {
                    "id": t.id,
                    "op": t.op,
                    "inputs": [{"id": i.id, "name": i.name, "format": i.format, "size": i.size} for i in t.inputs],
                    "target": t.target,
                    "status": t.status,
                    "error": t.error,
                    "attempts": t.attempts,
                    "output": None if not t.output else {
                        "id": t.output.id,
                        "filename": t.output.filename,
                        "size": t.output.size,
                        "format": t.output.format,
                        "mime": mime_for(t.output.format),
                    },
                }
                for t in batch.tasks
            ],
        }


def _kill_group(proc: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _limit_resources() -> None:
    """Applied inside each worker process before exec."""
    import resource

    try:
        cpu = settings.conversion_timeout_s + 10
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 5))
        two_gb = 2 * 1024 ** 3
        resource.setrlimit(resource.RLIMIT_FSIZE, (two_gb, two_gb))
        if sys.platform.startswith("linux"):
            four_gb = 4 * 1024 ** 3
            resource.setrlimit(resource.RLIMIT_AS, (four_gb, four_gb))
    except (ValueError, OSError):
        pass


manager = JobManager()
