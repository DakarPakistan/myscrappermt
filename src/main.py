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
                page_signatures = set()
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
                    source_ids = tuple(sorted(
                        provider.source_id(link) for link in links
                    ))
                    if source_ids in page_signatures:
                        logger.info("Repeated result page; completing category: %s",
                                    category["name"])
                        complete_category(connection, category["id"])
                        connection.commit()
                        break
                    page_signatures.add(source_ids)
                    existing = completed_businesses(
                        connection, list(source_ids)
                    )
                    connection.commit()
                    saved = skipped = 0
                    for link in links:
                        source_id = provider.source_id(link)
                        existing_id = existing.get(source_id)
                        if existing_id:
                            attach_category(connection, existing_id, category["id"])
                            connection.commit()
                            skipped += 1
                            continue
                        record = provider.detail(link)
                        if record is None:
                            logger.warning("Skipping missing listing: %s", link)
                            skipped += 1
                            continue
                        contact_count = sum(len(value) for value in
                                            record["contacts"].values())
                        logger.info("Business scraped: %s contacts=%d timings=%d",
                                    record["name"], contact_count,
                                    len(record["working_hours"]))
                        save_business(connection, category["id"], record)
                        connection.commit()
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
                    # The configured page limit is a safety boundary, not a
                    # scraper failure. Mark the category complete so a later
                    # run does not repeatedly start at page MAX_PAGES + 1.
                    complete_category(connection, category["id"])
                    connection.commit()
                    logger.warning("Category %s reached MAX_PAGES at page %d; "
                                   "marking it complete",
                                   category["name"], page)
            except Exception as error:
                connection.rollback()
                reason = f"{category['name']}: {type(error).__name__}: {error}"
                failures.append(reason)
                logger.exception(
                    "Category %s failed and remains pending", category["name"]
                )
    if failures:
        raise RuntimeError("Failed categories: " + "; ".join(failures))


if __name__ == "__main__":
    run()
