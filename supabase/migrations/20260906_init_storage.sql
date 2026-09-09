-- =============================================================================
-- FleetMind Phase 3 — Storage Bucket & RLS Policies
-- =============================================================================
-- Run this in the Supabase SQL editor or via the Supabase CLI:
--   supabase db push
--
-- Bucket created:
--   artifacts — Private storage for strategy briefs and generated documents.
--
-- RLS enforcement strategy:
--   All objects in the 'artifacts' bucket are stored with paths:
--     artifacts/{workspace_id}/{filename}
--   RLS policies extract the first folder segment ((storage.foldername(name))[1])
--   and verify the authenticated user (auth.uid()) is a member of that workspace.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 1. CREATE BUCKET
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'artifacts',
    'artifacts',
    false,  -- Private bucket; requires signed URLs or RLS-checked requests
    10485760, -- 10MB limit per file
    ARRAY['text/markdown', 'text/plain', 'application/json', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;


-- ---------------------------------------------------------------------------
-- 2. ENABLE ROW LEVEL SECURITY ON STORAGE.OBJECTS
-- ---------------------------------------------------------------------------
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;


-- ---------------------------------------------------------------------------
-- 3. RLS POLICIES FOR ARTIFACTS BUCKET
-- ---------------------------------------------------------------------------

-- Policy: INSERT objects if the user belongs to the target workspace_id
CREATE POLICY "artifacts_insert_workspace_member"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'artifacts'
    AND (
        (storage.foldername(name))[1]::uuid IN (
            SELECT workspace_id
            FROM workspace_users
            WHERE user_id = (SELECT auth.uid())
        )
    )
);

-- Policy: SELECT objects if the user belongs to the workspace_id
CREATE POLICY "artifacts_select_workspace_member"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'artifacts'
    AND (
        (storage.foldername(name))[1]::uuid IN (
            SELECT workspace_id
            FROM workspace_users
            WHERE user_id = (SELECT auth.uid())
        )
    )
);

-- Policy: UPDATE objects if the user belongs to the workspace_id
CREATE POLICY "artifacts_update_workspace_member"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
    bucket_id = 'artifacts'
    AND (
        (storage.foldername(name))[1]::uuid IN (
            SELECT workspace_id
            FROM workspace_users
            WHERE user_id = (SELECT auth.uid())
        )
    )
)
WITH CHECK (
    bucket_id = 'artifacts'
    AND (
        (storage.foldername(name))[1]::uuid IN (
            SELECT workspace_id
            FROM workspace_users
            WHERE user_id = (SELECT auth.uid())
        )
    )
);

-- Policy: DELETE objects if the user belongs to the workspace_id
CREATE POLICY "artifacts_delete_workspace_member"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'artifacts'
    AND (
        (storage.foldername(name))[1]::uuid IN (
            SELECT workspace_id
            FROM workspace_users
            WHERE user_id = (SELECT auth.uid())
        )
    )
);
