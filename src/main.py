import logging

from src.category_service import (
    checkpoint_category, complete_category, pending_categories, seed_categories,
)
from src.config import load_settings
from src.database import apply_schema, connect
from src.yellow_pages_provider import YellowPagesProvider
from src.progress import detail_completed
from src.repository import attach_category, save_business


def run() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("collector")
    apply_schema(settings.database_url)
    provider = YellowPagesProvider(settings)
    failures = []
    with connect(settings.database_url) as connection:
        count = seed_categories(connection)
        connection.commit()
        logger.info("Synchronized %d categories", count)
        categories = pending_categories(connection, settings.max_categories)
        for category in categories:
            logger.info("Starting category %s", category["name"])
            try:
                page = category["next_page"]
                while page <= settings.max_pages:
                    links = provider.page_links(category["search_query"], page)
                    if not links:
                        complete_category(connection, category["id"])
                        connection.commit()
                        break
                    saved = skipped = 0
                    for link in links:
                        existing_id = detail_completed(
                            connection, provider.source_id(link)
                        )
                        if existing_id:
                            attach_category(connection, existing_id, category["id"])
                            skipped += 1
                            continue
                        save_business(connection, category["id"], provider.detail(link))
                        saved += 1
                    checkpoint_category(connection, category["id"], page + 1)
                    connection.commit()
                    logger.info("Category %s page %d: saved=%d skipped=%d",
                                category["name"], page, saved, skipped)
                    page += 1
                    if len(links) < 20:
                        complete_category(connection, category["id"])
                        connection.commit()
                        break
                else:
                    logger.warning("Category %s reached MAX_PAGES at page %d",
                                   category["name"], page)
            except Exception:
                connection.rollback()
                failures.append(category["name"])
                logger.exception(
                    "Category %s failed and remains pending", category["name"]
                )
    if failures:
        raise RuntimeError(f"Failed categories: {', '.join(failures)}")


if __name__ == "__main__":
    run()
