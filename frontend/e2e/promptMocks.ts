const LONG_SON = 'Vaelithrandor of the Ninefold Unspoken Dawn, Keeper of Salt-Tides'

const BLOCKS = [
  { kind: 'world-header', needs_son: false, needs_entity: false, audience: 'every agent', rows: ['CTX-004'] },
  { kind: 'world-summary', needs_son: false, needs_entity: false, audience: 'son, Fate', rows: ['CTX-014'] },
  { kind: 'son-memory', needs_son: true, needs_entity: false, audience: 'son, council, son chat', rows: ['CTX-029'] },
  { kind: 'entity-detail', needs_son: false, needs_entity: true, audience: 'inspect tools, Fate', rows: ['CTX-025'] },
  { kind: 'tired-images', needs_son: false, needs_entity: false, audience: 'son, Fate', rows: ['CTX-019'] },
]

const WORLD_HEADER = [
  'WORLD: Velmora, the Drowned Crown of the Western Tides (ocean world, epoch 6, year 1240)',
  'TONE: gloomy, merciless, hope comes at a high price',
  'MAGIC 60 / DARKNESS 80 / TECHNOLOGY iron',
  'LORE LANGUAGE: English',
  'The Grand Confederation of the Seven Glass Harbours and Their Many Allied Free Cities holds the western coast; the Salt Choir sings in the marshes.',
].join('\n')

const SYSTEM_PROMPT = [
  `SON: ${LONG_SON}, legendary son of Aeron, domains sea and memory.`,
  'STANDING ORDER: keep the harbours at peace until the council meets.',
  'RULES: every creation must fit the canon; Fate judges it when the epoch ends.',
  '',
  WORLD_HEADER,
].join('\n')

const USER_PROMPT = [
  'EPOCH 6. You have 4 actions.',
  'RECENT: The Salt War began between Harrowmere and the Glass Harbours.',
  'THREADS: The tenth king of Vel; the silence of the gulls.',
  'MEMORY: In epoch 5 you raised the Crystal Ossuary of Vel beneath the marshes.',
].join('\n')

const SON_PROMPT = {
  son_id: 7,
  son_name: LONG_SON,
  epoch: 6,
  action_points: 4,
  system_prompt: SYSTEM_PROMPT,
  user_prompt: USER_PROMPT,
  system_characters: SYSTEM_PROMPT.length,
  user_characters: USER_PROMPT.length,
  total_characters: 18_420,
  token_estimate: 4_605,
  prompt_limit: 20_000,
  over_limit: false,
  tool_names: ['create_place', 'declare_war', 'inspect_entity', 'read_chronicle', 'bless_people'],
  paid_tools: ['create_place', 'declare_war', 'bless_people'],
  free_tools: ['inspect_entity', 'read_chronicle'],
  summary_sections: [
    { section: 'pantheon', characters: 1_200, limit: 1_500 },
    { section: 'events', characters: 2_950, limit: 3_000 },
    { section: 'geography', characters: 3_400, limit: 3_000 },
    { section: 'legends', characters: 640, limit: null },
  ],
  summary_characters: 8_190,
  summary_limit: 9_000,
  memory_characters: 2_100,
  memory_limit: 4_000,
}

const variable = (name: string, type: string, required = true) => ({ name, type, required })

const PROMPTS = [
  { prompt_id: 'fate_judgment_system', area: 'fate', template_path: 'fate/judgment_system.j2', context: 'FateJudgmentContext', variables: [variable('lore_language', 'str'), variable('criteria', 'list[str]')], output: 'FateVerdicts', has_constraints: true },
  { prompt_id: 'fate_judgment_user', area: 'fate', template_path: 'fate/judgment_user.j2', context: 'FateJudgmentContext', variables: [variable('epoch', 'int'), variable('creations', 'list[CreationEntry]'), variable('warnings', 'list[str]', false)], output: 'FateVerdicts', has_constraints: true },
  { prompt_id: 'son_turn_system', area: 'son_turn', template_path: 'son_turn/system.j2', context: 'SonTurnContext', variables: [variable('son', 'SonLine'), variable('world_header', 'str')], output: null, has_constraints: false },
  { prompt_id: 'chronicler_system', area: 'chronicler', template_path: 'chronicler/system.j2', context: 'ChroniclerContext', variables: [variable('lore_language', 'str')], output: 'ChronicleText', has_constraints: false },
  { prompt_id: 'voices_user', area: 'voices', template_path: 'voices/user.j2', context: 'VoicesContext', variables: [variable('peoples', 'list[PeopleLine]'), variable('epoch', 'int')], output: 'HistorianViews', has_constraints: true },
  { prompt_id: 'cosmos_image_prompts_user', area: 'image_prompts', template_path: 'image_prompts/cosmos_user.j2', context: 'CosmosImageContext', variables: [variable('bodies', 'list[BodyLine]')], output: 'ImagePrompts', has_constraints: false },
]

const tool = (tool_id: string, agent: string, description: string, read_only: boolean, action_cost: number, essence_cost: number) => ({
  tool_id,
  agent,
  description,
  read_only,
  action_cost,
  essence_cost,
  minimum_rarity: tool_id === 'declare_war' ? 'rare' : null,
  long_job: false,
  input_schema: { type: 'object', properties: { name: { type: 'string', title: 'Name' }, world_id: { type: 'integer', title: 'World' } }, required: ['name'] },
})

const CATALOGUE = {
  prompts: PROMPTS,
  son_tools: [
    tool('create_place', 'son', 'Raise a new place in a region of your world; Fate judges it at the end of the epoch.', false, 1, 0),
    tool('declare_war', 'son', 'Lead one community into war against another reachable community.', false, 2, 10),
    tool('inspect_entity', 'son', 'Read everything known about one record.', true, 0, 0),
  ],
  mortal_tools: [tool('pray', 'mortal', 'Pray to your patron for a sign or a blessing.', false, 1, 0)],
}

const TEMPLATE = [
  'Epoch {{ epoch }}. Weigh each creation below against the canon.',
  '{% for creation in creations %}',
  '- {{ creation.name }} ({{ creation.kind }}): {{ creation.summary }}',
  '{% endfor %}',
  '{% if warnings %}Warnings: {{ warnings | join("; ") }}{% endif %}',
].join('\n')

const SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: { entity_id: { type: 'integer' }, verdict: { enum: ['accepted', 'rejected', 'limbo'] }, rationale: { type: 'string' }, motifs: { type: 'array', items: { type: 'string' } } },
        required: ['entity_id', 'verdict'],
      },
    },
  },
  required: ['verdicts'],
}

function detail(promptId: string) {
  const entry = PROMPTS.find((item) => item.prompt_id === promptId) ?? PROMPTS[0]
  return { ...entry, template_source: TEMPLATE, output_schema: entry.output ? SCHEMA : null }
}

const MOTIFS = {
  world_id: null,
  motifs: [
    { key: 'weeping moon', percent: 34, pinned: false },
    { key: 'drowned king', percent: 21, pinned: true },
    { key: 'glass that remembers the first song sung over the drowned', percent: 12, pinned: false },
  ],
  foreign_images: [],
  overrides: [
    { id: 1, world_id: null, motif: 'drowned king', mode: 'pinned' },
    { id: 2, world_id: null, motif: 'silver tide', mode: 'allowed' },
  ],
}

export function promptResponse(method: string, url: URL): unknown {
  const route = url.pathname
  if (!route.startsWith('/api/prompt-context/')) return undefined
  if (method === 'PUT' || method === 'POST') return MOTIFS
  if (route === '/api/prompt-context/blocks') return BLOCKS
  if (route === '/api/prompt-context/catalogue') return CATALOGUE
  if (route.startsWith('/api/prompt-context/catalogue/')) return detail(route.split('/').at(-1) ?? '')
  if (/^\/api\/prompt-context\/son-prompt\/\d+$/.test(route)) return SON_PROMPT
  if (route === '/api/prompt-context/tired-motifs') {
    const world = url.searchParams.get('world_id')
    return world ? { ...MOTIFS, world_id: Number(world), foreign_images: ['drowned king', 'silver tide'] } : MOTIFS
  }
  const kind = route.split('/').at(-1) ?? 'world-header'
  return { kind, text: WORLD_HEADER, characters: WORLD_HEADER.length, token_estimate: Math.round(WORLD_HEADER.length / 4), world_id: 3, son_id: null, entity_id: null }
}
