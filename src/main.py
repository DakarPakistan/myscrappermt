import logging

from src.category_service import (
    checkpoint_category, complete_category, pending_categories,
)
from src.config import load_settings
from src.database import apply_schema, connect
from src.yellow_pages_provider import YellowPagesProvider
from src.progress import completed_businesses
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
        categories = pending_categories(connection, settings.max_categories)
        logger.info("Loaded categories from database: %d", len(categories))
        for category in categories:
            logger.info("Starting category: %s", category["name"])
            try:
                page = category["next_page"]
                while page <= settings.max_pages:
                    logger.info("Searching businesses: category=%s page=%d",
                                category["name"], page)
                    links = provider.page_links(category["search_query"], page)
                    logger.info("Found business links: category=%s page=%d count=%d",
                                category["name"], page, len(links))
                    if not links:
                        logger.info("No businesses found; completing category: %s",
                                    category["name"])
                        complete_category(connection, category["id"])
                        connection.commit()
                        break
                    existing = completed_businesses(
                        connection, [provider.source_id(link) for link in links]
                    )
                    saved = skipped = 0
                    for link in links:
                        source_id = provider.source_id(link)
                        existing_id = existing.get(source_id)
                        if existing_id:
                            attach_category(connection, existing_id, category["id"])
                            skipped += 1
                            continue
                        record = provider.detail(link)
                        contact_count = sum(len(value) for value in
                                            record["contacts"].values())
                        logger.info("Business scraped: %s contacts=%d timings=%d",
                                    record["name"], contact_count,
                                    len(record["working_hours"]))
                        save_business(connection, category["id"], record)
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
