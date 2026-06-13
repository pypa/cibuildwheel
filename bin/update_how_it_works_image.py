#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "playwright",
# ]
# ///

import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

CSS = """
    <link href="https://fonts.googleapis.com/css2?family=Lato&display=swap" rel="stylesheet">
    <style>
        html, body {
          font-family: Lato, "Helvetica Neue", Helvetica, Arial, sans-serif;
          font-weight: 400;
          font-size: 16px;
          color: #404040;
          background: white;
          margin: 0;
          padding: 0;
        }
        * {
          box-sizing: border-box;
        }
    </style>
"""


def main() -> None:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

    html_str = Path("docs/diagram.html").read_text()
    html_str = f"<html><head>{CSS}</head><body>{html_str}</body></html>"

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        html_path = Path(tmp_dir_str) / "diagram_screenshot.html"
        html_path.write_text(html_str)

        dest_path = Path("docs/data/how-it-works.png")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2, viewport={"width": 830, "height": 600})
            page.goto(html_path.as_uri())
            page.wait_for_load_state("networkidle")

            height = page.evaluate("document.body.scrollHeight")
            page.set_viewport_size({"width": 830, "height": height})

            page.screenshot(path=str(dest_path), full_page=True)
            browser.close()


if __name__ == "__main__":
    main()
