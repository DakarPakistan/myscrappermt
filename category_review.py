"""Prepare and display category candidates before any business scraping."""
import os

import psycopg
from dotenv import load_dotenv

from src.database import apply_schema
from src.config import load_settings
from src.yellow_pages_provider import YellowPagesProvider


def main() -> None:
    load_dotenv()
    database_url = os.environ["DATABASE_URL"]
    apply_schema(database_url)
    settings = load_settings()
    with psycopg.connect(database_url) as connection:
        candidates = YellowPagesProvider(settings).discover_categories()
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO categories (name, search_query, is_enabled)
                VALUES (%s, %s, FALSE) ON CONFLICT DO NOTHING""",
                [(name, slug) for name, slug in candidates],
            )
        total = len(candidates)
        connection.commit()
        rows = connection.execute(
            """SELECT id, name, search_query, is_enabled
            FROM categories ORDER BY id"""
        ).fetchall()
    print(f"Loaded {total} Yellow category candidates into the database.")
    print("ID | Enabled | Category | Yellow Pages keyword")
    for row in rows:
        print(f"{row[0]} | {row[3]} | {row[1]} | {row[2]}")
    print("\nReview categories in PostgreSQL and set is_enabled=true for wanted rows.")
    print("Then run: python -m src.main")


if __name__ == "__main__":
    main()
