from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def connect(database_url: str):
    return psycopg.connect(database_url, row_factory=dict_row)


def apply_schema(database_url: str) -> None:
    sql = Path("schema.sql").read_text(encoding="utf-8")
    with connect(database_url) as connection:
        connection.execute(sql)

