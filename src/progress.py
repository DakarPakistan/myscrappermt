def detail_completed(connection, source_id: str):
    row = connection.execute(
        """SELECT id, is_detail_completed FROM businesses
        WHERE source='yellow_malta' AND source_id=%s""", (source_id,)
    ).fetchone()
    return row["id"] if row and row["is_detail_completed"] else None


def completed_businesses(connection, source_ids: list[str]) -> dict[str, int]:
    if not source_ids:
        return {}
    rows = connection.execute(
        """SELECT id, source_id FROM businesses
        WHERE source='yellow_malta' AND is_detail_completed = TRUE
        AND source_id = ANY(%s)""", (source_ids,)
    ).fetchall()
    return {row["source_id"]: row["id"] for row in rows}
