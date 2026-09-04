# Malta Yellow Pages Collector

This project collects public business listings from Yellow Pages Malta and saves
them in PostgreSQL. Categories are discovered once, reviewed in the database,
then approved categories drive later business collection.

## 1. Create database

Create an Aiven PostgreSQL service and copy its connection URI. Keep
`sslmode=require` in the URI. Do not commit credentials to Git.

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL`. The remaining values configure the Yellow base
URL, timeout, delay between requests, page limit, categories per run, category
discovery, and logging.

## 3. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

These commands create an isolated environment, activate it, and install the
PostgreSQL, HTTP, HTML parsing, and `.env` libraries.

## 4. Discover categories once

```bash
python category_review.py
```

This creates tables, reads Yellow's `/all-categories/` page, and inserts new
category candidates with `is_enabled=false`. It does not fetch businesses.

Review PostgreSQL and enable only the categories you want:

```sql
UPDATE categories SET is_enabled = TRUE
WHERE name IN ('Restaurants', 'Cafes');
```

## 5. Start scraping

```bash
python -m src.main
```

The command loads enabled, unfinished categories from PostgreSQL into memory,
fetches each category page, batch-checks existing businesses, opens only missing
detail pages, and writes PostgreSQL records. `MAX_CATEGORIES_PER_RUN=0` loads
all pending categories.

Stop locally with `Ctrl+C`. Failed categories remain pending and can be retried
by running the command again. Completed categories and duplicate source IDs are
skipped safely.

## 6. Check progress

Run in the Aiven SQL console:

```sql
SELECT id,name,is_enabled,is_completed FROM categories ORDER BY id;
SELECT source,COUNT(*) FROM businesses GROUP BY source;
SELECT name FROM categories WHERE is_enabled AND NOT is_completed;
```

## 7. Refresh data

```sql
UPDATE categories SET is_completed=FALSE,completed_at=NULL
WHERE name='Restaurants';
```

Remove the `WHERE` clause to refresh all categories. Existing listings are updated
using their stable source ID instead of inserted twice.

## 8. Debug

```bash
LOG_LEVEL=DEBUG python -m src.main
```

This logs category progress, page processing, result counts, HTTP errors, and
stack traces. Never print `.env` or API/database credentials.

## 9. GitHub Actions

Add `DATABASE_URL` as an Actions secret. Optional Actions variables are
`YELLOW_BASE_URL` and `MAX_CATEGORIES_PER_RUN`. The workflow only scrapes
database categories with `is_enabled=true` and `is_completed=false`; it does not
discover categories. Run category discovery once, review the database, then run
the workflow manually. Its schedule runs every six hours.

See `TECHNICAL_GUIDE.md` for module responsibilities, field mapping, and provider
replacement details.
