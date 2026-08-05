# Los Sarapes Horsham

Single-page site for Los Sarapes — Mexican kitchen, margarita and tequila bar,
Horsham PA. Static: no build step, no dependencies, no framework.

```
index.html
css/site.css
js/site.js
fonts/                 self-hosted latin subsets (Karla variable, Lilita One)
images/hero/           hero poster
images/logo/           stacked lockup, ink and white
videos/                hero footage, desktop and mobile cuts
tools/                 single-file build for CSP-restricted hosts
```

## Running it

Any static server works — the page uses relative paths only.

```sh
python3 -m http.server 8000
```

## Editing hours

Hours live in one place: the `<ul id="hoursList">` in the Visit section of
`index.html`. Each row carries `data-open` / `data-close` as 24-hour decimals
(`11.5` = 11:30 AM); a row with neither is a closed day.

`js/site.js` reads that list and derives everything else from it — the printed
times, the "today" highlight, and the *Open now until…* badge in the hero. The
badge is computed in the restaurant's own time zone (`TIME_ZONE` in
`js/site.js`), not the visitor's. Edit the markup and the whole page follows;
the times still render with JavaScript off.

`openingHoursSpecification` in the JSON-LD block at the bottom of `index.html`
is the one copy that does not update itself — change it alongside.

## Still to fill in

Placeholders are marked `class="tbd"` in the markup and render with a dashed
red underline so they cannot ship unnoticed. Search for `tbd` and `TODO`:

- street address and phone number (Visit section)
- the real online-ordering URL — every `href="#order"` CTA currently points at
  the order band rather than an ordering system
- a full-menu link, and a patio photograph to replace the woven CSS panel

## Publishing to a CSP-restricted host

Some hosts block every external request, including same-origin subresources.
`tools/build-single-file.py` folds the CSS, JS, fonts, images and the mobile
video into one HTML file with data URIs:

```sh
python3 tools/build-single-file.py dist/index.html
```

Output lands around 4 MB. Only the mobile video cut is inlined — the desktop
cut base64-encodes to ~11 MB, which is too much to ship inside a document.
