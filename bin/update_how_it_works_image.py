#!/usr/bin/env python3


import subprocess
import sys
from pathlib import Path

try:
    from html2image import Html2Image  # type: ignore[import-not-found]
except ImportError:
    sys.exit(
        """
        html2image not found. Ensure you have Chrome (on Mac/Windows) or
        Chromium (on Linux) installed, and then do:
            pip install html2image
        """
    )


def main() -> None:
    subprocess.run(["mkdocs", "build"], check=True)

    hti = Html2Image(custom_flags=["--force-device-scale-factor=2"])

    html_str = Path("docs/diagram.md").read_text()
    css_tags = f"""
        <style>{Path("site/css/theme.css").read_text()}</style>
        <style>{Path("site/css/theme_extra.css").read_text()}</style>
        <style>{Path("site/extra.css").read_text()}</style>
        <style>
            body {{
                background: white;
            }}
        </style>
    """
    html_str = css_tags + html_str

    [screenshot, *_] = hti.screenshot(
        html_str=html_str,
        size=(830, 405),
    )

    dest_path = Path("docs/data/how-it-works.png")
    dest_path.unlink(missing_ok=True)

    Path(screenshot).rename(dest_path)


if __name__ == "__main__":
    main()
