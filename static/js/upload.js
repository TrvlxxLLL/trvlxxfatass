// Загрузка фото на сервер: проверка файла, геометка и фоновая отправка.
(function () {
    const { postForm } = window.SuhoApi;

    const MAX_BYTES = 5 * 1024 * 1024;
    const TYPES = ["image/png", "image/jpeg"];

    let state = { promise: null, result: null, error: "" };

    function reset() {
        state = { promise: null, result: null, error: "" };
    }

    function validate(file) {
        if (!file) return "Файл не выбран";
        if (!TYPES.includes(file.type)) return "Допустимы только PNG и JPG";
        if (file.size > MAX_BYTES) return "Фото больше 5 МБ";
        return "";
    }

    // onStatus(text, isError) вызывается при старте, успехе и ошибке.
    function start(file, onStatus) {
        reset();
        const data = new FormData();
        data.append("photo", file);
        if (onStatus) onStatus("Фото загружается на сервер…", false);

        const geoReady = window.SuhoGeo
            ? window.SuhoGeo.request().then((coords) => {
                if (coords) {
                    data.append("user_lat", coords.lat);
                    data.append("user_lng", coords.lng);
                }
            })
            : Promise.resolve();

        state.promise = geoReady
            .then(() => postForm("/api/uploads", data))
            .then((res) => {
                state.result = res;
                if (onStatus) onStatus("Фото загружено", false);
                return res;
            })
            .catch((err) => {
                state.error = err.message || "ошибка загрузки";
                if (onStatus) onStatus("Фото не загрузилось: " + state.error, true);
                return null;
            });
        return state.promise;
    }

    window.SuhoUpload = {
        start,
        reset,
        validate,
        get promise() {
            return state.promise;
        },
        get id() {
            return state.result ? state.result.upload_id : "";
        },
        get error() {
            return state.error;
        },
        get started() {
            return Boolean(state.promise);
        },
    };
})();
