"""LibreOffice (headless) adapter for office documents, presentations and spreadsheets."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# LibreOffice export filter per target format. Filters are explicit so the right component
# (Writer / Calc / Impress) export is used.
FILTERS = {
    "pdf": "pdf",
    "docx": 'docx:MS Word 2007 XML',
    "doc": "doc:MS Word 97",
    "odt": "odt",
    "rtf": "rtf:Rich Text Format",
    "txt": "txt:Text (encoded):UTF8",
    "html": "html:XHTML Writer File:UTF8",
    "pptx": "pptx:Impress MS PowerPoint 2007 XML",
    "ppt": "ppt:MS PowerPoint 97",
    "odp": "odp",
    "xlsx": "xlsx:Calc MS Excel 2007 XML",
    "xls": "xls:MS Excel 97",
    "ods": "ods",
    # Comma separated, double-quoted, UTF-8 (76), export ALL sheets (-1) as separate files.
    "csv": "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1",
}


class OfficeError(RuntimeError):
    pass


def convert_group(items: list[dict], dst: str, options: dict) -> dict[str, list[Path]]:
    """Convert several files to the same format in ONE LibreOffice launch.

    Starting LibreOffice costs ~1-3 s, converting a typical document a fraction of that, so
    grouping files amortises the start-up cost. `items` are {"id", "input", "stem", "out_dir"}.
    Returns {id: [output paths]}; an id with an empty list was not converted.
    """
    soffice = options.get("_soffice")
    if not soffice:
        raise OfficeError("LibreOffice is not installed on this server")
    profile = Path(options.get("_lo_profile") or tempfile.mkdtemp(prefix="zekrom-lo-"))
    work = Path(tempfile.mkdtemp(prefix="lo-group-", dir=options.get("_work_dir")))
    export_dir = work / "export"
    export_dir.mkdir()
    staged = []
    for it in items:
        # Stage under the (unique, safe) task id; LibreOffice names outputs after the input file.
        src = Path(it["input"])
        target = work / f"{it['id']}{src.suffix.lower()}"
        shutil.copyfile(src, target)
        staged.append(str(target))
    cmd = [
        soffice,
        f"-env:UserInstallation={profile.resolve().as_uri()}",
        "--headless", "--invisible", "--nologo", "--norestore", "--nodefault", "--nolockcheck",
        "--convert-to", FILTERS[dst],
        "--outdir", str(export_dir),
        *staged,
    ]
    if staged and staged[0].endswith(".csv"):
        cmd[1:1] = ["--infilter=CSV:44,34,76,1"]
    env = {**os.environ, "SAL_USE_VCLPLUGIN": "svp", "HOME": str(profile)}
    try:
        subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=options.get("_timeout", 170))
        produced = [p for p in export_dir.iterdir() if p.is_file() and p.stat().st_size > 0]
        results: dict[str, list[Path]] = {}
        for it in items:
            out_dir = Path(it["out_dir"])
            out_dir.mkdir(parents=True, exist_ok=True)
            moved = []
            for p in sorted(produced):
                rest = p.name[len(it["id"]):]
                if p.name.startswith(it["id"]) and rest[:1] in (".", "-"):
                    final = out_dir / f"{it['stem']}{rest}"
                    shutil.move(str(p), final)
                    moved.append(final)
            results[it["id"]] = moved
        return results
    finally:
        shutil.rmtree(work, ignore_errors=True)


def convert(src: Path, out_dir: Path, stem: str, dst: str, options: dict) -> list[Path]:
    item = {"id": "single0000000", "input": str(src), "stem": stem, "out_dir": str(out_dir)}
    outputs = convert_group([item], dst, {**options, "_work_dir": str(out_dir)})[item["id"]]
    if not outputs:
        raise OfficeError("LibreOffice could not convert this file")
    return outputs
