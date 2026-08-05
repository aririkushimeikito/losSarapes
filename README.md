# Los Sarapes Horsham

Fourteen-page site for Los Sarapes — Mexican kitchen, margarita and tequila
bar, 1101 Horsham Rd, Ambler PA. Static HTML, no dependencies, no framework.

```
src/layout.html        the header, footer and <head> every page shares
src/pages/*.html       front matter + body, one file per page
src/data/menus.json    every menu item on the site
tools/build.py         renders src/ -> _site/
tools/build-single-file.py   folds one page into a single self-contained file
css/ js/ fonts/ images/ videos/
```

## Building and running it

```sh
python3 tools/build.py _site
python3 -m http.server 8000 --directory _site
```

There is no dependency to install — `build.py` is stdlib Python. Output is
ordinary static HTML; nothing runs at request time.

Pushing to `main` builds and deploys to GitHub Pages automatically
(`.github/workflows/pages.yml`). The first run enabled Pages itself.

## Editing the site

**Navigation** is the `NAV` table at the top of `tools/build.py` — one list,
used for the desktop bar, the dropdown and the mobile panel. Add a page there
and add the matching file in `src/pages/`.

**Menus** are `src/data/menus.json`. Every menu page renders from it; the page
files themselves only name which menu they are. Prices are `null` and render
as a dashed `$—` placeholder, because the printed menu is the source of truth
for prices and none were supplied.

**Hours** live in the `<ul id="hoursList">` on `src/pages/index.html`. Each row
carries `data-open` / `data-close` as 24-hour decimals (`11.5` = 11:30 AM); a
row with neither is a closed day. `js/site.js` reads that list and derives the
printed times, the "today" highlight and the *Open now until…* badge in the
hero, computed in the restaurant's own time zone rather than the visitor's.
Edit the markup and the rest follows; times still render with JavaScript off.

Two copies of the hours do **not** update themselves — the footer block and
the `openingHoursSpecification` JSON-LD, both in `src/layout.html`. Change
them alongside.

## Still to fill in

Placeholders render with a dashed red underline (`class="tbd"`) or a dashed
outline on unwired buttons (`class="tbd-link"`), so they cannot ship
unnoticed. Search for `tbd` and `TODO`:

- the online-ordering URL — "Start an order" currently goes nowhere
- a reservation system — "Make a reservation" dials the restaurant instead
- social profile URLs (footer)
- menu prices, throughout `src/data/menus.json`
- catering pricing, minimums and lead times
- private-party room capacities, deposits and minimums
- this season's dated events, or delete that block
- photographs for the gallery; every empty tile is captioned with the shot
  that belongs there
- a patio photograph, to replace the woven CSS panel on the home page

Menu item names and descriptions are written as representative placeholders
and should be checked against the real menu before launch.

## Publishing one page to a CSP-restricted host

Some hosts block every external request, including same-origin subresources.
`tools/build-single-file.py` folds the CSS, JS, fonts, images and the mobile
video into one HTML file with data URIs:

```sh
python3 tools/build.py _site
python3 tools/build-single-file.py dist/index.html
```

Output lands around 4 MB. Only the mobile video cut is inlined — the desktop
cut base64-encodes to ~11 MB, which is too much to ship inside a document.
