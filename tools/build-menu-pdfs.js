/*
 * Print the built menu pages to PDF, for the download buttons.
 *
 *   python3 tools/build.py _site
 *   node tools/build-menu-pdfs.js _site
 *
 * The PDF is printed from the same page the site serves, so the two can
 * never disagree — change src/data/menus.json and both follow. It also
 * comes out searchable, selectable and a few hundred KB, which a scan of
 * the printed menu would not.
 *
 * Requires playwright and a Chromium. PLAYWRIGHT_BROWSERS_PATH is already
 * set in this environment; pass CHROME_PATH to point somewhere else.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SITE = process.argv[2] || '_site';
// Which pages get a PDF, and what the file is called. Must match the "pdf"
// field in src/data/menus.json.
const TARGETS = [{ page: 'menu-lunch.html', out: 'menus/los-sarapes-lunch-menu.pdf' }];

(async () => {
  const exe = process.env.CHROME_PATH || undefined;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const page = await browser.newPage();

  for (const { page: name, out } of TARGETS) {
    const src = path.resolve(SITE, name);
    if (!fs.existsSync(src)) throw new Error(`missing ${src} — run tools/build.py first`);

    await page.goto('file://' + src, { waitUntil: 'load' });
    // The open/closed badge and the jump links are navigation, not menu, and
    // print.css hides them. Give the fonts a moment so the PDF embeds them.
    await page.evaluateHandle('document.fonts.ready');

    const dest = path.resolve(SITE, out);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    await page.pdf({
      path: dest,
      format: 'Letter',
      printBackground: true,
      margin: { top: '14mm', bottom: '14mm', left: '12mm', right: '12mm' },
    });

    const kb = Math.round(fs.statSync(dest).size / 1024);
    console.log(`${out}  ${kb} KB`);
  }

  await browser.close();
})();
