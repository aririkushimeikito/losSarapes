#!/usr/bin/env python3
"""
Render the site from src/ into a directory of plain HTML.

Thirteen pages share one header, one footer and one navigation. Hand-copying
that chrome into thirteen files means every future nav change is thirteen
edits and one of them gets missed, so the chrome lives in src/layout.html
and this script stamps it out.

    python3 tools/build.py _site

Stdlib only, no dependencies. Output is ordinary static HTML — the site
still has no runtime build step and no framework.
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
ASSET_DIRS = ["css", "js", "fonts", "images", "videos"]

# Header order, matching the navigation the restaurant runs today.
# key, label, href, children
NAV = [
    ("home", "Home", "index.html", []),
    ("about", "About", "about.html", []),
    ("menus", "Menus", "menus.html", [
        ("Lunch menu", "menu-lunch.html"),
        ("Dinner menu", "menu-dinner.html"),
        ("Kids menu", "menu-kids.html"),
        ("Happy hour menu", "menu-happy-hour.html"),
        ("Cocktail menu", "menu-cocktails.html"),
        ("Beers & drafts", "menu-beers.html"),
        ("Sunday brunch", "menu-brunch.html"),
    ]),
    ("catering", "Catering", "catering.html", []),
    ("events", "Events", "events.html", []),
    ("private-parties", "Private parties", "private-parties.html", []),
    ("gallery", "Gallery", "gallery.html", []),
]


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def read_page(path: Path) -> tuple[dict, str]:
    """Split `key: value` front matter from the body at the first `---`."""
    raw = path.read_text()
    if "\n---\n" not in raw:
        raise SystemExit(f"{path}: missing '---' front-matter separator")
    head, body = raw.split("\n---\n", 1)
    meta = {}
    for line in head.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def desktop_nav(active: str) -> str:
    items = []
    for key, label, href, children in NAV:
        current = ' aria-current="page"' if key == active else ""
        if not children:
            items.append(f'<li><a href="{href}"{current}>{esc(label)}</a></li>')
            continue

        # The dropdown opens on hover for pointers and on click for
        # keyboards and touch, so it is reachable either way.
        subs = "".join(
            f'<li><a href="{h}">{esc(t)}</a></li>' for t, h in children
        )
        items.append(
            f'<li class="has-menu">'
            f'<a href="{href}"{current}>{esc(label)}</a>'
            f'<button class="submenu-toggle" type="button" aria-expanded="false"'
            f' aria-controls="submenu-{key}">'
            f'<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            f'<path d="M6 9l6 6 6-6"/></svg>'
            f'<span class="sr-only">Show {esc(label.lower())}</span>'
            f'</button>'
            f'<ul class="submenu" id="submenu-{key}">{subs}</ul>'
            f'</li>'
        )
    return "\n        ".join(items)


def mobile_nav(active: str) -> str:
    items = []
    for key, label, href, children in NAV:
        current = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{href}"{current}>{esc(label)}</a></li>')
        # Menus are the reason people open this panel; nesting them behind
        # another tap would bury them.
        for text, h in children:
            items.append(f'<li class="is-sub"><a href="{h}">{esc(text)}</a></li>')
    return "\n      ".join(items)


def render_menu(slug: str) -> str:
    """Build a menu page body from src/data/menus.json."""
    data = json.loads((SRC / "data" / "menus.json").read_text())
    menu = data["menus"][slug]

    courses = []
    for course in menu["courses"]:
        rows = []
        for item in course["items"]:
            price = item.get("price")
            price_html = (
                f'<span class="menu-item__price">{esc(price)}</span>'
                if price
                else '<span class="menu-item__price tbd">$—</span>'
            )
            note = (
                f'<span class="menu-item__tags">{esc(item["tags"])}</span>'
                if item.get("tags")
                else ""
            )
            rows.append(
                f'<li class="menu-item">'
                f'<div class="menu-item__head">'
                f'<h3>{esc(item["name"])}</h3>{price_html}</div>'
                f'<p>{esc(item["desc"])}</p>{note}'
                f'</li>'
            )
        courses.append(
            f'<section class="course">'
            f'<h2 class="course__title">{esc(course["name"])}</h2>'
            + (f'<p class="course__note">{esc(course["note"])}</p>'
               if course.get("note") else "")
            + f'<ul class="course__items">{"".join(rows)}</ul>'
            f'</section>'
        )

    return (
        f'<section class="page-head">\n'
        f'  <div class="wrap">\n'
        f'    <p class="eyebrow">Menus</p>\n'
        f'    <h1 class="section-title">{esc(menu["title"])}</h1>\n'
        f'    <p class="section-lede">{esc(menu["lede"])}</p>\n'
        f'    <p class="served">{esc(menu["served"])}</p>\n'
        f'  </div>\n'
        f'</section>\n'
        f'<div class="sarape-band sarape-rule" aria-hidden="true"></div>\n'
        f'<section class="menu-body">\n'
        f'  <div class="wrap courses">{"".join(courses)}</div>\n'
        f'</section>\n'
    )


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    layout = (SRC / "layout.html").read_text()
    built = []

    for page in sorted((SRC / "pages").glob("*.html")):
        meta, body = read_page(page)
        active = meta.get("nav", "")

        # A menu page declares its data key instead of writing out rows.
        if meta.get("menu"):
            body = render_menu(meta["menu"]) + body

        html = layout
        for token, value in {
            "title": meta.get("title", "Los Sarapes Horsham"),
            "description": meta.get("description", ""),
            "body_class": meta.get("class", ""),
            "nav_desktop": desktop_nav(active),
            "nav_mobile": mobile_nav(active),
            "content": body,
        }.items():
            html = html.replace("{{" + token + "}}", value)

        leftover = re.findall(r"\{\{(\w+)\}\}", html)
        if leftover:
            raise SystemExit(f"{page.name}: unfilled placeholders {leftover}")

        (out / page.name).write_text(html)
        built.append(page.name)

    for d in ASSET_DIRS:
        shutil.copytree(ROOT / d, out / d)
    (out / ".nojekyll").touch()

    print(f"{out}: {len(built)} pages — {', '.join(built)}")


if __name__ == "__main__":
    main()
