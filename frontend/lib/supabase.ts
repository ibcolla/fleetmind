/**
 * FleetMind — Supabase Client Singleton
 *
 * This module exports a single Supabase client instance for the frontend.
 * It uses the PUBLIC anon key — this is safe to expose to the browser.
 *
 * The anon key has limited permissions defined by your Supabase RLS policies.
 * It is NOT the service-role key.
 *
 * Required environment variables (frontend/.env.local):
 *   NEXT_PUBLIC_SUPABASE_URL      — Your Supabase project URL
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY — Your project's public anon key
 *
 * Both values can be found at:
 *   Supabase Dashboard → Project Settings → API
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  // In development without Supabase configured, warn clearly rather than crash.
  // The auth gate in the UI will handle the unconfigured state gracefully.
  console.warn(
    '[FleetMind] Supabase environment variables are not set.\n' +
    'Create frontend/.env.local with:\n' +
    '  NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co\n' +
    '  NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key\n' +
    'Authentication will not function until these are configured.'
  )
}

const supabase: SupabaseClient = createClient(
  supabaseUrl ?? 'http://localhost:54321',  // placeholder — auth will fail gracefully
  supabaseAnonKey ?? 'placeholder-key',
)

export default supabase
