# Zekrom

I kept running into the same annoying thing: needing a bunch of files in a different format (a few slides as PDF, a spreadsheet as CSV, some photos as WebP), and every online converter doing one file at a time, or asking me to sign up.

So I built Zekrom. Drop up to 30 files, pick a format, click once, download everything as a zip.

![Zekrom home](docs/screenshots/home.png)

## What it does

- Converts **documents, slides, spreadsheets, images, PDFs and data files** (110 routes across 25 input formats)
- Handles a **mixed batch** in one go: one format for everything, or a different one per file
- Only shows formats your files can actually become, so you never get a broken output
- Has a separate **Tools** page: merge / split / compress PDF, images to PDF, resize and compress images
- No account. Files get deleted automatically after an hour (or straight away with "Clear Session")

| Picking a format | Done | Tools |
|---|---|---|
| ![](docs/screenshots/files.png) | ![](docs/screenshots/done.png) | ![](docs/screenshots/tools.png) |

## Running it

You need Python 3.11+, Node 20+ and LibreOffice. LibreOffice does the Word / PowerPoint / Excel conversions, and without it those formats just get hidden.

```bash
# macOS: brew install --cask libreoffice
# Ubuntu: sudo apt install libreoffice

cd backend && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

scripts/dev.sh   # api on :8000, site on http://127.0.0.1:5173
```

There's also a `Dockerfile` if you want a single container (it builds the frontend and serves everything from one place).

### Deploying

It runs on Render's free plan using the `render.yaml` in this repo:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ganesh-tadigadapa/Snipex)

The free plan sleeps after 15 minutes without visitors, so the first visit after that takes about a minute to wake up. Every push to `main` redeploys it.

If you have Hugging Face PRO (Docker Spaces need it), `scripts/deploy-hf.sh <your-hf-username>` deploys there instead.

## How it's put together

```
backend/    FastAPI + the actual converters
  app/engines/   one file per kind of conversion (office, images, pdf, text, data)
  app/registry.py   every supported "X → Y" lives here
  app/jobs.py      the queue: runs things in parallel, retries, cleans up
frontend/   React + Tailwind + Framer Motion
docs/       screenshots
```

A few things I cared about:

- **Real conversions, tested.** `pytest` generates a sample of every format and runs every single conversion in the registry, checking the output is really what it claims to be (not just renamed).
- **One bad file doesn't ruin the batch.** Each conversion runs in its own process with a timeout, and whatever succeeds is still downloadable.
- **Speed.** LibreOffice is slow to start, so Office files are grouped per launch and images/PDFs run in a separate lane. A mixed 30-file batch takes about 4 seconds on my laptop.
- **Uploads are checked properly.** The file's bytes have to match its extension, archives are checked for zip bombs, and filenames can't escape the temp folder.

## Tests

```bash
cd backend
.venv/bin/python -m pytest -q                 # every conversion + the API
.venv/bin/python tests/e2e_ui.py /tmp/e2e     # clicks through the real UI (needs scripts/dev.sh running)
.venv/bin/python tests/bench.py <samples>     # 30-file speed check
```

## Settings

Everything is an environment variable: `ZEKROM_MAX_FILES` (30), `ZEKROM_MAX_FILE_MB` (100), `ZEKROM_MAX_BATCH_MB` (500), `ZEKROM_WORKERS`, `ZEKROM_OFFICE_WORKERS`, `ZEKROM_TIMEOUT`, `ZEKROM_RETENTION_S` (3600), `ZEKROM_RATE_LIMIT`, `ZEKROM_SCAN_COMMAND` (plug in a virus scanner like `clamdscan`), `ZEKROM_UNOSERVER` (1: keep one LibreOffice running instead of starting it per job; 0 turns that off).

## Known limits

- PDF → Word rebuilds the layout, so complicated pages can shift a bit. Scanned PDFs have no OCR.
- HTML / EPUB → PDF keeps the text and structure but not fancy styling or images.
- The job queue lives in memory, so this runs as a single server. Fine for me; it would need Redis/Celery to scale out.
- No end-to-end encryption. Put it behind HTTPS if you host it.

## Built with

FastAPI, LibreOffice, PyMuPDF, pdf2docx, Pillow, openpyxl, React, Tailwind, Framer Motion, Lucide.

## License

MIT, see [LICENSE](LICENSE). Use it, fork it, host your own.
