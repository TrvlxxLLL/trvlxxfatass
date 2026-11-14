// Управляет этапами UI: cover (стартовая обложка) -> map/pin/form.
// Прячет карту пока показана обложка, вызывает invalidateSize при первом показе,
// отмечает перетаскивание карты через data-dragging для анимации пина.
(function () {
    const body = document.body;
    let mapReady = false;

    function setStage(stage) {
        body.dataset.stage = stage;
        if (stage !== "cover") revealMapOnce();
    }

    function revealMapOnce() {
        if (mapReady) return;
        mapReady = true;
        requestAnimationFrame(() => {
            if (window.SuhoMap && window.SuhoMap.map) {
                try { window.SuhoMap.map.invalidateSize(); } catch (_) {}
            }
        });
    }

    function bindDragFlag() {
        if (!window.SuhoMap || !window.SuhoMap.map) return;
        const map = window.SuhoMap.map;
        map.on("movestart", () => body.dataset.dragging = "1");
        map.on("moveend", () => { delete body.dataset.dragging; });
    }

    window.SuhoStage = { setStage };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindDragFlag);
    } else {
        bindDragFlag();
    }
})();
