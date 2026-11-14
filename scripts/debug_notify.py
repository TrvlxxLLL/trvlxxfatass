from contextlib import closing

import settings_store as st
from db import get_connection


def main() -> None:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT key, value, updated_at FROM settings "
            "WHERE key LIKE 'notify_%' ORDER BY key"
        ).fetchall()
        print("notify_* rows in DB:", len(rows))
        for r in rows:
            print(f"- {r['key']}: {r['value']} (updated_at={r['updated_at']})")

    print("\nEffective st.notifications():")
    for k, v in sorted(st.notifications().items()):
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
