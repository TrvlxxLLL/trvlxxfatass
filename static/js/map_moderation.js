// Ручная модерация прямо из попапов карты (только для разработчика).
(function () {
    const { esc, postJSON } = window.SuhoApi;
    const map = window.SuhoMap;
    const toggle = document.getElementById("dev-moderation");
    const countsEl = document.getElementById("dev-counts");

    const LABELS = {
        none: "нет", pending: "на проверке", approved: "одобрено",
        rejected: "скрыто", published: "опубликована",
    };

    function badge(label, value) {
        const text = LABELS[value] || value || "—";
        return `<span class="badge badge--${esc(value)}">${esc(label)}: ${esc(text)}</span>`;
    }

    function button(point, target, action, label) {
        return `<button type="button" class="mod-btn" data-point="${point.id}" ` +
               `data-target="${target}" data-action="${action}">${esc(label)}</button>`;
    }

    map.hooks.popupExtra = function (point) {
        if (!point.moderation_status) return "";
        const ai = [];
        if (point.ai_photo_reason) ai.push("Фото/ИИ: " + point.ai_photo_reason);
        if (point.ai_comment_reason) ai.push("Коммент/ИИ: " + point.ai_comment_reason);

        let html = '<div class="mod">';
        html += badge("метка", point.moderation_status) +
                badge("фото", point.photo_status) +
                badge("коммент", point.comment_status);
        if (ai.length) html += `<div class="mod__ai">${esc(ai.join(" · "))}</div>`;
        if (point.moderated_by) {
            html += `<div class="mod__ai">Решение: ${esc(point.moderated_by)} ` +
                    `(${esc(point.moderated_at || "")})</div>`;
        }
        html += '<div class="mod__row">';
        if (point.photo_url) {
            html += button(point, "photo", "approve", "Фото ок");
            html += button(point, "photo", "reject", "Скрыть фото");
        }
        if (point.comment) {
            html += button(point, "comment", "approve", "Коммент ок");
            html += button(point, "comment", "reject", "Скрыть коммент");
        }
        html += button(point, "point", "approve", "Опубликовать");
        html += button(point, "point", "reject", "Отклонить метку");
        html += "</div></div>";
        return html;
    };

    map.hooks.onCounts = function (counts) {
        if (!countsEl) return;
        countsEl.textContent =
            `на проверке: ${counts.pending || 0} · опубликовано: ${counts.published || 0} ` +
            `· отклонено: ${counts.rejected || 0}`;
    };

    document.addEventListener("click", async (event) => {
        const btn = event.target.closest(".mod-btn");
        if (!btn) return;
        btn.disabled = true;
        try {
            await postJSON(`/api/dev/points/${btn.dataset.point}/moderate`, {
                target: btn.dataset.target,
                action: btn.dataset.action,
            });
            map.map.closePopup();
            await map.load();
        } catch (err) {
            alert("Не удалось применить решение: " + (err.message || "ошибка"));
        } finally {
            btn.disabled = false;
        }
    });

    if (toggle) {
        toggle.addEventListener("change", () => map.setDevMode(toggle.checked));
        map.setDevMode(toggle.checked);
    }
})();
