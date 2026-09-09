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

-- ============================================================
-- PROSPECT ACQUISITION PATH (advisor-branded free letter)
-- database.py creates these via Base.metadata.create_all on first
-- connection; this block keeps the SQL editor path in sync.
-- ============================================================

CREATE TABLE IF NOT EXISTS advisor_pages (
    id              serial PRIMARY KEY,
    advisor_email   text UNIQUE NOT NULL,
    slug            text UNIQUE NOT NULL,
    display_name    text NOT NULL,
    firm_name       text,
    headline        text,
    intro           text,
    prompt          text,
    photo_data      text,
    photo_mime      text,
    return_line1    text,
    return_city     text,
    return_state    text,
    return_zip      text,
    disclosure      text,
    active          boolean DEFAULT true,
    created_at      timestamp DEFAULT now(),
    updated_at      timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prospect_letters (
    id                  serial PRIMARY KEY,
    advisor_email       text NOT NULL,
    page_id             integer REFERENCES advisor_pages(id),
    prospect_name       text NOT NULL,
    prospect_phone      text NOT NULL,
    recipient_name      text NOT NULL,
    recipient_line1     text NOT NULL,
    recipient_city      text NOT NULL,
    recipient_state     text NOT NULL,
    recipient_zip       text NOT NULL,
    consent_version     text,
    consent_text        text,
    consent_at          timestamp,
    consent_ip          text,
    consent_user_agent  text,
    dnc_status          text,
    dnc_provider        text,
    dnc_checked_at      timestamp,
    call_sid            text,
    call_attempts       integer DEFAULT 0,
    last_call_at        timestamp,
    audio_url           text,
    transcript_raw      text,
    letter_text         text,
    letter_version      text,
    status              text DEFAULT 'consented',
    queued_at           timestamp,
    sent_at             timestamp,
    created_at          timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prospect_credit_ledger (
    id             serial PRIMARY KEY,
    advisor_email  text NOT NULL,
    delta          integer NOT NULL,
    reason         text,
    reference      text,
    created_at     timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dnc_suppressions (
    id          serial PRIMARY KEY,
    phone       text UNIQUE NOT NULL,
    reason      text,
    added_by    text,
    created_at  timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prospect_letters_call_sid ON prospect_letters(call_sid);
CREATE INDEX IF NOT EXISTS idx_prospect_letters_advisor ON prospect_letters(advisor_email, created_at);
CREATE INDEX IF NOT EXISTS idx_prospect_ledger_advisor ON prospect_credit_ledger(advisor_email);

-- ============================================================
-- INVITATION CAMPAIGNS (uploaded mailing list -> PostGrid)
-- ============================================================

ALTER TABLE advisor_pages    ADD COLUMN IF NOT EXISTS invite_body text;
ALTER TABLE prospect_letters ADD COLUMN IF NOT EXISTS invitation_id integer;

CREATE TABLE IF NOT EXISTS prospect_campaigns (
    id             serial PRIMARY KEY,
    advisor_email  text NOT NULL,
    page_id        integer REFERENCES advisor_pages(id),
    name           text,
    status         text DEFAULT 'draft',
    total_rows     integer DEFAULT 0,
    sent_count     integer DEFAULT 0,
    failed_count   integer DEFAULT 0,
    created_at     timestamp DEFAULT now(),
    sent_at        timestamp
);

CREATE TABLE IF NOT EXISTS campaign_invitations (
    id                  serial PRIMARY KEY,
    campaign_id         integer NOT NULL REFERENCES prospect_campaigns(id),
    advisor_email       text NOT NULL,
    token               text UNIQUE NOT NULL,
    full_name           text NOT NULL,
    first_name          text,
    line1               text NOT NULL,
    line2               text,
    city                text NOT NULL,
    state               text NOT NULL,
    zip_code            text NOT NULL,
    status              text DEFAULT 'pending',
    skip_reason         text,
    postgrid_id         text,
    error               text,
    sent_at             timestamp,
    responded_letter_id integer,
    responded_at        timestamp,
    created_at          timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaign_invitations_campaign ON campaign_invitations(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_invitations_advisor ON campaign_invitations(advisor_email, status);
CREATE INDEX IF NOT EXISTS idx_prospect_campaigns_advisor ON prospect_campaigns(advisor_email, created_at);

ALTER TABLE prospect_campaigns   ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_invitations ENABLE ROW LEVEL SECURITY;

-- Mail provider columns are reused as-is: campaign_invitations.postgrid_id
-- holds whichever provider's id came back (PCM orderID, or PostGrid letter id).

-- Advisor-reported sales outcome, added for the campaign dashboard. Nothing
-- writes this automatically; the advisor sets it by hand after they
-- follow up, since whether a call became a client happens entirely off
-- this platform. NULL means "no outcome recorded yet," not "not interested."
ALTER TABLE prospect_letters ADD COLUMN IF NOT EXISTS outcome text;
ALTER TABLE prospect_letters ADD COLUMN IF NOT EXISTS outcome_updated_at timestamp;
