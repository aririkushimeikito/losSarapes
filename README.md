# Los Sarapes Horsham

Fourteen-page site for Los Sarapes — Mexican kitchen, margarita and tequila
bar, 1101 Horsham Rd, Ambler PA. Static HTML, no dependencies, no framework.

```
src/layout.html        the header, footer and <head> every page shares
src/pages/*.html       front matter + body, one file per page
src/data/menus.json    every menu item on the site
src/data/hours.json    THE hours — everything that states a time comes from here
src/data/reviews.json  guest reviews on the home page
src/data/gallery.json  every photograph, and which gallery group it belongs to
menus/*.pdf            the restaurant's own printed menus, for download
tools/build.py         renders src/ -> _site/
tools/build-single-file.py   folds one page into a single self-contained file
css/ js/ fonts/ videos/
images/photos/         67 photographs, renamed by subject and resized for the web
```

## Building and running it

```sh
python3 tools/build.py _site
python3 -m http.server 8000 --directory _site
```

There is no dependency to install — `build.py` is stdlib Python. Output is
ordinary static HTML; nothing runs at request time.

### How it gets published

GitHub Pages serves either an Actions artifact or the branch root, depending
on a repository setting this build cannot control. Both are kept working:

- `.github/workflows/pages.yml` renders into `_site/` and uploads it, for an
  Actions-source build.
- The rendered pages are **also committed at the repo root**, for a
  branch-root build. `.nojekyll` sits alongside them, without which Pages
  hands the repo to Jekyll and serves a rendering of this README instead of
  the site.

**So after editing anything under `src/`, rebuild in place and commit the
result:**

```sh
python3 tools/build.py . --in-place
```

CI re-runs that and fails the build if the committed pages have drifted.

(If you would rather keep only one path, set Settings → Pages → Source to
"GitHub Actions" and the root copies become dead weight you can delete.)

## Editing the site

**Navigation** is the `NAV` table at the top of `tools/build.py` — one list,
used for the desktop bar, the dropdown and the mobile panel. Add a page there
and add the matching file in `src/pages/`.

**Menus** are `src/data/menus.json`. Every menu page renders from it; the page
files themselves only name which menu they are. Prices are `null` and render
as a dashed `$—` placeholder, because the printed menu is the source of truth
for prices and none were supplied.

**Photographs** are `src/data/gallery.json` — one entry per file in
`images/photos`, giving its alt text and its gallery group (Cocktails,
Cuisine, Ambient). The gallery page renders from it, and **the build fails if
a file in `images/photos` is missing from the list**, so an upload cannot sit
in the repository unused. Add photographs at 2000px on the long edge,
quality ~82.

**Hours** are `src/data/hours.json`, and that file is the only place any
opening time is written down. `tools/build.py` renders all of it from there:

- the seven-row table in the Visit section
- the grouped list in the footer (consecutive days with matching hours are
  collapsed automatically — `Tue–Thu`, `Fri–Sat`)
- the `openingHoursSpecification` in the JSON-LD
- a JSON blob `js/site.js` reads to work out whether the kitchen is open
  right now

`open` / `close` are 24-hour decimals (`11.5` = 11:30 AM); a day with `null`
for both is closed. Change a time, run the build, and every one of those
follows — they cannot drift apart.

**The open/closed badge** appears in the header on every page, in the hero
line, above the Visit hours and in the footer. Each one shows a single word
— Open or Closed — which fits any column at any width. Screen readers get
the full sentence instead ("Open now until 9 PM"), since it is worth more to
someone who cannot see the hours printed beside it.

All of them are filled by one computation in `js/site.js`, evaluated in the
restaurant's own time zone rather than the visitor's — someone checking from
California sees whether Ambler is open. With JavaScript off every badge stays
hidden, since the answer is not knowable; the printed hours still render,
because they are static.

## Still to fill in

Placeholders render with a dashed red underline (`class="tbd"`), so they
cannot ship unnoticed. Search for `tbd` and `TODO`:

- a reservation system — "Make a reservation" dials the restaurant instead
- menu prices, throughout `src/data/menus.json`
- catering pricing, minimums and lead times
- private-party room capacities, deposits and minimums
- this season's dated events, or delete that block
- real guest reviews in `src/data/reviews.json` — three of the four cards
  are templates and render greyed with a PLACEHOLDER chip

Two menu cards use the nearest photograph rather than an exact one: Sunday
brunch and Kids have no dedicated shot in the library. Swap them in
`src/pages/menus.html` when brunch and kids' plates are photographed.

Lunch and Cocktails are transcribed from the printed cards, with real
prices. Dinner, Kids, Happy hour, Beers and Brunch are still representative
placeholders and should be replaced from the printed menus.

## The jump bar

Menu pages and the gallery carry a bar of section titles that sticks under
the header, so the list stays reachable from anywhere on a long page. It is
rendered as a direct child of `<main>` — a sticky element only sticks inside
its own parent, so leaving it in the page head would unstick it as soon as
that section scrolled away.

Pages that have one get `has-jump` on `<body>`, which adds the bar's height
to their anchor offset. `html` already carries `scroll-padding-top` for the
header; the class adds only the bar on top of that. Counting the header
twice is what once dropped every jump target a header-height too low.

## SEO

`SITE_URL` at the top of `tools/build.py` is the domain everything is built
from — canonical links, `og:url`, the absolute share image, `sitemap.xml`,
`robots.txt` and the structured data. Moving the site is one line there.

Each page carries its own title, description and canonical URL. The
Restaurant JSON-LD in `src/layout.html` includes the address, phone, hours,
menu URL, price range and `sameAs` links to every social profile.

## The downloadable menus

`menus/` holds the restaurant's own menu PDFs — the printed artwork, not a
rendering of the web page. `menus/los-sarapes-lunch-menu.pdf` is three
pages: prix fixe, the a la carte lunch card, and drinks. The download
button on `menu-lunch.html` opens it in a new tab; the path is the `pdf`
field in `src/data/menus.json`.

To add one for another menu, drop the PDF in `menus/` and set that menu's
`pdf` field to its path.

`@media print` in `css/site.css` still styles the menu pages for anyone
printing one straight from the browser — it drops the header, footer, jump
links and download button, and adds the address and phone under the title.

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
