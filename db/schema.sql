-- =============================================================================
-- Wayfind Core Persistence Schema
-- PostgreSQL 16 + PostGIS Extension
-- =============================================================================

-- Enable PostGIS for geospatial coordinates and distance bounding
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- -----------------------------------------------------------------------------
-- 1. Guardians Table
-- Stores guardian profiles with masked phone for public safety and encrypted PII
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guardians (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    phone_masked VARCHAR(64) NOT NULL,
    phone_encrypted BYTEA,
    national_id_hash VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 2. Child Status Enum
-- -----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE child_status_enum AS ENUM ('REGISTERED_SAFE', 'MISSING', 'FOUND');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 3. Children Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS children (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guardian_id UUID REFERENCES guardians(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    dob DATE,
    estimated_age INT,
    gender VARCHAR(32),
    status child_status_enum NOT NULL DEFAULT 'REGISTERED_SAFE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_children_status ON children(status);
CREATE INDEX IF NOT EXISTS idx_children_guardian ON children(guardian_id);

-- -----------------------------------------------------------------------------
-- 4. Physical Attributes Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS physical_attributes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    child_id UUID UNIQUE REFERENCES children(id) ON DELETE CASCADE,
    height_cm NUMERIC(5, 2),
    hair_color VARCHAR(64),
    eye_color VARCHAR(64),
    skin_tone VARCHAR(64),
    identifying_features TEXT[],
    current_clothing TEXT,
    medical_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 5. Baseline Photos (For REGISTERED_SAFE children)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS baseline_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    child_id UUID REFERENCES children(id) ON DELETE CASCADE,
    s3_key VARCHAR(512) NOT NULL,
    embedding_vector BYTEA,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 6. SOS Beacons (When a registered or new child is reported MISSING)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sos_beacons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    child_id UUID REFERENCES children(id) ON DELETE CASCADE,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_missing TIMESTAMPTZ NOT NULL,
    last_seen_location_name VARCHAR(255),
    last_seen_geom GEOGRAPHY(POINT, 4326),
    status VARCHAR(64) NOT NULL DEFAULT 'ACTIVE'
);

CREATE INDEX IF NOT EXISTS idx_sos_beacons_geom ON sos_beacons USING GIST(last_seen_geom);
CREATE INDEX IF NOT EXISTS idx_sos_date_missing ON sos_beacons(date_missing);

-- -----------------------------------------------------------------------------
-- 7. Found Child Cases (Intake cases filed by citizen finders or shelters)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS found_child_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_reference VARCHAR(64) UNIQUE NOT NULL,
    found_location_name VARCHAR(255),
    found_geom GEOGRAPHY(POINT, 4326),
    found_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(64) NOT NULL DEFAULT 'UNDER_REVIEW',
    reporter_name VARCHAR(255),
    reporter_contact_masked VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_found_cases_ref ON found_child_cases(case_reference);
CREATE INDEX IF NOT EXISTS idx_found_cases_geom ON found_child_cases USING GIST(found_geom);
CREATE INDEX IF NOT EXISTS idx_found_cases_time ON found_child_cases(found_at);

-- -----------------------------------------------------------------------------
-- 8. Intake Photos (For found children)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS intake_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES found_child_cases(id) ON DELETE CASCADE,
    s3_key VARCHAR(512) NOT NULL,
    embedding_vector BYTEA,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 9. Review Queue (For staff verification before Phase 2 disclosure)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_reference VARCHAR(64) NOT NULL,
    candidate_case_id VARCHAR(64),
    confidence_tier VARCHAR(32) NOT NULL,
    composite_score NUMERIC(4, 3) NOT NULL,
    metadata_score NUMERIC(4, 3),
    image_score NUMERIC(4, 3),
    geo_score NUMERIC(4, 3),
    evidence_json JSONB,
    staff_id UUID,
    decision VARCHAR(32) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_review_decision ON review_queue(decision);

-- -----------------------------------------------------------------------------
-- 10. Audit Log (Immutable append-only log)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    actor_id VARCHAR(128),
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
