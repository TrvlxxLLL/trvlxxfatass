// Кабинет разработчика: вкладки, настройки модели, промпты, тексты.
(function () {
    const { getJSON, postJSON } = window.SuhoApi;
    const statusEl = document.getElementById("dev-status");
    const panels = document.querySelectorAll(".dev__panel");
    const tabs = document.querySelectorAll(".dev__tabs .tab");
    let defaults = {};

    function status(message, isError) {
        statusEl.textContent = message;
        statusEl.classList.toggle("dev__status--error", Boolean(isError));
        statusEl.hidden = !message;
    }

    tabs.forEach((tab) => tab.addEventListener("click", () => {
        tabs.forEach((other) => other.classList.toggle("is-active", other === tab));
        panels.forEach((panel) => panel.classList.toggle(
            "is-active", panel.dataset.panel === tab.dataset.tab
        ));
    }));

    function fields() {
        return document.querySelectorAll("[data-setting]");
    }

    function fill(values) {
        fields().forEach((input) => {
            const key = input.dataset.setting;
            if (!(key in values)) return;
            if (input.type === "checkbox") input.checked = values[key] === "1";
            else input.value = values[key];
        });
        const source = document.getElementById("key-source");
        if (source) source.textContent = values._api_key_source || "—";
        const gigaSource = document.getElementById("giga-key-source");
        if (gigaSource) gigaSource.textContent = values._gigachat_key_source || "—";
    }

    function collect() {
        const body = {};
        fields().forEach((input) => {
            const key = input.dataset.setting;
            if (input.type === "checkbox") body[key] = input.checked ? "1" : "0";
            else body[key] = input.value;
        });
        return body;
    }

    async function load() {
        try {
            const data = await getJSON("/api/dev/settings");
            defaults = data.defaults || {};
            fill(data.settings || {});
        } catch (err) {
            status("Не удалось загрузить настройки: " + err.message, true);
        }
    }

    async function save() {
        status("Сохраняем…");
        try {
            const data = await postJSON("/api/dev/settings", collect());
            fill(data.settings || {});
            document.querySelectorAll(
                '[data-setting="ai_api_key"], [data-setting="gigachat_auth_key"]'
            ).forEach((input) => { input.value = ""; });
            status("Сохранено: " + (data.saved || []).join(", "));
        } catch (err) {
            status("Ошибка сохранения: " + err.message, true);
        }
    }

    document.querySelectorAll("[data-save]").forEach(
        (btn) => btn.addEventListener("click", save)
    );

    document.querySelectorAll("[data-reset]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const key = btn.dataset.reset;
            const input = document.querySelector(`[data-setting="${key}"]`);
            if (input && key in defaults) input.value = defaults[key];
            status("Стандартный текст подставлен, не забудьте сохранить");
        });
    });

    const testBtn = document.getElementById("ai-test");
    if (testBtn) {
        testBtn.addEventListener("click", async () => {
            const out = document.getElementById("ai-test-result");
            testBtn.disabled = true;
            status("Проверяем связь с моделью…");
            try {
                const data = await postJSON("/api/dev/ai/test", {});
                out.hidden = false;
                out.textContent = JSON.stringify(data, null, 2);
                status(data.ok ? "Модель ответила" : "Модель вернула ошибку", !data.ok);
            } catch (err) {
                out.hidden = false;
                out.textContent = err.message;
                status("Проверка не удалась: " + err.message, true);
            } finally {
                testBtn.disabled = false;
            }
        });
    }

    load();
})();
