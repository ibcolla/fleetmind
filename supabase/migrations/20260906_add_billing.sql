-- =============================================================================
-- FleetMind Phase 4 — Billing Schema & Usage Limits Migration
-- =============================================================================
-- Run this in the Supabase SQL editor or via the Supabase CLI:
--   supabase db push
--
-- Columns added to 'workspaces':
--   stripe_customer_id     — Stripe Customer object ID (e.g. 'cus_123456')
--   stripe_subscription_id — Stripe Subscription object ID (e.g. 'sub_123456')
--   subscription_status    — Subscription tier ('free', 'active', 'canceled', 'past_due')
--   agent_runs_count       — Total agent execution runs completed by this workspace
-- =============================================================================

ALTER TABLE workspaces
    ADD COLUMN IF NOT EXISTS stripe_customer_id     TEXT UNIQUE DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT UNIQUE DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS subscription_status    TEXT NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS agent_runs_count       INTEGER NOT NULL DEFAULT 0;

-- Indexes for fast Stripe webhook lookups
CREATE INDEX IF NOT EXISTS idx_workspaces_stripe_customer_id     ON workspaces(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_stripe_subscription_id ON workspaces(stripe_subscription_id);
