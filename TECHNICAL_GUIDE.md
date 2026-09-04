# Technical Guide

## Architecture

```text
GitHub schedule/manual run
          |
          v
      src.main
          |
          +--> category_service.py --> category review/state
          |
          +--> yellow_pages_provider.py --> Yellow public pages
          |
          +--> repository.py --> PostgreSQL upserts
```

`config.py` validates environment settings. `database.py` applies the schema.
`category_review.py` performs human approval. `main.py` coordinates work but has
no HTML selectors. `yellow_pages_provider.py` owns HTTP, pagination, parsing, and
source-specific field mapping. `repository.py` owns persistence only.

## Execution sequence

1. Category review creates the schema and synchronizes `categories.csv`.
2. Yellow's all-categories page can add new disabled candidates.
3. The user sets selected CSV rows to `enabled=true`.
4. The runner selects enabled and unfinished categories.
5. The provider requests `/<category>/malta/` and its page parameters.
6. Listing links are collected and each detail page is requested.
7. JSON-LD is preferred; HTML title/meta and links provide fallbacks.
8. Normalized records are sent to the repository.
9. The category is completed only after all records commit successfully.

## Normalized provider record

The repository expects `source_id`, `name`, `description`, `rating`, `site`,
`full_address`, `latitude`, `longitude`, `is_head_office`, `contacts`,
`working_hours`, and `raw_data`. A new source adapter should return the same keys.
It may use any source-specific ID internally, but must provide a stable
`source_id` for deduplication.

## Pagination and safety

The provider follows pages until there are no new detail links, fewer than the
expected page size, or `MAX_PAGES_PER_CATEGORY` is reached. Requests use a clear
User-Agent, timeout, and configurable delay. It does not use CAPTCHA bypasses,
proxy rotation, or browser stealth techniques. Respect Yellow's terms, robots
rules, rate limits, and any permission requirement.

## Transactions and retries

Each category is one PostgreSQL transaction. Any HTTP, parsing, or SQL exception
causes rollback, logs a stack trace, and leaves the category pending. GitHub gets
a failed job status, so the next scheduled run can retry it.

## Deduplication and provenance

The business identity is `(source, source_id)`. This implementation derives the
Yellow source ID from the stable listing URL. `ON CONFLICT` updates the listing.
`business_categories` preserves multiple category memberships. `raw_data` keeps
the normalized source object for troubleshooting and future mapping.

## Field mapping

JSON-LD `name`, `description`, `aggregateRating`, `address`, `geo`, `telephone`,
`email`, `url`, `sameAs`, and `openingHoursSpecification` map to the requested
business, location, contact, website, rating, and timing tables. Yellow does not
reliably identify head offices, so the flag remains false unless the source later
provides an explicit signal.

## Adding another source

Create `src/<source>_provider.py` with `fetch(query) -> list[dict]`, add its settings
to `config.py` and `.env.example`, and select it in `main.py`. Do not change the
repository or deduplication rules unless the new source has a different identity.

References: [Yellow Pages Malta](https://www.yellow.com.mt/),
[all categories](https://www.yellow.com.mt/all-categories/), and
[Yellow business information](https://www.business.yellow.com.mt/).
