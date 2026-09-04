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

1. Category review creates the schema and imports Yellow category candidates.
2. The user reviews PostgreSQL and sets selected rows to `is_enabled=true`.
3. The runner loads enabled and unfinished categories into memory.
4. The provider requests `/<category>/malta/`; later pages use
   `/<category>/malta/pageno=<page>`.
5. Only links matching `/<business>/<category>/` are treated as businesses.
6. Listing URLs are batch-checked before detail requests.
7. Only new or incomplete businesses have detail pages requested.
8. JSON-LD is preferred; HTML title/meta and links provide fallbacks.
9. Records and the next-page checkpoint are committed per page.
10. The category is completed only after all pages finish.

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

Security-verification HTML raises an error so the page remains pending for a
later retry; the collector does not attempt to bypass the verification.

## Transactions, cache, and retries

The selected category batch is held in memory. Each listing page uses one batch
database lookup for completed businesses, then commits records and the next-page
checkpoint. Any exception rolls back the current page, logs a stack trace, and
leaves the category pending at its last committed page.

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

Create `src/<source>_provider.py` with `page_links(query, page)` and `detail(url)`, add its settings
to `config.py` and `.env.example`, and select it in `main.py`. Do not change the
repository or deduplication rules unless the new source has a different identity.

References: [Yellow Pages Malta](https://www.yellow.com.mt/),
[all categories](https://www.yellow.com.mt/all-categories/), and
[Yellow business information](https://www.business.yellow.com.mt/).
