/* ============================================================
   LOS SARAPES — SITE BEHAVIOUR
   Vanilla JS. No dependencies.
   ============================================================ */
(function () {
  'use strict';

  /* ------------------------------------------------------------
     EDIT ME — service hours live in the markup, not here.
     The <ul id="hoursList"> in the Visit section carries
     data-day / data-open / data-close on each row and is the one
     place hours are written down: it renders without JS, it is
     crawlable, and the "Open now" badge in the hero is derived
     from it. To change hours, edit that list.

     data-open / data-close are 24h decimals: 11.5 = 11:30 AM.
     A row with no data-open is a closed day.
     ------------------------------------------------------------ */
  var TIME_ZONE = 'America/New_York';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var conn = navigator.connection || {};
  var saveData = conn.saveData === true;

  /* ---------- Hero video ------------------------------------ */

  var video = document.getElementById('heroVideo');
  var soundBtn = document.getElementById('soundToggle');

  function loadVideo() {
    if (!video) return false;
    // Motion sensitivity or a metered connection: poster only.
    if (reduceMotion || saveData) return false;

    var small = window.matchMedia('(max-width: 900px)').matches;
    video.src = small
      ? 'videos/los-sarapes-hero-mobile.mp4'
      : 'videos/los-sarapes-hero.mp4';
    video.preload = 'auto';

    video.addEventListener('canplay', function () {
      video.classList.add('is-ready');
    }, { once: true });

    // Decode failure (a browser without the H.264 codec, a truncated
    // download): fall back to the poster and take the sound toggle away,
    // since there is no longer anything to unmute.
    video.addEventListener('error', function () {
      video.classList.remove('is-ready');
      if (soundBtn) soundBtn.hidden = true;
    }, { once: true });

    var attempt = video.play();
    if (attempt && attempt.catch) {
      // Autoplay blocked (rare when muted) — poster carries the section.
      attempt.catch(function () { video.classList.remove('is-ready'); });
    }
    return true;
  }

  var videoOn = loadVideo();

  // No video means nothing to unmute.
  if (!videoOn && soundBtn) soundBtn.hidden = true;

  if (videoOn && soundBtn && video) {
    var label = document.getElementById('soundLabel');
    soundBtn.addEventListener('click', function () {
      var wantSound = video.muted;
      video.muted = !wantSound;
      if (wantSound) video.play().catch(function () {});
      soundBtn.setAttribute('aria-pressed', String(wantSound));
      if (label) label.textContent = wantSound ? 'Sound on' : 'Sound off';
    });
  }

  // Don't burn battery on a video nobody is looking at.
  if ('IntersectionObserver' in window && video) {
    new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!video.src) return;
        if (entry.isIntersecting) { video.play().catch(function () {}); }
        else { video.pause(); }
      });
    }, { threshold: 0.15 }).observe(video);
  }

  document.addEventListener('visibilitychange', function () {
    if (!video || !video.src) return;
    if (document.hidden) video.pause();
    else if (isInView(video)) video.play().catch(function () {});
  });

  function isInView(el) {
    var r = el.getBoundingClientRect();
    return r.bottom > 0 && r.top < window.innerHeight;
  }

  /* ---------- Header state ---------------------------------- */

  var header = document.getElementById('siteHeader');
  var hero = document.getElementById('hero');

  if (header && hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      header.classList.toggle('is-stuck', !entries[0].isIntersecting);
    }, { rootMargin: '-72px 0px 0px 0px', threshold: 0 }).observe(hero);
  }

  /* ---------- Mobile nav ------------------------------------ */

  var navToggle = document.getElementById('navToggle');
  var mobileNav = document.getElementById('mobileNav');

  function setNav(open) {
    if (!navToggle || !mobileNav) return;
    navToggle.setAttribute('aria-expanded', String(open));
    mobileNav.hidden = !open;
    // The panel paints its own bone background, so the header has to go
    // solid with it — otherwise light nav sits on a transparent bar.
    if (header) header.classList.toggle('is-open', open);
    // Stop the page scrolling underneath the open panel.
    document.body.classList.toggle('is-locked', open);
  }

  if (navToggle && mobileNav) {
    navToggle.addEventListener('click', function () {
      setNav(navToggle.getAttribute('aria-expanded') !== 'true');
    });

    mobileNav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setNav(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !mobileNav.hidden) {
        setNav(false);
        navToggle.focus();
      }
    });

    // Tap anywhere outside the header to dismiss.
    document.addEventListener('click', function (e) {
      if (mobileNav.hidden) return;
      if (!header.contains(e.target)) setNav(false);
    });

    // Rotating to a wide viewport hides the toggle; don't strand the lock.
    window.matchMedia('(min-width: 901px)').addEventListener('change', function (e) {
      if (e.matches) setNav(false);
    });
  }

  /* ---------- Menus dropdown --------------------------------- */

  /* CSS opens the submenu on hover and on focus-within, which covers mice
     and keyboards. This adds the click path, which is what touch devices
     and anyone tapping the chevron actually use. */
  var dropdowns = document.querySelectorAll('.site-nav .has-menu');

  Array.prototype.forEach.call(dropdowns, function (item) {
    var toggle = item.querySelector('.submenu-toggle');
    if (!toggle) return;

    function setOpen(open) {
      item.setAttribute('data-open', String(open));
      toggle.setAttribute('aria-expanded', String(open));
    }

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = toggle.getAttribute('aria-expanded') === 'true';
      // Only one open at a time.
      Array.prototype.forEach.call(dropdowns, function (other) {
        other.setAttribute('data-open', 'false');
        var t = other.querySelector('.submenu-toggle');
        if (t) t.setAttribute('aria-expanded', 'false');
      });
      setOpen(!open);
    });

    // Tabbing out of the last link should close it behind you.
    item.addEventListener('focusout', function (e) {
      if (!item.contains(e.relatedTarget)) setOpen(false);
    });

    document.addEventListener('click', function (e) {
      if (!item.contains(e.target)) setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (item.getAttribute('data-open') !== 'true') return;
      setOpen(false);
      toggle.focus();
    });
  });

  /* Nav highlighting is not done here — now that each nav item is its own
     page, tools/build.py stamps aria-current="page" into the markup. */

  /* ---------- Hours: read the markup, don't duplicate it ------ */

  var HOURS = {};
  var hoursRows = document.querySelectorAll('#hoursList li[data-day]');

  Array.prototype.forEach.call(hoursRows, function (row) {
    var day = parseInt(row.getAttribute('data-day'), 10);
    var open = row.getAttribute('data-open');
    var close = row.getAttribute('data-close');
    HOURS[day] = (open === null || close === null)
      ? null
      : [[parseFloat(open), parseFloat(close)]];
  });

  function localNow() {
    // Read the clock in the restaurant's time zone, not the visitor's.
    var parts = new Intl.DateTimeFormat('en-US', {
      timeZone: TIME_ZONE,
      weekday: 'short', hour: 'numeric', minute: 'numeric', hour12: false
    }).formatToParts(new Date());

    var map = {};
    parts.forEach(function (p) { map[p.type] = p.value; });
    var days = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    var hour = parseInt(map.hour, 10) % 24;

    return { day: days[map.weekday], time: hour + parseInt(map.minute, 10) / 60 };
  }

  function pretty(decimal) {
    var h = Math.floor(decimal % 24);
    var m = Math.round((decimal % 1) * 60);
    var suffix = h >= 12 ? 'PM' : 'AM';
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return h12 + (m ? ':' + String(m).padStart(2, '0') : '') + ' ' + suffix;
  }

  function nextOpening(day) {
    var names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    for (var i = 1; i <= 7; i++) {
      var d = (day + i) % 7;
      if (HOURS[d] && HOURS[d].length) {
        var when = i === 1 ? 'tomorrow' : names[d];
        return 'Opens ' + when + ' at ' + pretty(HOURS[d][0][0]);
      }
    }
    return '';
  }

  var now = localNow();

  // Rewrite each row's time text from its own data, so the printed hours
  // and the badge can never disagree, and flag today.
  Array.prototype.forEach.call(hoursRows, function (row) {
    var day = parseInt(row.getAttribute('data-day'), 10);
    var blocks = HOURS[day];
    var cell = row.querySelector('.hours__time');

    if (cell) {
      cell.textContent = blocks
        ? blocks.map(function (b) { return pretty(b[0]) + ' – ' + pretty(b[1]); }).join(', ')
        : 'Closed';
    }
    row.classList.toggle('is-closed', !blocks);
    row.classList.toggle('is-today', day === now.day);
  });

  var status = document.getElementById('openStatus');
  if (status && hoursRows.length) {
    var today = HOURS[now.day] || [];
    var openBlock = null;

    for (var i = 0; i < today.length; i++) {
      if (now.time >= today[i][0] && now.time < today[i][1]) { openBlock = today[i]; break; }
    }

    if (openBlock) {
      status.textContent = 'Open now until ' + pretty(openBlock[1]);
      status.className = 'status is-open';
    } else {
      var later = null;
      for (var j = 0; j < today.length; j++) {
        if (now.time < today[j][0]) { later = today[j]; break; }
      }
      status.textContent = later
        ? 'Opens today at ' + pretty(later[0])
        : nextOpening(now.day);
      status.className = 'status is-closed';
    }
    status.hidden = !status.textContent;
  }

  /* ---------- Footer year ------------------------------------ */

  var year = document.getElementById('year');
  if (year) year.textContent = String(new Date().getFullYear());
})();
