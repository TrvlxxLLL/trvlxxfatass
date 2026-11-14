// Адрес по координатам: разовый запрос и слежение за центром карты.
(function () {
    const { getJSON } = window.SuhoApi;

    let timer = null;
    let seq = 0;
    let current = "";

    async function lookup(lat, lng) {
        const url = `/api/geo/address?lat=${lat.toFixed(6)}&lng=${lng.toFixed(6)}`;
        const data = await getJSON(url);
        return data.address || "";
    }

    // Следит за центром карты и зовёт onChange(text, isLoading) при остановке.
    function follow(map, onChange) {
        function update() {
            const point = map.getCenter();
            const my = ++seq;
            onChange("Определяем адрес…", true);
            lookup(point.lat, point.lng)
                .then((address) => {
                    if (my !== seq) return;
                    current = address;
                    onChange(address || "Адрес не определён", false);
                })
                .catch(() => {
                    if (my !== seq) return;
                    current = "";
                    onChange("Адрес не определён", false);
                });
        }

        function onMove() {
            clearTimeout(timer);
            timer = setTimeout(update, 700);
        }

        map.on("moveend", onMove);
        update();

        return function stop() {
            map.off("moveend", onMove);
            clearTimeout(timer);
            seq += 1;
        };
    }

    window.SuhoAddress = {
        follow,
        lookup,
        get current() {
            return current;
        },
        reset() {
            current = "";
            seq += 1;
        },
    };
})();
