/* =========================================================
   NPTOR THEME MANAGER
   static/js/theme.js
   ========================================================= */

(function () {
    "use strict";

    const STORAGE_KEY = "nptor_theme";
    const COOKIE_KEY = "darkmode";

    function getCurrentTheme() {
        return document.documentElement.getAttribute("data-theme") === "dark"
            ? "dark"
            : "light";
    }

    function applyTheme(theme) {
        const root = document.documentElement;

        if (theme === "dark") {
            root.setAttribute("data-theme", "dark");
        } else {
            root.removeAttribute("data-theme");
        }

        updateThemeIcon(theme);
    }

    function saveTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (error) {
            // localStorage may be unavailable.
        }

        /*
         * Keep the existing cookie because Django's base template
         * currently reads request.COOKIES.darkmode.
         */
        document.cookie =
            `${COOKIE_KEY}=${theme === "dark" ? "1" : "0"}; path=/; SameSite=Lax`;
    }

    function updateThemeIcon(theme) {
        const toggle = document.getElementById("theme-toggle");

        if (!toggle) {
            return;
        }

        const icon = toggle.querySelector("i");

        if (!icon) {
            return;
        }

        icon.classList.remove(
            "fa-moon",
            "fa-sun"
        );

        icon.classList.add(
            theme === "dark"
                ? "fa-sun"
                : "fa-moon"
        );

        toggle.setAttribute(
            "aria-label",
            theme === "dark"
                ? "Switch to light mode"
                : "Switch to dark mode"
        );

        toggle.setAttribute(
            "title",
            theme === "dark"
                ? "Switch to light mode"
                : "Switch to dark mode"
        );
    }

    function loadSavedTheme() {
        let savedTheme = null;

        try {
            savedTheme =
                localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            savedTheme = null;
        }

        /*
         * If localStorage doesn't have a value, preserve the
         * server-rendered cookie state from base.html.
         */
        if (
            savedTheme !== "dark" &&
            savedTheme !== "light"
        ) {
            savedTheme =
                getCurrentTheme();
        }

        applyTheme(savedTheme);
    }

    function toggleTheme() {
        const currentTheme =
            getCurrentTheme();

        const nextTheme =
            currentTheme === "dark"
                ? "light"
                : "dark";

        applyTheme(nextTheme);
        saveTheme(nextTheme);
    }

    function init() {
        loadSavedTheme();

        const toggle =
            document.getElementById("theme-toggle");

        if (!toggle) {
            return;
        }

        toggle.addEventListener(
            "click",
            toggleTheme
        );
    }

    /*
     * Expose a small public API.
     * Useful later if another page needs to change theme.
     */
    window.NPTORTheme = {
        getTheme: getCurrentTheme,
        setTheme: function (theme) {
            if (
                theme !== "dark" &&
                theme !== "light"
            ) {
                return;
            }

            applyTheme(theme);
            saveTheme(theme);
        },
        toggle: toggleTheme
    };

    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }
})();