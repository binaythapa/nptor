// static/js/ui.js - improved
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

  // set initial sidebar visibility based on width
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

      // close sidebar when clicking outside (mobile)
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

    // ---------- THEME TOGGLE ----------
    const themeToggle = document.getElementById('theme-toggle');
    on(themeToggle, 'click', () => {
      const html = document.documentElement;
      const nowDark = html.getAttribute('data-theme') === 'dark';
      if (nowDark) {
        html.removeAttribute('data-theme');
        document.cookie = "darkmode=0; path=/";
        themeToggle.setAttribute('aria-pressed', 'false');
      } else {
        html.setAttribute('data-theme', 'dark');
        document.cookie = "darkmode=1; path=/";
        themeToggle.setAttribute('aria-pressed', 'true');
      }
    });

    // ---------- USER DROPDOWN ----------
    // allow click toggle and close others when opening
    $$('.user-dropdown').forEach(function (container) {
      const toggle = $('.user-toggle', container);
      const menu = $('.user-menu', container);
      if (!toggle || !menu) return;

      toggle.setAttribute('role', 'button');
      toggle.setAttribute('tabindex', '0');

      function openMenu() {
        // close other menus
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

      // keyboard (Enter / Space to toggle)
      toggle.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          toggle.click();
        }
      });

      // don't close when clicking inside the menu
      menu.addEventListener('click', ev => ev.stopPropagation());
    });

    // ---------- NOTIFICATIONS PANEL ----------
    const notifBtn = document.getElementById('notif-btn');
    const notifPanel = document.getElementById('notif-panel');
    if (notifBtn && notifPanel) {
      notifBtn.setAttribute('aria-expanded', 'false');
      notifPanel.setAttribute('aria-hidden', 'true');

      notifBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        const open = notifPanel.style.display === 'block';
        // close any user menus first
        $$('.user-menu').forEach(m => { m.style.display = 'none'; m.setAttribute('aria-hidden', 'true'); });
        if (open) {
          notifPanel.style.display = 'none';
          notifPanel.setAttribute('aria-hidden', 'true');
          notifBtn.setAttribute('aria-expanded', 'false');
        } else {
          notifPanel.style.display = 'block';
          notifPanel.setAttribute('aria-hidden', 'false');
          notifBtn.setAttribute('aria-expanded', 'true');
        }
      });

      notifPanel.addEventListener('click', ev => ev.stopPropagation());
    }

    // ---------- GLOBAL CLICK/CLOSE HANDLING ----------
    // Close dropdowns / panels on outside click
    document.addEventListener('click', function () {
      // close user menus
      $$('.user-menu').forEach(m => { m.style.display = 'none'; m.setAttribute('aria-hidden', 'true'); });
      // close notif
      if (notifPanel) { notifPanel.style.display = 'none'; notifPanel.setAttribute('aria-hidden', 'true'); if (notifBtn) notifBtn.setAttribute('aria-expanded', 'false'); }
      // optionally collapse mobile sidebar
      // (we keep it collapsed only when clicking outside on mobile)
      if (window.innerWidth <= 980 && sidebar && sidebar.style.display === 'block') {
        sidebar.style.display = 'none';
        sidebar.classList.remove('open');
        sidebar.setAttribute('aria-hidden', 'true');
        if (sbToggle) sbToggle.setAttribute('aria-expanded', 'false');
      }
    });

    // ESC key closes everything
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' || ev.key === 'Esc') {
        // close user menus
        $$('.user-menu').forEach(m => { m.style.display = 'none'; m.setAttribute('aria-hidden', 'true'); });
        // close notif
        if (notifPanel) { notifPanel.style.display = 'none'; notifPanel.setAttribute('aria-hidden', 'true'); if (notifBtn) notifBtn.setAttribute('aria-expanded', 'false'); }
        // close sidebar on mobile
        if (window.innerWidth <= 980 && sidebar && sidebar.style.display === 'block') {
          sidebar.style.display = 'none';
          sidebar.classList.remove('open');
          sidebar.setAttribute('aria-hidden', 'true');
          if (sbToggle) sbToggle.setAttribute('aria-expanded', 'false');
        }
      }
    });

    // Keep things keyboard-focusable for accessibility: close menus on blur for user-toggle
    $$('.user-toggle').forEach(function (t) {
      t.addEventListener('blur', function () {
        // small timeout to allow click on menu
        setTimeout(function () {
          const menu = t && t.parentElement ? $('.user-menu', t.parentElement) : null;
          if (menu) {
            menu.style.display = 'none';
            menu.setAttribute('aria-hidden', 'true');
            t.setAttribute('aria-expanded', 'false');
          }
        }, 200);
      });
    });

  }); // DOMContentLoaded

})();


