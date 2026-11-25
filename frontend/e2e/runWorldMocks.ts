import { APP_VERSION } from './appVersion'
import { readFileSync } from 'node:fs'
import path from 'node:path'

const NOW = '2026-01-01T12:00:00+00:00'
const LONG_NAME = 'Vaelithrandor of the Ninefold Unspoken Dawn, Keeper of Salt-Tides'
const CURRENT_EPOCH = 7

type SonFixture = { son: Record<string, unknown> } & Record<string, unknown>

const SHARED = JSON.parse(
  readFileSync(path.resolve(import.meta.dirname, 'fixtures/mapGraph.json'), 'utf8')
) as { sons: SonFixture[]; rules: Record<string, unknown>[] }

function son(id: number, name: string, rarity: string, status = 'active'): SonFixture {
  const template = SHARED.sons[0]
  return { ...template, son: { ...template.son, id, name, rarity, status } }
}

const SONS = [
  son(4, 'Ithren', 'rare'),
  son(7, LONG_NAME, 'legendary'),
  son(9, 'Moru', 'common'),
  son(11, 'Selvane the Quiet', 'epic', 'asleep'),
]

const WORLD = {
  id: 1,
  name: 'Saltreach, the World Where the Dead Crystallize and Keep Their Last Thoughts',
  lore_language: 'english',
  seed_idea:
    'A world made of salt; the seas are fresh and the land is salty. The dead crystallize and keep their last thoughts inside them, and the living mine those thoughts.',
  cosmology: 'Salt and memory.',
  tone: 'melancholic and strange',
  epoch: CURRENT_EPOCH,
  epoch_start_year: 1240,
  doom_clock: 38,
  fate_mode: 'auto',
  son_distribution: 'auto',
  council_every_epochs: 4,
  mortal_agents_per_epoch: 4,
  mortal_agent_parallelism: 2,
  fate_debt_epoch: 6,
  alignment_until_epoch: null,
  map_version: 1,
  primary_world_id: 3,
  travel_resource: null,
  created_at: NOW,
}

const CREATOR = {
  id: 1,
  name: 'Aeron',
  title: 'the Salt-Father',
  appearance: null,
  temperament: null,
  image_prompt: null,
  note: null,
  essence: 1840,
  passions: [],
  depth: null,
  epic: null,
}

function stats(epoch: number) {
  return {
    population: 1200 + epoch * 340,
    followers: 300 + epoch * 120,
    entities: 40 + epoch * 18,
    words: 120 + epoch * 60,
    knowledge: 5 + epoch * 3,
    languages: 2 + Math.floor(epoch / 3),
    wars: epoch % 3,
    trade_routes: 1 + Math.floor(epoch / 2),
    alliances: Math.floor(epoch / 2),
    structures: 10 + epoch * 4,
    items: 6 + epoch * 2,
    dead: epoch * 40,
    godless: Math.max(0, 4 - epoch),
    doom: 10 + epoch * 4,
    doom_items: [
      { item: 'godless_communities', delta: 6 },
      { item: 'wars', delta: 4 },
      { item: 'miracles', delta: -3 },
      { item: 'faith', delta: -2 },
    ],
    population_items: [
      { item: 'births', delta: 420 },
      { item: 'plague_in_the_lowland_settlements_of_the_salt_coast', delta: -80 },
    ],
    essence_items: [
      { item: 'refill', delta: 20 },
      { item: 'faith_of_the_sons', delta: 34 },
      { item: 'summoning', delta: -60 },
    ],
  }
}

const STATE = {
  world: WORLD,
  creator: CREATOR,
  creator_cover: null,
  world_cover: null,
  sons: SONS,
  counts: { person: 34, settlement: 12, people: 5, region: 8 },
  prayers_pending: 3,
  relations: [],
  worlds: [
    { id: 3, name: 'Saltreach', world_type: 'terrestrial', discovery: 'known', leakage: 12 },
    { id: 5, name: 'The Hollow Moon of Ashes', world_type: 'moon', discovery: 'legend', leakage: 48 },
  ],
  foreign_god_count: 2,
  pending_son_ids: [4, 7],
  covenants: [],
  threads: [],
  last_epoch: {
    epoch: CURRENT_EPOCH - 1,
    name: 'The Age of Brine and Whispering Crystal',
    narrative: null,
    summary: null,
    year_start: 1180,
    year_end: 1240,
    closed_at: NOW,
    chronicler_name: null,
    chronicler_identity: null,
  },
  image_count: 12,
  promptless_count: 5,
  pulse: null,
  read_only: false,
  discovery: null,
  version: 'v7',
  notifications_unread: 128,
  running_jobs: 1,
  epoch_running: false,
  half_epoch: null,
  mood: { contentment: 40, anger: 12, interest: 70, loneliness: 25, label: 'uneasy' },
  image_gen: {
    available: false,
    reason: 'Image generation is not configured.',
    current: null,
    queue: [],
    bulk: {
      running: false,
      stop_requested: false,
      auto: false,
      total: 0,
      done: 0,
      failed: 0,
      skipped: 0,
      rerun_requested: false,
      restyle: false,
    },
    width: 768,
    height: 768,
    steps: 4,
    log: [],
  },
  batch_deepen: { running: true, stop_requested: false, total: 40, done: 12, failed: 1, skipped: 2 },
  llm_enabled: true,
}

const EMPTY_STATE = { ...STATE, world: null, creator: null, sons: [], worlds: [], pending_son_ids: [], last_epoch: null }

const STATISTICS = Array.from({ length: CURRENT_EPOCH }, (_, index) => ({
  epoch: index + 1,
  data: stats(index + 1),
  live: index + 1 === CURRENT_EPOCH,
}))

const BREAKDOWN = {
  epoch: CURRENT_EPOCH - 1,
  current: stats(CURRENT_EPOCH - 1),
  previous: stats(CURRENT_EPOCH - 2),
  deltas: {},
  sons: [
    { son_id: 4, changes: { faith: 12, fame: 3 } },
    { son_id: 7, changes: { faith: -4, existence: 6, level: 1 } },
  ],
}

const ESTIMATE = {
  samples: 5,
  average_epoch_seconds: 412,
  average_phase_start_seconds: { '1': 0, '2': 30, '3': 210, '4': 290, '5': 380 },
  running: false,
  elapsed_seconds: null,
  remaining_seconds: null,
  phase: null,
  overrun: false,
}

const ACTIVITY = [
  { id: 101, kind: 'epoch.started', payload: { epoch: 6, resuming: false, order: [{ id: 4, name: 'Ithren', ini: 12 }, { id: 7, name: LONG_NAME, ini: 9 }] }, at: NOW },
  { id: 102, kind: 'epoch.progress', payload: { epoch: 6, no: 1, total: 5, name: 'The sons act', elapsed_s: 2 }, at: NOW },
  { id: 103, kind: 'son.turn_started', payload: { epoch: 6, son_id: 7, son_name: LONG_NAME, resumed: false, order: 2, order_total: 5, model: 'haiku', rarity: 'legendary' }, at: NOW },
  { id: 104, kind: 'son.turn_finished', payload: { epoch: 6, son_id: 7, son_name: LONG_NAME, status: 'ok', word: 'Let the salt remember what the sea forgets, and let every crystal sing of the drowned kings.', creations: [] }, at: NOW },
  { id: 105, kind: 'engine.started', payload: { epoch: 6 }, at: NOW },
  ...[0, 1, 2, 3].map((index) => ({
    id: 106 + index,
    kind: 'engine.note',
    payload: { epoch: 6, phase: 'warfare', kind: 'world', text: `The salt clans of the eastern reach clash again over crystal field ${index + 1}.`, feed: 'war' },
    at: NOW,
  })),
  { id: 110, kind: 'engine.note', payload: { epoch: 6, phase: 'sky', kind: 'world', text: 'A pale star rises that only the dying can see.', feed: 'sky' }, at: NOW },
  { id: 111, kind: 'fate.finished', payload: { epoch: 6, rejected: [], corrected: [1], fate_debt: false }, at: NOW },
  { id: 120, kind: 'agent.retry', payload: { epoch: 6, actor: LONG_NAME, kind: 'continuation', attempt: 1, total: 3, reason: 'The connection dropped.', done: 4, wait_s: 8 }, at: NOW },
  { id: 121, kind: 'agent.thought', payload: { epoch: 6, actor_kind: 'son', actor_id: 7, actor_name: LONG_NAME, text: 'The salt remembers what the sea forgets. I will raise a tower of crystal where the drowned kings once knelt, and let every window face the place the tide withdraws, so that those who come after read the shape of the loss before they read a single word of it. Then I will ask the clans of the eastern reach whether they would carry the first stone, and listen to what they refuse.' }, at: NOW },
  ...['read_place', 'read_people', 'read_chronicle'].map((tool, index) => ({
    id: 122 + index,
    kind: 'agent.tool_called',
    payload: { epoch: 6, actor_kind: 'son', actor_id: 7, actor_name: LONG_NAME, tool, call_id: `read-${index}`, input: {}, read_only: true },
    at: NOW,
  })),
  { id: 126, kind: 'agent.tool_called', payload: { epoch: 6, actor_kind: 'son', actor_id: 7, actor_name: LONG_NAME, tool: 'create_place', call_id: 'make-1', input: {}, read_only: false }, at: NOW },
  { id: 127, kind: 'agent.tool_result', payload: { epoch: 6, actor_kind: 'son', actor_id: 7, actor_name: LONG_NAME, tool: 'create_place', call_id: 'make-1', text: 'The Tower of Salt was raised.', error: false, quiet: false }, at: NOW },
  { id: 128, kind: 'agent.tool_called', payload: { epoch: 6, actor_kind: 'son', actor_id: 7, actor_name: LONG_NAME, tool: 'declare_war', call_id: 'war-1', input: {}, read_only: false }, at: NOW },
  { id: 129, kind: 'agent.tool_result', payload: { epoch: 6, actor_kind: 'son', actor_id: 7, actor_name: LONG_NAME, tool: 'declare_war', call_id: 'war-1', text: 'The target does not exist.', error: true, quiet: false }, at: NOW },
  { id: 112, kind: 'epoch.finished', payload: { epoch: 6, new_epoch: CURRENT_EPOCH, duration_s: 398, summary: {} }, at: NOW },
]

const RULES = [
  ...SHARED.rules,
  { namespace: 'balance', key: 'apocalypse_threshold', value: 140, default: 100, minimum: 1, maximum: 1000, group: 'Apocalypse', label: 'Apocalypse threshold', integer: true },
  { namespace: 'apocalypse', key: 'warning_1_pct', value: 50, default: 50, minimum: 1, maximum: 100, group: 'Apocalypse', label: 'Point at which the first omen comes (% of threshold)', integer: true },
  { namespace: 'apocalypse', key: 'warning_2_pct', value: 80, default: 80, minimum: 1, maximum: 100, group: 'Apocalypse', label: 'Point at which the final warning comes (% of threshold)', integer: true },
  { namespace: 'costs', key: 'summon_son', value: 40, default: 40, minimum: 0, maximum: 1000, group: "The god's actions", label: 'Cost of summoning a son', integer: true },
  { namespace: 'costs', key: 'rite_cost', value: 5000, default: 20, minimum: 0, maximum: 1000, group: "The god's actions", label: 'Cost of a resurrection rite with a very long descriptive label that must wrap cleanly', integer: true, warning: 'costs.rite_cost is above its advised maximum of 1000.' },
  { namespace: 'costs', key: 'revelation', value: 25, default: 25, minimum: 0, maximum: 1000, group: "The god's actions", label: 'Cost of a revelation', integer: true },
  { namespace: 'engine_phases', key: 'warfare', value: 0, default: 1, minimum: 0, maximum: 1, group: 'Engine phases', label: 'Run the engine step: warfare', integer: true },
  { namespace: 'engine_phases', key: 'sky', value: 1, default: 1, minimum: 0, maximum: 1, group: 'Engine phases', label: 'Run the engine step: sky', integer: true },
  { namespace: 'server', key: 'cheat_essence_max', value: 1000000, default: 1000000, minimum: 1, maximum: 1000000000, group: "The god's actions", label: 'Cheat: maximum essence that can be added at once', integer: true },
  { namespace: 'server', key: 'ledger_page_max', value: 300, default: 300, minimum: 1, maximum: 100000, group: 'Interface', label: "Fate's ledger: largest page", integer: true },
  { namespace: 'ledger', key: 'keep_epochs', value: 6, default: 6, minimum: 1, maximum: 200, group: 'Records', label: 'Epochs kept in the action ledger', integer: true },
  { namespace: 'setup_wizard', key: 'peoples_max', value: 5, default: 5, minimum: 1, maximum: 50, group: 'Genesis wizard', label: 'Wizard: maximum initial peoples', integer: true },
  { namespace: 'notifications', key: 'toast_min_importance', value: 3, default: 3, minimum: 1, maximum: 5, group: 'Notifications', label: 'Notifications of this importance and above also appear as a short on-screen toast (5: none)', integer: true },
  { namespace: 'balance', key: 'doom_threshold', value: 140, default: 100, minimum: 10, maximum: 1000, group: 'Apocalypse', label: 'The doom clock destroys a world when it reaches this value, unless miracles, faith and the patient prayers of the godless push it back first', integer: true },
  { namespace: 'economy', key: 'trade_bonus', value: 0.25, default: 0.25, minimum: 0, maximum: 5, group: 'Economy', label: 'Trade bonus per route', integer: false },
]

const SETTINGS = {
  fate_mode: 'auto',
  son_distribution: 'auto',
  mortal_agents_per_epoch: 4,
  council_every_epochs: 4,
  mortal_agent_parallelism: 2,
  llm_enabled: true,
  image_generation: false,
  image_style: 'photoreal',
  image_style_custom: '',
}

const HEALTH_REPORT = {
  report: {
    status: 'ok',
    version: APP_VERSION,
    uptime_seconds: 9300,
    database: { file: 'aerona.db', size: 48_234_496, wal_size: 2_097_152, quick_check: 'ok' },
    latest_backup: 'epoch-0006.db',
    latest_backup_age_minutes: 42,
    backup_count: 3,
    running_jobs: 1,
    read_only: false,
    log_file: 'logs/aerona.log',
    recent_errors: [{ level: 'error', at: NOW, text: 'A son turn timed out after 360 seconds and was retried.' }],
  },
}

const BACKUPS = [
  { file: 'epoch-0006.db', size: 47_000_000, modified: NOW, label: 'Before epoch 6' },
  { file: 'manual-2026-01-01-the-long-night-before-the-salt-council.db', size: 46_500_000, modified: NOW, label: 'Manual backup' },
]

const BULK = {
  state: { running: true, stop_requested: false, total: 40, done: 12, failed: 1, skipped: 2, current: [{ kind: 'entity', id: 42, name: LONG_NAME }], started: NOW, finished: null },
  log: [
    { level: 'info', at: NOW, text: 'Deepened the Crystal Ossuary of Vel (12/40).' },
    { level: 'warning', at: NOW, text: 'Skipped a record that was merged meanwhile.' },
    { level: 'error', at: NOW, text: 'The model did not answer in time for the Salt Choir.' },
  ],
  waiting: 25,
  unnamed: 3,
}

const METRICS = {
  totals: { calls: 1240, milliseconds: 4_210_000, cost: 18.4, input_tokens: 3_400_000, output_tokens: 610_000 },
  epochs: [5, 6].map((epoch) => ({ epoch, calls: 200 + epoch, milliseconds: 380_000, input_tokens: 520_000, output_tokens: 90_000, cost: 2.6, errors: epoch === 6 ? 2 : 0, retried: epoch === 6 ? 1 : 0, slow: 3 })),
  models: [{ model: 'claude-haiku-4-5-20251001', calls: 1240, milliseconds: 4_210_000, average_ms: 3395, input_tokens: 3_400_000, output_tokens: 610_000, cost: 18.4 }],
  steps: [
    { step: 'Son turn', calls: 620, average_ms: 5200, longest_ms: 42_000, cost: 11.2, errors: 2 },
    { step: 'Deepening', calls: 140, average_ms: 2900, longest_ms: 9000, cost: 2.1, errors: 0 },
  ],
  slowest: [{ id: 1, epoch: 6, job: 'epoch', role: 'son', model: 'claude-haiku-4-5-20251001', kind: 'agent', status: 'ok', duration_ms: 42_000, attempts: 1, turns: 8, input_tokens: 9000, output_tokens: 1200, cost_usd: 0.04, error: null, created_at: NOW }],
  latest_errors: [{ id: 2, epoch: 6, job: 'epoch', role: 'fate', model: 'claude-haiku-4-5-20251001', kind: 'structured', status: 'error', duration_ms: 30_000, attempts: 3, turns: null, input_tokens: 0, output_tokens: 0, cost_usd: 0, error: 'The model did not answer in time.', created_at: NOW }],
  slow_threshold_ms: 20_000,
}

const CATEGORIES = [
  { category: 'death', label: 'Death', severity: 3, enabled_by_default: true },
  { category: 'war', label: 'War', severity: 2, enabled_by_default: true },
  { category: 'achievement', label: 'Achievement', severity: 2, enabled_by_default: true },
  { category: 'note', label: "The god's note", severity: 1, enabled_by_default: true },
]

const NOTIFICATIONS = {
  unread: 128,
  counts: [
    { category: 'death', total: 40, unread: 30 },
    { category: 'war', total: 90, unread: 88 },
    { category: 'achievement', total: 4, unread: 1 },
    { category: 'note', total: 2, unread: 0 },
  ],
  settings: { death: true, war: true, achievement: true, note: true },
  categories: CATEGORIES,
  items: [
    { id: 300, epoch: 7, category: 'death', severity: 3, title: `${LONG_NAME} mourns the fall of the salt king`, body: 'The crystal of the king holds his last thought: a song without an end.', target_node_id: 7, chronicle_id: null, is_read: false, created_at: NOW },
    { id: 299, epoch: 6, category: 'achievement', severity: 2, title: 'First Faith', body: null, target_node_id: null, chronicle_id: null, is_read: true, created_at: NOW },
    { id: 298, epoch: 6, category: 'note', severity: 1, title: 'Reminder: reconcile the two eldest sons', body: 'Before the council.', target_node_id: null, chronicle_id: null, is_read: true, created_at: NOW },
  ],
}

const LEDGER = {
  current_epoch: CURRENT_EPOCH,
  epochs: [
    { epoch: 7, entries: 3, undone: 0 },
    { epoch: 6, entries: 12, undone: 2 },
  ],
  entries: [
    {
      entry: { id: 88, epoch: 7, actor_kind: 'creator', actor_node_id: 1, actor_name: 'Aeron', tool: 'bless', action_kind: 'bless_essence', input_summary: `Blessed ${LONG_NAME} with 40 essence for his patience during the long salt winter.`, undone: false, undone_at: null, applied: [], conflicts: [], created_at: NOW },
      label: 'Bless a son',
      change_count: 2,
      rows: ['changed: son essence 40 → 80', 'changed: creator essence 1880 → 1840'],
      dependents: [91],
    },
    {
      entry: { id: 87, epoch: 6, actor_kind: 'son', actor_node_id: 7, actor_name: LONG_NAME, tool: 'create_entity', action_kind: 'create_entity', input_summary: 'Raised the Crystal Ossuary of Vel.', undone: true, undone_at: NOW, applied: ['deleted: entity 42'], conflicts: ['bond 12 was already removed'], created_at: NOW },
      label: 'Create a record',
      change_count: 1,
      rows: ['added: entity 42'],
      dependents: [],
    },
  ],
}

const NAMES = [
  { kind: 'creator', id: 1, name: 'Aeron', type: 'creator' },
  { kind: 'son', id: 7, name: LONG_NAME, type: 'Legendary' },
  { kind: 'son', id: 4, name: 'Ithren', type: 'Rare' },
]

const FAVORITES = [
  { id: 42, name: 'The Crystal Ossuary of Vel, Where the Drowned Kings Sing', title: null, entity_type: 'structure', subtype: null, status: 'canon', world_id: 3, location_id: null, power_level: 4, birth_epoch: 2, end_epoch: null, importance: 8, favorite: true, pending_name: false },
]

const MAP_NOTES = [
  { id: 1, world_id: 3, x: 0.3, y: 0.4, text: 'The salt clans will war here next; send a son before the third epoch passes.', color: null, created_at: NOW },
]

const NOTES = {
  entity_notes: [
    { entity_id: 42, entity_name: 'The Crystal Ossuary of Vel, Where the Drowned Kings Sing', entity_type: 'structure', world_id: 3, text: 'Ask Ithren about the tenth king, and whether the glass remembers the first song or only the last one that was sung over the drowned.' },
  ],
  map_notes: MAP_NOTES,
}

const CHANGES = {
  full: false,
  version: 'v1',
  entities: [],
  removed_entity_ids: [],
  sons: [],
  removed_son_ids: [],
  new_chronicle_lines: 0,
  bonds_changed: false,
  cosmos_changed: false,
  worlds_changed: false,
  relations_changed: false,
  foreign_god_ids: [],
}

const ENUMS = { actor_kinds: ['creator', 'son', 'mortal', 'foreign_god', 'fate', 'engine', 'system'] }

const ACTIONS = [
  { id: 'cheat:essence', title: 'Add essence', group: 'settings', mode: 'ledgered', cost: 'Free', confirmation: null, rows: [], path: '/api/cheats/essence', method: 'POST', input_schema: { properties: { amount: { title: 'Amount', type: 'integer' } }, required: ['amount'], type: 'object' } },
  { id: 'record:merge', title: 'Merge two records', group: 'canon', mode: 'ledgered', cost: '20 essence', confirmation: 'MERGE', rows: [], path: '/api/actions/record:merge', method: 'POST', input_schema: { properties: { entity_id: { type: 'integer', title: 'Entity Id' }, other_id: { type: 'integer', title: 'Other Id' }, confirm: { type: 'string', title: 'Confirm' } }, required: ['entity_id', 'other_id', 'confirm'], type: 'object' } },
]

const WIZARD = {
  technology: { stone: 'Stone age', bronze: 'Bronze age', iron: 'Iron age', medieval: 'Medieval', renaissance: 'Renaissance', steam: 'Steam and gunpowder' },
  language: { flowing: 'Flowing, vowel-rich, soft', hard: 'Hard consonants, short syllables', guttural: 'Guttural, deep', sibilant: 'Sibilant, fricative', long: 'Long, agglutinative, polysyllabic', free: 'Free' },
  cosmos: [
    { size: 'single', label: 'Single world', worlds: 1 },
    { size: 'small', label: 'Small cosmos', worlds: 2 },
    { size: 'large', label: 'Large cosmos', worlds: 3 },
  ],
  lore_languages: { english: 'English', turkish: 'Turkish' },
  first_sons: { minimum: 1, maximum: 5, rarities: ['common', 'uncommon', 'rare', 'epic', 'legendary'], default: ['common', 'rare', 'legendary'] },
  templates: [
    { key: 'dark_fantasy', name: 'Dark fantasy', tone: 'gloomy, merciless, hope comes at a high price', magic: 60, darkness: 80, technology: 'iron', language: 'guttural', peoples: 3, cosmos: 'single', seed: 'A world built on the corpses of gods who once died; every bounty comes from a rot.' },
    { key: 'star_myth', name: 'Star myth', tone: 'vast, full of wonder, cosmic in scale', magic: 55, darkness: 45, technology: 'renaissance', language: 'flowing', peoples: 3, cosmos: 'large', seed: 'A cosmos where star-wind fills the ships’ sails.' },
  ],
}

const IMPORT_RESULT = {
  mode: 'merge',
  world: { name: 'Ember Hollow, the Furnace-World of the Twelve Sleeping Smiths', epoch: 31, creator: 'Seravel', date: NOW },
  safety_backup: 'before-import-2026-01-01.db',
  merge: {
    rows: { nodes: 214, entities: 190, bonds: 640, chronicle: 311, images: 12 },
    skipped: { messages: 40, notifications: 9, ledger_entries: 120 },
    renamed: [
      { old_name: 'Oskar', new_name: 'Oskar II' },
      { old_name: 'The Glass Wells of the Weeping Salt Marshes', new_name: 'The Glass Wells of the Weeping Salt Marshes II' },
    ],
    images: { 'portrait-12.png': 'merged-portrait-12.png' },
  },
}

export type RunWorldVariant = 'default' | 'empty' | 'llm-off' | 'discovery'

function stateFor(variant: RunWorldVariant) {
  if (variant === 'empty') return EMPTY_STATE
  if (variant === 'llm-off') return { ...EMPTY_STATE, llm_enabled: false }
  if (variant === 'discovery')
    return { ...STATE, read_only: true, discovery: { name: 'Ember Hollow', epoch: 31, creator: 'Seravel', date: NOW } }
  return STATE
}

const SAVED_GENESIS = {
  lore_language: 'english',
  seed_idea: 'A sea of salt that remembers every drowned name, and the twelve lanterns that keep them from waking',
  tone: 'Grave, tidal and patient',
  settings: {
    template: 'mythic_age',
    magic: 60,
    darkness: 35,
    technology: 'bronze',
    language_texture: 'flowing',
    peoples: 3,
    cosmos_size: 'small',
  },
}

const SECONDARY_BACKUP = {
  directory: '/Volumes/Archive of the Twelve Lanterns/aerona/backups/Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin',
  keep: 5,
}

const ENGINE_SEED = {
  world_seed: 918273645,
  epoch: 12,
  stream_format: "world seed + epoch + '<phase>.<stream>'",
  phase_streams: ['mortals', 'population', 'settlements', 'diplomacy', 'warfare', 'economy', 'faith', 'climate', 'cosmos', 'horror'],
}

export function runWorldResponse(method: string, url: URL, variant: RunWorldVariant): unknown {
  const route = url.pathname
  if (method === 'POST' && route === '/api/world/import') return IMPORT_RESULT
  if (method !== 'GET') return undefined
  const direct: Record<string, unknown> = {
    '/api/state': stateFor(variant),
    '/api/stats/epochs': STATISTICS,
    '/api/epochs/current/estimate': ESTIMATE,
    '/api/activity-log': ACTIVITY,
    '/api/rules': RULES,
    '/api/settings': SETTINGS,
    '/api/health/report': HEALTH_REPORT,
    '/api/backups': BACKUPS,
    '/api/discovery':
      variant === 'discovery'
        ? { active: true, guest: { name: 'Ember Hollow, the Furnace-World of the Twelve Sleeping Smiths', epoch: 31, creator: 'Seravel', date: NOW } }
        : { active: false, guest: null },
    '/api/batch-deepen': BULK,
    '/api/metrics/models': METRICS,
    '/api/notifications': NOTIFICATIONS,
    '/api/ledger': LEDGER,
    '/api/names': NAMES,
    '/api/favorites': FAVORITES,
    '/api/map-notes': MAP_NOTES,
    '/api/notes': NOTES,
    '/api/changes': CHANGES,
    '/api/catalogue/enums': ENUMS,
    '/api/actions': ACTIONS,
    '/api/genesis/wizard': WIZARD,
    '/api/genesis/settings': SAVED_GENESIS,
    '/api/backups/secondary': SECONDARY_BACKUP,
    '/api/engine/seed': ENGINE_SEED,
    '/api/search': [],
  }
  if (/^\/api\/epochs\/\d+\/breakdown$/.test(route)) return BREAKDOWN
  return direct[route]
}
