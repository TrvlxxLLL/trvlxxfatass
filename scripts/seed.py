import argparse
import os
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from db import get_connection, init_db  # noqa: E402

# (lat, lng, title, description, severity, confirmations, status, hours_ago)
SEED_POINTS = [
    (43.1262, 131.9042, "Вторая речка, ул. Калинина",
     "Вода по колено на перекрёстке, проезд для легковых закрыт.",
     "high", 14, "active", 2),
    (43.1321, 131.9118, "Вторая речка, пр-т 100 лет Владивостоку",
     "Вода выше бордюра, пешеходный переход не виден.",
     "medium", 6, "active", 5),
    (43.1044, 131.9385, "Луговая, ул. Луговая",
     "Вода в подвальных помещениях жилых домов, откачка не справляется.",
     "high", 9, "active", 1),
    (43.1071, 131.9352, "Луговая, у рынка",
     "Ручей пересёк проезжую часть.",
     "medium", 3, "active", 26),
    (43.1013, 131.8895, "Океанский проспект, перекрёсток с ул. Фадеева",
     "Машины буксуют в луже, объезд через встречную полосу.",
     "high", 12, "active", 3),
    (43.1058, 131.8952, "Океанский проспект, у дома 58",
     "Вода ушла после работы ливнёвки.",
     "low", 2, "gone", 30),
    (43.1205, 131.9020, "Ул. Русская, подземный переход",
     "Переход затоплен, ступени скрыты водой.",
     "high", 8, "active", 0),
    (43.1224, 131.9068, "Ул. Русская, у моста через ручей",
     "Уровень воды у моста поднимается, перила скрыты.",
     "medium", 7, "active", 48),
    (43.0020, 131.9255, "Патрокл, основная дорога посёлка",
     "Колея полна воды, пешеходам приходится идти по обочине.",
     "medium", 2, "active", 72),
    (42.9965, 131.9310, "Патрокл, у пляжа",
     "Небольшое подтопление, вода сошла к утру.",
     "low", 1, "gone", 96),
    (43.1584, 131.9216, "Чуркин, ул. Чуркина",
     "Двор и въезд в гараж под водой, машины стоят в воде.",
     "high", 11, "active", 4),
    (43.1609, 131.9154, "Чуркин, ул. Мира",
     "Лужи у остановки, проход по бордюру.",
     "medium", 4, "active", 12),
    (43.1218, 131.9158, "Вторая речка, ул. Адмирала Фокина",
     "Подтопление обочины, вода уже ушла.",
     "medium", 2, "gone", 60),
    (43.1191, 131.9102, "Вторая речка, ул. Фадеева",
     "Небольшие лужи у дворов, проезд возможен.",
     "low", 5, "active", 10),
    (43.0951, 131.9012, "Океанский проспект, у дома 92",
     "Вода стояла около суток, сейчас сошла.",
     "low", 3, "gone", 120),
]

INSERT_SQL = """
INSERT INTO points
    (lat, lng, title, description, photo_path,
     severity, confirmations, status, created_at,
     photo_status, comment_status, moderation_status)
VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, 'none', 'approved', 'published')
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Наполнить базу тестовыми точками")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="удалить существующие точки и заполнить заново",
    )
    args = parser.parse_args()

    init_db()
    now = datetime.now(timezone.utc)

    with closing(get_connection()) as conn:
        count = conn.execute("SELECT COUNT(*) FROM points").fetchone()[0]
        if count and not args.reset:
            print(f"В таблице points уже {count} записей, сид пропущен. "
                  "Для перезаписи запустите с --reset.")
            return

        if args.reset:
            conn.execute("DELETE FROM points")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'points'")

        rows = []
        for lat, lng, title, description, severity, confirmations, status, hours_ago in SEED_POINTS:
            created_at = (now - timedelta(hours=hours_ago)).isoformat(timespec="seconds")
            rows.append((lat, lng, title, description, severity, confirmations, status, created_at))

        conn.executemany(INSERT_SQL, rows)
        conn.commit()

    print(f"Добавлено точек: {len(rows)}")


if __name__ == "__main__":
    main()
