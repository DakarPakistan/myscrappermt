import csv
from pathlib import Path


def seed_categories(connection, path: str = "categories.csv") -> int:
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8")))
    for row in rows:
        row["enabled"] = row.get("enabled", "false").lower() in {"1", "true", "yes"}
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO categories (name, search_query, is_enabled)
            VALUES (%(name)s, %(search_query)s, %(enabled)s)
            ON CONFLICT (name) DO UPDATE SET
              search_query = EXCLUDED.search_query,
              is_enabled = EXCLUDED.is_enabled
            """,
            rows,
        )
    return len(rows)


def pending_categories(connection, limit: int):
    with connection.cursor() as cursor:
        query = """SELECT id, name, search_query, next_page
        FROM categories WHERE is_enabled = TRUE AND is_completed = FALSE
        ORDER BY id"""
        if limit > 0:
            query += " LIMIT %s"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        return cursor.fetchall()


def complete_category(connection, category_id: int) -> None:
    connection.execute(
        """
        UPDATE categories SET is_completed = TRUE, completed_at = NOW()
        WHERE id = %s
        """,
        (category_id,),
    )


def checkpoint_category(connection, category_id: int, next_page: int) -> None:
    connection.execute(
        "UPDATE categories SET next_page=%s WHERE id=%s",
        (next_page, category_id),
    )


def discover_categories(connection, places: list[dict]) -> int:
    names = set()
    for place in places:
        if category := place.get("category") or place.get("type"):
            names.add(category.strip())
        subtypes = place.get("subtypes") or ""
        values = subtypes if isinstance(subtypes, list) else subtypes.split(",")
        names.update(value.strip() for value in values if value.strip())
    rows = [(name, name) for name in names if len(name) <= 120]
    with connection.cursor() as cursor:
        cursor.executemany(
            """INSERT INTO categories (name, search_query, is_enabled)
            VALUES (%s, %s, FALSE)
            ON CONFLICT DO NOTHING""",
            rows,
        )
    return len(rows)
