// Мобильные улучшения «как приложение» без влияния на десктоп.
// - Чиним поведение панелей при появлении клавиатуры (VisualViewport).
// - Даём CSS переменную --vvh для более стабильной высоты.
// - Убираем "резиновый" скролл страницы, оставляя скролл в панелях.
(function () {
    const root = document.documentElement;

    function setVar(name, value) {
        root.style.setProperty(name, value);
    }

    function updateVvh() {
        const vv = window.visualViewport;
        const height = vv ? vv.height : window.innerHeight;
        setVar("--vvh", `${Math.round(height)}px`);
        setVar("--kb", "0px");
    }

    function updateKeyboardOffset() {
        const vv = window.visualViewport;
        if (!vv) return;
        const offset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
        setVar("--kb", `${Math.round(offset)}px`);
    }

    function isNarrow() {
        return window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
    }

    function lockBodyScroll() {
        // На десктопе не трогаем.
        if (!isNarrow()) return;
        // Не даём странице прыгать при фокусе/скролле: карта/панели управляют сами.
        document.body.style.overflow = "hidden";
        document.body.style.touchAction = "manipulation";
    }

    function onFocusIn(e) {
        const node = e.target;
        if (!node) return;
        const tag = (node.tagName || "").toLowerCase();
        if (tag !== "input" && tag !== "textarea" && tag !== "select") return;
        updateKeyboardOffset();

        // Подскроллим поле внутрь панели, чтобы оно не оказалось под клавиатурой.
        const panel = node.closest && node.closest(".panel");
        if (panel && panel.scrollIntoView) {
            setTimeout(() => {
                try { node.scrollIntoView({ block: "center", inline: "nearest" }); } catch (_) {}
            }, 50);
        }
    }

    function onFocusOut() {
        setTimeout(() => setVar("--kb", "0px"), 50);
    }

    updateVvh();
    lockBodyScroll();

    window.addEventListener("resize", () => { updateVvh(); updateKeyboardOffset(); });
    window.addEventListener("orientationchange", () => { updateVvh(); updateKeyboardOffset(); });
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("focusout", onFocusOut);

    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", () => {
            updateVvh();
            updateKeyboardOffset();
        });
        window.visualViewport.addEventListener("scroll", updateKeyboardOffset);
    }
})();
