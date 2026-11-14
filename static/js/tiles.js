// Подложка карты. Провайдер приходит из data-provider у #map (MAP_PROVIDER).
// Яндекс рисует тайлы в проекции EPSG:3395, поэтому карта создаётся с этой CRS,
// иначе метки «уезжают» от реальных мест на сотни метров.
(function () {
    const YANDEX_URL =
        "https://core-renderer-tiles.maps.yandex.net/tiles" +
        "?l=map&x={x}&y={y}&z={z}&scale=1&lang=ru_RU";
    const OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

    const PROVIDERS = {
        yandex: {
            crs: L.CRS.EPSG3395,
            minZoom: 3,
            maxZoom: 19,
            url: YANDEX_URL,
            // Убираем лишние/ошибочные ватермарки в контроле атрибуции Leaflet.
            // Оставляем только «Яндекс Карты».
            attribution:
                '<a href="https://yandex.ru/maps/" target="_blank" rel="noopener">' +
                'Яндекс Карты</a>',
        },
        osm: {
            crs: L.CRS.EPSG3857,
            minZoom: 3,
            maxZoom: 19,
            url: OSM_URL,
            attribution: "",
        },
    };

    function config(name) {
        return PROVIDERS[name] || PROVIDERS.yandex;
    }

    function layer(cfg) {
        // Leaflet показывает атрибуцию в правом нижнем углу через L.control.attribution.
        // Нам нужна только атрибуция провайдера (Яндекс), без строки "Leaflet".
        if (cfg.attributionControl) cfg.attributionControl.setPrefix(false);
        return L.tileLayer(cfg.url, {
            minZoom: cfg.minZoom,
            maxZoom: cfg.maxZoom,
            attribution: cfg.attribution,
        });
    }

    window.SuhoTiles = { config, layer };
})();
