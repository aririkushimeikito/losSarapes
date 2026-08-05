#!/usr/bin/env python3
"""
Render the site from src/ into a directory of plain HTML.

Thirteen pages share one header, one footer and one navigation. Hand-copying
that chrome into thirteen files means every future nav change is thirteen
edits and one of them gets missed, so the chrome lives in src/layout.html
and this script stamps it out.

    python3 tools/build.py _site            # a clean directory, for local work
    python3 tools/build.py . --in-place     # pages next to the assets, for Pages

GitHub Pages can serve either an Actions artifact or the branch root, and
which one a repository uses is not something this build controls. So the
rendered pages are also committed at the repo root: under a branch-root
build they are the site, and under an Actions build the workflow renders
into _site and ignores them. Either way the visitor gets the site rather
than a Jekyll rendering of the README.

CI re-runs this and fails if the committed pages have drifted from src/.

Stdlib only, no dependencies. Output is ordinary static HTML — the site
still has no runtime build step and no framework.
"""

import json
import re
import struct
import shutil
import sys
from pathlib import Path

# The domain the site will be served from. Canonical URLs, Open Graph URLs,
# the sitemap and the structured data are all built from it, so moving the
# site is a one-line change here.
SITE_URL = "https://www.lossarapeshorsham.com"

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


# ---------------------------------------------------------------- hours

def load_hours() -> dict:
    return json.loads((SRC / "data" / "hours.json").read_text())


def pretty(decimal: float) -> str:
    """11 -> '11 AM', 21.5 -> '9:30 PM'. Matches pretty() in js/site.js."""
    hour = int(decimal) % 24
    minute = round((decimal % 1) * 60)
    suffix = "PM" if hour >= 12 else "AM"
    twelve = 12 if hour % 12 == 0 else hour % 12
    return f"{twelve}{f':{minute:02d}' if minute else ''} {suffix}"


def span(day: dict) -> str:
    if day["open"] is None:
        return "Closed"
    return f'{pretty(day["open"])} &ndash; {pretty(day["close"])}'


def grouped(hours: dict) -> list:
    """Collapse consecutive days that keep the same hours into one row.

    Walked in displayOrder, which starts on Tuesday, so the closed day
    falls at the end rather than leading the list with 'Closed'."""
    by_day = {d["day"]: d for d in hours["days"]}
    runs = []
    for num in hours["displayOrder"]:
        day = by_day[num]
        key = (day["open"], day["close"])
        if runs and runs[-1][0] == key:
            runs[-1][1].append(day)
        else:
            runs.append([key, [day]])

    rows = []
    for _, days in runs:
        if len(days) == 1:
            label = days[0]["short"]
        else:
            label = f'{days[0]["short"]}&ndash;{days[-1]["short"]}'
        rows.append((label, span(days[0])))
    return rows


def hours_table(hours: dict) -> str:
    """The full seven-row table for the Visit section."""
    by_day = {d["day"]: d for d in hours["days"]}
    rows = []
    for num in hours["displayOrder"]:
        day = by_day[num]
        closed = ' class="is-closed"' if day["open"] is None else ""
        rows.append(
            f'<li data-day="{day["day"]}"{closed}>'
            f'<span class="hours__day">{day["name"]}</span>'
            f'<span class="hours__time">{span(day)}</span>'
            f'</li>'
        )
    return f'<ul class="hours" id="hoursList">{"".join(rows)}</ul>'


def hours_footer(hours: dict) -> str:
    rows = "".join(
        f'<li><span>{label}</span><span>{time}</span></li>'
        for label, time in grouped(hours)
    )
    return f'<ul class="hours-compact">{rows}</ul>'


def hours_jsonld(hours: dict) -> str:
    by_day = {d["day"]: d for d in hours["days"]}
    buckets = {}
    for day in hours["days"]:
        if day["open"] is None:
            continue
        buckets.setdefault((day["open"], day["close"]), []).append(day["name"])

    specs = []
    for (opens, closes), names in buckets.items():
        day_of_week = names[0] if len(names) == 1 else names
        specs.append({
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": day_of_week,
            "opens": f"{int(opens):02d}:{round((opens % 1) * 60):02d}",
            "closes": f"{int(closes):02d}:{round((closes % 1) * 60):02d}",
        })
    return json.dumps(specs, indent=4)[1:-1].strip()


def hours_data(hours: dict) -> str:
    """The blob js/site.js reads to decide open or closed, right now."""
    return json.dumps({
        "timeZone": hours["timeZone"],
        "days": {
            str(d["day"]): None if d["open"] is None else [d["open"], d["close"]]
            for d in hours["days"]
        },
    })


def owners_image() -> str:
    """The photograph of the three owners on the About page.

    It has been sent through chat several times but chat attachments never
    reach this filesystem — only what is pushed to the repository does. So
    rather than hard-code one or the other, this checks: drop the file at
    images/photos/owners.jpg, rebuild, and it appears. No edit needed."""
    path = ROOT / "images" / "photos" / "owners.jpg"
    if path.exists():
        width, height = jpeg_size(path)
        return (
            f'<img class="aside-image" src="images/photos/owners.jpg"'
            f' alt="Luis, Mauricio and Alfonso"'
            f' width="{width}" height="{height}" loading="lazy">'
        )
    return (
        '<div class="aside-image aside-image--pending" aria-hidden="true">'
        '<span class="tbd">Owners\' photograph — push it to '
        'images/photos/owners.jpg</span></div>'
    )


# --------------------------------------------------------------- gallery

def render_gallery() -> str:
    """The gallery page, from src/data/gallery.json and the files on disk."""
    data = json.loads((SRC / "data" / "gallery.json").read_text())

    # Photographs with a dedicated home elsewhere on the site, which are
    # deliberately not in the gallery. Without this the completeness check
    # below would reject them and fail the build.
    NOT_IN_GALLERY = {"owners"}

    on_disk = {p.stem for p in (ROOT / "images" / "photos").glob("*.jpg")} - NOT_IN_GALLERY
    listed = {p["file"] for p in data["photos"]}
    # An uploaded photograph nobody added to the data file would otherwise sit
    # in the repository unused and unnoticed. Fail instead.
    if on_disk - listed:
        raise SystemExit(
            "gallery.json is missing photographs that exist in images/photos: "
            + ", ".join(sorted(on_disk - listed))
        )
    if listed - on_disk:
        raise SystemExit(
            "gallery.json lists photographs that are not in images/photos: "
            + ", ".join(sorted(listed - on_disk))
        )

    jump = "".join(
        f'<li><a href="#gallery-{g["id"]}">{esc(g["title"])}</a></li>'
        for g in data["groups"]
    )

    sections = []
    for group in data["groups"]:
        photos = [p for p in data["photos"] if p["group"] == group["id"]]
        tiles = []
        for i, photo in enumerate(photos):
            width, height = jpeg_size(ROOT / "images" / "photos" / f'{photo["file"]}.jpg')
            # Every fourth photograph runs double width, so the grid has a
            # rhythm instead of reading as a uniform contact sheet.
            wide = " tile--wide" if i % 7 == 3 else ""
            tiles.append(
                f'<li class="tile{wide}">'
                f'<img src="images/photos/{photo["file"]}.jpg" alt="{esc(photo["alt"])}"'
                f' width="{width}" height="{height}" loading="lazy">'
                f'</li>'
            )
        sections.append(
            f'<section class="gallery-group" id="gallery-{group["id"]}">'
            f'<h2 class="gallery-heading">{esc(group["title"])}</h2>'
            f'<ul class="gallery">{"".join(tiles)}</ul>'
            f'</section>'
        )

    return (
        f'<nav class="jump-nav" aria-label="Sections of this gallery">\n'
        f'  <ul>{jump}</ul>\n'
        f'</nav>\n'
        f'{"".join(sections)}\n'
    )


def jpeg_size(path: Path) -> tuple[int, int]:
    """Width and height straight from the JPEG header — no dependencies, and
    no chance of the markup disagreeing with the file."""
    data = path.read_bytes()
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    raise SystemExit(f"{path}: could not read dimensions")


# --------------------------------------------------------------- reviews

def render_reviews() -> str:
    data = json.loads((SRC / "data" / "reviews.json").read_text())

    cards = []
    for review in data["reviews"]:
        placeholder = review.get("placeholder", False)
        rating = int(review.get("rating", 5))

        stars = "".join(
            f'<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"'
            f' class="star{"" if i < rating else " is-empty"}">'
            f'<path d="M10 1.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L1.6 7.7l5.8-.8z"/>'
            f"</svg>"
            for i in range(5)
        )

        name = esc(review["name"])
        source = esc(review["source"])
        attribution = (
            f'<a href="{esc(review["url"])}" target="_blank" rel="noopener">{source}</a>'
            if review.get("url") else source
        )

        cards.append(
            f'<li class="review-card{" review-card--placeholder" if placeholder else ""}">'
            + ('<p class="review-card__flag">Placeholder</p>' if placeholder else "")
            + f'<p class="stars" role="img" aria-label="{rating} out of 5">{stars}</p>'
            f'<blockquote><p>{esc(review["quote"])}</p></blockquote>'
            f'<p class="review-card__by">'
            f'<span class="review-card__name">{name}</span>'
            f'<span class="review-card__source">on {attribution}</span>'
            f'</p>'
            f'</li>'
        )

    return (
        f'<section class="reviews" id="reviews">\n'
        f'  <div class="wrap">\n'
        f'    <p class="eyebrow">Reviews</p>\n'
        f'    <h2 class="section-title">{esc(data["heading"])}</h2>\n'
        f'    <p class="section-lede">{esc(data["lede"])}</p>\n'
        f'    <ul class="review-grid">{"".join(cards)}</ul>\n'
        f'  </div>\n'
        f'</section>\n'
    )


def anchor(text: str) -> str:
    """A stable id from a course name, for the jump links at the top."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"course-{slug}"


def render_menu(slug: str) -> str:
    """Build a menu page body from src/data/menus.json."""
    data = json.loads((SRC / "data" / "menus.json").read_text())
    menu = data["menus"][slug]

    # The titles run at the top of the page and jump down to their section,
    # so a long menu can be navigated without scrolling through it.
    jump = "".join(
        f'<li><a href="#{anchor(c["name"])}">{esc(c["name"])}</a></li>'
        for c in menu["courses"]
    )

    pdf = ""
    if menu.get("pdf"):
        label = menu.get("downloadLabel", f'Download the {menu["title"].lower()} menu (PDF)')
        pdf = (
            f'<a class="btn btn--solid menu-download" href="{esc(menu["pdf"])}"'
            f' target="_blank" rel="noopener">'
            f'<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            f'<path d="M12 3v12m0 0l-4.5-4.5M12 15l4.5-4.5M4 19h16"/></svg>'
            f'{esc(label)}</a>'
        )

    footnote = ""
    if menu.get("footnote"):
        footnote = f'<p class="menu-footnote wrap">{esc(menu["footnote"])}</p>'

    courses = []
    for course in menu["courses"]:
        # A prix fixe course, or one where the choice is the whole price,
        # has nothing to put in a price column.
        hide_price = course.get("hidePrice", False)

        rows = []
        for item in course["items"]:
            price = item.get("price")
            if hide_price:
                price_html = ""
            elif price:
                price_html = f'<span class="menu-item__price">{esc(price)}</span>'
            else:
                price_html = '<span class="menu-item__price tbd">$—</span>'
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
            f'<section class="course" id="{anchor(course["name"])}">'
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
        f'    <nav class="course-jump" aria-label="Sections of this menu">\n'
        f'      <ul>{jump}</ul>\n'
        f'    </nav>\n'
        f'    {pdf}\n'
        f'  </div>\n'
        f'</section>\n'
        f'<div class="sarape-band sarape-rule" aria-hidden="true"></div>\n'
        f'<section class="menu-body">\n'
        f'  <div class="wrap courses">{"".join(courses)}</div>\n'
        f'  {footnote}\n'
        f'</section>\n'
    )


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # In-place means "write the pages beside the assets already here" — so it
    # must never wipe the target, which is the repository itself.
    in_place = "--in-place" in sys.argv

    out = Path(args[0] if args else "_site")
    if not in_place:
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

    layout = (SRC / "layout.html").read_text()
    hours = load_hours()
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
            "canonical": f"{SITE_URL}/{'' if page.name == 'index.html' else page.name}",
            "site_url": SITE_URL,
            "og_image": meta.get("image", "images/photos/dining-room.jpg"),
            "nav_desktop": desktop_nav(active),
            "nav_mobile": mobile_nav(active),
            # `content` is substituted before the hours tokens so that a page
            # body may use them too — the Visit table on the home page does.
            "content": body,
            "hours_table": hours_table(hours),
            "hours_footer": hours_footer(hours),
            "hours_note": hours["note"],
            "hours_footer_note": hours["footerNote"],
            "hours_jsonld": hours_jsonld(hours),
            "hours_data": hours_data(hours),
            "reviews": render_reviews(),
            "gallery": render_gallery(),
            "owners_image": owners_image(),
        }.items():
            html = html.replace("{{" + token + "}}", value)

        leftover = re.findall(r"\{\{(\w+)\}\}", html)
        if leftover:
            raise SystemExit(f"{page.name}: unfilled placeholders {leftover}")

        (out / page.name).write_text(html)
        built.append(page.name)

    # In place, the assets are already sitting next to the pages.
    if not in_place:
        for d in ASSET_DIRS:
            shutil.copytree(ROOT / d, out / d)

    # Without this, a branch-root Pages build hands the repo to Jekyll, which
    # renders README.md as the home page and ignores everything else.
    (out / ".nojekyll").touch()

    # A sitemap listing exactly the pages that exist, so it cannot go stale.
    urls = "".join(
        f"  <url><loc>{SITE_URL}/{'' if name == 'index.html' else name}</loc>"
        f"<changefreq>monthly</changefreq>"
        f"<priority>{'1.0' if name == 'index.html' else '0.7'}</priority></url>\n"
        for name in built
    )
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    )

    print(f"{out}: {len(built)} pages — {', '.join(built)}")


if __name__ == "__main__":
    main()
