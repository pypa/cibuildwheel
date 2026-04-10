#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "mkdocs",
#   "playwright",
# ]
# ///

import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]


def main() -> None:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        subprocess.run(["mkdocs", "build", "--site-dir", tmp_dir], check=True)

        html_str = Path("docs/diagram.html").read_text()
        css_tags = f"""
            <style>{(tmp_dir / "css/theme.css").read_text()}</style>
            <style>{(tmp_dir / "css/theme_extra.css").read_text()}</style>
            <style>{(tmp_dir / "extra.css").read_text()}</style>
            <style>
                body {{
                    background: white;
                }}
            </style>
        """
        html_str = f"<html><head>{css_tags}</head><body>{html_str}</body></html>"

        html_path = Path(tmp_dir) / "diagram_screenshot.html"
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
