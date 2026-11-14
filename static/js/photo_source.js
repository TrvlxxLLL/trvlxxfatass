// Выбор источника фото: камера или галерея.
// Важно: под каждый источник — свой <input> с атрибутами, прописанными
// в разметке. Android Chrome берёт параметры файлового диалога из разметки:
// capture, навешанный скриптом перед click(), игнорируется и открывается
// галерея вместо камеры.
(function () {
    const sheet = document.getElementById("photo-sheet");
    const camera = document.getElementById("photo-camera");
    const gallery = document.getElementById("photo-gallery");
    if (!sheet || !camera || !gallery) return;

    const handlers = [];
    let origin = "";

    function isMobile() {
        if (!window.matchMedia) return false;
        return Boolean(
            window.matchMedia("(pointer: coarse)").matches ||
            window.matchMedia("(max-width: 640px)").matches
        );
    }

    function openSheet() {
        sheet.classList.remove("hidden");
        document.body.dataset.sheet = "photo";
        const first = sheet.querySelector("[data-photo-source]");
        if (first) {
            setTimeout(() => {
                try { first.focus(); } catch (_) {}
            }, 30);
        }
    }

    function closeSheet() {
        sheet.classList.add("hidden");
        delete document.body.dataset.sheet;
    }

    // value сбрасываем, иначе повторный выбор того же файла не даст change.
    function openInput(input) {
        input.value = "";
        input.click();
    }

    function emit(file) {
        handlers.forEach((cb) => {
            try {
                cb(file, origin);
            } catch (err) {
                console.warn("Обработчик фото упал", err);
            }
        });
    }

    function onChange(event) {
        const files = event.target.files;
        const file = files && files[0];
        if (file) emit(file);
    }

    camera.addEventListener("change", onChange);
    gallery.addEventListener("change", onChange);

    sheet.addEventListener("click", (event) => {
        const node = event.target;
        if (!node || !node.closest) return;
        if (node.closest("[data-sheet-close]")) {
            closeSheet();
            return;
        }
        const btn = node.closest("[data-photo-source]");
        if (!btn) return;
        const source = btn.getAttribute("data-photo-source");
        closeSheet();
        openInput(source === "camera" ? camera : gallery);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !sheet.classList.contains("hidden")) {
            closeSheet();
        }
    });

    // from: "cover" — фото со стартового экрана, "form" — поле в форме.
    function pick(from) {
        origin = from || "";
        if (!isMobile()) {
            openInput(gallery);
            return;
        }
        openSheet();
    }

    window.SuhoPhotoSource = {
        pick,
        close: closeSheet,
        onFile(cb) {
            if (typeof cb === "function") handlers.push(cb);
        },
        clear() {
            camera.value = "";
            gallery.value = "";
            origin = "";
        },
        get isMobile() { return isMobile(); },
    };
})();
