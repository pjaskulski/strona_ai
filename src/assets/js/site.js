(() => {
    "use strict";

    const readPreference = (key) => {
        try {
            return window.localStorage.getItem(key);
        } catch {
            return null;
        }
    };

    const writePreference = (key, value) => {
        try {
            window.localStorage.setItem(key, value);
        } catch {
            // The page still works when storage is disabled.
        }
    };

    const acceptCookies = () => {
        writePreference("cookieConsent", "true");
        const cookieBanner = document.getElementById("cookie-banner");
        if (!cookieBanner) {
            return;
        }

        cookieBanner.classList.add("translate-y-full");
        window.setTimeout(() => {
            cookieBanner.hidden = true;
        }, 500);
    };

    const initializeHomePage = () => {
        const cookieBanner = document.getElementById("cookie-banner");
        if (!cookieBanner) {
            return;
        }

        document.getElementById("accept-cookies")?.addEventListener("click", acceptCookies);

        if (!readPreference("cookieConsent")) {
            window.setTimeout(() => {
                cookieBanner.hidden = false;
                window.requestAnimationFrame(() => {
                    cookieBanner.classList.remove("translate-y-full");
                });
            }, 1000);
        }
    };

    const initializeBibliographyTooltips = () => {
        if (!document.body.classList.contains("bibliography-tooltips")) {
            return;
        }

        const references = document.querySelectorAll('article a[href^="#bib_"]');
        if (!references.length) {
            return;
        }

        const tooltip = document.createElement("div");
        tooltip.className = "bibliography-tooltip";
        tooltip.setAttribute("role", "tooltip");
        document.body.appendChild(tooltip);

        const getBibliographyText = (link) => {
            const target = document.querySelector(link.getAttribute("href"));
            const entry = target ? target.closest("li") : null;
            return entry ? entry.textContent.replace(/\s+/g, " ").trim() : "";
        };

        const placeTooltip = (event) => {
            const margin = 16;
            const offset = 14;
            const linkRect = event.currentTarget.getBoundingClientRect();
            const rect = tooltip.getBoundingClientRect();
            const hasPointerPosition = Number.isFinite(event.clientX)
                && Number.isFinite(event.clientY);
            const sourceX = hasPointerPosition
                ? event.clientX
                : linkRect.left + (linkRect.width / 2);
            const sourceY = hasPointerPosition ? event.clientY : linkRect.bottom;
            let left = sourceX + offset;
            let top = sourceY + offset;

            if (left + rect.width > window.innerWidth - margin) {
                left = window.innerWidth - rect.width - margin;
            }
            if (top + rect.height > window.innerHeight - margin) {
                top = sourceY - rect.height - offset;
            }

            tooltip.style.left = `${Math.max(margin, left)}px`;
            tooltip.style.top = `${Math.max(margin, top)}px`;
        };

        const showTooltip = (event) => {
            const text = getBibliographyText(event.currentTarget);
            if (!text) {
                return;
            }

            tooltip.textContent = text;
            tooltip.classList.add("is-visible");
            placeTooltip(event);
        };

        const hideTooltip = () => {
            tooltip.classList.remove("is-visible");
        };

        references.forEach((link) => {
            const text = getBibliographyText(link);
            if (!text) {
                return;
            }

            const label = document.documentElement.lang === "en"
                ? "Bibliography entry"
                : "Pozycja bibliografii";
            link.setAttribute("aria-label", `${label}: ${text}`);
            link.addEventListener("mouseenter", showTooltip);
            link.addEventListener("mousemove", placeTooltip);
            link.addEventListener("mouseleave", hideTooltip);
            link.addEventListener("focus", showTooltip);
            link.addEventListener("blur", hideTooltip);
        });
    };

    document.addEventListener("DOMContentLoaded", () => {
        initializeHomePage();
        initializeBibliographyTooltips();
    });
})();
