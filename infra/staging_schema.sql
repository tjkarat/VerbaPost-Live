-- ============================================================
-- VerbaPost STAGING database schema
-- Run this in the Supabase SQL Editor of the STAGING project.
-- Derived from database.py models + known production drift
-- (created_by on user_profiles, tier on letter_drafts).
-- Idempotent: safe to run more than once.
-- ============================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id              serial PRIMARY KEY,
    email           text UNIQUE NOT NULL,
    full_name       text,
    parent_name     text,
    parent_phone    text,
    role            text,
    created_at      timestamp DEFAULT now(),
    address_line1   text,
    address_city    text,
    address_state   text,
    address_zip     text,
    country         text,
    timezone        text,
    advisor_firm    text,
    credits         integer DEFAULT 0,
    created_by      text              -- drift column used by B2B supabase-client code
);

CREATE TABLE IF NOT EXISTS advisors (
    id                   serial PRIMARY KEY,
    email                text UNIQUE NOT NULL,
    firm_name            text,
    full_name            text,
    stripe_customer_id   text,
    subscription_status  text DEFAULT 'active',
    credits              integer DEFAULT 0,
    created_at           timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clients (
    id             serial PRIMARY KEY,
    advisor_email  text,
    name           text NOT NULL,
    phone          text,
    email          text,
    address_json   text,
    status         text DEFAULT 'Active',
    heir_name      text,
    parent_email   text,
    created_at     timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id                 serial PRIMARY KEY,
    advisor_email      text NOT NULL,
    client_id          integer REFERENCES clients(id),
    project_type       text DEFAULT 'Retainer_Letter',
    status             text DEFAULT 'Draft',
    content            text,
    audio_ref          text,
    tracking_number    text,            -- holds the audio URL for voice projects
    heir_name          text,
    heir_address_json  text,
    strategic_prompt   text,
    call_sid           text,
    scheduled_time     timestamp,
    audio_released     boolean DEFAULT false,
    created_at         timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS letter_drafts (
    id               serial PRIMARY KEY,
    user_email       text,
    content          text,
    status           text,
    call_sid         text,
    created_at       timestamp DEFAULT now(),
    tracking_number  text,
    tier             text DEFAULT 'Heirloom'   -- drift column from prod
);

CREATE TABLE IF NOT EXISTS audit_events (
    id                 serial PRIMARY KEY,
    timestamp          timestamp DEFAULT now(),
    user_email         text,
    event_type         text,
    details            text,
    description        text,
    stripe_session_id  text
);

CREATE TABLE IF NOT EXISTS payment_fulfillments (
    stripe_session_id  text PRIMARY KEY,
    product_name       text,
    user_email         text,
    created_at         timestamp DEFAULT now()
);

-- Helpful indexes for webhook lookups
CREATE INDEX IF NOT EXISTS idx_projects_call_sid ON projects(call_sid);
CREATE INDEX IF NOT EXISTS idx_letter_drafts_call_sid ON letter_drafts(call_sid);
CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);

-- ============================================================
-- MANUAL STEP (dashboard, not SQL): create a PRIVATE storage
-- bucket named exactly:  heirloom-audio
-- (Storage -> New bucket -> name: heirloom-audio -> Private)
-- ============================================================
