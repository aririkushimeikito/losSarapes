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

    print(f"{out}: {len(built)} pages — {', '.join(built)}")


if __name__ == "__main__":
    main()
