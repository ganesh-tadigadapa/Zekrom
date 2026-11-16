"""Catalog of the file formats ZEKROM understands."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Format:
    id: str
    label: str
    category: str
    extensions: tuple[str, ...]
    mime: str


FORMATS: dict[str, Format] = {
    f.id: f
    for f in [
        # Documents
        Format("doc", "DOC", "document", ("doc",), "application/msword"),
        Format("docx", "DOCX", "document", ("docx",), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        Format("odt", "ODT", "document", ("odt",), "application/vnd.oasis.opendocument.text"),
        Format("rtf", "RTF", "document", ("rtf",), "application/rtf"),
        Format("txt", "TXT", "document", ("txt",), "text/plain"),
        Format("html", "HTML", "document", ("html", "htm"), "text/html"),
        Format("epub", "EPUB", "document", ("epub",), "application/epub+zip"),
        # Presentations
        Format("ppt", "PPT", "presentation", ("ppt",), "application/vnd.ms-powerpoint"),
        Format("pptx", "PPTX", "presentation", ("pptx",), "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        Format("odp", "ODP", "presentation", ("odp",), "application/vnd.oasis.opendocument.presentation"),
        # Spreadsheets
        Format("xls", "XLS", "spreadsheet", ("xls",), "application/vnd.ms-excel"),
        Format("xlsx", "XLSX", "spreadsheet", ("xlsx",), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        Format("ods", "ODS", "spreadsheet", ("ods",), "application/vnd.oasis.opendocument.spreadsheet"),
        Format("csv", "CSV", "spreadsheet", ("csv",), "text/csv"),
        # Images
        Format("jpg", "JPG", "image", ("jpg", "jpeg"), "image/jpeg"),
        Format("png", "PNG", "image", ("png",), "image/png"),
        Format("webp", "WEBP", "image", ("webp",), "image/webp"),
        Format("bmp", "BMP", "image", ("bmp",), "image/bmp"),
        Format("tiff", "TIFF", "image", ("tiff", "tif"), "image/tiff"),
        Format("gif", "GIF", "image", ("gif",), "image/gif"),
        Format("svg", "SVG", "image", ("svg",), "image/svg+xml"),
        # PDF
        Format("pdf", "PDF", "pdf", ("pdf",), "application/pdf"),
        # Data
        Format("json", "JSON", "data", ("json",), "application/json"),
        Format("xml", "XML", "data", ("xml",), "application/xml"),
        Format("md", "Markdown", "data", ("md", "markdown"), "text/markdown"),
        # Packaged multi-file outputs (never an input)
        Format("zip", "ZIP", "archive", ("zip",), "application/zip"),
    ]
}

EXTENSION_TO_FORMAT: dict[str, str] = {
    ext: f.id for f in FORMATS.values() if f.id != "zip" for ext in f.extensions
}


def format_for_filename(filename: str) -> str | None:
    if "." not in filename:
        return None
    return EXTENSION_TO_FORMAT.get(filename.rsplit(".", 1)[1].lower())


def primary_extension(fmt: str) -> str:
    return FORMATS[fmt].extensions[0]


def mime_for(fmt: str) -> str:
    return FORMATS[fmt].mime if fmt in FORMATS else "application/octet-stream"
