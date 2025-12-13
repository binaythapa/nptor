// static/js/ui.js - improved (FINAL)
(function () {
  "use strict";

  // small helpers
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const on = (el, ev, fn) => { if (el) el.addEventListener(ev, fn); };

  function debounce(fn, wait = 120) {
    let t = null;
    return function () {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, arguments), wait);
    };
  }

  // ===============================
  // SIDEBAR INITIAL STATE
  // ===============================
  function initSidebarState() {
    const sb = document.getElementById('site-sidebar');
    if (!sb) return;
    if (window.innerWidth <= 980) {
      sb.classList.remove('open');
      sb.style.display = 'none';
      sb.setAttribute('aria-hidden', 'true');
    } else {
      sb.classList.remove('open');
      sb.style.display = '';
      sb.setAttribute('aria-hidden', 'false');
    }
  }

  document.addEventListener('DOMContentLoaded', function () {

    // ---------- SIDEBAR ----------
    const sidebar = document.getElementById('site-sidebar');
    const sbToggle = document.getElementById('sidebar-toggle');

    initSidebarState();
    window.addEventListener('resize', debounce(initSidebarState, 120));

    if (sbToggle && sidebar) {
      sbToggle.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = sidebar.classList.toggle('open');
        if (isOpen) {
          sidebar.style.display = 'block';
          sidebar.setAttribute('aria-hidden', 'false');
          sbToggle.setAttribute('aria-expanded', 'true');
        } else {
          sidebar.style.display = 'none';
          sidebar.setAttribute('aria-hidden', 'true');
          sbToggle.setAttribute('aria-expanded', 'false');
        }
      });

      document.addEventListener('click', function (ev) {
        if (window.innerWidth <= 980 && sidebar.style.display === 'block') {
          if (!sidebar.contains(ev.target) && !sbToggle.contains(ev.target)) {
            sidebar.style.display = 'none';
            sidebar.classList.remove('open');
            sidebar.setAttribute('aria-hidden', 'true');
            sbToggle.setAttribute('aria-expanded', 'false');
          }
        }
      });
    }

    // ===============================
    // THEME (NIGHT / DARK MODE)
    // ===============================
    const themeToggle = document.getElementById('theme-toggle');
    const root = document.documentElement;

    function applyTheme(isDark) {
      const icon = themeToggle ? themeToggle.querySelector('i') : null;

      if (isDark) {
        root.setAttribute('data-theme', 'dark');
        document.cookie = "darkmode=1; path=/";
        themeToggle?.setAttribute('aria-pressed', 'true');
        if (icon) icon.className = 'fa fa-sun';
      } else {
        root.removeAttribute('data-theme');
        document.cookie = "darkmode=0; path=/";
        themeToggle?.setAttribute('aria-pressed', 'false');
        if (icon) icon.className = 'fa fa-moon';
      }
    }

    if (themeToggle) {
      applyTheme(root.getAttribute('data-theme') === 'dark');
      on(themeToggle, 'click', () => {
        applyTheme(root.getAttribute('data-theme') !== 'dark');
      });
    }

    // ===============================
    // ACTIVE MENU HIGHLIGHT
    // ===============================
    const currentPath = window.location.pathname;
    $$('.menu-list a').forEach(link => {
      const href = link.getAttribute('href');
      if (href && currentPath.startsWith(href)) {
        link.classList.add('is-active');
        link.setAttribute('aria-current', 'page');
      }
    });

    // ===============================
    // PRACTICE PROGRESS (SESSION)
    // ===============================
    const practiceCounter = document.getElementById('practice-count');
    if (practiceCounter) {
      const count = parseInt(sessionStorage.getItem('practice_count') || '0', 10);
      practiceCounter.textContent = `Practiced: ${count} questions`;
    }

    // Helper to increment practice count (call from practice page)
    window.incrementPracticeCount = function () {
      const current = parseInt(sessionStorage.getItem('practice_count') || '0', 10) + 1;
      sessionStorage.setItem('practice_count', current);
      if (practiceCounter) {
        practiceCounter.textContent = `Practiced: ${current} questions`;
      }
    };

    // ---------- USER DROPDOWN ----------
    $$('.user-dropdown').forEach(function (container) {
      const toggle = $('.user-toggle', container);
      const menu = $('.user-menu', container);
      if (!toggle || !menu) return;

      toggle.setAttribute('role', 'button');
      toggle.setAttribute('tabindex', '0');

      function openMenu() {
        $$('.user-menu').forEach(m => {
          if (m !== menu) {
            m.style.display = 'none';
            m.setAttribute('aria-hidden', 'true');
          }
        });
        menu.style.display = 'block';
        menu.setAttribute('aria-hidden', 'false');
        toggle.setAttribute('aria-expanded', 'true');
      }

      function closeMenu() {
        menu.style.display = 'none';
        menu.setAttribute('aria-hidden', 'true');
        toggle.setAttribute('aria-expanded', 'false');
      }

      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        if (menu.style.display === 'block') closeMenu();
        else openMenu();
      });

      toggle.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          toggle.click();
        }
      });

      menu.addEventListener('click', ev => ev.stopPropagation());
    });

    // ---------- GLOBAL CLOSE ----------
    document.addEventListener('click', function () {
      $$('.user-menu').forEach(m => {
        m.style.display = 'none';
        m.setAttribute('aria-hidden', 'true');
      });

      if (window.innerWidth <= 980 && sidebar && sidebar.style.display === 'block') {
        sidebar.style.display = 'none';
        sidebar.classList.remove('open');
        sidebar.setAttribute('aria-hidden', 'true');
        if (sbToggle) sbToggle.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') {
        $$('.user-menu').forEach(m => {
          m.style.display = 'none';
          m.setAttribute('aria-hidden', 'true');
        });

        if (window.innerWidth <= 980 && sidebar && sidebar.style.display === 'block') {
          sidebar.style.display = 'none';
          sidebar.classList.remove('open');
          sidebar.setAttribute('aria-hidden', 'true');
          if (sbToggle) sbToggle.setAttribute('aria-expanded', 'false');
        }
      }
    });

  }); // DOMContentLoaded

})();
