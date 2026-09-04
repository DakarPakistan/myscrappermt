"""Prepare and display category candidates before any business scraping."""
import os

import psycopg
from dotenv import load_dotenv

from src.category_service import seed_categories
from src.database import apply_schema
from src.config import load_settings
from src.yellow_pages_provider import YellowPagesProvider


def main() -> None:
    load_dotenv()
    database_url = os.environ["DATABASE_URL"]
    apply_schema(database_url)
    settings = load_settings()
    with psycopg.connect(database_url) as connection:
        total = seed_categories(connection)
        if settings.discover_categories:
            candidates = YellowPagesProvider(settings).discover_categories()
            connection.executemany(
                """INSERT INTO categories (name, search_query, is_enabled)
                VALUES (%s, %s, FALSE) ON CONFLICT DO NOTHING""",
                [(name, slug) for name, slug in candidates],
            )
            total += len(candidates)
        connection.commit()
        rows = connection.execute(
            """SELECT id, name, search_query, is_enabled
            FROM categories ORDER BY id"""
        ).fetchall()
    print(f"Loaded {total} category candidates.")
    print("ID | Enabled | Category | Yellow Pages keyword")
    for row in rows:
        print(f"{row[0]} | {row[3]} | {row[1]} | {row[2]}")
    print("\nEdit categories.csv: set enabled=true only for wanted categories.")
    print("Then run: python -m src.main")


if __name__ == "__main__":
    main()
