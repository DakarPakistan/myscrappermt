def pending_categories(
    connection, limit: int, start_id: int = 0, end_id: int = 0
):
    with connection.cursor() as cursor:
        query = """SELECT id, name, search_query, next_page
        FROM categories WHERE is_enabled = TRUE AND is_completed = FALSE"""
        parameters = []
        if start_id > 0:
            query += " AND id >= %s"
            parameters.append(start_id)
        if end_id > 0:
            query += " AND id <= %s"
            parameters.append(end_id)
        query += " ORDER BY id"
        if limit > 0:
            query += " LIMIT %s"
            parameters.append(limit)
        cursor.execute(query, tuple(parameters))
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
