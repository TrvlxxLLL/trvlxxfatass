// Карта происшествий: отрисовка точек и общий доступ для остальных модулей.
(function () {
    const { esc, getJSON } = window.SuhoApi;
    const COLORS = { low: "#2a9d8f", medium: "#e9c46a", high: "#e63946" };

    const mapEl = document.getElementById("map");
    const center = [Number(mapEl.dataset.lat), Number(mapEl.dataset.lon)];
    const isDev = document.body.dataset.dev === "1";

    const tiles = window.SuhoTiles.config(mapEl.dataset.provider);
    const map = L.map("map", { zoomControl: true, crs: tiles.crs })
        .setView(center, 13);
    tiles.attributionControl = map.attributionControl;
    window.SuhoTiles.layer(tiles).addTo(map);

    const layer = L.layerGroup().addTo(map);
    const hooks = { popupExtra: null, onCounts: null };
    const points = new Map();
    const markers = new Map();
    let devMode = false;

    function markerColor(point) {
        if (point.moderation_status === "rejected") return "#6c757d";
        if (point.moderation_status === "pending") return "#8e44ad";
        if (point.status === "gone") return "#8d99ae";
        return COLORS[point.severity] || "#1d70b8";
    }

    function votesHtml(point) {
        return window.SuhoVotes ? window.SuhoVotes.html(point) : "";
    }

    function popupHtml(point) {
        const state = point.status === "gone" ? "Происшествие устранено" : "Есть происшествие";
        const photo = point.photo_url
            ? `<img class="popup-photo" src="${esc(point.photo_url)}" alt="Фото происшествия">`
            : "";
        const comment = point.comment
            ? `<div class="popup-comment">${esc(point.comment)}</div>`
            : "";
        const address = point.address
            ? `<div class="popup-address">${esc(point.address)}</div>`
            : "";
        const extra = hooks.popupExtra ? hooks.popupExtra(point) : "";
        return (
            `<strong>${esc(point.title)}</strong><br>` +
            address +
            `<em>${state}</em><br>` +
            `<span class="popup-date">${esc(point.created_at)}</span>` +
            comment + photo + votesHtml(point) + extra
        );
    }

    function labelHtml(point) {
        return `(${point.confirmations || 0}/${point.denials || 0})`;
    }

    function addPoint(point) {
        points.set(point.id, point);
        const marker = L.circleMarker([point.lat, point.lng], {
            radius: 11,
            color: "#ffffff",
            weight: 2,
            fillColor: markerColor(point),
            fillOpacity: 0.95,
        })
            .addTo(layer)
            .bindPopup(popupHtml(point))
            .bindTooltip(labelHtml(point), {
                permanent: true,
                direction: "bottom",
                offset: [0, 8],
                className: "vote-label",
            });
        markers.set(point.id, marker);
        return marker;
    }

    function updatePoint(id, patch) {
        const point = points.get(id);
        if (!point) return;
        Object.assign(point, patch);
        const marker = markers.get(id);
        if (!marker) return;
        marker.setTooltipContent(labelHtml(point));
        marker.setPopupContent(popupHtml(point));
    }

    async function load() {
        const url = isDev && devMode ? "/api/dev/points?scope=all" : "/api/points";
        try {
            const data = await getJSON(url);
            const items = Array.isArray(data) ? data : (data.items || []);
            layer.clearLayers();
            points.clear();
            markers.clear();
            items.forEach(addPoint);
            if (hooks.onCounts && data.counts) hooks.onCounts(data.counts);
        } catch (err) {
            console.error("Не удалось загрузить точки", err);
        }
    }

    function setDevMode(value) {
        devMode = Boolean(value);
        return load();
    }

    window.SuhoMap = {
        map,
        load,
        addPoint,
        updatePoint,
        setDevMode,
        hooks,
        cityCenter: { lat: center[0], lng: center[1] },
    };

    load();
})();
