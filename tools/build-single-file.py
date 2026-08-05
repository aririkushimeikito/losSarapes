#!/usr/bin/env python3
"""
Build a single self-contained page from the built site.

The published/preview host serves the page under a strict CSP that blocks
every external request — no stylesheets, no fonts, no media. So this
inlines the CSS and JS and rewrites every asset reference to a data URI.

    python3 tools/build.py _site
    python3 tools/build-single-file.py dist/index.html [_site/index.html]

Reads the *rendered* page, so it picks up the shared layout rather than
a second copy of it. Only the home page is worth doing this to; the rest
of the site is ordinary linked HTML.

Only the mobile video is inlined. The desktop cut is 8 MB, which base64
encodes to ~11 MB and would push a single HTML file past what is
reasonable to ship; the mobile cut is the same footage and sits under a
heavy scrim anyway.
"""

import base64
import mimetypes
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/index.html")
PAGE = Path(sys.argv[2] if len(sys.argv) > 2 else REPO / "_site/index.html")
ROOT = PAGE.parent  # asset paths in the page are relative to it

MOBILE_VIDEO = "videos/los-sarapes-hero-mobile.mp4"


def data_uri(rel_path: str) -> str:
    path = ROOT / rel_path
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def inline_css(css: str) -> str:
    """Rewrite url("../x/y") references, which are relative to css/."""
    def sub(match):
        ref = match.group(1).strip("\"'")
        return f'url("{data_uri(ref.replace("../", "", 1))}")'

    css = re.sub(r'url\((\s*["\'][^)]+["\']\s*)\)', sub, css)

    # The host supplies its own <body>, so the page's `has-hero` class never
    # reaches it and the "no hero on this page" rules would all fire. This
    # build is always the home page, which does have a hero, so those rules
    # are disabled outright rather than papered over with a class-adding
    # script that would flash a solid header before it ran.
    return css.replace("body:not(.has-hero)", ".single-file-build-has-a-hero")


def inline_js(js: str) -> str:
    """Point both video branches at the one inlined file."""
    uri = data_uri(MOBILE_VIDEO)
    js = re.sub(
        r"video\.src = small\s*\n\s*\?\s*'[^']+'\s*\n\s*:\s*'[^']+';",
        f"video.src = '{uri}';",
        js,
    )
    # The data URI is already in memory; letting the browser preload it is
    # pointless work, and 'auto' on a data: source is a no-op anyway.
    return js


def main() -> None:
    html = PAGE.read_text()
    css = inline_css((ROOT / "css/site.css").read_text())
    js = inline_js((ROOT / "js/site.js").read_text())

    # The host wraps our output in its own <!doctype>/<head>/<body>, so
    # strip our shell and keep only <title> plus the page content.
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S).group(1)

    # Local asset references -> data URIs.
    body = re.sub(
        r'(src|poster)="((?:images|videos)/[^"]+)"',
        lambda m: f'{m.group(1)}="{data_uri(m.group(2))}"',
        body,
    )
    # Drop the script/style tags that pointed at the now-inlined files.
    body = re.sub(r'\s*<script src="js/site\.js" defer></script>', "", body)

    out = f"""<title>{title}</title>
<style>
/* The brand commits to one visual world — adobe, bone and ink — so the
   page holds that ground in either viewer theme rather than inverting. */
:root {{ color-scheme: light; }}
html {{ background: #F6EFE2; }}
{css}
</style>
{body}
<script>
{js}
</script>
"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out)
    print(f"{OUT}  {len(out) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
