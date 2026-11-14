// Сценарий жителя: место на карте -> адрес, фото, комментарий -> отправка.
(function () {
    const { getJSON, postJSON } = window.SuhoApi;
    const el = (id) => document.getElementById(id);
    const picker = window.SuhoPhotoSource || null;

    const DEFAULTS = {
        notify_point_hint: "Передвиньте карту так, чтобы метка встала на место проблемы",
        notify_success: "Спасибо! Сообщение принято.",
        notify_thanks: "Вы помогаете другим жителям Владивостока заранее узнать о рисках стихийных происшествий.",
        notify_pending: "Фото и комментарий проверяются, метка появится после проверки.",
        notify_error: "Не удалось отправить сообщение. Попробуйте ещё раз.",
    };

    const n = {
        start: el("start-screen"), pin: el("pin-panel"), form: el("form-panel"),
        fab: el("fab-report"), centerPin: el("center-pin"), toast: el("toast"),
        error: el("flow-error"), pinUpload: el("pin-upload"), pinHint: el("pin-hint"),
        pinAddress: el("pin-address"), address: el("form-address"),
        comment: el("form-comment"), photoStatus: el("form-photo-status"),
        send: el("form-send"), back: el("form-back"),
    };

    let texts = {};
    let place = null;
    let stopFollow = null;
    let toastTimer = null;

    const t = (key) => texts[key] || DEFAULTS[key] || "";
    const show = (node) => node && node.classList.remove("hidden");
    const hide = (node) => node && node.classList.add("hidden");
    const setStage = (stage) => {
        if (window.SuhoStage) window.SuhoStage.setStage(stage);
    };
    const flyTo = (lat, lng, zoom) => {
        const map = window.SuhoMap && window.SuhoMap.map;
        if (!map) return;
        const target = zoom != null ? zoom : map.getZoom();
        try {
            map.flyTo([lat, lng], target, { duration: 0.9, easeLinearity: 0.25 });
        } catch (_) {
            map.setView([lat, lng], target);
        }
    };

    function toast(message, isError) {
        n.toast.textContent = message;
        n.toast.classList.toggle("toast--error", Boolean(isError));
        show(n.toast);
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => hide(n.toast), 7000);
    }

    function setError(message) {
        n.error.textContent = message || "";
        n.error.hidden = !message;
    }

    function photoStatus(text, isError) {
        [n.pinUpload, n.photoStatus].forEach((node) => {
            node.textContent = text;
            node.classList.toggle("panel__status--error", Boolean(isError));
        });
    }

    function attachPhoto(file) {
        const problem = window.SuhoUpload.validate(file);
        if (problem) {
            toast(problem, true);
            return false;
        }
        window.SuhoUpload.start(file, photoStatus);
        return true;
    }

    async function geoFallback() {
        try {
            const hint = await getJSON("/api/geo/hint");
            flyTo(hint.lat, hint.lng, hint.source === "ip" ? 14 : 13);
        } catch (err) {
            console.warn("Подсказка места недоступна", err);
        }
    }

    function locate() {
        // Запрашиваем геопозицию только при первом входе и по явному действию
        // (кнопка "Моё место")/перед загрузкой фото. Здесь — явное действие.
        if (window.SuhoGeo) {
            return window.SuhoGeo.request("entry").then((pos) => {
                if (pos) {
                    flyTo(pos.lat, pos.lng, 17);
                } else {
                    geoFallback();
                }
            });
        }
        if (!navigator.geolocation) return geoFallback();
        navigator.geolocation.getCurrentPosition(
            (pos) => flyTo(pos.coords.latitude, pos.coords.longitude, 17),
            () => geoFallback(),
            { timeout: 7000, maximumAge: 60000, enableHighAccuracy: true }
        );
    }

    function showMapOnly() {
        [n.start, n.pin, n.form, n.centerPin].forEach(hide);
        show(n.fab);
        setStage("map");
    }

    function openPinStep() {
        setError("");
        n.pinHint.textContent = t("notify_point_hint");
        [n.start, n.form, n.fab].forEach(hide);
        setStage("pin");
        show(n.centerPin);
        show(n.pin);
        locate();
        if (stopFollow) stopFollow();
        stopFollow = window.SuhoAddress.follow(
            window.SuhoMap.map,
            (text) => { n.pinAddress.textContent = text; }
        );
    }

    function openFormStep() {
        place = window.SuhoMap.map.getCenter();
        if (stopFollow) { stopFollow(); stopFollow = null; }
        hide(n.pin);
        hide(n.centerPin);
        n.address.value = window.SuhoAddress.current || "";
        show(n.form);
        setStage("form");
        n.address.focus();
    }

    function resetFlow() {
        place = null;
        if (stopFollow) { stopFollow(); stopFollow = null; }
        window.SuhoUpload.reset();
        window.SuhoAddress.reset();
        if (picker) picker.clear();
        n.address.value = "";
        n.comment.value = "";
        photoStatus("", false);
        setError("");
    }

    async function submit() {
        if (!place) return;
        setError("");
        n.send.disabled = true;
        try {
            if (window.SuhoUpload.promise) await window.SuhoUpload.promise;
            const body = {
                lat: place.lat,
                lng: place.lng,
                address: n.address.value.trim(),
                comment: n.comment.value.trim(),
                upload_id: window.SuhoUpload.id,
            };
            if (window.SuhoGeo) await window.SuhoGeo.fill(body);
            const res = await postJSON("/api/points", body);
            const tail = window.SuhoUpload.error ? " Фото отправить не удалось." : "";
            resetFlow();
            showMapOnly();
            toast(`${res.message || t("notify_success")} ${res.thanks || t("notify_thanks")} ` +
                  `${res.pending || t("notify_pending")}${tail}`);
            window.SuhoMap.load();
        } catch (err) {
            const message = err.message || t("notify_error");
            setError(message);
            toast(t("notify_error") + " " + message, true);
        } finally {
            n.send.disabled = false;
        }
    }

    // Файл приходит из photo_source.js: origin "cover" — со стартового экрана
    // (сразу ведём к выбору места), "form" — поле «Фото» внутри формы.
    function handleFile(file, origin) {
        // При каждой попытке загрузить фотографию — запрашиваем геопозицию.
        const afterGeo = () => {
            const ok = attachPhoto(file);
            if (ok && origin === "cover") openPinStep();
        };
        if (window.SuhoGeo) {
            window.SuhoGeo.request("photo").then(afterGeo);
        } else {
            afterGeo();
        }
    }

    if (picker) picker.onFile(handleFile);

    el("btn-report-photo").addEventListener("click", () => {
        if (picker) picker.pick("cover");
    });
    el("form-photo-pick").addEventListener("click", () => {
        if (picker) picker.pick("form");
    });
    el("btn-report-map").addEventListener("click", openPinStep);
    el("btn-open-map").addEventListener("click", showMapOnly);
    el("fab-report").addEventListener("click", () => { resetFlow(); openPinStep(); });
    el("pin-locate").addEventListener("click", locate);
    el("pin-cancel").addEventListener("click", () => { resetFlow(); showMapOnly(); });
    el("pin-confirm").addEventListener("click", openFormStep);
    n.back.addEventListener("click", openPinStep);
    n.send.addEventListener("click", submit);

    getJSON("/api/texts")
        .then((data) => { texts = data || {}; })
        .catch(() => { texts = {}; });

    // При первом входе: если есть сохранённая геопозиция — используем её молча,
    // иначе один раз спрашиваем разрешение и центруем карту.
    if (window.SuhoGeo) {
        const stored = window.SuhoGeo.current;
        if (stored && stored.lat && stored.lng) {
            window.SuhoMap.map.setView([stored.lat, stored.lng], 14);
        } else {
            window.SuhoGeo.request("entry").then((pos) => {
                if (pos) window.SuhoMap.map.setView([pos.lat, pos.lng], 14);
            });
        }
    }

    // На старте показываем обложку — карта скрыта под ней.
    setStage("cover");
})();
