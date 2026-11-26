import {
  type ChainEntry,
  type LoginView,
  type ProviderConnection,
  type ProviderKindView,
  type ProvidersView,
  type RoleView,
} from './types'

const TERMS =
  "Using a subscription inside another program may be against the provider's terms."
const TEAM_REASON =
  'A subscription belongs to one person, so it can only be logged in to in a personal workspace.'
const NOW = '2026-11-26T08:00:00+00:00'

function kind(
  overrides: Partial<ProviderKindView> & Pick<ProviderKindView, 'kind'>
): ProviderKindView {
  return {
    label: overrides.kind,
    family: 'api',
    roles: ['world_agents', 'writing', 'conversation'],
    asks_key: true,
    asks_address: false,
    key_page: '',
    terms: null,
    refusal: null,
    ...overrides,
  }
}

export function kinds(personal: boolean): ProviderKindView[] {
  const refusal = personal ? null : TEAM_REASON
  return [
    kind({
      kind: 'claude_subscription',
      label: 'Claude Pro or Max',
      family: 'subscription',
      asks_key: false,
      terms: TERMS,
      refusal,
    }),
    kind({
      kind: 'copilot_subscription',
      label: 'GitHub Copilot',
      family: 'subscription',
      asks_key: false,
      terms: TERMS,
      refusal,
    }),
    kind({
      kind: 'openai',
      label: 'OpenAI',
      roles: ['world_agents', 'writing', 'conversation', 'images'],
      key_page: 'https://platform.openai.com/api-keys',
    }),
    kind({ kind: 'groq', label: 'Groq' }),
    kind({
      kind: 'local_server',
      label: 'Local model server',
      family: 'local',
      asks_address: true,
    }),
    kind({
      kind: 'image_worker',
      label: 'Local image worker',
      family: 'local',
      roles: ['images'],
      asks_key: false,
      asks_address: true,
    }),
  ]
}

export function connection(
  overrides: Partial<ProviderConnection> & Pick<ProviderConnection, 'id'>
): ProviderConnection {
  return {
    kind: 'openai',
    label: 'Studio key',
    secret_hint: 'cdef',
    base_url: '',
    logged_in_at: null,
    created_at: NOW,
    unusable: null,
    from_server: false,
    ...overrides,
  }
}

export function entry(
  overrides: Partial<ChainEntry> & Pick<ChainEntry, 'id' | 'connection_id'>
): ChainEntry {
  return {
    model: 'fast',
    tools_work: null,
    sees_images: null,
    checked_at: null,
    check_note: '',
    ...overrides,
  }
}

function role(
  name: RoleView['role'],
  label: string,
  entries: ChainEntry[] = [],
  server: ChainEntry[] = []
): RoleView {
  return {
    role: name,
    label,
    description: `What ${label.toLowerCase()} does.`,
    entries,
    server_entries: server,
  }
}

export function providersView(
  overrides: Partial<ProvidersView> & {
    writing?: ChainEntry[]
    conversation?: ChainEntry[]
    serverImages?: ChainEntry[]
  } = {}
): ProvidersView {
  const { writing, conversation, serverImages, ...rest } = overrides
  const personal = rest.personal ?? false
  return {
    workspace_id: 7,
    personal,
    editable: true,
    gateway_ready: true,
    kinds: kinds(personal),
    connections: [connection({ id: 1 })],
    roles: [
      role('world_agents', 'World agents'),
      role('writing', 'Writing', writing ?? []),
      role('conversation', 'Conversation', conversation ?? []),
      role('images', 'Images', [], serverImages ?? []),
    ],
    ...rest,
  }
}

export function loginView(overrides: Partial<LoginView> = {}): LoginView {
  return {
    state: 'running',
    output:
      'To authenticate, visit https://github.com/login/device and enter code ABCD-1234',
    links: ['https://github.com/login/device'],
    code: 'ABCD-1234',
    note: '',
    started_at: NOW,
    ended_at: null,
    ...overrides,
  }
}
