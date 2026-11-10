import { readFileSync } from 'node:fs'
import path from 'node:path'

function fixture<T>(name: string): T {
  return JSON.parse(readFileSync(path.resolve(import.meta.dirname, 'fixtures', name), 'utf8')) as T
}

const ACTIONS = fixture<unknown[]>('actions.json')
const COSMOS_FIXTURE = fixture<{ cosmos: unknown }>('cosmos.json')
const MAP_GRAPH = fixture<{ catalogue: unknown }>('mapGraph.json')

const NOW = '2026-01-01T12:00:00+00:00'
const WORLD = 3
const MOON = 5
const PIXEL_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='

export const LORE_PIXEL = Buffer.from(PIXEL_PNG, 'base64')

const LORE_SCREENS = /^\/(atlas|chronicle|languages|gallery)(\/|$)/

export function onLoreScreen(referer: string | undefined): boolean {
  if (!referer) return false
  const url = new URL(referer)
  return LORE_SCREENS.test(url.pathname) || /drawer=[^&]*entity/.test(url.search)
}

type Summary = {
  id: number
  name: string
  type: string
  world?: number
  location?: number | null
  subtype?: string | null
  status?: string
  epoch?: number
  favorite?: boolean
  importance?: number | null
}

function summary(item: Summary) {
  return {
    id: item.id,
    name: item.name,
    title: null,
    entity_type: item.type,
    subtype: item.subtype ?? null,
    status: item.status ?? 'canon',
    world_id: item.world ?? WORLD,
    location_id: item.location ?? null,
    power_level: (item.id % 7) + 1,
    birth_epoch: item.epoch ?? 1,
    end_epoch: null,
    importance: item.importance ?? 5,
    favorite: item.favorite ?? false,
    pending_name: false,
  }
}

const ENTITIES = [
  summary({ id: 41, name: 'Ashreach, the Salt Steppe Where the Wind Remembers Every Caravan', type: 'region', subtype: 'salt steppe' }),
  summary({ id: 42, name: 'The Crystal Ossuary of Vel, Where the Drowned Kings Sing', type: 'structure', location: 43, epoch: 2, favorite: true }),
  summary({ id: 43, name: 'Velmora-under-the-Glass', type: 'settlement', location: 41, subtype: 'harbour town of brine-glass', epoch: 1 }),
  summary({ id: 44, name: 'The Brine-Singers of the Ninth Shore', type: 'people', epoch: 1 }),
  summary({ id: 45, name: 'Orun the Pale, Keeper of the Last Lantern of Velmora', type: 'mortal', location: 43, epoch: 3 }),
  summary({ id: 46, name: 'Old Brine Tongue', type: 'language', epoch: 1 }),
  summary({ id: 47, name: 'Low Vel', type: 'language', epoch: 4 }),
  summary({ id: 48, name: 'Salt Reading', type: 'knowledge', epoch: 2 }),
  summary({ id: 49, name: 'The Song of the Glass That Remembers', type: 'legend', epoch: 3 }),
  summary({ id: 50, name: 'The War of the Glass Wells', type: 'event', epoch: 5, subtype: 'war' }),
  summary({ id: 51, name: 'The Ash Choir', type: 'cult', world: MOON, epoch: 6 }),
  summary({ id: 52, name: 'A Drowned Lantern Nobody Remembers', type: 'item', status: 'rejected', epoch: 6 }),
]

const ref = (id: number) => {
  const entity = ENTITIES.find((item) => item.id === id)
  return { id, kind: 'entity', name: entity?.name ?? `Record ${id}` }
}

function bond(id: number, kind: string, other: { id: number; kind: string; name: string } | null, outgoing: boolean, extra: Record<string, unknown> = {}) {
  return {
    id,
    source_node_id: outgoing ? 43 : (other?.id ?? 0),
    target_node_id: outgoing ? (other?.id ?? 0) : 43,
    kind,
    description: null,
    role: null,
    epoch: 2,
    state: 'active',
    closed_epoch: null,
    closed_reason: null,
    war_id: null,
    debt_amount: null,
    debt_what: null,
    debt_due_epoch: null,
    debt_status: null,
    outgoing,
    other,
    ...extra,
  }
}

const BONDS = [
  bond(1, 'inside', ref(41), true),
  bond(2, 'party_to', ref(50), true, { war_id: 1, role: 'side' }),
  bond(3, 'ally', ref(44), true, { description: 'sworn on the glass wells in the year of the white tide' }),
  bond(4, 'owes', ref(44), true, { debt_amount: 12, debt_what: 'barrels of brine-glass', debt_due_epoch: 8, debt_status: 'open' }),
  bond(5, 'knows', ref(48), true),
  bond(6, 'speaks', ref(46), true),
  bond(7, 'worships', { id: 7, kind: 'son', name: 'Ithren the Unbowed' }, true),
  bond(8, 'enemy', ref(51), true, { state: 'past' }),
  bond(9, 'holds_captive', ref(45), true),
  bond(10, 'pays_tribute', ref(44), false),
]

function line(id: number, epoch: number, kind: string, text: string, ids: number[] = [], world = WORLD) {
  return { id, epoch, year: 1100 + epoch * 20 + (id % 5), kind, son_id: null, world_id: world, text, created_at: NOW, entity_ids: ids }
}

const LINES = [
  line(1, 1, 'creation', 'Ithren raised Velmora-under-the-Glass from the brine, and the glass remembered the first song.', [43]),
  line(2, 1, 'birth', 'The Brine-Singers of the Ninth Shore were born of the white tide.', [44]),
  line(3, 2, 'construction', 'The Crystal Ossuary of Vel, Where the Drowned Kings Sing, was raised under Velmora-under-the-Glass.', [42, 43]),
  line(4, 3, 'birth', 'Orun the Pale, Keeper of the Last Lantern of Velmora, opened his eyes in a house of salt.', [45, 43]),
  line(5, 5, 'war', 'The War of the Glass Wells began when Velmora-under-the-Glass refused the tithe.', [50, 43]),
  line(6, 5, 'death', 'Three hundred drowned in the glass wells; the songs of the drowned kings grew louder.', [42]),
  line(7, 6, 'fate', 'Fate struck A Drowned Lantern Nobody Remembers from the canon.', [52]),
  line(8, 7, 'engine_raw', 'tick 7: prosperity +2', [43]),
  line(9, 7, 'trade', 'Velmora-under-the-Glass sold brine-glass to the Brine-Singers of the Ninth Shore.', [43, 44]),
  line(10, 6, 'horror', 'On the Hollow Moon of Ashes the Ash Choir sang a note nobody could hear.', [51], MOON),
]

const EPOCHS = [6, 5, 4, 3, 2, 1].map((epoch) => ({
  epoch,
  name: epoch === 6 ? 'The Age of Brine and Whispering Crystal, When the Kings Under the Glass Began to Sing' : `The ${['First', 'Second', 'Third', 'Fourth', 'Fifth'][epoch - 1]} Tide`,
  narrative:
    epoch >= 5
      ? 'The glass wells ran red and then white again. Velmora counted its dead in songs, and the ossuary learned new verses every night. The Brine-Singers kept their oath, though it cost them a harbour.'
      : null,
  summary: `Epoch ${epoch} of salt and memory.`,
  year_start: 1100 + epoch * 20,
  year_end: 1119 + epoch * 20,
  closed_at: NOW,
  chronicler_name: epoch >= 5 ? 'Maelis of the Lantern' : null,
  chronicler_identity: epoch >= 5 ? 'a blind archivist who reads salt by touch' : null,
  worlds:
    epoch === 6
      ? [
          { world_id: WORLD, world_name: 'Saltreach', narrative: 'Saltreach mourned and traded.', summary: null },
          { world_id: MOON, world_name: 'The Hollow Moon of Ashes', narrative: 'The moon sang in silence.', summary: null },
        ]
      : [],
}))

const COUNTS = [1, 2, 3, 5, 6, 7].map((epoch) => ({
  epoch,
  name: EPOCHS.find((item) => item.epoch === epoch)?.name ?? null,
  lines: LINES.filter((item) => item.epoch === epoch).length,
}))

const PERSPECTIVES = [
  { id: 1, epoch: 6, people_id: 44, people_name: 'The Brine-Singers of the Ninth Shore', historian: 'Oda Three-Voices', text: 'It was we who held the wells; Velmora only watched and counted coins.' },
]

const COSMIC = [7, 6, 5].map((epoch) => ({
  epoch,
  name: EPOCHS.find((item) => item.epoch === epoch)?.name ?? null,
  summary: null,
  worlds: [
    { world_id: WORLD, name: 'Saltreach', event_count: epoch === 5 ? 3 : 1, headlines: ['The War of the Glass Wells began when Velmora-under-the-Glass refused the tithe.'], summary: null, narrative: null },
    { world_id: MOON, name: 'The Hollow Moon of Ashes', event_count: epoch === 6 ? 1 : 0, headlines: epoch === 6 ? ['The Ash Choir sang a note nobody could hear.'] : [], summary: null, narrative: null },
  ],
}))

const IMAGES = [
  { id: 1, target_node_id: 42, file_name: 'ossuary.png', mime: 'image/png', origin: 'generated', caption: 'The singing ossuary at the hour of the white tide', prompt: 'A crystal ossuary under a salt town, drowned kings in glass, moonlight', is_cover: true, size_bytes: 1000, width: 640, height: 640, created_at: NOW },
  { id: 2, target_node_id: 42, file_name: 'ossuary-hall.png', mime: 'image/png', origin: 'uploaded', caption: null, prompt: null, is_cover: false, size_bytes: 1000, width: 640, height: 640, created_at: NOW },
]

const INSIGHT_SETTLEMENT = {
  society: {
    shares: { farmer: 0.4, artisan: 0.2, merchant: 0.15, priest: 0.1, warrior: 0.1, scribe: 0.05 },
    satisfaction: { farmer: 31, artisan: 62, merchant: 70, priest: 55, warrior: 18, scribe: 80 },
    stocks: { food: 140, ore: 30, goods: 75 },
    prices: { food: 90, ore: 190, goods: 100 },
    unhappiest: 'warrior',
    bankruptcy_risk: false,
    uprising_risk: true,
  },
  capacity: { capacity: 4000, region_population: 4300, occupancy_pct: 108, region: ref(41) },
  exploration: { regions: 3, places: 5, communities: 4, pressure: 2, narrow: true },
  ancestors: [],
  descendants: [],
}

const INSIGHT_MORTAL = {
  life: { age: 61, lifespan: 74, lifespan_base: 60, medicine_bonus: 6, notable_bonus: 8, immortal: false, death_year: null, kill_chance_pct: 35, son_kill_cost: 18, creator_kill_cost: 15 },
  ancestors: [ref(44)],
  descendants: [],
}

function record(id: number) {
  const base = ENTITIES.find((item) => item.id === id) ?? ENTITIES[1]
  const stats: Record<string, unknown> = { kind: base.entity_type }
  if (base.entity_type === 'settlement') Object.assign(stats, { population: 4300, prosperity: 64, defense: 41, piety: 77 })
  if (base.entity_type === 'mortal') Object.assign(stats, { hp: 80, strength: 34, agility: 51, intellect: 88, charisma: 72, age: 61, lifespan: 74 })
  if (base.entity_type === 'structure') Object.assign(stats, { splendor: 93, durability: 70, function: 45 })
  return {
    ...base,
    description:
      'Under Velmora-under-the-Glass the drowned kings sleep in walls of brine-glass. The Brine-Singers of the Ninth Shore say the ossuary hums before every storm, and Orun the Pale, Keeper of the Last Lantern of Velmora, keeps its door.',
    stats,
    domain: 'salt',
    origin: 'son',
    creator_son_id: 7,
    mortal_role: base.entity_type === 'mortal' ? 'hero' : null,
    legend_category: null,
    fate_note: id === 42 ? 'Accepted: the ossuary binds the town to its dead, and the dead to the town.' : null,
    depth:
      id === 42
        ? {
            history: 'Built in the second tide by salt-masons who never spoke again.',
            rumours: ['A tenth king sleeps in a wall nobody has found.'],
            sayings: [{ form: 'proverb', text: 'What the glass keeps, the glass sings.' }],
            details: ['Its door opens only at low tide.'],
            hidden_truth: 'The kings are not dead; they are listening.',
            specifics: { keeper: 'Orun the Pale' },
            epoch: 4,
          }
        : null,
    archive_override: null,
    private_note: id === 42 ? 'Ask Ithren about the tenth king.' : null,
    map_x: 0.4,
    map_y: 0.3,
    image_prompt: id === 42 ? IMAGES[0].prompt : null,
    civ_tier: base.entity_type === 'settlement' ? 2 : null,
    sanity: base.entity_type === 'mortal' ? 34 : null,
    last_acted_epoch: base.entity_type === 'settlement' ? 6 : 0,
    is_underworld: false,
    is_water: false,
  }
}

function detail(id: number) {
  const entity = record(id)
  const community = entity.entity_type === 'settlement'
  return {
    entity,
    cover: id === 42 ? IMAGES[0].file_name : null,
    creator_son: { id: 7, kind: 'son', name: 'Ithren the Unbowed' },
    maker: null,
    patron: community ? { id: 7, kind: 'son', name: 'Ithren the Unbowed' } : null,
    breadcrumb: entity.location_id === 43 ? [ref(41), ref(43)] : entity.location_id === 41 ? [ref(41)] : [],
    contents: community ? [summary({ id: 42, name: ENTITIES[1].name, type: 'structure', location: 43 }), summary({ id: 45, name: ENTITIES[4].name, type: 'mortal', location: 43 })] : [],
    content_total: community ? 2 : 0,
    flags: community ? ['protected_from_ruin', 'agent_selected'] : id === 45 ? ['chosen'] : ['wonder'],
    traits: [],
    tags: community ? ['tier:2'] : [],
    bonds: community ? BONDS : BONDS.slice(0, 1).map((item) => ({ ...item, other: ref(43) })),
    bond_total: community ? BONDS.length : 1,
    chronicle: LINES.filter((item) => item.entity_ids.includes(id)),
    chronicle_total: LINES.filter((item) => item.entity_ids.includes(id)).length,
    facts: [
      { id: 1, subject: ref(id), predicate: 'opens only at', object: null, object_text: 'the lowest tide of the year', epoch: 3 },
      { id: 2, subject: ref(id), predicate: 'is guarded by', object: ref(45), object_text: null, epoch: 4 },
    ],
    perspectives: [],
    similar: [{ entity: summary({ id: 49, name: ENTITIES[8].name, type: 'legend' }), score: 0.62, reasons: ['shared bonds', 'the same maker'] }],
    anchored_sons: [],
    importance: { importance: 14, archived: false, reason: null, last_mention: 6 },
    images: id === 42 ? IMAGES : [],
    insight: community ? INSIGHT_SETTLEMENT : id === 45 ? INSIGHT_MORTAL : {},
  }
}

const NAMES = [
  { kind: 'creator', id: 1, name: 'Aeron', type: 'creator' },
  { kind: 'son', id: 7, name: 'Ithren the Unbowed', type: 'son' },
  ...ENTITIES.map((item) => ({ kind: 'entity', id: item.id, name: item.name, type: item.entity_type, status: item.status, world_id: item.world_id })),
]

const LANGUAGES = [
  {
    language: ENTITIES[5],
    description: 'The tongue of the first tide, thick with words for salt and grief.',
    cover: null,
    speakers: [ref(44), ref(43)],
    words: [
      { id: 1, word: 'velm', meaning: 'glass that remembers', part_of_speech: 'noun', etymology: 'from the first song', example: 'velm ora sang', added_by_kind: 'son', added_by: { id: 7, kind: 'son', name: 'Ithren the Unbowed' }, epoch: 1 },
      { id: 2, word: 'oru', meaning: 'pale, without salt', part_of_speech: 'adjective', etymology: null, example: null, added_by_kind: 'engine', added_by: null, epoch: 3 },
    ],
    word_total: 2,
  },
  { language: ENTITIES[6], description: 'A harbour dialect.', cover: null, speakers: [], words: [], word_total: 0 },
]

const LANGUAGE_TREE = [
  {
    language: ENTITIES[5],
    writing_system: 'notch',
    parent_language_id: null,
    words: 2,
    speakers: 2,
    sample_names: ['Velmora', 'Orun', 'Saelith'],
    signature: { consonants: 'vlmr', cluster: 'th', ending: 'ora', length_bias: 1 },
    alphabet: ['a', 'e', 'i', 'l', 'm', 'o', 'r', 's', 't', 'h', 'v'],
    cognates: [],
  },
  {
    language: ENTITIES[6],
    writing_system: null,
    parent_language_id: 46,
    words: 0,
    speakers: 0,
    sample_names: ['Vellin'],
    signature: null,
    alphabet: ['a', 'e', 'i', 'l', 'n', 'v'],
    cognates: [{ first_word: 'velm', second_word: 'vell', first_meaning: 'glass that remembers', second_meaning: 'window' }],
  },
]

const KNOWLEDGE = [
  { knowledge: ENTITIES[7], description: 'Reading the thoughts kept in salt crystals.', branch: 'writing', level: 2, spread: 40, knowers: [ref(43), ref(44)], inventor: ref(45), prerequisites: [] },
]

const IMAGE_GEN = {
  status: {
    available: false,
    reason: 'No image worker is configured.',
    current: null,
    queue: [],
    bulk: { running: false, stop_requested: false, auto: false, total: 0, done: 0, failed: 0, skipped: 0, started: null, finished: null, rerun_requested: false, restyle: false },
    width: 1024,
    height: 1024,
    steps: 8,
    log: [{ level: 'warning', at: NOW, text: 'The worker is not configured; set IMAGE_WORKER_URL to paint.' }],
  },
  missing: 7,
  off_style: 0,
}

const THREADS = [
  { id: 1, epoch: 5, text: 'Who drowned the three hundred in the glass wells, and why do the kings sing louder since?', status: 'open', closing_text: null, closed_epoch: null, progress: 40, related: [ref(43), ref(42)] },
  { id: 2, epoch: 2, text: 'The salt-masons who never spoke again.', status: 'closed', closing_text: 'Their silence became the ossuary.', closed_epoch: 4, progress: 100, related: [] },
]

function page<T>(items: T[], url: URL) {
  const offset = Number(url.searchParams.get('offset') ?? 0)
  const limit = Number(url.searchParams.get('limit') ?? 100)
  return { items: items.slice(offset, offset + limit), total: items.length, offset, limit }
}

const ACCEPTED_ACTION = { action: 'done', message: 'Done', essence_spent: 0, essence_gained: 0, created_ids: [], values: {} }

export function loreResponse(method: string, url: URL, referer: string | undefined): unknown {
  const route = url.pathname
  const note = /^\/api\/entities\/(\d+)\/note$/.exec(route)
  if (method === 'GET' && note) {
    const id = Number(note[1])
    const found = ENTITIES.find((item) => item.id === id)
    return id === 42 && found ? { entity_id: id, entity_name: found.name, entity_type: found.entity_type, world_id: WORLD, text: 'Ask Ithren about the tenth king.' } : undefined
  }
  if (method !== 'GET') return /^\/api\/(entities|facts|links|beliefs|images|image-gen|threads|languages)/.test(route) ? ACCEPTED_ACTION : undefined
  const extra = /^\/api\/entities\/(\d+)\/(opportunities|agent-context|dreams)$/.exec(route)
  if (extra && onLoreScreen(referer)) {
    const id = Number(extra[1])
    if (extra[2] === 'opportunities') return { subject_id: id, lines: [{ kind: 'at_war', text: 'AT WAR: #43 The Glass Kings. Peace or tribute could end it.', tension: true, tools: ['propose_peace'] }] }
    if (extra[2] === 'dreams') return { entity_id: id, received: [{ id: 1, epoch: 4, sender: { id: 7, kind: 'son', name: 'Ithren the Unbowed' }, recipient: null, text: 'Salt rises from the sea.', is_read: false }], sent: [] }
    return { entity_id: id, name: 'Agent', epoch: 5, action_points: 6, system_prompt: 'You are a people of salt.', user_prompt: 'Epoch 5. What do you do?', available: [{ name: 'propose_peace', description: 'Offer peace to an enemy.', fields: {}, action_cost: 1, essence_cost: 0, read_only: false, long_job: false, minimum_rarity: null }], blocked: [], counters: [] }
  }
  const entity = /^\/api\/entities\/(\d+)(\/(bonds|chronicle))?$/.exec(route)
  if (entity) {
    const id = Number(entity[1])
    if (!ENTITIES.some((item) => item.id === id)) return undefined
    if (entity[3] === 'bonds') return page(detail(id).bonds, url)
    if (entity[3] === 'chronicle') return page(detail(id).chronicle, url)
    return detail(id)
  }
  if (route === '/api/entities') return page(ENTITIES, url)
  if (route === '/api/epochs') return EPOCHS
  if (route === '/api/chronicle/epochs') return COUNTS
  if (route === '/api/chronicle/perspectives') return PERSPECTIVES
  if (route === '/api/chronicle/cosmic') return COSMIC
  if (route === '/api/chronicle') {
    const epoch = Number(url.searchParams.get('epoch') ?? 0)
    const items = epoch ? LINES.filter((item) => item.epoch === epoch) : LINES
    return { items, total: items.length }
  }
  if (route === '/api/languages/tree') return LANGUAGE_TREE
  if (route === '/api/knowledge') return KNOWLEDGE
  if (route === '/api/gallery/missing') return ENTITIES.slice(2, 6)
  if (route === '/api/image-gen') return IMAGE_GEN
  if (!onLoreScreen(referer)) return undefined
  if (route === '/api/languages') return LANGUAGES
  if (route === '/api/names') return NAMES
  if (route === '/api/actions') return ACTIONS
  if (route === '/api/catalogue') return MAP_GRAPH.catalogue
  if (route === '/api/cosmos') return COSMOS_FIXTURE.cosmos
  if (route === '/api/threads') return THREADS
  if (route === '/api/images') return IMAGES.map((image) => ({ image, target_name: ENTITIES[1].name, target_kind: 'entity', target_world_id: WORLD }))
  if (route === '/api/graph/path') return { path: [42, 43, 7], names: { 42: ENTITIES[1].name, 43: ENTITIES[2].name, 7: 'Ithren the Unbowed' }, steps: [{ source: 42, target: 43, kind: 'inside', forward: true, description: null }, { source: 43, target: 7, kind: 'worships', forward: true, description: 'since the first tide' }], found: true }
  return undefined
}
