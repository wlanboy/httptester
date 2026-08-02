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

    const requestForm = document.getElementById("request-form");
    requestForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setLoading(requestForm, true);
        try {
            const data = await postJson("/api/request", {
                url: document.getElementById("url").value,
                method: document.getElementById("method").value,
                timeout: document.getElementById("timeout").value,
                headers: document.getElementById("headers").value,
            });
            document.getElementById("response-body").value = data.response;
            const headersTable = document.getElementById("headers-table");
            const entries = Object.entries(data.headers || {});
            headersTable.innerHTML = "<tr><th>Key</th><th>Value</th></tr>" +
                entries.map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join("");
            document.getElementById("headers-section").hidden = entries.length === 0;
            document.getElementById("request-result").hidden = false;
        } catch (err) {
            showToast(`Request fehlgeschlagen: ${err.message}`);
        } finally {
            setLoading(requestForm, false);
        }
    });

    const resolveForm = document.getElementById("resolve-form");
    resolveForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setLoading(resolveForm, true);
        try {
            const data = await postJson("/api/resolve", {
                hostname: document.getElementById("hostname").value,
            });
            document.getElementById("resolve-body").value = data.result;
            document.getElementById("resolve-result").hidden = false;
        } catch (err) {
            showToast(`Auflösen fehlgeschlagen: ${err.message}`);
        } finally {
            setLoading(resolveForm, false);
        }
    });

    const chainForm = document.getElementById("chain-form");
    chainForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setLoading(chainForm, true);
        try {
            const chain = document.getElementById("chain_urls").value
                .split("\n")
                .map((line) => line.trim())
                .filter(Boolean);
            const message = document.getElementById("chain_message").value;
            const timeout = parseFloat(document.getElementById("chain_timeout").value) || 5;
            const data = await postJson("/chain", { message: message || null, chain, timeout });

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
        } catch (err) {
            showToast(`Chain fehlgeschlagen: ${err.message}`);
        } finally {
            setLoading(chainForm, false);
        }
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
