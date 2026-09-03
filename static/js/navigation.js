/* =========================================================
   NPTOR NAVIGATION MANAGER
   static/js/navigation.js

   Responsibilities:
   - Mobile sidebar
   - Sidebar overlay
   - Escape key handling
   - Track accordion
   - Responsive sidebar cleanup
   - Accessible navigation state

   NOTE:
   - No backend logic here.
   - No URL handling here.
   - No theme handling here.
   - No practice statistics here.
   ========================================================= */

(function () {
    "use strict";

    /* =====================================================
       CONFIGURATION
       ===================================================== */

    const MOBILE_BREAKPOINT = 1023;

    const SELECTORS = {
        sidebar: "#site-sidebar",
        sidebarToggle: "#sidebar-toggle",
        overlay: ".sidebar-overlay",
        trackHeader: ".track-header",
        trackAccordion: ".track-accordion"
    };

    /* =====================================================
       SIDEBAR STATE
       ===================================================== */

    let sidebarInitialized = false;
    let sidebar = null;
    let sidebarToggle = null;
    let overlay = null;

    /* =====================================================
       CREATE OVERLAY
       ===================================================== */

    function getOrCreateOverlay() {
        overlay = document.querySelector(SELECTORS.overlay);

        if (!overlay) {
            overlay = document.createElement("div");
            overlay.className = "sidebar-overlay";
            overlay.setAttribute("aria-hidden", "true");
            document.body.appendChild(overlay);
        }

        return overlay;
    }

    /* =====================================================
       OPEN SIDEBAR
       ===================================================== */

    function openSidebar() {
        if (!sidebar || !sidebarToggle || !overlay) {
            return;
        }

        sidebar.classList.add("is-active");
        overlay.classList.add("is-active");
        overlay.setAttribute("aria-hidden", "false");
        document.body.classList.add("sidebar-open");
        sidebarToggle.setAttribute("aria-expanded", "true");
        sidebarToggle.setAttribute("aria-label", "Close navigation");
    }

    /* =====================================================
       CLOSE SIDEBAR
       ===================================================== */

    function closeSidebar() {
        if (!sidebar || !sidebarToggle || !overlay) {
            return;
        }

        sidebar.classList.remove("is-active");
        overlay.classList.remove("is-active");
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("sidebar-open");
        sidebarToggle.setAttribute("aria-expanded", "false");
        sidebarToggle.setAttribute("aria-label", "Open navigation");
    }

    /* =====================================================
       TOGGLE SIDEBAR
       ===================================================== */

    function toggleSidebar(event) {
        if (event) {
            event.preventDefault();
        }

        if (!sidebar) {
            return;
        }

        if (sidebar.classList.contains("is-active")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    /* =====================================================
       INITIALIZE SIDEBAR
       ===================================================== */

    function initSidebar() {
        sidebar = document.querySelector(SELECTORS.sidebar);
        sidebarToggle = document.querySelector(SELECTORS.sidebarToggle);

        if (!sidebar || !sidebarToggle) {
            return;
        }

        if (sidebarInitialized) {
            return;
        }

        sidebarInitialized = true;
        overlay = getOrCreateOverlay();

        if (!sidebarToggle.hasAttribute("aria-expanded")) {
            sidebarToggle.setAttribute("aria-expanded", "false");
        }

        if (!sidebarToggle.hasAttribute("aria-label")) {
            sidebarToggle.setAttribute("aria-label", "Open navigation");
        }

        sidebarToggle.addEventListener("click", toggleSidebar);

        overlay.addEventListener("click", function () {
            closeSidebar();
        });

        sidebar.addEventListener("click", function (event) {
            const link = event.target.closest("a");

            if (!link) {
                return;
            }

            if (link.classList.contains("is-disabled")) {
                return;
            }

            if (window.innerWidth <= MOBILE_BREAKPOINT) {
                closeSidebar();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }

            if (sidebar.classList.contains("is-active")) {
                closeSidebar();
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > MOBILE_BREAKPOINT) {
                closeSidebar();
            }
        });
    }

    /* =====================================================
       TRACK ACCORDION
       ===================================================== */

    function initTrackAccordions() {
        const headers = document.querySelectorAll(SELECTORS.trackHeader);

        headers.forEach(function (header) {
            if (header.dataset.navigationInitialized === "true") {
                return;
            }

            header.dataset.navigationInitialized = "true";

            const accordion = header.closest(SELECTORS.trackAccordion);

            if (!accordion) {
                return;
            }

            const initiallyExpanded = accordion.classList.contains("is-open");

            header.setAttribute("role", "button");
            header.setAttribute("tabindex", "0");
            header.setAttribute("aria-expanded", initiallyExpanded ? "true" : "false");

            function toggleAccordion() {
                accordion.classList.toggle("is-open");
                const expanded = accordion.classList.contains("is-open");
                header.setAttribute("aria-expanded", expanded ? "true" : "false");
            }

            header.addEventListener("click", function () {
                toggleAccordion();
            });

            header.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    toggleAccordion();
                }
            });
        });
    }

    /* =====================================================
       CLOSE SIDEBAR ON PAGE VISIBILITY CHANGE
       ===================================================== */

    function initVisibilityHandling() {
        document.addEventListener("visibilitychange", function () {
            if (document.hidden) {
                closeSidebar();
            }
        });
    }

    /* =====================================================
       GLOBAL INIT
       ===================================================== */

    function init() {
        initSidebar();
        initTrackAccordions();
        initVisibilityHandling();
    }

    /* =====================================================
       DOM READY
       ===================================================== */

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }

    /* =====================================================
       PUBLIC API
       ===================================================== */

    window.NPTORNavigation = {
        init: init,
        openSidebar: openSidebar,
        closeSidebar: closeSidebar,
        toggleSidebar: toggleSidebar,
        initSidebar: initSidebar,
        initTrackAccordions: initTrackAccordions
    };
})();