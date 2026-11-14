// Кабинет разработчика: очередь ручной модерации фото и комментариев.
(function () {
    const { esc, getJSON, postJSON } = window.SuhoApi;
    const list = document.getElementById("queue-list");
    const countsEl = document.getElementById("queue-counts");
    const filters = document.querySelectorAll("[data-scope]");
    let scope = "pending";

    const LABELS = {
        none: "нет", pending: "на проверке", approved: "одобрено", rejected: "скрыто",
        published: "опубликовано",
    };

    function fmtVotes(value) {
        // В очереди должны отображаться и отрицательные значения (если они есть).
        const n = Number(value);
        if (!Number.isFinite(n)) return "0";
        return String(n);
    }

    function badge(label, value) {
        return `<span class="badge badge--${esc(value)}">` +
               `${esc(label)}: ${esc(LABELS[value] || value)}</span>`;
    }

    function button(id, target, action, label) {
        return `<button type="button" class="mod-btn" data-point="${id}" ` +
               `data-target="${target}" data-action="${action}">${esc(label)}</button>`;
    }

    function card(point) {
        const photo = point.photo_url
            ? `<img class="queue__photo" src="${esc(point.photo_url)}" alt="Фото метки">`
            : '<div class="queue__photo queue__photo--empty">без фото</div>';
        const ai = [];
        if (point.ai_photo_reason) ai.push("Фото/ИИ: " + point.ai_photo_reason);
        if (point.ai_comment_reason) ai.push("Коммент/ИИ: " + point.ai_comment_reason);

        let actions = "";
        if (point.photo_url) {
            actions += button(point.id, "photo", "approve", "Фото ок");
            actions += button(point.id, "photo", "reject", "Скрыть фото");
        }
        if (point.comment) {
            actions += button(point.id, "comment", "approve", "Коммент ок");
            actions += button(point.id, "comment", "reject", "Скрыть коммент");
        }
        actions += button(point.id, "point", "approve", "Опубликовать");
        actions += button(point.id, "point", "reject", "Отклонить метку");

        return `<article class="queue__item">${photo}
            <div class="queue__body">
                <div class="queue__head">#${point.id} · ${esc(point.created_at)} ·
                    ${esc(point.lat.toFixed(5))}, ${esc(point.lng.toFixed(5))} ·
                    подтверждений: ${esc(fmtVotes(point.confirmations))} ·
                    опровержений: ${esc(fmtVotes(point.denials))}
                </div>
                <div class="queue__comment">${esc(point.comment || "без комментария")}</div>
                <div class="queue__badges">
                    ${badge("метка", point.moderation_status)}
                    ${badge("фото", point.photo_status)}
                    ${badge("коммент", point.comment_status)}
                </div>
                ${ai.length ? `<div class="queue__ai">${esc(ai.join(" · "))}</div>` : ""}
                <div class="queue__actions">${actions}</div>
            </div></article>`;
    }

    async function load() {
        list.innerHTML = "<p>Загрузка…</p>";
        try {
            const data = await getJSON("/api/dev/points?scope=" + encodeURIComponent(scope));
            const items = data.items || [];
            list.innerHTML = items.length
                ? items.map(card).join("")
                : "<p>Здесь пусто.</p>";
            const counts = data.counts || {};
            countsEl.textContent =
                `на проверке: ${counts.pending || 0} · опубликовано: ` +
                `${counts.published || 0} · отклонено: ${counts.rejected || 0}`;
        } catch (err) {
            list.innerHTML = `<p class="form-error">Ошибка: ${esc(err.message)}</p>`;
        }
    }

    filters.forEach((btn) => btn.addEventListener("click", () => {
        scope = btn.dataset.scope;
        filters.forEach((other) => other.classList.toggle("is-active", other === btn));
        load();
    }));

    const refresh = document.getElementById("queue-refresh");
    if (refresh) refresh.addEventListener("click", load);

    list.addEventListener("click", async (event) => {
        const btn = event.target.closest(".mod-btn");
        if (!btn) return;
        btn.disabled = true;
        try {
            await postJSON(`/api/dev/points/${btn.dataset.point}/moderate`, {
                target: btn.dataset.target,
                action: btn.dataset.action,
            });
            await load();
        } catch (err) {
            alert("Не удалось применить решение: " + (err.message || "ошибка"));
            btn.disabled = false;
        }
    });

    load();
})();
