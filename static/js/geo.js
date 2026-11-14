// Геопозиция пользователя: запрашиваем только когда нужно, и кешируем в localStorage.
(function () {
    const LS_KEY = "suho_geo_cached_v1";
    const LS_TTL_MS = 1000 * 60 * 60 * 6; // 6 часов

    let cached = null;
    let denied = false;
    let pending = null;

    function loadFromStorage() {
        try {
            const raw = localStorage.getItem(LS_KEY);
            if (!raw) return null;
            const data = JSON.parse(raw);
            if (!data || !data.ts || !data.coords) return null;
            if (Date.now() - Number(data.ts) > LS_TTL_MS) return null;
            if (!data.coords.lat || !data.coords.lng) return null;
            return data.coords;
        } catch (_) {
            return null;
        }
    }

    function saveToStorage(coords) {
        try {
            localStorage.setItem(LS_KEY, JSON.stringify({ ts: Date.now(), coords }));
        } catch (_) {
            // ignore
        }
    }

    // mode:
    //  - "entry": при первом входе (один раз, если нет кеша)
    //  - "photo": перед загрузкой фото (разрешаем переспросить/обновить)
    //  - "silent": не спрашивать, только вернуть кеш (если есть)
    function request(mode, options) {
        if (cached) return Promise.resolve(cached);
        const stored = loadFromStorage();
        if (stored) {
            cached = stored;
            return Promise.resolve(cached);
        }

        if (mode === "silent") return Promise.resolve(null);
        if (pending) return pending;
        if (denied || !navigator.geolocation) return Promise.resolve(null);

        const opts = Object.assign(
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 },
            options || {}
        );

        pending = new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    cached = {
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude,
                        accuracy: pos.coords.accuracy || 0,
                    };
                    saveToStorage(cached);
                    resolve(cached);
                },
                (error) => {
                    if (error && error.code === 1) denied = true;
                    resolve(null);
                },
                opts
            );
        }).then((value) => {
            pending = null;
            return value;
        });

        return pending;
    }

    function fill(body, mode) {
        return request(mode || "silent").then((coords) => {
            if (coords) {
                body.user_lat = coords.lat;
                body.user_lng = coords.lng;
            }
            return body;
        });
    }

    window.SuhoGeo = {
        request,
        fill,
        get current() {
            return cached || loadFromStorage();
        },
    };
})();
