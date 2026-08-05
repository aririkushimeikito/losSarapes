/* ============================================================
   LOS SARAPES — SITE BEHAVIOUR
   Vanilla JS. No dependencies.
   ============================================================ */
(function () {
  'use strict';

  /* ------------------------------------------------------------
     Hours are not edited here. They live in src/data/hours.json and
     tools/build.py renders every printed time on the site from that
     file, plus the JSON blob this script reads further down.
     ------------------------------------------------------------ */

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

  /* ---------- Open or closed, right now ---------------------- */

  /* Every printed time on the site is generated at build time from
     src/data/hours.json. The same file is emitted here as JSON, and it is
     the only thing this script reads — so the badge can never contradict
     the hours printed next to it. */
  var blob = document.getElementById('hoursData');
  var HOURS = {};
  var TIME_ZONE = 'America/New_York';

  if (blob) {
    try {
      var parsed = JSON.parse(blob.textContent);
      TIME_ZONE = parsed.timeZone || TIME_ZONE;
      Object.keys(parsed.days).forEach(function (day) {
        var block = parsed.days[day];
        HOURS[parseInt(day, 10)] = block ? [block] : null;
      });
    } catch (e) {
      // Malformed data: leave every badge hidden rather than guess.
      HOURS = {};
    }
  }

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

  var targets = document.querySelectorAll('[data-status]');

  if (targets.length && Object.keys(HOURS).length) {
    var now = localNow();
    var today = HOURS[now.day] || [];
    var openBlock = null;

    for (var i = 0; i < today.length; i++) {
      if (now.time >= today[i][0] && now.time < today[i][1]) { openBlock = today[i]; break; }
    }

    var isOpen = Boolean(openBlock);
    var text;

    if (isOpen) {
      text = 'Open now until ' + pretty(openBlock[1]);
    } else {
      var later = null;
      for (var j = 0; j < today.length; j++) {
        if (now.time < today[j][0]) { later = today[j]; break; }
      }
      var next = later ? 'Opens today at ' + pretty(later[0]) : nextOpening(now.day);
      // Lowercase only the leading O, so the AM/PM stays capitalised.
      text = 'Closed — ' + next.charAt(0).toLowerCase() + next.slice(1);
    }

    Array.prototype.forEach.call(targets, function (el) {
      // The hero badge is bare text inside an existing line; everywhere
      // else the badge is a pill that owns its own dot.
      var bare = el.getAttribute('data-status-style') === 'bare';

      el.innerHTML = '';

      if (!bare) {
        var dot = document.createElement('span');
        dot.className = 'status-pill__dot';
        dot.setAttribute('aria-hidden', 'true');
        el.appendChild(dot);
      }

      // One word on screen, everywhere. It fits any column at any width,
      // and it is the part anyone actually scans for.
      var word = document.createElement('span');
      word.className = 'status-pill__word';
      word.setAttribute('aria-hidden', 'true');
      word.textContent = isOpen ? 'Open' : 'Closed';
      el.appendChild(word);

      // The sentence is worth more to someone who cannot see the printed
      // hours beside it, so it is announced instead of the bare word.
      var spoken = document.createElement('span');
      spoken.className = 'sr-only';
      spoken.textContent = text;
      el.appendChild(spoken);

      el.classList.remove('is-open', 'is-closed');
      el.classList.add(isOpen ? 'is-open' : 'is-closed');
      el.hidden = !text;
    });

    // Mark today's row wherever the full table is printed.
    var todayRow = document.querySelector('.hours li[data-day="' + now.day + '"]');
    if (todayRow) todayRow.classList.add('is-today');
  }

  /* ---------- Footer year ------------------------------------ */

  var year = document.getElementById('year');
  if (year) year.textContent = String(new Date().getFullYear());
})();
