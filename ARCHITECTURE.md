# Source-Independent Architecture

This project is a reusable business-data ingestion pipeline. Google Maps is only
one possible source. A new source should implement the provider interface and
return the same normalized record shape; database and orchestration remain unchanged.

## System flow
```text
Scheduler / manual run
        |
        v
Runner -> pending source categories -> Source Adapter
                                      |
                                      v
                              normalized records
                                      |
                                      v
                              Repository / upserts
                                      |
                                      v
                                  PostgreSQL
```
The runner applies the schema, loads categories, selects pending work, calls one
source adapter, saves records, and marks the source category complete only after
the whole category transaction succeeds. A failed transaction leaves work pending.

## Main modules
`config.py` reads environment variables and validates credentials.
`source_provider.py` is the only source-specific module. It handles authentication,
pagination, rate limits, retries, provider errors, and converts responses into
normalized records.

`category_service.py` owns category definitions, pending work, completion state,
and optional discovery of new source categories.

`repository.py` owns PostgreSQL inserts, updates, constraints, and transactions.
`main.py` coordinates the modules. It should not contain provider-specific field
names or scraping logic.

`schema.sql` defines durable data. The workflow only schedules `main.py`; it does
not contain business logic.

## Provider contract
Every adapter should expose a method similar to:

```python
fetch(category_query: str) -> list[dict]
```
Each returned record should contain:
```text
external_id, name, description, rating, website_url,
address, latitude, longitude, is_head_office,
contacts, working_hours, raw_data
```
The adapter owns mapping provider names such as `place_id`, `business_id`, or
`record_id` to `external_id`. The repository must never depend on those names.

## Recommended generic schema
`sources` identifies providers such as `google_maps`, `osm`, `yellow_pages`, or
an internal CRM. `source_categories` stores a provider-specific query and tracks
completion independently for each source.

```sql
CREATE TABLE sources (
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE categories (
  id BIGSERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  slug TEXT UNIQUE NOT NULL
);

CREATE TABLE source_categories (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES sources(id),
  category_id BIGINT REFERENCES categories(id),
  query TEXT NOT NULL,
  is_completed BOOLEAN NOT NULL DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  UNIQUE (source_id, category_id, query)
);

CREATE TABLE businesses (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE business_sources (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
  source_id BIGINT REFERENCES sources(id),
  external_id TEXT NOT NULL,
  rating NUMERIC(3,2),
  website_url TEXT,
  is_detail_completed BOOLEAN NOT NULL DEFAULT FALSE,
  raw_data JSONB NOT NULL DEFAULT '{}',
  UNIQUE (source_id, external_id)
);

CREATE TABLE business_categories (
  business_source_id BIGINT REFERENCES business_sources(id) ON DELETE CASCADE,
  category_id BIGINT REFERENCES categories(id),
  PRIMARY KEY (business_source_id, category_id)
);

CREATE TABLE locations (
  id BIGSERIAL PRIMARY KEY,
  business_source_id BIGINT REFERENCES business_sources(id) ON DELETE CASCADE,
  address TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  is_head_office BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE contacts (
  id BIGSERIAL PRIMARY KEY,
  business_source_id BIGINT REFERENCES business_sources(id) ON DELETE CASCADE,
  contact_type TEXT NOT NULL,
  contact_value TEXT NOT NULL,
  UNIQUE (business_source_id, contact_type, contact_value)
);

CREATE TABLE business_timings (
  id BIGSERIAL PRIMARY KEY,
  business_source_id BIGINT REFERENCES business_sources(id) ON DELETE CASCADE,
  day_of_week TEXT NOT NULL,
  hours_text TEXT NOT NULL,
  UNIQUE (business_source_id, day_of_week)
);
```
## Deduplication and identity
Never use the business name as the primary identity. First deduplicate by
`(source_id, external_id)`. Optional canonical merging across sources can compare
normalized website domain, phone, address, and coordinates. Keep the original
source rows even after merging so provenance is not lost.

## Adding another source
1. Create `src/<source>_provider.py` implementing `fetch`.
2. Map its response to the provider contract.
3. Add credentials and limits to `.env.example`.
4. Register the source and its queries in `source_categories`.
5. Select the provider in configuration; do not change repository SQL.
6. Test pagination, empty results, retries, malformed records, and duplicate runs.
