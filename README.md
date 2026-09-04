# Malta Yellow Pages Collector

This project collects public business listings from Yellow Pages Malta and saves
them in PostgreSQL. It uses a review-first workflow: discover categories, approve
keywords, then collect businesses.

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

## 4. Discover and review categories

```bash
python category_review.py
```

This creates tables, loads candidates from `categories.csv`, optionally reads
Yellow's `/all-categories/` page, and prints category IDs and keywords. It does
not fetch business detail pages.

Edit `categories.csv` and set `enabled=true` only for categories you want:

```csv
name,search_query,enabled
Restaurants,restaurants,true
Cafes,cafes,false
```

Unwanted rows can remain `false` or be removed. New discovered categories are
disabled automatically and require review.

## 5. Start scraping

```bash
python -m src.main
```

The command applies the schema, synchronizes categories, fetches each approved
category page, follows pagination, opens each business detail page, normalizes
the fields, and writes PostgreSQL records. It processes one category by default;
configure `MAX_CATEGORIES_PER_RUN` to change that.

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
`YELLOW_BASE_URL`, `MAX_CATEGORIES_PER_RUN`, and `DISCOVER_YELLOW_CATEGORIES`.
The workflow first discovers categories, then scrapes only categories whose
`enabled` value is `true` in the committed `categories.csv`. Run the workflow
manually first; its schedule runs every six hours. Failed jobs retain logs for
debugging. Review Yellow's terms and robots guidance before automated collection.

See `TECHNICAL_GUIDE.md` for module responsibilities, field mapping, and provider
replacement details.
