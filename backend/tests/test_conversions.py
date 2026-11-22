"""Run EVERY conversion advertised by the registry against a real sample file and verify the
output's actual bytes (not just its extension) match the target format."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app import registry
from app.config import settings
from app.validation import validate_file
from app.worker import run

CONVERSIONS = registry.all_conversions(include_unavailable=True)


def _check_output(path: Path, fmt: str) -> None:
    assert path.exists() and path.stat().st_size > 0, f"{path} is empty"
    validate_file(path, fmt)


@pytest.mark.parametrize("conv", CONVERSIONS, ids=[f"{c.src}->{c.dst}" for c in CONVERSIONS])
def test_conversion(conv, samples, tmp_path):
    if not conv.available:
        pytest.skip(f"missing dependency: {conv.requires}")
    src = samples[conv.src]
    outputs = run({
        "op": "convert",
        "inputs": [str(src)],
        "src_format": conv.src,
        "dst": conv.dst,
        "out_dir": str(tmp_path / "out"),
        "stem": "result",
        "options": {"_soffice": settings.soffice, "_lo_profile": str(tmp_path / "lo"), "_timeout": 170},
    })
    assert outputs, "no output files"
    for out in outputs:
        _check_output(Path(out), conv.dst)


def test_registry_has_no_self_conversions():
    assert all(c.src != c.dst for c in CONVERSIONS)


def test_multi_page_pdf_to_png_produces_one_image_per_page(samples, tmp_path):
    outputs = run({"op": "convert", "inputs": [str(samples["pdf"])], "src_format": "pdf", "dst": "png",
                   "out_dir": str(tmp_path), "stem": "r", "options": {}})
    assert len(outputs) == 2


def test_xlsx_to_csv_exports_each_sheet(samples, tmp_path):
    outputs = run({"op": "convert", "inputs": [str(samples["xlsx"])], "src_format": "xlsx", "dst": "csv",
                   "out_dir": str(tmp_path), "stem": "b", "options": {}})
    assert sorted(Path(o).name for o in outputs) == ["b-Notes.csv", "b-Sales.csv"]
    assert "Apple,3" in Path(sorted(outputs)[1]).read_text(encoding="utf-8-sig")


def test_csv_to_xlsx_keeps_numbers(samples, tmp_path):
    from openpyxl import load_workbook

    out = run({"op": "convert", "inputs": [str(samples["csv"])], "src_format": "csv", "dst": "xlsx",
               "out_dir": str(tmp_path), "stem": "d", "options": {}})[0]
    ws = load_workbook(out).active
    assert ws["B2"].value == 3 and ws["C2"].value == 1.25 and ws["A4"].value == "Cherry, red"


def test_json_xml_roundtrip_content(samples, tmp_path):
    out = run({"op": "convert", "inputs": [str(samples["json"])], "src_format": "json", "dst": "xml",
               "out_dir": str(tmp_path), "stem": "j", "options": {}})[0]
    text = Path(out).read_text()
    assert "<name>Apple</name>" in text and "<origin>NZ</origin>" in text


def test_docx_to_pdf_contains_text(samples, tmp_path):
    if not settings.soffice:
        pytest.skip("LibreOffice not installed")
    import pymupdf

    out = run({"op": "convert", "inputs": [str(samples["docx"])], "src_format": "docx", "dst": "pdf",
               "out_dir": str(tmp_path), "stem": "r",
               "options": {"_soffice": settings.soffice, "_lo_profile": str(tmp_path / "lo")}})[0]
    with pymupdf.open(out) as doc:
        assert "Quarterly report" in doc[0].get_text()


def test_html_to_pdf_drops_scripts(samples, tmp_path):
    import pymupdf

    out = run({"op": "convert", "inputs": [str(samples["html"])], "src_format": "html", "dst": "pdf",
               "out_dir": str(tmp_path), "stem": "p", "options": {}})[0]
    with pymupdf.open(out) as doc:
        text = doc[0].get_text()
    assert "Hello" in text and "alert" not in text


# ---- tools -----------------------------------------------------------------------------------

def _tool(op, inputs, tmp_path, **options):
    return [Path(p) for p in run({"op": op, "inputs": [str(i) for i in inputs], "out_dir": str(tmp_path),
                                  "stem": "t", "options": options, "dst": None, "src_format": None})]


def test_merge_pdf(samples, tmp_path):
    import pymupdf

    out = _tool("merge_pdf", [samples["pdf"], samples["pdf"]], tmp_path)
    with pymupdf.open(out[0]) as doc:
        assert doc.page_count == 4


def test_split_pdf_modes(samples, tmp_path):
    import pymupdf

    assert len(_tool("split_pdf", [samples["pdf"]], tmp_path / "a", mode="pages")) == 2
    extracted = _tool("split_pdf", [samples["pdf"]], tmp_path / "b", mode="extract", ranges="2")
    with pymupdf.open(extracted[0]) as doc:
        assert doc.page_count == 1
    with pytest.raises(ValueError):
        _tool("split_pdf", [samples["pdf"]], tmp_path / "c", mode="ranges", ranges="5-9")


def test_compress_pdf_never_grows(samples, tmp_path):
    out = _tool("compress_pdf", [samples["pdf"]], tmp_path, level="high")[0]
    assert out.stat().st_size <= samples["pdf"].stat().st_size
    validate_file(out, "pdf")


def test_resize_and_compress_images(samples, tmp_path):
    from PIL import Image

    out = _tool("resize_image", [samples["jpg"]], tmp_path / "r", width=160)[0]
    with Image.open(out) as im:
        assert im.size == (160, 100)
    out = _tool("compress_image", [samples["png"]], tmp_path / "c", quality=60)[0]
    assert out.stat().st_size <= samples["png"].stat().st_size


def test_images_to_single_pdf(samples, tmp_path):
    import pymupdf

    out = _tool("images_to_pdf", [samples["jpg"], samples["png"], samples["svg"], samples["tiff"]], tmp_path)[0]
    with pymupdf.open(out) as doc:
        assert doc.page_count == 5  # tiff has 2 pages


def test_zip_outputs_are_valid(samples, tmp_path):
    out = _tool("split_pdf", [samples["pdf"]], tmp_path, mode="pages")
    for p in out:
        validate_file(p, "pdf")
    assert all(not zipfile.is_zipfile(p) for p in out)


@pytest.mark.parametrize("orientation", [1, 3, 6, 8, 2])
def test_phone_photo_to_pdf_keeps_orientation_and_bytes(orientation, tmp_path):
    """Phone JPEGs are embedded as-is (no decode); the EXIF rotation must still be applied.
    Orientation 2 (mirrored) exercises the decode-and-redraw fallback."""
    import io

    import pymupdf
    from PIL import Image, ImageOps

    from app.engines.images import _jpeg_passthrough

    img = Image.new("RGB", (400, 200), "white")
    img.paste((255, 0, 0), (0, 0, 100, 60))  # red block marks the stored top-left corner
    exif = Image.Exif()
    exif[0x0112] = orientation
    src = tmp_path / "IMG_0001.jpg"
    img.save(src, "JPEG", quality=95, exif=exif)
    want = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    assert (_jpeg_passthrough(src) is None) == (orientation == 2)

    for out in (_tool("images_to_pdf", [src, src], tmp_path)[0],
                Path(run({"op": "convert", "inputs": [str(src)], "src_format": "jpg", "dst": "pdf",
                          "out_dir": str(tmp_path / "single"), "stem": "one", "options": {}})[0])):
        with pymupdf.open(out) as doc:
            pix = doc[0].get_pixmap()
            got = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if orientation != 2:  # passthrough: the original JPEG stream is embedded unchanged
                xref = doc[0].get_images()[0][0]
                assert doc.extract_image(xref)["image"] == src.read_bytes()
        assert (got.width > got.height) == (want.width > want.height)
        small = (8, 4) if want.width > want.height else (4, 8)
        g, w = got.resize(small).load(), want.resize(small).load()
        red = [(x, y) for x in range(small[0]) for y in range(small[1]) if w[x, y][0] > 200 and w[x, y][2] < 100]
        assert red and all(g[x, y][0] > 200 and g[x, y][2] < 100 for x, y in red)
