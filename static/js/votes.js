// Голосование: активный голос пользователя, смена и отмена.
(function () {
    const { esc, postJSON } = window.SuhoApi;

    function agoText(point) {
        if (!point.confirmed_ago) return "";
        if (point.confirmations > 0) return "Подтверждено: " + point.confirmed_ago;
        return "Добавлено: " + point.confirmed_ago;
    }

    function html(point) {
        const published = !point.moderation_status ||
            point.moderation_status === "published";
        const my = point.my_vote || "";
        const ago = agoText(point);
        const id = esc(point.id);

        let buttons = "";
        if (published) {
            const yes = my === "confirm" ? " is-active" : "";
            const no = my === "deny" ? " is-active" : "";
            buttons = '<div class="votes__row">' +
                `<button type="button" class="vote-btn vote-btn--yes${yes}" ` +
                `data-point="${id}" data-vote="confirm">Тоже есть проблема</button>` +
                `<button type="button" class="vote-btn vote-btn--no${no}" ` +
                `data-point="${id}" data-vote="deny">Проблемы нет</button>` +
                "</div>";
            if (my) {
                buttons += `<button type="button" class="vote-clear" ` +
                    `data-point="${id}" data-vote="clear">Убрать мой голос</button>`;
            }
        }

        return '<div class="votes">' +
            `<div class="votes__line">Подтверждений: <b>${esc(point.confirmations || 0)}</b>` +
            ` · Опровержений: <b>${esc(point.denials || 0)}</b></div>` +
            (ago ? `<div class="votes__ago">${esc(ago)}</div>` : "") +
            buttons +
            "</div>";
    }

    function setBusy(busy) {
        document.querySelectorAll(".vote-btn, .vote-clear").forEach((node) => {
            node.disabled = busy;
        });
    }

    document.addEventListener("click", async (event) => {
        const btn = event.target.closest(".vote-btn, .vote-clear");
        if (!btn) return;
        event.preventDefault();
        event.stopPropagation();

        const id = Number(btn.dataset.point);
        const vote = btn.dataset.vote;
        setBusy(true);
        try {
            const body = { vote };
            // Геопозиция для голосований не обязательна: не дёргаем разрешение.
            if (window.SuhoGeo) await window.SuhoGeo.fill(body, "silent");
            const data = await postJSON(`/api/points/${id}/vote`, body);
            if (window.SuhoMap && window.SuhoMap.updatePoint) {
                window.SuhoMap.updatePoint(id, data);
            }
        } catch (err) {
            alert("Не удалось проголосовать: " + (err.message || "ошибка"));
        } finally {
            setBusy(false);
        }
    });

    window.SuhoVotes = { html };
})();
