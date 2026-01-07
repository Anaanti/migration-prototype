from playwright.sync_api import sync_playwright
from datetime import datetime
import json
import os

STAGING_DIR = "staging/raw_files"
LOG_FILE = "staging/logs/download_log.json"

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs("staging/logs", exist_ok=True)

download_logs = []

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-pdf-viewer",     # IMPORTANT
            "--disable-extensions"
        ]
    )

    context = browser.new_context(
        accept_downloads=True
    )
    page = context.new_page()

    page.goto("http://localhost:8000/web_ui/index.html")



    download_links = page.locator("a[download]")

    for i in range(download_links.count()):
        with page.expect_download() as download_info:
            download_links.nth(i).click()

        download = download_info.value

        file_path = os.path.join(STAGING_DIR, download.suggested_filename)
        download.save_as(file_path)

        download_logs.append({
            "file": download.suggested_filename,
            "downloaded_at": datetime.utcnow().isoformat()
        })

    browser.close()

with open(LOG_FILE, "w") as f:
    json.dump(download_logs, f, indent=2)
