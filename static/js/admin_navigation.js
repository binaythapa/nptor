/* =========================================================
   NPTOR ADMIN NAVIGATION
   Accessible mobile sidebar with keyboard and focus support.
   ========================================================= */

(function () {
    "use strict";

    const BREAKPOINT = 650;
    const sidebar = document.getElementById("admin-sidebar");
    const toggle = document.getElementById("admin-sidebar-toggle");

    if (!sidebar || !toggle) {
        return;
    }

    let overlay = document.querySelector(".admin-sidebar-overlay");
    let lastFocused = null;

    if (!overlay) {
        overlay = document.createElement("button");
        overlay.type = "button";
        overlay.className = "admin-sidebar-overlay";
        overlay.setAttribute("aria-label", "Close navigation");
        overlay.setAttribute("tabindex", "-1");
        document.body.appendChild(overlay);
    }

    function isMobile() {
        return window.innerWidth <= BREAKPOINT;
    }

    function setOpen(open) {
        if (!isMobile() && open) {
            return;
        }

        sidebar.classList.toggle("is-active", open);
        overlay.classList.toggle("is-active", open);
        document.body.classList.toggle("admin-sidebar-open", open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");

        if (open) {
            lastFocused = document.activeElement;
            const firstLink = sidebar.querySelector("a, button");
            if (firstLink) {
                firstLink.focus();
            }
        } else if (lastFocused && typeof lastFocused.focus === "function") {
            lastFocused.focus();
            lastFocused = null;
        }
    }

    function toggleSidebar(event) {
        if (event) {
            event.preventDefault();
        }
        setOpen(!sidebar.classList.contains("is-active"));
    }

    toggle.addEventListener("click", toggleSidebar);
    overlay.addEventListener("click", function () {
        setOpen(false);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && sidebar.classList.contains("is-active")) {
            setOpen(false);
        }
    });

    sidebar.addEventListener("click", function (event) {
        if (event.target.closest("a") && isMobile()) {
            setOpen(false);
        }
    });

    window.addEventListener("resize", function () {
        if (!isMobile()) {
            setOpen(false);
        }
    });

    window.NPTORAdminNavigation = {
        open: function () { setOpen(true); },
        close: function () { setOpen(false); },
        toggle: toggleSidebar,
    };
})();
