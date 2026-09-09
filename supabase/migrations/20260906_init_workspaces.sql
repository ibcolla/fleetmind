-- =============================================================================
-- FleetMind Phase 2 — Workspace & Tenant Schema
-- =============================================================================
-- Run this in the Supabase SQL editor or via the Supabase CLI:
--   supabase db push
--
-- Tables created:
--   workspaces        — one per founder (auto-provisioned on first login)
--   workspace_users   — user ↔ workspace membership (supports future teams)
--   signals           — market signals discovered by the agent
--   actions           — actions taken by the agent (Composio integrations)
--
-- RLS enforcement strategy:
--   All data tables are scoped to workspace_id.
--   RLS policies check membership via workspace_users JOIN, using auth.uid()
--   for the currently-authenticated Supabase user.
--   The backend service-role client bypasses RLS but always scopes queries
--   explicitly to the verified workspace_id (defence-in-depth).
-- =============================================================================


-- ---------------------------------------------------------------------------
-- EXTENSION: ensure uuid generation is available
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ===========================================================================
-- TABLE: workspaces
-- ===========================================================================
CREATE TABLE IF NOT EXISTS workspaces (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL DEFAULT 'Personal Workspace',
    owner_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookup by owner
CREATE INDEX IF NOT EXISTS idx_workspaces_owner_id ON workspaces(owner_id);

-- Enable RLS
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- Policy: users can see their own workspaces
CREATE POLICY "workspace_select_own"
ON workspaces
FOR SELECT
TO authenticated
USING (owner_id = (SELECT auth.uid()));

-- Policy: users can update their own workspaces (rename, etc.)
CREATE POLICY "workspace_update_own"
ON workspaces
FOR UPDATE
TO authenticated
USING (owner_id = (SELECT auth.uid()))
WITH CHECK (owner_id = (SELECT auth.uid()));

-- Policy: INSERT is restricted to service role (backend auto-provisions)
-- No authenticated INSERT policy = regular users cannot create workspaces directly.
-- The backend service-role client handles provisioning.


-- ===========================================================================
-- TABLE: workspace_users
-- Junction table: maps auth.users <-> workspaces with roles.
-- Enables future team/invite functionality.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS workspace_users (
    workspace_id    UUID    NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role            TEXT    NOT NULL DEFAULT 'owner'
                            CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- Indexes for fast policy lookups (critical for RLS performance)
CREATE INDEX IF NOT EXISTS idx_workspace_users_user_id      ON workspace_users(user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_users_workspace_id ON workspace_users(workspace_id);

-- Enable RLS
ALTER TABLE workspace_users ENABLE ROW LEVEL SECURITY;

-- Policy: users can see their own memberships
CREATE POLICY "workspace_users_select_own"
ON workspace_users
FOR SELECT
TO authenticated
USING (user_id = (SELECT auth.uid()));

-- Policy: INSERT/UPDATE/DELETE restricted to service role only
-- (backend controls membership, prevents self-invitation to other workspaces)


-- ===========================================================================
-- TABLE: signals
-- Market signals discovered by the FleetMind agent.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS signals (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    content         TEXT        NOT NULL DEFAULT '',
    title           TEXT        NOT NULL DEFAULT '',
    url             TEXT        NOT NULL DEFAULT '',
    snippet         TEXT        NOT NULL DEFAULT '',
    source          TEXT        NOT NULL DEFAULT '',
    signal_type     TEXT        NOT NULL DEFAULT 'market'
                                CHECK (signal_type IN ('competitor', 'market', 'tech', 'mention')),
    importance      TEXT        NOT NULL DEFAULT 'medium'
                                CHECK (importance IN ('high', 'medium', 'low')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_signals_workspace_id   ON signals(workspace_id);
CREATE INDEX IF NOT EXISTS idx_signals_created_at     ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_discovered_at  ON signals(discovered_at DESC);

-- Enable RLS
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;

-- Policy: users can SELECT signals only in workspaces they belong to
CREATE POLICY "signals_select_workspace_member"
ON signals
FOR SELECT
TO authenticated
USING (
    workspace_id IN (
        SELECT workspace_id
        FROM workspace_users
        WHERE user_id = (SELECT auth.uid())
    )
);

-- Policy: users can INSERT signals into their own workspaces
CREATE POLICY "signals_insert_workspace_member"
ON signals
FOR INSERT
TO authenticated
WITH CHECK (
    workspace_id IN (
        SELECT workspace_id
        FROM workspace_users
        WHERE user_id = (SELECT auth.uid())
    )
);

-- Policy: users can DELETE signals from their own workspaces
CREATE POLICY "signals_delete_workspace_member"
ON signals
FOR DELETE
TO authenticated
USING (
    workspace_id IN (
        SELECT workspace_id
        FROM workspace_users
        WHERE user_id = (SELECT auth.uid())
    )
);


-- ===========================================================================
-- TABLE: actions
-- Actions taken by the FleetMind agent (Composio integrations).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS actions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID        REFERENCES auth.users(id) ON DELETE CASCADE,
    content         TEXT        NOT NULL DEFAULT '',
    action_type     TEXT        NOT NULL DEFAULT 'unknown',
    description     TEXT        NOT NULL DEFAULT '',
    tool            TEXT        NOT NULL DEFAULT '',
    status          TEXT        NOT NULL DEFAULT 'completed'
                                CHECK (status IN ('completed', 'failed', 'pending')),
    result          JSONB       DEFAULT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_actions_workspace_id ON actions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_actions_user_id      ON actions(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_executed_at  ON actions(executed_at DESC);

-- Enable RLS
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;

-- Policy: users can SELECT actions in their workspaces
CREATE POLICY "actions_select_workspace_member"
ON actions
FOR SELECT
TO authenticated
USING (
    workspace_id IN (
        SELECT workspace_id
        FROM workspace_users
        WHERE user_id = (SELECT auth.uid())
    )
);

-- Policy: users can INSERT actions into their workspaces
CREATE POLICY "actions_insert_workspace_member"
ON actions
FOR INSERT
TO authenticated
WITH CHECK (
    workspace_id IN (
        SELECT workspace_id
        FROM workspace_users
        WHERE user_id = (SELECT auth.uid())
    )
);


-- ===========================================================================
-- GRANT: ensure the anon and authenticated roles have table access
-- ===========================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON workspaces      TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON signals         TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON actions         TO authenticated;

GRANT SELECT ON workspaces      TO anon;
GRANT SELECT ON workspace_users TO anon;
GRANT SELECT ON signals         TO anon;
GRANT SELECT ON actions         TO anon;
