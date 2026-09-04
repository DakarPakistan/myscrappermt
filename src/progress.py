def detail_completed(connection, source_id: str):
    row = connection.execute(
        """SELECT id, is_detail_completed FROM businesses
        WHERE source='yellow_malta' AND source_id=%s""", (source_id,)
    ).fetchone()
    return row["id"] if row and row["is_detail_completed"] else None
