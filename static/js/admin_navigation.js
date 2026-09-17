/* =========================================================
   NPTOR ADMIN NAVIGATION
   Responsive sidebar with desktop collapse and mobile overlay.
   ========================================================= */

(function () {
    "use strict";

    const BREAKPOINT = 650;
    const STORAGE_KEY = "nptor-admin-sidebar-collapsed";
    const sidebar = document.getElementById("admin-sidebar");
    const layout = document.querySelector(".admin-layout");
    const toggle = document.getElementById("admin-sidebar-toggle");

    if (!sidebar || !layout || !toggle) {
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

    function updateToggleIcon(label) {
        let icon = "☰";

        if (label === "Collapse navigation") {
            icon = "«";
        } else if (label === "Expand navigation") {
            icon = "»";
        }

        toggle.innerHTML = '<span aria-hidden="true" style="font-size:1.45rem;line-height:1;">' + icon + '</span>';
    }

    function updateToggleState(expanded, label) {
        toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
        toggle.setAttribute("aria-label", label);
        toggle.setAttribute("title", label);
        updateToggleIcon(label);
    }

    function setDesktopCollapsed(collapsed, persist) {
        layout.classList.toggle("collapsed", collapsed);

        if (persist) {
            try {
                window.localStorage.setItem(STORAGE_KEY, collapsed ? "true" : "false");
            } catch (error) {
                // Ignore storage restrictions; the sidebar remains functional.
            }
        }

        updateToggleState(!collapsed, collapsed ? "Expand navigation" : "Collapse navigation");
    }

    function restoreDesktopState() {
        let collapsed = false;

        try {
            collapsed = window.localStorage.getItem(STORAGE_KEY) === "true";
        } catch (error) {
            // Use the expanded default when storage is unavailable.
        }

        setDesktopCollapsed(collapsed, false);
    }

    function setMobileOpen(open) {
        sidebar.classList.toggle("is-active", open);
        overlay.classList.toggle("is-active", open);
        document.body.classList.toggle("admin-sidebar-open", open);
        updateToggleState(open, open ? "Close navigation" : "Open navigation");

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

        if (isMobile()) {
            setMobileOpen(!sidebar.classList.contains("is-active"));
            return;
        }

        setDesktopCollapsed(!layout.classList.contains("collapsed"), true);
    }

    restoreDesktopState();
    toggle.addEventListener("click", toggleSidebar);

    overlay.addEventListener("click", function () {
        setMobileOpen(false);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && sidebar.classList.contains("is-active")) {
            setMobileOpen(false);
        }
    });

    sidebar.addEventListener("click", function (event) {
        if (event.target.closest("a") && isMobile()) {
            setMobileOpen(false);
        }
    });

    window.addEventListener("resize", function () {
        if (isMobile()) {
            layout.classList.remove("collapsed");
            updateToggleState(false, "Open navigation");
        } else {
            setMobileOpen(false);
            restoreDesktopState();
        }
    });

    window.NPTORAdminNavigation = {
        open: function () {
            if (isMobile()) {
                setMobileOpen(true);
            } else {
                setDesktopCollapsed(false, true);
            }
        },
        close: function () {
            if (isMobile()) {
                setMobileOpen(false);
            } else {
                setDesktopCollapsed(true, true);
            }
        },
        toggle: toggleSidebar,
    };
})();
