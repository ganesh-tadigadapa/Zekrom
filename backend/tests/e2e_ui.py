"""Browser end-to-end check of the real UI against the running servers.
Usage: python tests/e2e_ui.py <out_dir> [base_url]"""
import re, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from tests.samples import build

out = Path(sys.argv[1]); base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5173"
s = build(out / "samples")
(out / "samples" / "malware.exe").write_bytes(b"MZ fake")
files = [str(s[k]) for k in ("docx", "pptx", "xlsx", "jpg", "png", "csv", "txt", "md", "pdf")] + [str(out / "samples" / "malware.exe")]

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(base); page.wait_for_selector("text=Drop your files here")
    page.screenshot(path=out / "1-hero.png")
    page.locator('input[type=file]').first.set_input_files(files)
    page.wait_for_selector("text=/Convert \\d+ files/")
    page.screenshot(path=out / "2-files.png")
    page.get_by_role("button", name="Customize per file").click()
    page.screenshot(path=out / "3-perfile.png")
    page.get_by_role("button", name="Use one format for all").click()
    page.get_by_role("button", name=re.compile(r"Convert \d+ files")).click()
    page.wait_for_selector("text=/Converting|Uploading|Your Files Are Ready/", timeout=30000)
    page.screenshot(path=out / "4-progress.png")
    page.wait_for_selector("text=Your Files Are Ready!", timeout=240000)
    page.wait_for_timeout(1200)
    page.screenshot(path=out / "5-done.png", full_page=False)
    with page.expect_download() as dl:
        page.get_by_role("link", name="Download All as ZIP").click()
    zpath = out / "all.zip"; dl.value.save_as(zpath)
    print("ZIP:", zipfile.ZipFile(zpath).namelist())
    # Page 2: Tools. Merge two PDFs.
    page.get_by_role("button", name="Convert More Files").click()
    page.get_by_role("tab", name="Tools").click()
    page.wait_for_selector("text=Every Tool.")
    page.locator("button:has-text('Merge PDF')").first.click()
    import shutil; second = out / "samples" / "appendix.pdf"; shutil.copyfile(s["pdf"], second)
    page.locator("input[type=file]").first.set_input_files([str(s["pdf"]), str(out / "samples" / "novel.epub"), str(second)])
    page.get_by_role("button", name="Run Merge PDF").click()
    page.wait_for_selector("text=Your Files Are Ready!", timeout=60000)
    page.wait_for_timeout(800)
    page.screenshot(path=out / "6-tool.png")
    print("TOOL OUTPUT:", page.locator("li p").first.inner_text())
    m = b.new_page(viewport={"width": 390, "height": 844})
    m.goto(base); m.wait_for_selector("text=Drop your files here"); m.wait_for_timeout(1000); m.screenshot(path=out / "7-mobile.png")
    m.evaluate("localStorage.setItem('zekrom-theme','light')"); m.reload(); m.wait_for_selector("text=Drop your files here")
    m.locator('input[type=file]').first.set_input_files(files[:5]); m.wait_for_timeout(500)
    m.screenshot(path=out / "8-mobile-light.png")
    print("ERRORS:", errors)
    b.close()
