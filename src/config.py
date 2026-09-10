import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    yellow_url: str
    http_timeout: int
    request_delay: float
    max_pages: int
    max_categories: int
    category_start_id: int
    category_end_id: int
    discover_categories: bool
    log_level: str


def load_settings() -> Settings:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "").strip().strip("\"'")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    category_start_id = int(os.getenv("CATEGORY_START_ID", "0"))
    category_end_id = int(os.getenv("CATEGORY_END_ID", "0"))
    if category_start_id < 0 or category_end_id < 0:
        raise ValueError("CATEGORY_START_ID and CATEGORY_END_ID cannot be negative")
    if category_end_id and category_start_id > category_end_id:
        raise ValueError("CATEGORY_START_ID cannot be greater than CATEGORY_END_ID")
    return Settings(
        database_url=database_url,
        yellow_url=os.getenv("YELLOW_BASE_URL", "https://www.yellow.com.mt").rstrip("/"),
        http_timeout=int(os.getenv("HTTP_TIMEOUT_SECONDS", "60")),
        request_delay=float(os.getenv("REQUEST_DELAY_SECONDS", "2")),
        max_pages=int(os.getenv("MAX_PAGES_PER_CATEGORY", "100")),
        max_categories=int(os.getenv("MAX_CATEGORIES_PER_RUN", "0")),
        category_start_id=category_start_id,
        category_end_id=category_end_id,
        discover_categories=os.getenv("DISCOVER_YELLOW_CATEGORIES", "false").lower()
        in {"1", "true", "yes"},
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
