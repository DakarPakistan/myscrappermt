import logging

from src.category_service import complete_category, pending_categories, seed_categories
from src.config import load_settings
from src.database import apply_schema, connect
from src.yellow_pages_provider import YellowPagesProvider
from src.repository import save_business


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
                elements = provider.fetch(category["search_query"])
                for element in elements:
                    save_business(connection, category["id"], element)
                complete_category(connection, category["id"])
                connection.commit()
                logger.info(
                    "Completed category %s: %d records",
                    category["name"], len(elements),
                )
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
