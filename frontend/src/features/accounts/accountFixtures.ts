import {
  type Member,
  type UniverseAccess,
  type Workspace,
} from '@/features/workspaces/types'
import { type Account, type AuthState, type SessionView } from './types'

const AT = '2026-11-25T10:00:00Z'

export function account(overrides: Partial<Account> = {}): Account {
  return {
    id: 1,
    username: 'mara',
    email: 'mara@example.org',
    display_name: 'Mara Ilven',
    server_role: 'owner',
    status: 'active',
    must_change_password: false,
    avatar_tone: 'gold',
    created_at: AT,
    last_sign_in_at: AT,
    locked_until: null,
    password_changed_at: null,
    ...overrides,
  }
}

export function signedIn(overrides: Partial<Account> = {}): AuthState {
  const who = account(overrides)
  return {
    setup_required: false,
    account: who,
    must_change_password: who.must_change_password,
    password_min_length: 10,
  }
}

export const SIGNED_OUT: AuthState = {
  setup_required: false,
  account: null,
  must_change_password: false,
  password_min_length: 10,
}

export const SETUP: AuthState = {
  setup_required: true,
  account: null,
  must_change_password: false,
  password_min_length: 10,
}

export function session(overrides: Partial<SessionView> = {}): SessionView {
  return {
    id: 1,
    created_at: AT,
    last_used_at: AT,
    expires_at: '2027-01-24T10:00:00Z',
    user_agent: 'Mozilla/5.0 (Macintosh; Mac OS X 14_0) Safari/605.1.15',
    address: '127.0.0.1',
    current: true,
    ...overrides,
  }
}

export function workspace(overrides: Partial<Workspace> = {}): Workspace {
  return {
    id: 7,
    name: 'Studio Team',
    kind: 'team',
    role: 'admin',
    member_count: 2,
    universe_count: 1,
    created_at: AT,
    ...overrides,
  }
}

export function member(
  overrides: Partial<Account> = {},
  role: Member['role'] = 'viewer'
): Member {
  return {
    account: account({ server_role: 'member', ...overrides }),
    role,
    added_at: AT,
    universe_count: 1,
  }
}

export function access(
  overrides: Partial<UniverseAccess> = {}
): UniverseAccess {
  return {
    universe_id: 'aaaaaaaaaaaa',
    universe_name: 'Haluvra',
    workspace_id: 7,
    people: [
      {
        account: account({
          id: 2,
          username: 'oren',
          display_name: 'Oren Vell',
          email: 'oren@example.org',
          server_role: 'member',
          avatar_tone: 'info',
        }),
        workspace_role: 'viewer',
        role: 'viewer',
        overridden: false,
      },
    ],
    permissions: [
      {
        permission: 'view',
        label: 'Read the universe',
        meaning: 'Every screen, chronicle, Atlas and the book on screen.',
        editor_default: true,
        viewer_default: true,
        editor: true,
        viewer: true,
      },
      {
        permission: 'edit_world',
        label: 'Shape the world',
        meaning:
          'Every god lever that creates, edits, holds or deletes a thing.',
        editor_default: true,
        viewer_default: false,
        editor: true,
        viewer: false,
      },
    ],
    canon_approval: false,
    ...overrides,
  }
}
