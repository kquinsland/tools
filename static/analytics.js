(() => {
    "use strict";

    const STORAGE_KEY = "tools.localAnalytics.v1";
    const FOOTER_ID = "local-analytics-footer";
    const STYLE_ID = "local-analytics-style";

    const nowIso = () => new Date().toISOString();

    const safeJsonParse = (value) => {
        try {
            return JSON.parse(value);
        } catch (error) {
            return null;
        }
    };

    const loadData = () => {
        if (typeof localStorage === "undefined") {
            return { version: 1, tools: {} };
        }
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return { version: 1, tools: {} };
        }
        const parsed = safeJsonParse(raw);
        if (!parsed || typeof parsed !== "object") {
            return { version: 1, tools: {} };
        }
        if (!parsed.tools || typeof parsed.tools !== "object") {
            parsed.tools = {};
        }
        if (!parsed.version) {
            parsed.version = 1;
        }
        return parsed;
    };

    const saveData = (data) => {
        if (typeof localStorage === "undefined") {
            return;
        }
        data.updatedAt = nowIso();
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    };

    const getToolPath = () => {
        const path = window.location.pathname || "";
        return path.split("?")[0].split("#")[0] || "unknown";
    };

    const getToolTitle = () => document.title || "Untitled tool";

    const getFooterCountText = (count) => {
        if (count === 1) {
            return "Viewed 1 time";
        }
        return `Viewed ${count} times`;
    };

    const addFooter = (count, includeCount) => {
        if (!document.body || document.getElementById(FOOTER_ID)) {
            return;
        }

        if (!document.getElementById(STYLE_ID)) {
            const style = document.createElement("style");
            style.id = STYLE_ID;
            style.textContent = `
                #${FOOTER_ID} {
                    margin-top: 2.5rem;
                    padding: 0.85rem 1rem;
                    border-top: 1px solid #d9d9d9;
                    background: #f7f7f7;
                    color: #444;
                    font-size: 0.85rem;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                    align-items: center;
                }
                #${FOOTER_ID} a {
                    color: inherit;
                    text-decoration: underline;
                    font-weight: 600;
                }
                #${FOOTER_ID} span {
                    white-space: nowrap;
                }
            `;
            document.head.appendChild(style);
        }

        const footer = document.createElement("footer");
        footer.id = FOOTER_ID;

        const tracking = document.createElement("span");
        tracking.textContent = "Local usage tracking enabled.";

        const manage = document.createElement("a");
        manage.href = "/analytics.html";
        manage.textContent = "Manage usage data";

        footer.appendChild(tracking);
        if (includeCount) {
            const countSpan = document.createElement("span");
            countSpan.textContent = getFooterCountText(count);
            footer.appendChild(countSpan);
        }
        footer.appendChild(manage);
        document.body.appendChild(footer);
    };

    const init = () => {
        const skipTracking = document.body && document.body.dataset.analyticsSkip === "true";
        const path = getToolPath();
        const title = getToolTitle();

        const data = loadData();
        if (!skipTracking) {
            if (!data.tools[path]) {
                data.tools[path] = {
                    path,
                    title,
                    count: 0,
                    lastAccess: null
                };
            }

            data.tools[path].count += 1;
            data.tools[path].lastAccess = nowIso();
            data.tools[path].title = title;
            saveData(data);
        }

        const count = data.tools[path] ? data.tools[path].count : 0;
        addFooter(count, !skipTracking);
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
