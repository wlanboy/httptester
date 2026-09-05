(() => {
    "use strict";

    const toast = document.getElementById("toast");
    let toastTimer = null;

    function showToast(message, isError = true) {
        toast.textContent = message;
        toast.classList.toggle("toast-error", isError);
        toast.classList.toggle("toast-success", !isError);
        toast.hidden = false;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => { toast.hidden = true; }, 5000);
    }

    // --- localStorage history (URL/Hostname) ---

    const HISTORY_LIMIT = 20;

    function loadHistory(key) {
        try {
            const raw = localStorage.getItem(key);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }

    function saveToHistory(key, value) {
        if (!value) return;
        const list = loadHistory(key).filter((v) => v !== value);
        list.unshift(value);
        try {
            localStorage.setItem(key, JSON.stringify(list.slice(0, HISTORY_LIMIT)));
        } catch { /* Storage voll oder deaktiviert */ }
    }

    function renderDatalist(id, values) {
        const datalist = document.getElementById(id);
        if (!datalist) return;
        datalist.innerHTML = values.map((v) => `<option value="${escapeHtml(v)}"></option>`).join("");
    }

    function wireHistory(inputId, datalistId, storageKey) {
        renderDatalist(datalistId, loadHistory(storageKey));
        const form = document.getElementById(inputId).closest("form");
        form.addEventListener("submit", () => {
            saveToHistory(storageKey, document.getElementById(inputId).value.trim());
            renderDatalist(datalistId, loadHistory(storageKey));
        });
    }

    // --- localStorage persistence (Chain-Formular) ---

    const CHAIN_STORAGE_KEY = "httptester:chain-form";
    const CHAIN_FIELD_IDS = ["chain_urls", "chain_message", "chain_timeout"];

    function restoreChainForm() {
        try {
            const raw = localStorage.getItem(CHAIN_STORAGE_KEY);
            if (!raw) return;
            const saved = JSON.parse(raw);
            CHAIN_FIELD_IDS.forEach((id) => {
                if (saved[id]) document.getElementById(id).value = saved[id];
            });
        } catch { /* ignorieren */ }
    }

    function persistChainForm() {
        const data = {};
        CHAIN_FIELD_IDS.forEach((id) => { data[id] = document.getElementById(id).value; });
        try {
            localStorage.setItem(CHAIN_STORAGE_KEY, JSON.stringify(data));
        } catch { /* Storage voll oder deaktiviert */ }
    }

    function setLoading(form, loading) {
        const button = form.querySelector("button[type=submit]");
        button.disabled = loading;
        button.querySelector(".btn-label").hidden = loading;
        button.querySelector(".spinner").hidden = !loading;
    }

    async function postJson(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            let detail = res.statusText;
            try {
                const err = await res.json();
                detail = err.detail ? JSON.stringify(err.detail) : detail;
            } catch { /* ignore body parse errors */ }
            throw new Error(`${res.status} ${detail}`);
        }
        return res.json();
    }

    function badge(statusCode) {
        if (statusCode === null || statusCode === undefined) {
            return '<span class="badge badge-muted">-</span>';
        }
        let cls = "badge-err";
        if (statusCode < 300) cls = "badge-ok";
        else if (statusCode < 400) cls = "badge-warn";
        return `<span class="badge ${cls}">${statusCode}</span>`;
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function handleFormSubmit(form, { buildBody, url, onSuccess, errorPrefix }) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            setLoading(form, true);
            try {
                const data = await postJson(url, buildBody());
                onSuccess(data);
            } catch (err) {
                showToast(`${errorPrefix}: ${err.message}`);
            } finally {
                setLoading(form, false);
            }
        });
    }

    let lastRequestParams = null;

    function renderRequestResult(data) {
        document.getElementById("repeat-result").hidden = true;
        document.getElementById("response-body").value = data.response;

        const redirects = data.redirects || [];
        const redirectsTable = document.getElementById("redirects-table");
        redirectsTable.innerHTML = "<tr><th>#</th><th>Status</th><th>Von</th><th>Nach</th></tr>" +
            redirects.map((r, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${badge(r.status_code)}</td>
                    <td>${escapeHtml(r.from_url)}</td>
                    <td>${escapeHtml(r.location)}</td>
                </tr>`).join("");
        document.getElementById("redirects-section").hidden = redirects.length === 0;

        const headersTable = document.getElementById("headers-table");
        const entries = Object.entries(data.headers || {});
        headersTable.innerHTML = "<tr><th>Key</th><th>Value</th></tr>" +
            entries.map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join("");
        document.getElementById("headers-section").hidden = entries.length === 0;
        const headersFilter = document.getElementById("headers-filter");
        headersFilter.value = "";
        headersFilter.dispatchEvent(new Event("input"));

        document.getElementById("request-result").hidden = false;
    }

    function renderRepeatResult(data) {
        document.getElementById("request-result").hidden = true;

        const s = data.stats;
        document.getElementById("repeat-summary").innerHTML =
            `${s.success_count}/${s.count} erfolgreich &middot; min ${s.min_ms ?? "-"} ms ` +
            `&middot; avg ${s.avg_ms ?? "-"} ms &middot; max ${s.max_ms ?? "-"} ms`;

        const table = document.getElementById("repeat-table");
        const rows = data.attempts.map((a) => `
            <tr>
                <td>${a.attempt}</td>
                <td>${badge(a.status_code)}</td>
                <td>${a.duration_ms ?? "-"}</td>
                <td>${a.error ? escapeHtml(a.error) : "-"}</td>
            </tr>`).join("");
        table.innerHTML = "<tr><th>#</th><th>Status</th><th>Dauer (ms)</th><th>Fehler</th></tr>" + rows;
        document.getElementById("repeat-result").hidden = false;

        showToast(`Wiederholungen abgeschlossen: ${s.success_count}/${s.count} erfolgreich`, s.success_count < s.count);
    }

    document.getElementById("request-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const repeatCount = parseInt(document.getElementById("repeat_count").value, 10) || 1;
        lastRequestParams = {
            url: document.getElementById("url").value,
            method: document.getElementById("method").value,
            timeout: document.getElementById("timeout").value,
            headers: document.getElementById("headers").value,
        };
        setLoading(form, true);
        try {
            if (repeatCount > 1) {
                const data = await postJson("/api/repeat", { ...lastRequestParams, count: repeatCount });
                renderRepeatResult(data);
            } else {
                const data = await postJson("/api/request", lastRequestParams);
                renderRequestResult(data);
            }
        } catch (err) {
            showToast(`Request fehlgeschlagen: ${err.message}`);
        } finally {
            setLoading(form, false);
        }
    });

    handleFormSubmit(document.getElementById("resolve-form"), {
        url: "/api/resolve",
        errorPrefix: "Auflösen fehlgeschlagen",
        buildBody: () => ({
            hostname: document.getElementById("hostname").value,
        }),
        onSuccess: (data) => {
            document.getElementById("resolve-body").value = data.result;

            const addresses = data.addresses || [];
            document.getElementById("resolve-addresses-list").innerHTML =
                addresses.map((ip) => `<li>${escapeHtml(ip)}</li>`).join("");
            document.getElementById("resolve-addresses-count").textContent = String(addresses.length);
            document.getElementById("resolve-addresses-section").hidden = addresses.length === 0;

            document.getElementById("resolve-result").hidden = false;
        },
    });

    handleFormSubmit(document.getElementById("chain-form"), {
        url: "/chain",
        errorPrefix: "Chain fehlgeschlagen",
        buildBody: () => {
            const chain = document.getElementById("chain_urls").value
                .split("\n")
                .map((line) => line.trim())
                .filter(Boolean);
            const message = document.getElementById("chain_message").value;
            const timeout = parseFloat(document.getElementById("chain_timeout").value) || 5;
            return { message: message || null, chain, timeout };
        },
        onSuccess: (data) => {
            document.getElementById("chain-status").innerHTML =
                `Status: ${badge(data.final_status)}` +
                (data.message ? ` &middot; Message: ${escapeHtml(data.message)}` : "");

            const table = document.getElementById("chain-table");
            const rows = data.path.map((hop, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${escapeHtml(hop.target)}</td>
                    <td>${badge(hop.status_code)}</td>
                    <td>${hop.duration_ms ?? "-"}</td>
                    <td>${hop.error ? escapeHtml(hop.error) : "-"}</td>
                </tr>`).join("");
            table.innerHTML = "<tr><th>#</th><th>Ziel</th><th>Status</th><th>Dauer (ms)</th><th>Fehler</th></tr>" + rows;
            document.getElementById("chain-result").hidden = false;

            const ok = data.final_status < 400;
            showToast(`Kette ${ok ? "erfolgreich" : "mit Fehler"} beendet (Status ${data.final_status})`, !ok);
        },
    });

    document.querySelectorAll(".copy-btn[data-copy-target]").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const target = document.getElementById(btn.dataset.copyTarget);
            try {
                await navigator.clipboard.writeText(target.value);
                const original = btn.textContent;
                btn.textContent = "Kopiert!";
                setTimeout(() => { btn.textContent = original; }, 1500);
            } catch {
                showToast("Kopieren nicht möglich (Clipboard-Zugriff verweigert)");
            }
        });
    });

    // --- Als curl kopieren ---

    function buildCurlCommand(params) {
        if (!params || !params.url) return "";
        const parts = ["curl", "-i", "-X", params.method || "GET"];
        (params.headers || "")
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean)
            .forEach((line) => parts.push("-H", `"${line.replace(/"/g, '\\"')}"`));
        if (params.timeout) parts.push("--max-time", String(params.timeout));
        parts.push(`"${params.url}"`);
        return parts.join(" ");
    }

    document.getElementById("curl-copy-btn").addEventListener("click", async () => {
        const cmd = buildCurlCommand(lastRequestParams);
        if (!cmd) {
            showToast("Zuerst einen Request senden");
            return;
        }
        try {
            await navigator.clipboard.writeText(cmd);
            showToast("curl-Befehl kopiert", false);
        } catch {
            showToast("Kopieren nicht möglich (Clipboard-Zugriff verweigert)");
        }
    });

    // --- Header-Tabelle filtern ---

    document.getElementById("headers-filter").addEventListener("input", (event) => {
        const query = event.target.value.toLowerCase();
        const rows = document.querySelectorAll("#headers-table tr");
        rows.forEach((row, index) => {
            if (index === 0) return;
            row.hidden = query.length > 0 && !row.textContent.toLowerCase().includes(query);
        });
    });

    // --- Init: History & Persistenz ---

    wireHistory("url", "url-history", "httptester:url-history");
    wireHistory("hostname", "hostname-history", "httptester:hostname-history");

    restoreChainForm();
    CHAIN_FIELD_IDS.forEach((id) => {
        document.getElementById(id).addEventListener("input", persistChainForm);
    });
})();
