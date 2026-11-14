// Общие помощники для запросов к API и экранирования HTML.
(function () {
    async function parse(response) {
        let data = {};
        try {
            data = await response.json();
        } catch (err) {
            data = {};
        }
        if (!response.ok) {
            const error = new Error(data.error || "Ошибка запроса");
            error.status = response.status;
            error.data = data;
            throw error;
        }
        return data;
    }

    async function getJSON(url) {
        return parse(await fetch(url, { headers: { Accept: "application/json" } }));
    }

    async function postJSON(url, body) {
        return parse(await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify(body || {}),
        }));
    }

    async function postForm(url, formData) {
        return parse(await fetch(url, { method: "POST", body: formData }));
    }

    function esc(value) {
        return String(value === null || value === undefined ? "" : value)
            .replace(/[&<>"']/g, (c) => ({
                "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
            }[c]));
    }

    window.SuhoApi = { getJSON, postJSON, postForm, esc };
})();
