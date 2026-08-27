(() => {
    "use strict";

    const toast = document.getElementById("toast");
    let toastTimer = null;

    function showToast(message, isError = true) {
        toast.textContent = message;
        toast.classList.toggle("toast-error", isError);
        toast.hidden = false;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => { toast.hidden = true; }, 5000);
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

    handleFormSubmit(document.getElementById("request-form"), {
        url: "/api/request",
        errorPrefix: "Request fehlgeschlagen",
        buildBody: () => ({
            url: document.getElementById("url").value,
            method: document.getElementById("method").value,
            timeout: document.getElementById("timeout").value,
            headers: document.getElementById("headers").value,
        }),
        onSuccess: (data) => {
            document.getElementById("response-body").value = data.response;
            const headersTable = document.getElementById("headers-table");
            const entries = Object.entries(data.headers || {});
            headersTable.innerHTML = "<tr><th>Key</th><th>Value</th></tr>" +
                entries.map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join("");
            document.getElementById("headers-section").hidden = entries.length === 0;
            document.getElementById("request-result").hidden = false;
        },
    });

    handleFormSubmit(document.getElementById("resolve-form"), {
        url: "/api/resolve",
        errorPrefix: "Auflösen fehlgeschlagen",
        buildBody: () => ({
            hostname: document.getElementById("hostname").value,
        }),
        onSuccess: (data) => {
            document.getElementById("resolve-body").value = data.result;
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
        },
    });

    document.querySelectorAll(".copy-btn").forEach((btn) => {
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
})();
