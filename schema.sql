CREATE TABLE IF NOT EXISTS categories (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    search_query TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (search_query)
);

ALTER TABLE categories ADD COLUMN IF NOT EXISTS next_page INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS businesses (
    id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES categories(id),
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    ratings NUMERIC(3, 2),
    is_detail_completed BOOLEAN NOT NULL DEFAULT FALSE,
    website_url TEXT,
    raw_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source, source_id)
);

CREATE TABLE IF NOT EXISTS locations (
    id BIGSERIAL PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_head_office BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (business_id, is_head_office)
);

CREATE TABLE IF NOT EXISTS business_categories (
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (business_id, category_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id BIGSERIAL PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    contact_type TEXT NOT NULL,
    contact_value TEXT NOT NULL,
    UNIQUE (business_id, contact_type, contact_value)
);

CREATE TABLE IF NOT EXISTS business_timings (
    id BIGSERIAL PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    day_of_week TEXT NOT NULL,
    hours_text TEXT NOT NULL,
    UNIQUE (business_id, day_of_week)
);

CREATE INDEX IF NOT EXISTS idx_business_category ON businesses(category_id);
CREATE INDEX IF NOT EXISTS idx_business_detail ON businesses(is_detail_completed);
CREATE INDEX IF NOT EXISTS idx_category_pending ON categories(is_completed);
