"""Raster/vector image conversions using Pillow (raster) and PyMuPDF (SVG rasterising)."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence

# Refuse decompression bombs (~ 16k x 11k pixels).
Image.MAX_IMAGE_PIXELS = 180_000_000

PIL_FORMAT = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "bmp": "BMP", "tiff": "TIFF", "gif": "GIF", "pdf": "PDF"}
NO_ALPHA = {"jpg", "bmp", "pdf"}
# EXIF orientation -> PyMuPDF insert_image rotation. Mirrored orientations (2, 4, 5, 7) aren't
# listed: those few files take the decode-and-redraw path.
JPEG_ROTATE = {1: 0, 3: 180, 6: 270, 8: 90}
PDF_DPI = 150.0


def _jpeg_passthrough(src: Path) -> tuple[int, int, int] | None:
    """(rotation, width, height) if this JPEG can go into a PDF as-is, else None.

    Embedding the original JPEG bytes skips decoding entirely: a 12 MP phone photo would
    otherwise need ~36 MB per copy of raw pixels (several copies), which is what ran a 512 MB
    instance out of memory. It is also much faster and loses no quality.
    """
    with Image.open(src) as im:  # reads the header only
        if im.format != "JPEG" or im.mode not in ("RGB", "L"):
            return None
        rot = JPEG_ROTATE.get(im.getexif().get(0x0112, 1))
        return None if rot is None else (rot, *im.size)


def _insert_jpeg_page(doc, src: Path, rot: int, width: int, height: int) -> None:
    pw, ph = (height, width) if rot in (90, 270) else (width, height)
    page = doc.new_page(width=pw * 72 / PDF_DPI, height=ph * 72 / PDF_DPI)
    page.insert_image(page.rect, filename=str(src), rotate=rot)


def _flatten(img: Image.Image, background=(255, 255, 255)) -> Image.Image:
    """Composite transparency onto white for formats that can't store alpha."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, background)
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        return canvas
    return img.convert("RGB") if img.mode not in ("RGB", "L") else img


def _prepare(img: Image.Image, dst: str) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if dst in NO_ALPHA:
        return _flatten(img)
    if img.mode in ("CMYK", "YCbCr", "I;16", "I", "F"):
        return img.convert("RGB")
    if dst == "webp" and img.mode not in ("RGB", "RGBA"):
        return img.convert("RGBA" if "transparency" in img.info or img.mode in ("LA", "PA") else "RGB")
    return img


def save_image(img: Image.Image, target: Path, dst: str, quality: int = 90) -> None:
    kwargs: dict = {}
    if dst == "jpg":
        kwargs = {"quality": quality, "optimize": True, "progressive": True}
    elif dst == "webp":
        kwargs = {"quality": quality, "method": 4}
    elif dst == "png":
        # optimize=True is ~3x slower for a <1% smaller file. Big images (photos) barely compress
        # as PNG anyway, so they get the fast level: ~4x quicker for ~10% more bytes.
        kwargs = {"compress_level": 1 if img.width * img.height > 4_000_000 else 6}
    elif dst == "tiff":
        kwargs = {"compression": "tiff_lzw"}
    elif dst == "pdf":
        kwargs = {"resolution": 150.0}
    img.save(target, PIL_FORMAT[dst], **kwargs)


def convert(src: Path, out_dir: Path, stem: str, dst: str, options: dict) -> list[Path]:
    target = out_dir / f"{stem}.{dst}"
    if dst == "pdf" and (jpeg := _jpeg_passthrough(src)):
        import pymupdf

        with pymupdf.open() as doc:
            _insert_jpeg_page(doc, src, *jpeg)
            doc.save(target, garbage=3, deflate=True)
        return [target]
    with Image.open(src) as im:
        frames = getattr(im, "n_frames", 1)
        if dst == "pdf" and frames > 1:
            # Multi-page TIFF (or animated GIF) -> one PDF page per frame.
            pages = [_prepare(f.copy(), "pdf") for f in ImageSequence.Iterator(im)]
            pages[0].save(target, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
            return [target]
        if dst == "gif" and src.suffix.lower() in (".webp", ".gif") and frames > 1:
            im.save(target, "GIF", save_all=True, loop=im.info.get("loop", 0))
            return [target]
        im.seek(0)
        save_image(_prepare(im.copy(), dst), target, dst, int(options.get("quality", 90)))
    return [target]


def convert_svg(src: Path, out_dir: Path, stem: str, dst: str, options: dict) -> list[Path]:
    import pymupdf

    target = out_dir / f"{stem}.{dst}"
    with pymupdf.open(src, filetype="svg") as doc:
        if dst == "pdf":
            pdf_bytes = doc.convert_to_pdf()
            target.write_bytes(pdf_bytes)
            return [target]
        page = doc[0]
        # Render at 2x for crisp output, capped so huge viewBoxes can't explode memory.
        scale = min(2.0, 8000 / max(page.rect.width, page.rect.height, 1))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=dst not in NO_ALPHA)
        img = Image.frombytes("RGBA" if pix.alpha else "RGB", (pix.width, pix.height), pix.samples)
        save_image(_prepare(img, dst), target, dst)
    return [target]


# ---- Image tools -------------------------------------------------------------------------

def _fmt_of(src: Path) -> str:
    ext = src.suffix.lower().lstrip(".")
    return {"jpeg": "jpg", "tif": "tiff"}.get(ext, ext)


def resize(src: Path, out_dir: Path, stem: str, options: dict) -> list[Path]:
    fmt = _fmt_of(src)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        percent = options.get("percent")
        if percent:
            nw, nh = max(1, round(w * float(percent) / 100)), max(1, round(h * float(percent) / 100))
        else:
            tw, th = options.get("width"), options.get("height")
            if not tw and not th:
                raise ValueError("Provide a width, height or percentage")
            tw, th = int(tw or 0), int(th or 0)
            if options.get("keep_aspect", True):
                ratio = min(tw / w if tw else float("inf"), th / h if th else float("inf"))
                nw, nh = max(1, round(w * ratio)), max(1, round(h * ratio))
            else:
                nw, nh = tw or w, th or h
        if nw * nh > Image.MAX_IMAGE_PIXELS:
            raise ValueError("Requested size is too large")
        out = im.resize((nw, nh), Image.LANCZOS)
        target = out_dir / f"{stem}.{fmt}"
        save_image(_prepare(out, fmt), target, fmt, quality=92)
    return [target]


def compress(src: Path, out_dir: Path, stem: str, options: dict) -> list[Path]:
    quality = max(10, min(95, int(options.get("quality", 75))))
    fmt = _fmt_of(src)
    with Image.open(src) as im:
        im = _prepare(im.copy(), fmt)
        target = out_dir / f"{stem}.{fmt}"
        if fmt == "png":
            # PNG is lossless: reduce to an adaptive 256-colour palette for real savings.
            pal = im.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
            pal.save(target, "PNG", optimize=True)
        else:
            save_image(im, target, fmt, quality=quality)
    if target.stat().st_size >= src.stat().st_size:
        # Never hand back a "compressed" file that is bigger than the original.
        target.write_bytes(src.read_bytes())
    return [target]


def images_to_pdf(srcs: list[Path], out_dir: Path, stem: str, options: dict) -> list[Path]:
    import pymupdf

    target = out_dir / f"{stem}.pdf"
    out = pymupdf.open()
    for src in srcs:
        if src.suffix.lower() == ".svg":
            with pymupdf.open(src, filetype="svg") as d, pymupdf.open("pdf", d.convert_to_pdf()) as page_pdf:
                out.insert_pdf(page_pdf)
            continue
        if jpeg := _jpeg_passthrough(src):
            _insert_jpeg_page(out, src, *jpeg)
            continue
        with Image.open(src) as im:
            for frame in ImageSequence.Iterator(im):
                buf = io.BytesIO()
                _prepare(frame.copy(), "pdf").save(buf, "PDF", resolution=PDF_DPI)
                with pymupdf.open("pdf", buf.getvalue()) as page_pdf:
                    out.insert_pdf(page_pdf)
    out.save(target, garbage=3, deflate=True)
    out.close()
    return [target]
