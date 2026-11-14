# SuhoVL

Народная карта подтоплений Владивостока: Flask + SQLite + Leaflet.

## Быстрый старт (Docker)

```bash
docker compose up -d --build
```

Открыть: http://localhost:5000

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните `SECRET_KEY` и `GPTUNNEL_API_KEY`.

## Локальный запуск

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Подробнее: `readme.txt`
