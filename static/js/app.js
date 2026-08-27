(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const applySystemTheme = () => {
        document.documentElement.dataset.theme = mediaQuery.matches ? "dark" : "light";
    };

    applySystemTheme();
    mediaQuery.addEventListener?.("change", applySystemTheme);
})();
