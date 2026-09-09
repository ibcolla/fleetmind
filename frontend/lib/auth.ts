/**
 * FleetMind — Authentication Helpers
 *
 * Provides typed wrappers around Supabase auth operations and a helper
 * that produces the Authorization header required by the FleetMind backend.
 *
 * The backend requires:
 *   Authorization: Bearer <supabase-access-token>
 *
 * The access token is a short-lived JWT issued by Supabase Auth.
 * It is automatically refreshed by the Supabase client.
 * It must NEVER be placed in URL query parameters.
 */

import supabase from './supabase'
import type { Session, User, AuthError } from '@supabase/supabase-js'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface AuthHeaders {
  Authorization: string
  'Content-Type': string
  [key: string]: string  // index signature required for HeadersInit compatibility
}

// ─────────────────────────────────────────────────────────────────────────────
// Session / Token
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Returns the current Supabase session, or null if the user is not signed in.
 */
export async function getSession(): Promise<Session | null> {
  const { data } = await supabase.auth.getSession()
  return data.session
}

/**
 * Returns Authorization headers for the FleetMind backend API.
 *
 * The token is placed in the Authorization header — NEVER in a URL parameter.
 *
 * @throws Error if the user is not authenticated.
 */
export async function getAuthHeaders(): Promise<AuthHeaders> {
  const session = await getSession()
  if (!session?.access_token) {
    throw new Error('Not authenticated. Please sign in.')
  }
  return {
    Authorization: `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  }
}

/**
 * Returns the current authenticated user, or null.
 */
export async function getCurrentUser(): Promise<User | null> {
  const session = await getSession()
  return session?.user ?? null
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth operations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Sign in with email and password.
 */
export async function signIn(
  email: string,
  password: string
): Promise<{ user: User | null; error: AuthError | null }> {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  return { user: data.user, error }
}

/**
 * Sign up a new user with email and password.
 */
export async function signUp(
  email: string,
  password: string
): Promise<{ user: User | null; error: AuthError | null }> {
  const { data, error } = await supabase.auth.signUp({ email, password })
  return { user: data.user, error }
}

/**
 * Sign the current user out.
 */
export async function signOut(): Promise<void> {
  await supabase.auth.signOut()
}

/**
 * Subscribe to auth state changes.
 * Returns the unsubscribe function.
 */
export function onAuthStateChange(
  callback: (user: User | null) => void
): () => void {
  const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session?.user ?? null)
  })
  return () => subscription.unsubscribe()
}
