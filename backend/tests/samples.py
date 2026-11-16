"""Generate a small, real sample file for every supported input format."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from app.config import settings

TEXT = "ZEKROM sample. Every File. One Click."


def _lo(src: Path, dst_ext: str, filt: str, out: Path) -> Path:
    profile = Path(tempfile.mkdtemp(prefix="lo-test-"))
    subprocess.run(
        [settings.soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore",
         "--convert-to", filt, "--outdir", str(out), str(src)],
        check=True, capture_output=True, timeout=180,
    )
    shutil.rmtree(profile, ignore_errors=True)
    return out / f"{src.stem}.{dst_ext}"


def build(out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    s: dict[str, Path] = {}

    # Text-ish
    (out / "notes.txt").write_text(f"{TEXT}\nSecond line with unicode: café ✓\n\nNew paragraph.\n", encoding="utf-8")
    (out / "readme.md").write_text(f"# Title\n\n{TEXT}\n\n- one\n- two\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```\ncode\n```\n")
    (out / "page.html").write_text(
        f"<!doctype html><html><head><title>t</title><script>alert(1)</script></head><body><h1>Hello</h1>"
        f"<p>{TEXT} <b>bold</b> <a href='https://example.com'>link</a></p><ul><li>a</li><li>b</li></ul>"
        "<table><tr><th>x</th><th>y</th></tr><tr><td>1</td><td>2</td></tr></table></body></html>"
    )
    (out / "data.csv").write_text("name,qty,price\nApple,3,1.25\nBanana,12,0.5\n\"Cherry, red\",100,9.99\n")
    (out / "data.json").write_text(json.dumps([
        {"name": "Apple", "qty": 3, "tags": ["fruit", "red"], "meta": {"origin": "NZ"}},
        {"name": "Banana", "qty": 12, "tags": ["fruit"], "meta": {"origin": "EC"}},
    ]))
    (out / "feed.xml").write_text(
        '<?xml version="1.0"?><catalog xmlns="urn:x"><book id="1"><title>A</title></book>'
        '<book id="2"><title>B</title></book></catalog>'
    )
    (out / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120" viewBox="0 0 200 120">'
        '<rect width="200" height="120" rx="16" fill="#7C3AED"/><circle cx="60" cy="60" r="30" fill="#C4B5FD"/></svg>'
    )
    (out / "letter.rtf").write_text(r"{\rtf1\ansi\deff0{\fonttbl{\f0 Helvetica;}}\f0\fs24 " + TEXT + r"\par Second paragraph.\par}")
    s.update(txt=out / "notes.txt", md=out / "readme.md", html=out / "page.html", csv=out / "data.csv",
             json=out / "data.json", xml=out / "feed.xml", svg=out / "logo.svg", rtf=out / "letter.rtf")

    # Images (RGBA source so alpha flattening is exercised)
    img = Image.new("RGBA", (320, 200), (124, 58, 237, 255))
    d = ImageDraw.Draw(img)
    d.ellipse((40, 40, 160, 160), fill=(196, 181, 253, 128))
    d.text((180, 90), "ZEKROM", fill="white")
    img.save(out / "photo.png")
    img.convert("RGB").save(out / "photo.jpg", quality=90)
    img.save(out / "photo.webp")
    img.convert("RGB").save(out / "photo.bmp")
    frames = [img.convert("RGB"), Image.new("RGB", (320, 200), "white")]
    frames[0].save(out / "scan.tiff", save_all=True, append_images=frames[1:])
    frames[0].save(out / "anim.gif", save_all=True, append_images=frames[1:], duration=200, loop=0)
    s.update(png=out / "photo.png", jpg=out / "photo.jpg", webp=out / "photo.webp", bmp=out / "photo.bmp",
             tiff=out / "scan.tiff", gif=out / "anim.gif")

    # PDF: 2 pages with text and an image
    import pymupdf

    doc = pymupdf.open()
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"{TEXT} Page {i + 1}", fontsize=14)
        page.insert_image(pymupdf.Rect(72, 100, 392, 300), filename=str(out / "photo.png"))
    doc.save(out / "report.pdf")
    s["pdf"] = out / "report.pdf"

    # DOCX
    from docx import Document

    docx = Document()
    docx.add_heading("Quarterly report", 1)
    docx.add_paragraph(TEXT)
    table = docx.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text, table.cell(1, 0).text, table.cell(1, 1).text = "a", "b", "1", "2"
    docx.save(out / "report.docx")
    s["docx"] = out / "report.docx"

    # PPTX
    from pptx import Presentation

    prs = Presentation()
    for title in ("Hello ZEKROM", "Second slide"):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title
        slide.placeholders[1].text = TEXT
    prs.save(out / "deck.pptx")
    s["pptx"] = out / "deck.pptx"

    # XLSX with two sheets
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales"
    for row in (["name", "qty"], ["Apple", 3], ["Banana", 12]):
        ws.append(row)
    ws2 = wb.create_sheet("Notes")
    ws2.append(["note"])
    ws2.append([TEXT])
    wb.save(out / "book.xlsx")
    s["xlsx"] = out / "book.xlsx"

    # EPUB (minimal valid package)
    with zipfile.ZipFile(out / "novel.epub", "w") as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")
        zf.writestr("META-INF/container.xml",
                    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                    '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        zf.writestr("OEBPS/content.opf",
                    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
                    '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Novel</dc:title><dc:identifier id="id">x</dc:identifier></metadata>'
                    '<manifest><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/></manifest>'
                    '<spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
        for n in (1, 2):
            zf.writestr(f"OEBPS/c{n}.xhtml", f'<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Chapter {n}</h1><p>{TEXT}</p></body></html>')
    s["epub"] = out / "novel.epub"

    # Legacy / OpenDocument formats produced by LibreOffice from the modern ones
    if settings.soffice:
        s["doc"] = _lo(s["docx"], "doc", "doc:MS Word 97", out)
        s["odt"] = _lo(s["docx"], "odt", "odt", out)
        s["ppt"] = _lo(s["pptx"], "ppt", "ppt:MS PowerPoint 97", out)
        s["odp"] = _lo(s["pptx"], "odp", "odp", out)
        s["xls"] = _lo(s["xlsx"], "xls", "xls:MS Excel 97", out)
        s["ods"] = _lo(s["xlsx"], "ods", "ods", out)
    return s
