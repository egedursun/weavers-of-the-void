import type { components } from '../src/api/generated/schema'

type Schemas = components['schemas']

const NOW = '2026-01-01T12:00:00+00:00'
const EPOCH = 12
const OPPORTUNITY_LINES = [
  { kind: 'rival_siblings', text: 'RIVAL SIBLINGS: son#9 Kharun (relation -40). Tell this feud: challenge openly with challenge, or curse his creation with curse.', tension: true, tools: ['challenge', 'curse'] },
  { kind: 'unclaimed', text: 'Communities that worship no one: #42 The Dune Mirrors. A miracle or a dream could bind them to you.', tension: false, tools: [] },
]

const TOOL_VIEW = {
  son_id: 7,
  rarity: 'legendary',
  epoch: 3,
  action_points_left: 4,
  available: [
    { name: 'send_dream', description: 'Send a dream to a mortal; success depends on your charisma.', fields: { text: 'What the sleeper sees.' }, action_cost: 1, essence_cost: 10, read_only: false, long_job: false, minimum_rarity: 'rare' },
    { name: 'read_world', description: 'Read the world summary.', fields: {}, action_cost: 0, essence_cost: 0, read_only: true, long_job: false, minimum_rarity: null },
  ],
  blocked: [{ name: 'birth_world', reason: 'rarity', minimum_rarity: 'mythic' }],
  counters: [{ counter: 'gifts', value: 1 }],
}

const LONG = 'Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin'

const PERSONALITY: Schemas['Personality'] = {
  appearance: 'A tall figure of salt and storm light whose shadow falls the wrong way at noon.',
  temperament: 'Patient, then sudden; he forgives slowly and forgets nothing.',
  obsession: 'Binding the restless sea to an oath it cannot break.',
  fear: "Being remembered only as his father's instrument.",
  speech_style: 'Short sentences, old words, long silences.',
  secret: 'He once let a city drown to win a wager with his brother.',
}

function son(overrides: Partial<Schemas['SonRecord']> & { id: number; name: string }): Schemas['SonRecord'] {
  return {
    title: 'Keeper of the Drowned Bells',
    rarity: 'legendary',
    stars: 3,
    domain_primary: 'sea',
    domain_secondary: 'oath',
    strength: 62,
    endurance: 55,
    agility: 48,
    wisdom: 71,
    cunning: 66,
    will: 80,
    creativity: 58,
    charisma: 74,
    might: 69,
    sanity: 82,
    loyalty: 61,
    ambition: 54,
    wrath: 33,
    mercy: 40,
    personality: PERSONALITY,
    existence_profile: {
      nature: 'Tide and memory',
      mode: 'semi_concrete',
      manifestation: 'A voice in the bell towers of drowned cities',
      true_name: 'Ul-Varesh',
    },
    existence: 72,
    fading_epochs: 0,
    hp: 120,
    essence: 64,
    faith: 18,
    fame: 46,
    xp: 340,
    level: 5,
    status: 'active',
    sleep_epochs_left: 0,
    chained: false,
    rebel: false,
    outer_bargain_forbidden: false,
    standing_order: null,
    order_absolute: false,
    turn_rank: null,
    plan: 'Raise a lighthouse temple on the western cliffs and draw the fisher folk to his worship.',
    epic: {
      title: 'The Song of the Drowned Bells',
      verse: 'Where the bells sink, his name rises.',
      body: 'Before the first tide was named, he walked the floor of the sea counting the bones of ships.',
      chapters: [
        { title: 'The First Oath', text: 'He bound the western storm with a word and paid for it with his voice.', epoch_start: 2, epoch_end: 4 },
        { title: 'The City Beneath', text: 'The fisher folk heard bells under the waves and built a temple above them.', epoch_start: 5, epoch_end: 9 },
      ],
      epoch: 10,
    },
    anchor_entity_id: 42,
    corpse_entity_id: null,
    parent_son_id: null,
    co_parent_son_id: null,
    current_world_id: 1,
    manually_assigned_epoch: null,
    birth_epoch: 1,
    death_epoch: null,
    death_cause: null,
    last_acted_epoch: EPOCH - 1,
    reputation_love: 58,
    reputation_fear: 32,
    reputation_forgotten: 12,
    reputation_unanswered: 1,
    reputation_last_contact_epoch: EPOCH - 1,
    reputation_label: 'loved',
    manual_love: 10,
    manual_fear: 0,
    manual_forgotten: 0,
    image_prompt: 'A storm-lit figure among drowned bell towers, oil painting',
    ...overrides,
  }
}

const POWERS: Schemas['SonPower'][] = [
  { slot: 0, name: 'Tide Ledger', description: 'Creations within his domain cost less.', effect: 'cheap_creation', param_entity_type: null, param_stat: null },
  { slot: 1, name: 'Bell of Return', description: 'He wakes sooner when struck down.', effect: 'reviving', param_entity_type: null, param_stat: null },
  { slot: 2, name: 'Oathbinder', description: 'Duels on his chosen stat favour him.', effect: 'duel_master', param_entity_type: null, param_stat: 'will' },
]

function view(record: Schemas['SonRecord'], extra: Partial<Schemas['SonPublic']> = {}): Schemas['SonPublic'] {
  return {
    son: record,
    powers: POWERS,
    max_hp: 140,
    max_essence: 150,
    action_points: 3,
    power_cap: 7,
    band: 'solid',
    band_label: 'Solid',
    band_effect: 'No strain on his body or will.',
    band_action_loss: 0,
    unlocked_powers: 2,
    power_slots: 3,
    next_star: { stars: record.stars + 1, level: 7, fame: 60, essence: 45 },
    ascension: null,
    cover: null,
    card: {
      last_action: 'Raised a lighthouse temple above the drowned city of Oskar.',
      last_action_epoch: EPOCH - 1,
      last_words: 'The sea keeps every promise it is made to keep.',
      reputation: 'loved',
      best_friend: { id: 8, name: LONG, value: 64 },
      worst_rival: { id: 9, name: 'Kharun the Ashen', value: -48 },
    },
    ...extra,
  }
}

const SON_RECORDS = [
  son({ id: 7, name: 'Thalassir' }),
  son({
    id: 8,
    name: LONG,
    title: 'The Very Long Titled Warden of Every Forgotten Border Between Sleep and Waking',
    rarity: 'mythic',
    stars: 5,
    domain_primary: 'dream',
    domain_secondary: 'border',
    standing_order: 'Send a dream of fire to the priests of Kharun before the next harvest.',
    order_absolute: true,
    turn_rank: null,
    current_world_id: 2,
    reputation_label: 'respected',
  }),
  son({
    id: 9,
    name: 'Kharun the Ashen',
    title: 'Lord of Cinders',
    rarity: 'rare',
    stars: 1,
    domain_primary: 'fire',
    domain_secondary: 'ash',
    rebel: true,
    chained: true,
    loyalty: 12,
    wrath: 88,
    reputation_label: 'hated',
    fading_epochs: 1,
    existence: 9,
  }),
  son({
    id: 10,
    name: 'Mirel',
    title: 'The Quiet Seed',
    rarity: 'common',
    stars: 0,
    status: 'dead',
    death_epoch: 9,
    death_cause: 'killed_by_sibling',
    corpse_entity_id: 43,
    reputation_label: null,
    reputation_love: null,
    epic: null,
  }),
]

const SONS: Schemas['SonPublic'][] = [
  view(SON_RECORDS[0]),
  view(SON_RECORDS[1], { next_star: null, ascension: { stars: 5, level: 9, fame: 90, essence: 90, target: 'mythic' }, band: 'radiant', band_label: 'Radiant' }),
  view(SON_RECORDS[2], { band: 'being_forgotten', band_label: 'Fading', band_effect: 'He is fading from memory and loses part of his turn.', band_action_loss: 1, unlocked_powers: 1 }),
  view(SON_RECORDS[3], { powers: [], unlocked_powers: 0, next_star: null }),
]

const CREATOR: Schemas['CreatorRecord'] = {
  id: 1,
  name: 'Aeron',
  title: 'The Unwritten Dawn',
  appearance: 'A dawn that never finishes rising, with a voice like distant surf.',
  temperament: 'Curious, slow to anger, terrible when roused.',
  image_prompt: 'A radiant dawn figure over a dark ocean of stars',
  note: 'No son may unmake the western sea.',
  essence: 186,
  passions: ['creation', 'order'],
  depth: {
    history: 'Before the first star, Aeron dreamed of a sea that remembered.',
    names: [{ name: 'The First Light', used_by: 'The fisher folk', meaning: 'He who lit the western waters' }],
    secrets: ['He cannot see the bottom of the oldest sea.'],
    fears: ['A world that forgets him entirely.'],
    taboos: ['No temple may be built of drowned stone.'],
    gifts: ['The first tide.'],
    desire: 'To be remembered by something he did not make.',
    sayings: [{ form: 'Proverb', text: 'The dawn owes nothing to the night.' }],
    rumours: ['Some say he had a brother before the sons.'],
    hidden_truth: 'The sons were made to forget his loneliness.',
    view_of_pantheon: 'Proud and wary.',
    worship: 'Dawn prayers at the shore.',
    epoch: 8,
  },
  epic: null,
}

const COSMOS: Schemas['CosmosRecord'] = {
  id: 1,
  name: 'Orvael',
  lore_language: 'english',
  seed_idea: 'A cosmos of drowned bells.',
  cosmology: 'Three worlds turn around a pale star; the sea of the first world remembers every name spoken over it.',
  tone: 'Melancholic, mythic, salt-worn.',
  epoch: EPOCH,
  epoch_start_year: 1,
  doom_clock: 62,
  fate_mode: 'auto',
  son_distribution: 'auto',
  council_every_epochs: null,
  mortal_agents_per_epoch: null,
  mortal_agent_parallelism: null,
  fate_debt_epoch: null,
  alignment_until_epoch: null,
  map_version: 1,
  primary_world_id: 1,
  travel_resource: null,
  created_at: NOW,
}

const WORLDS: Schemas['WorldBriefItem'][] = [
  { id: 1, name: 'Thessaly Deep', world_type: 'ocean', discovery: 'known', leakage: 10 },
  { id: 2, name: `The Glass Wastes of ${LONG}`, world_type: 'crystal', discovery: 'known', leakage: 34 },
]

const RELATIONS: Schemas['SonRelationItem'][] = [
  { son_a_id: 7, son_b_id: 8, value: 64, note: 'Brothers of the tide and the dream.' },
  { son_a_id: 7, son_b_id: 9, value: -48, note: 'Fire and sea never agree.' },
  { son_a_id: 8, son_b_id: 9, value: -12, note: null },
  { son_a_id: 7, son_b_id: 10, value: 20, note: null },
  { son_a_id: 8, son_b_id: 10, value: 5, note: null },
  { son_a_id: 9, son_b_id: 10, value: -80, note: 'He killed him.' },
]

const THREADS: Schemas['ThreadRecord'][] = [
  {
    id: 3,
    epoch: 9,
    text: 'The exiled heir of the drowned city will return to claim the throne beneath the bells.',
    status: 'open',
    closing_text: null,
    closed_epoch: null,
    progress: 2,
    related: [
      { id: 42, kind: 'entity', name: 'Oskar' },
      { id: 7, kind: 'son', name: 'Thalassir' },
    ],
  },
  {
    id: 4,
    epoch: 11,
    text: `Rumours say ${LONG} dreams of a second sun.`,
    status: 'open',
    closing_text: null,
    closed_epoch: null,
    progress: 0,
    related: [],
  },
]

const PULSE: Schemas['EpochStatsData'] = {
  population: 1284000,
  followers: 412000,
  entities: 320,
  words: 1840,
  knowledge: 26,
  languages: 7,
  wars: 2,
  trade_routes: 5,
  alliances: 3,
  structures: 40,
  items: 18,
  dead: 12,
  godless: 3,
  doom: 62,
  soldiers: 4200,
  travelling: 300,
  flow_items: [],
  doom_items: [
    { item: 'Open wars', delta: 8 },
    { item: 'Miracles worked', delta: -3 },
  ],
  population_items: [],
  essence_items: [
    { item: 'Epoch refill', delta: 120 },
    { item: 'Summoned a son', delta: -40 },
  ],
}

export const GOD_STATE: Schemas['StateResponse'] = {
  world: COSMOS,
  creator: CREATOR,
  creator_cover: null,
  world_cover: null,
  sons: SONS,
  counts: { people: 6, settlement: 14, mortal: 38, legend: 9 },
  prayers_pending: 2,
  relations: RELATIONS,
  worlds: WORLDS,
  foreign_god_count: 1,
  pending_son_ids: [7],
  covenants: [{ son_a_id: 7, son_b_id: 8, description: 'The oath of the tide.' }],
  threads: THREADS,
  last_epoch: null,
  image_count: 14,
  promptless_count: 2,
  pulse: PULSE,
  read_only: false,
  discovery: null,
  version: '1',
  notifications_unread: 3,
  running_jobs: 0,
  epoch_running: false,
  half_epoch: null,
  mood: { contentment: 64, anger: 22, interest: 71, loneliness: 38, label: 'content' },
  image_gen: { available: false, reason: 'No image worker is configured.', current: null, queue: [], bulk: { running: false, stop_requested: false, auto: false, total: 0, done: 0, failed: 0, skipped: 0, rerun_requested: false, restyle: false }, width: 512, height: 512, steps: 20, log: [] },
  batch_deepen: { running: false, stop_requested: false, total: 0, done: 0, failed: 0, skipped: 0 },
  llm_enabled: true,
}

const ENTITY = (id: number, name: string, type: Schemas['EntityType']): Schemas['EntitySummary'] => ({
  id,
  name,
  title: null,
  entity_type: type,
  subtype: null,
  status: 'canon',
  world_id: 1,
  location_id: null,
  power_level: 4,
  birth_epoch: 3,
  end_epoch: null,
  importance: 10,
  favorite: false,
  pending_name: false,
})

const CHRONICLE: Schemas['ChronicleLineRecord'][] = [
  { id: 91, epoch: 11, year: 340, kind: 'creation', son_id: 7, world_id: 1, text: 'Thalassir raised a lighthouse temple over the drowned city.', created_at: NOW },
  { id: 92, epoch: 12, year: 352, kind: 'prayer', son_id: 7, world_id: 1, text: 'The fisher folk prayed for calm seas.', created_at: NOW },
]

const SON_DETAIL: Schemas['SonDetail'] = {
  son: SON_RECORDS[0],
  kill_cost: 100,
  reputation: { son_id: 7, name: 'Thalassir', love: 58, fear: 32, forgotten: 12, unanswered: 1, last_contact: EPOCH - 1, label: 'loved' },
  folk_views: [
    { people_id: 50, people_name: 'The Fisher Folk', local_name: 'Bellfather', account: 'He rings the drowned bells to warn us of storms.', misconception: 'He does it to count the dead.', epoch: 10 },
  ],
  creations: [ENTITY(42, 'Oskar', 'settlement'), { ...ENTITY(44, 'The Bell Choir', 'tradition'), status: 'rejected' }],
  chronicle: CHRONICLE,
  messages: [
    { id: 301, epoch: 11, sender: { id: 7, kind: 'son', name: 'Thalassir' }, recipient: { id: 1, kind: 'creator', name: 'Aeron' }, intent: 'prayer', text: 'Grant me the strength to hold the western storm.', answered: false },
  ],
  siblings: [
    { son: { id: 8, kind: 'son', name: LONG }, value: 64, note: 'Brothers of the tide and the dream.', cover: null },
    { son: { id: 9, kind: 'son', name: 'Kharun the Ashen' }, value: -48, note: 'Fire and sea never agree.', cover: null },
  ],
  bonds: [
    { id: 501, source_node_id: 7, target_node_id: 42, kind: 'protects', description: 'He shelters the drowned city.', role: null, epoch: 6, state: 'active', closed_epoch: null, closed_reason: null, war_id: null, debt_amount: null, debt_what: null, debt_due_epoch: null, debt_status: null, outgoing: true, other: { id: 42, kind: 'entity', name: 'Oskar' } },
    { id: 502, source_node_id: 9, target_node_id: 7, kind: 'enemy', description: null, role: null, epoch: 8, state: 'active', closed_epoch: null, closed_reason: null, war_id: null, debt_amount: null, debt_what: null, debt_due_epoch: null, debt_status: null, outgoing: false, other: { id: 9, kind: 'son', name: 'Kharun the Ashen' } },
  ],
  bond_total: 2,
  live_faith: 18.4,
  worshippers: [ENTITY(50, 'The Fisher Folk', 'people')],
  anchor: ENTITY(42, 'Oskar', 'settlement'),
  parent: null,
  children: [],
  images: [],
}

const CREATOR_DETAIL: Schemas['CreatorDetail'] = {
  creator: CREATOR,
  cover: null,
  mood: {
    contentment: 64,
    anger: 22,
    interest: 71,
    loneliness: 38,
    label: 'content',
    breakdown: [
      { epoch: 11, axis: 'contentment', item: 'faith', delta: 2.5 },
      { epoch: 11, axis: 'anger', item: 'godless communities', delta: 1.2 },
    ],
  },
  faith: 12.6,
  cult_essence: 3,
  cult: [ENTITY(51, 'The Dawn Watchers', 'cult')],
  folk_views: [],
  traces: CHRONICLE,
  images: [],
}

const REPUTATION: Schemas['CreatorReputation'] = {
  love: 52,
  fear: 30,
  forgotten: 18,
  label: 'respected',
  sons: [
    { son_id: 7, name: 'Thalassir', love: 58, fear: 32, forgotten: 12, unanswered: 1, last_contact: EPOCH - 1, label: 'loved' },
    { son_id: 9, name: 'Kharun the Ashen', love: 8, fear: 70, forgotten: 30, unanswered: 3, last_contact: EPOCH - 4, label: 'hated' },
  ],
  passions: ['creation', 'order'],
  automatic: true,
  all_passions: [
    { passion: 'order', name: 'Order', hint: 'Laws, borders and kept oaths.' },
    { passion: 'chaos', name: 'Chaos', hint: 'Storms, plagues and broken things.' },
    { passion: 'creation', name: 'Creation', hint: 'New peoples, works and worlds.' },
    { passion: 'mercy', name: 'Mercy', hint: 'Answered prayers and spared lives.' },
  ],
}

const FOREIGN_GOD: Schemas['ForeignGodRecord'] = {
  id: 3,
  name: 'Ysmera of the Hollow Moon',
  title: 'She Who Waits Beneath the Glass',
  domain_primary: 'moon',
  domain_secondary: 'glass',
  world_id: 2,
  power: 54,
  faith: 6.5,
  stance: -22,
  status: 'asleep',
  contacted: false,
  description: 'An old goddess of the glass wastes who sleeps beneath the dunes and dreams in reflections.',
  image_prompt: null,
  strength: 50,
  endurance: 61,
  agility: 44,
  wisdom: 70,
  cunning: 66,
  will: 72,
  creativity: 40,
  charisma: 52,
  might: 58,
  sanity: null,
  personality: null,
  existence_profile: null,
  depth: null,
  awakening_pressure: 46,
  awakening_average: 4,
  created_epoch: 2,
  defeated_epoch: null,
  death_epoch: null,
}

const FOREIGN_DETAIL: Schemas['ForeignGodDetail'] = {
  god: FOREIGN_GOD,
  powers: [{ slot: 0, name: 'Mirror Veil', effect: 'deathless', description: 'She cannot be slain by ordinary means.' }],
  kill_cost: 90,
  drain_amount: 12,
  drain_gain: 24,
  deathless: true,
  deathless_caption: 'She cannot be killed while her mirror veil holds.',
  world: null,
  worshippers: [{ entity: ENTITY(60, 'The Dune Mirrors', 'people'), cover: null }],
  bonds: [],
  bond_total: 0,
  chronicle: [],
  sons_here: [{ id: 8, kind: 'son', name: LONG }],
  images: [],
  cover: null,
}

const PRAYERS: Schemas['PrayerView'][] = [
  {
    message: { id: 301, epoch: 11, sender_node_id: 7, recipient_node_id: 1, intent: 'prayer', text: 'Grant me the strength to hold the western storm.', request: 'essence', wish: 'Essence', is_read: false, answered: false, answered_epoch: null, answer_essence: null, created_at: NOW },
    sender: { id: 7, kind: 'son', name: 'Thalassir' },
  },
  {
    message: { id: 302, epoch: 12, sender_node_id: 70, recipient_node_id: 1, intent: 'prayer', text: `Let the rains return to the valley of ${LONG}.`, request: 'blessing', wish: null, is_read: false, answered: false, answered_epoch: null, answer_essence: null, created_at: NOW },
    sender: { id: 70, kind: 'entity', name: 'Old Ilsa the Netmender' },
  },
  {
    message: { id: 303, epoch: 10, sender_node_id: 9, recipient_node_id: 1, intent: 'prayer', text: 'Forgive me, father.', request: 'forgiveness', wish: null, is_read: true, answered: true, answered_epoch: 10, answer_essence: 10, created_at: NOW },
    sender: { id: 9, kind: 'son', name: 'Kharun the Ashen' },
  },
]

const COUNCILS: Schemas['CouncilRecord'][] = [
  {
    id: 1,
    epoch: 8,
    topic: 'How can the doom clock be stopped?',
    passed: true,
    created_at: NOW,
    minutes: {
      topic: 'How can the doom clock be stopped?',
      convened_by: 'fate',
      speeches: [
        { son_id: 7, name: 'Thalassir', words: 'Bind the godless to an oath and the clock will slow.' },
        { son_id: 9, name: 'Kharun the Ashen', words: 'Let it burn. Ash is a kind of peace.' },
      ],
      motion: 'Every son claims one godless people before the next epoch.',
      ballots: [
        { son_id: 7, name: 'Thalassir', vote: 'yes', reason: 'Order holds the sea.' },
        { son_id: 8, name: LONG, vote: 'yes', reason: 'The dream agrees.' },
        { son_id: 9, name: 'Kharun the Ashen', vote: 'no', reason: 'I will not bow.' },
      ],
      passed: true,
      decision: 'The sons will claim the godless.',
      notes: ['Kharun left the hall before the vote ended.'],
      summary: 'A seer dreamed of three brothers arguing under a pale star.',
    },
  },
]

const GOALS: Schemas['GoalsOverview'] = {
  scenarios: [
    { key: 'doom_far', name: 'Keep the doom far', description: 'Keep the doom clock below half for ten epochs.', points: 40, history: [] },
    { key: 'one_faith', name: 'One faith', description: 'Make one son worshipped by every people.', points: 60, history: [{ id: 1, status: 'failed', start_epoch: 2, end_epoch: 6, result: null }] },
  ],
  running: [{ id: 2, key: 'doom_far', name: 'Keep the doom far', start_epoch: 9, progress: { percent: 30, text: '3 of 10 epochs below half.', done: false, failed: false } }],
  achievements: [
    { key: 'first_prayer', name: 'First prayer', description: 'Answer your first prayer.', points: 5, earned: true, epoch: 2 },
    { key: 'babel', name: 'Babel', description: 'Seven languages are spoken.', points: 15, earned: false, epoch: null },
  ],
  score: { parts: { population: 120, diversity: 40, languages: 35, worlds: 20, civilization: 30, doomsday: -25, achievements: 5, scenarios: 0 } },
  score_history: [[9, 160], [10, 190], [11, 210], [12, 225]],
}

const HINTS: Schemas['PlayerHints'] = {
  creator: {
    unanswered_prayers: 2,
    unclaimed: ['The Dune Mirrors'],
    rebel_sons: ['Kharun the Ashen'],
    fading_sons: [{ name: 'Kharun the Ashen', existence: 9 }],
    doom: 62,
    doom_threshold: 100,
    godless_worlds: [],
    stale_threads: 1,
    essence: 186,
  },
  sons_waiting: ['Thalassir'],
  sons_without_orders: ['Thalassir'],
  sleeping_sons: [],
  dead_sons: ['Mirel'],
  open_threads: 2,
  sons_without_image: 4,
  unread_notifications: 3,
  epoch_in_progress: false,
}

const RULE_VALUES: [string, string, number][] = [
  ['costs', 'summon_son', 30],
  ['costs', 'bless_essence', 15],
  ['costs', 'bless_hp', 15],
  ['costs', 'bless_stat', 40],
  ['costs', 'lightning', 10],
  ['costs', 'revelation', 25],
  ['balance', 'council', 20],
  ['balance', 'awaken_peoples', 35],
  ['balance', 'resurrection', 150],
  ['balance', 'suppress_revolt', 20],
  ['balance', 'apocalypse_threshold', 100],
  ['apocalypse', 'warning_1_pct', 50],
  ['apocalypse', 'warning_2_pct', 80],
  ['awakening', 'batch_cap', 3],
  ['council', 'min_members', 2],
  ['council', 'default_interval', 4],
  ['council', 'chat_max_chars', 800],
  ['core_rules', 'xp_per_level', 100],
  ['core_rules', 'relation_sibling', 75],
  ['core_rules', 'relation_close_friend', 45],
  ['core_rules', 'relation_friend', 15],
  ['core_rules', 'relation_cold', 10],
  ['core_rules', 'relation_enemy', 35],
  ['core_rules', 'relation_blood_enemy', 70],
  ['death', 'fading_death_epochs', 3],
  ['death', 'resurrection_min_epochs', 3],
  ['god_power', 'absolute_command_cost', 25],
  ['god_power', 'demote_cost', 40],
  ['god_power', 'strip_power_cost', 30],
  ['god_power', 'drain_son_pct', 50],
  ['god_power', 'drain_son_efficiency_pct', 80],
  ['god_power', 'devour_son_essence_per_might', 3],
  ['god_power', 'devour_son_essence_per_level', 20],
  ['god_power', 'drain_foreign_pct', 30],
  ['god_power', 'foreign_essence_per_strength', 3],
  ['god_power', 'kill_foreign_base_cost', 60],
  ['god_power', 'kill_foreign_strength_pct', 100],
  ['god_power', 'kill_immortal_foreign_mult', 2],
  ['god_actions', 'prayer_essence_cap', 100],
  ['god_hand', 'assignment_protection_epochs', 3],
  ['creator', 'wrath_threshold', 70],
  ['creator', 'content_threshold', 70],
  ['creator', 'label_silent', 20],
  ['creator', 'label_lonely', 70],
  ['reputation', 'max_passions', 3],
  ['reputation', 'manual_push_cap', 60],
  ['reputation', 'manual_love_click', 10],
  ['reputation', 'manual_fear_click', 10],
  ['reputation', 'manual_neglect_click', 15],
  ['reputation', 'manual_push_keep_pct', 60],
  ['pantheon', 'son_war_max_attitude', 30],
  ['pantheon', 'foreign_friend_min_attitude', 40],
  ['pantheon', 'sleep_wake_threshold', 100],
]

const RULES: Schemas['RuleResponse'][] = RULE_VALUES.map(([namespace, key, value]) => ({
  namespace,
  key,
  value,
  default: value,
  minimum: 0,
  maximum: 100000,
  group: 'Gods',
  label: key,
  integer: true,
}))

const CATALOGUE = {
  enums: {},
  entity_types: [
    { key: 'people', label: 'People', plural: 'Peoples', containers: [], location_required: false, stats: [] },
    { key: 'settlement', label: 'Settlement', plural: 'Settlements', containers: [], location_required: true, stats: [] },
    { key: 'mortal', label: 'Mortal', plural: 'Mortals', containers: [], location_required: false, stats: [] },
    { key: 'legend', label: 'Legend', plural: 'Legends', containers: [], location_required: false, stats: [] },
  ],
  bond_kinds: [
    { key: 'protects', label: 'Protects', category: 'care', fate_suggestable: true, weavable: true, link_groups: ["all", "no_location"] },
    { key: 'enemy', label: 'Enemy', category: 'conflict', fate_suggestable: true, weavable: true, link_groups: ["all", "no_location", "conflict"] },
  ],
  domains: [
    { key: 'sea', label: 'Sea' },
    { key: 'oath', label: 'Oath' },
    { key: 'dream', label: 'Dream' },
    { key: 'border', label: 'Border' },
    { key: 'fire', label: 'Fire' },
    { key: 'ash', label: 'Ash' },
    { key: 'moon', label: 'Moon' },
    { key: 'glass', label: 'Glass' },
  ],
  link_groups: [{"key": "all", "label": "All links", "kinds": ["ally", "apprentice_of", "beat", "blessed", "built", "captain_of", "caused", "celebrates", "commands", "companion", "created", "cursed", "descends_from", "destroyed", "discovered", "enemy", "fears", "forbids", "holds_captive", "hunts", "in_world", "inside", "killed", "knows", "lives_in", "loves", "member_of", "migrated_to", "owes", "owns", "part_of", "party_to", "passenger_of", "pays_tribute", "produced", "prophesies", "protects", "pursues", "related", "rival", "route", "rules", "soul_descended_to", "source_of", "speaks", "spy_network", "tamed", "tells_of", "trades_with", "truce", "worships"]}, {"key": "travel", "label": "Travel and trade network", "kinds": ["captain_of", "discovered", "migrated_to", "passenger_of", "pays_tribute", "route", "trades_with"]}, {"key": "no_location", "label": "Excluding location links", "kinds": ["ally", "apprentice_of", "beat", "blessed", "built", "captain_of", "caused", "celebrates", "commands", "companion", "created", "cursed", "descends_from", "destroyed", "discovered", "enemy", "fears", "forbids", "holds_captive", "hunts", "in_world", "killed", "knows", "lives_in", "loves", "member_of", "migrated_to", "owes", "owns", "part_of", "party_to", "passenger_of", "pays_tribute", "produced", "prophesies", "protects", "pursues", "related", "rival", "route", "rules", "soul_descended_to", "source_of", "speaks", "spy_network", "tamed", "tells_of", "trades_with", "truce", "worships"]}, {"key": "conflict", "label": "Conflict", "kinds": ["beat", "caused", "cursed", "destroyed", "enemy", "holds_captive", "hunts", "killed", "party_to", "pursues", "rival"]}, {"key": "faith", "label": "Faith and narrative", "kinds": ["blessed", "celebrates", "prophesies", "soul_descended_to", "tells_of", "worships"]}, {"key": "lineage", "label": "Lineage, property and making", "kinds": ["apprentice_of", "built", "commands", "created", "descends_from", "member_of", "migrated_to", "owns", "part_of", "produced", "rules"]}, {"key": "knowledge", "label": "Knowledge, language and trade", "kinds": ["ally", "knows", "owes", "source_of", "speaks", "trades_with", "truce"]}],
  world_types: [],
  chronicle_kinds: [],
  creature_traits: [],
  passions: [],
}

const SETTINGS: Schemas['WorldSettingsView'] = {
  fate_mode: 'auto',
  son_distribution: 'auto',
  mortal_agents_per_epoch: null,
  council_every_epochs: null,
  mortal_agent_parallelism: null,
  llm_enabled: true,
  image_generation: false,
  image_style: 'photoreal',
  image_style_custom: '',
}

const LEDGER: Schemas['LedgerPage'] = {
  current_epoch: EPOCH,
  epochs: [],
  entries: [
    {
      entry: { id: 900, epoch: 11, actor_kind: 'son', actor_node_id: 7, actor_name: 'Thalassir', tool: 'create_structure', action_kind: 'create_entity', input_summary: 'A lighthouse temple above Oskar', undone: false, undone_at: null, applied: [], conflicts: [], created_at: NOW },
      label: 'Raised a structure',
      change_count: 3,
      rows: [],
      dependents: [],
    },
  ],
}

const CHAT: Schemas['MessageRecord'][] = [
  { id: 401, epoch: 11, sender_node_id: 1, recipient_node_id: 7, intent: 'chat', text: 'Why do the bells ring at night?', request: null, wish: null, is_read: true, answered: true, answered_epoch: 11, answer_essence: null, created_at: NOW },
  { id: 402, epoch: 11, sender_node_id: 7, recipient_node_id: 1, intent: 'chat', text: 'To remind the drowned that someone still counts them, father.', request: null, wish: null, is_read: true, answered: false, answered_epoch: null, answer_essence: null, created_at: NOW },
]

const ACCEPTED = { action: 'mock', message: 'Done.', essence_spent: 0, essence_gained: 0 }

const GET_ROUTES: Record<string, unknown> = {
  '/api/state': GOD_STATE,
  '/api/sons': SONS,
  '/api/sons/relations': RELATIONS,
  '/api/sons/7': SON_DETAIL,
  '/api/sons/7/opportunities': { subject_id: 7, lines: OPPORTUNITY_LINES },
  '/api/sons/9/opportunities': { subject_id: 9, lines: OPPORTUNITY_LINES },
  '/api/sons/10/opportunities': { subject_id: 10, lines: [] },
  '/api/sons/7/tools': TOOL_VIEW,
  '/api/sons/9/tools': { ...TOOL_VIEW, son_id: 9 },
  '/api/sons/10/tools': { ...TOOL_VIEW, son_id: 10 },
  '/api/opportunities/creator': { lines: [{ kind: 'unanswered_prayers', text: '3 prayers await an answer: answering raises loyalty and faith.' }, { kind: 'rich_essence', text: 'You have 900 essence: enough for a new world, son or star.' }] },
  '/api/sons/7/chat': CHAT,
  '/api/sons/9': { ...SON_DETAIL, son: SON_RECORDS.find((record) => record.id === 9) ?? SON_RECORDS[0] },
  '/api/sons/9/chat': CHAT,
  '/api/sons/10': { ...SON_DETAIL, son: SON_RECORDS.find((record) => record.id === 10) ?? SON_RECORDS[0] },
  '/api/sons/10/chat': CHAT,
  '/api/sons/10/resurrection': {
    son_id: 10,
    name: 'Mirel',
    death_epoch: 9,
    death_cause: 'killed_by_sibling',
    earliest_return_epoch: 12,
    epochs_remaining: 3,
    devotion: 40,
    devotion_required: 100,
    corpse: { id: 45, name: `The remains of ${LONG}`, title: null, entity_type: 'item', subtype: null, status: 'active', world_id: 1, location_id: null, power_level: 0, birth_epoch: 9, end_epoch: null, importance: null, favorite: false, pending_name: false },
    orders: [{ id: 43, name: LONG, devotion: 40, followers: 18 }],
    loyal_communities: [{ id: 44, name: 'The Brine-Singers of the Ninth Shore' }],
  },
  '/api/creator': CREATOR_DETAIL,
  '/api/creator/reputation': REPUTATION,
  '/api/foreign-gods': [FOREIGN_GOD],
  '/api/foreign-gods/3': FOREIGN_DETAIL,
  '/api/prayers': PRAYERS,
  '/api/councils': COUNCILS,
  '/api/goals': GOALS,
  '/api/opportunities': HINTS,
  '/api/cosmos/epoch-star': {
    current: [{ world_id: 1, world_name: 'Aerona', star: { id: 42, name: LONG, title: null, entity_type: 'star', subtype: null, status: 'active', world_id: 1, location_id: null, power_level: 0, birth_epoch: 1, end_epoch: null, importance: null, favorite: false, pending_name: false } }],
    history: [
      { epoch: 11, entity_id: 42, name: LONG, text: `In epoch 11 the star ${LONG} rose above the drowned bells.` },
      { epoch: 10, entity_id: null, name: null, text: 'In epoch 10 no star rose; the sky stayed dark.' },
      { epoch: 9, entity_id: 44, name: 'Brine-Star', text: 'In epoch 9 Brine-Star was seen from every shore.' },
    ],
  },
  '/api/expeditions': [
    { thread_id: 3, kind: 'dead_star', name: 'Rekindle the Dead Star', text: `A great expedition to rekindle ${LONG}.`, declared_by: 'creator', opened_epoch: 9, deadline_epoch: 15, epochs_remaining: 4, thread_status: 'open', outcome: null, target_star_id: 2, target_route_id: null, target_entity_id: null },
    { thread_id: 1, kind: 'sealed_gate', name: 'Unseal the Gate', text: 'The sealed gate must open before the tide turns.', declared_by: 'son', opened_epoch: 5, deadline_epoch: 12, epochs_remaining: 1, thread_status: 'open', outcome: null, target_star_id: null, target_route_id: 1, target_entity_id: null },
    { thread_id: 2, kind: 'archive', name: 'Recover the Archive', text: 'The archive of the salt-masons.', declared_by: 'fate', opened_epoch: 2, deadline_epoch: 6, epochs_remaining: 0, thread_status: 'closed', outcome: 'completed', target_star_id: null, target_route_id: null, target_entity_id: 42 },
  ],
  '/api/threads': THREADS,
  '/api/rules': RULES,
  '/api/actions': [],
  '/api/catalogue': CATALOGUE,
  '/api/settings': SETTINGS,
  '/api/names': [],
  '/api/images': [],
}

export function godResponse(method: string, url: URL): unknown {
  const route = url.pathname
  if (method === 'GET') {
    if (route === '/api/ledger' && url.searchParams.get('actor_kind') === 'son') return LEDGER
    return GET_ROUTES[route]
  }
  if (route.startsWith('/api/sons') || route.startsWith('/api/creator') || route.startsWith('/api/foreign-gods') || route.startsWith('/api/prayers')) return ACCEPTED
  return undefined
}
