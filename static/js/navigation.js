/* NPTOR navigation: responsive mobile drawer and collapsible desktop sidebar. */
(function () {
    "use strict";

    const MOBILE_BREAKPOINT = 1023;
    const sidebarSelector = "#site-sidebar";
    const toggleSelector = "#sidebar-toggle";
    let sidebar = null;
    let toggle = null;
    let overlay = null;
    let initialized = false;

    function isMobile() {
        return window.innerWidth <= MOBILE_BREAKPOINT;
    }

    function getOverlay() {
        let element = document.querySelector(".sidebar-overlay");
        if (!element) {
            element = document.createElement("div");
            element.className = "sidebar-overlay";
            element.setAttribute("aria-hidden", "true");
            document.body.appendChild(element);
        }
        return element;
    }

    function updateToggleIcon() {
        if (!toggle) return;
        const icon = toggle.querySelector("i");
        if (!icon) return;
        icon.className = isMobile()
            ? (sidebar.classList.contains("is-active") ? "fa fa-xmark" : "fa fa-bars")
            : (document.body.classList.contains("sidebar-collapsed") ? "fa fa-angles-right" : "fa fa-angles-left");
    }

    function updateToggleState(label, expanded) {
        if (!toggle) return;
        toggle.setAttribute("aria-label", label);
        toggle.setAttribute("title", label);
        toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
        updateToggleIcon();
    }

    function closeMobileSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.remove("is-active");
        overlay.classList.remove("is-active");
        overlay.setAttribute("aria-hidden", "true");
        document.body.classList.remove("sidebar-open");
        if (isMobile()) updateToggleState("Open navigation", false);
    }

    function openMobileSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.add("is-active");
        overlay.classList.add("is-active");
        overlay.setAttribute("aria-hidden", "false");
        document.body.classList.add("sidebar-open");
        updateToggleState("Close navigation", true);
    }

    function setDesktopCollapsed(collapsed, persist) {
        document.body.classList.toggle("sidebar-collapsed", collapsed);
        if (persist) {
            try {
                window.localStorage.setItem("nptor-sidebar-collapsed", collapsed ? "1" : "0");
            } catch (error) {
                /* Storage may be unavailable; the UI still works. */
            }
        }
        updateToggleState(collapsed ? "Expand navigation" : "Collapse navigation", !collapsed);
    }

    function toggleSidebar(event) {
        if (event) event.preventDefault();
        if (!sidebar || !toggle) return;

        if (isMobile()) {
            if (sidebar.classList.contains("is-active")) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
            return;
        }

        setDesktopCollapsed(!document.body.classList.contains("sidebar-collapsed"), true);
    }

    function initSidebar() {
        sidebar = document.querySelector(sidebarSelector);
        toggle = document.querySelector(toggleSelector);
        if (!sidebar || !toggle || initialized) return;
        initialized = true;
        overlay = getOverlay();

        let collapsed = false;
        try {
            collapsed = window.localStorage.getItem("nptor-sidebar-collapsed") === "1";
        } catch (error) {
            collapsed = false;
        }
        if (!isMobile()) {
            setDesktopCollapsed(collapsed, false);
        } else {
            updateToggleState("Open navigation", false);
        }

        toggle.addEventListener("click", toggleSidebar);
        overlay.addEventListener("click", closeMobileSidebar);

        sidebar.addEventListener("click", function (event) {
            const link = event.target.closest("a");
            if (link && !link.classList.contains("is-disabled") && isMobile()) {
                closeMobileSidebar();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                if (isMobile() && sidebar.classList.contains("is-active")) {
                    closeMobileSidebar();
                }
            }
        });

        window.addEventListener("resize", function () {
            if (isMobile()) {
                document.body.classList.remove("sidebar-collapsed");
                closeMobileSidebar();
            } else {
                closeMobileSidebar();
                setDesktopCollapsed(document.body.classList.contains("sidebar-collapsed"), false);
            }
        });
    }

    function initTrackAccordions() {
        document.querySelectorAll(".track-header").forEach(function (header) {
            if (header.dataset.navigationInitialized === "true") return;
            const accordion = header.closest(".track-accordion");
            if (!accordion) return;
            header.dataset.navigationInitialized = "true";
            header.setAttribute("role", "button");
            header.setAttribute("tabindex", "0");
            header.setAttribute("aria-expanded", accordion.classList.contains("is-open") ? "true" : "false");

            function toggleAccordion() {
                accordion.classList.toggle("is-open");
                header.setAttribute("aria-expanded", accordion.classList.contains("is-open") ? "true" : "false");
            }
            header.addEventListener("click", toggleAccordion);
            header.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    toggleAccordion();
                }
            });
        });
    }

    function init() {
        initSidebar();
        initTrackAccordions();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }

    window.NPTORNavigation = {
        init: init,
        openSidebar: openMobileSidebar,
        closeSidebar: closeMobileSidebar,
        toggleSidebar: toggleSidebar,
        initSidebar: initSidebar,
        initTrackAccordions: initTrackAccordions
    };
})();
