-- Responsible for defining every Saathi table in Azure SQL. Run by data/seed/scripts/load_sql.py; each GO line ends one batch.
-- policies.status is only ACTIVE or CANCELLED: the renewal state (in grace, lapsed) is computed in code from renewal_date.
-- audit_events is append-only by convention: the API never updates or deletes rows, and each row stores the previous row's hash.

IF OBJECT_ID('agents') IS NULL
CREATE TABLE agents (
    agent_id NVARCHAR(16) NOT NULL PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    role NVARCHAR(16) NOT NULL CHECK (role IN ('agent', 'supervisor')),
    products NVARCHAR(200) NOT NULL,  -- JSON array, e.g. ["health","motor"]
    passcode_hash CHAR(64) NOT NULL  -- sha256 of the demo passcode
)
GO

IF OBJECT_ID('customers') IS NULL
CREATE TABLE customers (
    customer_id NVARCHAR(16) NOT NULL PRIMARY KEY,
    agent_id NVARCHAR(16) NOT NULL REFERENCES agents(agent_id),
    name NVARCHAR(100) NOT NULL,
    phone NVARCHAR(32) NOT NULL,
    language NVARCHAR(8) NOT NULL,
    consent BIT NOT NULL,
    consent_updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
)
GO

IF OBJECT_ID('policies') IS NULL
CREATE TABLE policies (
    policy_id NVARCHAR(16) NOT NULL PRIMARY KEY,
    customer_id NVARCHAR(16) NOT NULL REFERENCES customers(customer_id),
    product NVARCHAR(16) NOT NULL,
    tier NVARCHAR(32) NOT NULL,
    annual_premium_inr INT NOT NULL,
    renewal_date DATE NOT NULL,
    status NVARCHAR(16) NOT NULL CHECK (status IN ('ACTIVE', 'CANCELLED'))
)
GO

IF OBJECT_ID('interactions') IS NULL
CREATE TABLE interactions (
    interaction_id NVARCHAR(16) NOT NULL PRIMARY KEY,
    customer_id NVARCHAR(16) NOT NULL REFERENCES customers(customer_id),
    date DATE NOT NULL,
    channel NVARCHAR(16) NOT NULL,
    text NVARCHAR(1000) NOT NULL
)
GO

IF OBJECT_ID('sessions') IS NULL
CREATE TABLE sessions (
    session_id NVARCHAR(36) NOT NULL PRIMARY KEY,
    agent_id NVARCHAR(16) NOT NULL REFERENCES agents(agent_id),
    customer_id NVARCHAR(16) NOT NULL REFERENCES customers(customer_id),
    summary NVARCHAR(MAX) NULL
)
GO

IF OBJECT_ID('turns') IS NULL
CREATE TABLE turns (
    turn_id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    session_id NVARCHAR(36) NOT NULL REFERENCES sessions(session_id),
    role NVARCHAR(16) NOT NULL,
    text NVARCHAR(MAX) NOT NULL,
    citations NVARCHAR(MAX) NULL,  -- JSON array
    ts DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
)
GO

IF OBJECT_ID('drafts') IS NULL
CREATE TABLE drafts (
    draft_id NVARCHAR(36) NOT NULL PRIMARY KEY,
    customer_id NVARCHAR(16) NOT NULL REFERENCES customers(customer_id),
    agent_id NVARCHAR(16) NOT NULL REFERENCES agents(agent_id),
    text NVARCHAR(MAX) NOT NULL,
    citations NVARCHAR(MAX) NULL,  -- JSON array
    status NVARCHAR(16) NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'SENT')),
    approved_by NVARCHAR(16) NULL REFERENCES agents(agent_id),
    ts DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
)
GO

IF OBJECT_ID('audit_events') IS NULL
CREATE TABLE audit_events (
    id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ts DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    actor NVARCHAR(16) NOT NULL,
    type NVARCHAR(32) NOT NULL,
    payload NVARCHAR(MAX) NOT NULL,  -- JSON with IDs only, no raw personal data
    prev_hash CHAR(64) NOT NULL,
    hash CHAR(64) NOT NULL
)
GO

CREATE INDEX ix_customers_agent ON customers(agent_id)
GO
CREATE INDEX ix_interactions_customer ON interactions(customer_id)
GO
CREATE INDEX ix_turns_session ON turns(session_id)
GO
CREATE INDEX ix_drafts_status ON drafts(status)
GO
