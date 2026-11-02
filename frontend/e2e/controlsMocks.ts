const LONG = 'Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin'

const ACCEPTED = {
  action: 'done',
  message: 'The deed is done.',
  essence_spent: 0,
  essence_gained: 0,
  target_node_id: null,
  created_ids: [],
  ledger_entry_id: null,
  values: {},
  job_id: null,
}

function ref(id: number, name: string) {
  return { id, kind: 'entity', name }
}

function summary(id: number, name: string, type: string, world = 3) {
  return {
    id,
    name,
    title: null,
    entity_type: type,
    subtype: null,
    status: 'canon',
    world_id: world,
    location_id: null,
    power_level: 2,
    birth_epoch: 1,
    end_epoch: null,
    importance: null,
    favorite: false,
    pending_name: false,
  }
}

const ADDICTIONS = [
  {
    community: ref(43, 'Velmora-under-the-Glass'),
    resource: ref(90, `Dream Salt of ${LONG}`),
    owned_epochs: 6,
    addicted_since_epoch: 5,
    withdrawal_since_epoch: null,
  },
  {
    community: ref(44, `The Brine-Singers of ${LONG}`),
    resource: ref(91, 'Ember Moss'),
    owned_epochs: 4,
    addicted_since_epoch: 7,
    withdrawal_since_epoch: 9,
  },
]

const LAWS = [
  { entity: summary(61, `The Law of Returning Tides of ${LONG}`, 'natural_law'), mechanic: 'dead_return' },
  { entity: summary(62, 'The Salt Oath', 'law'), mechanic: null },
]

const GEOGRAPHY = [
  'Known regions: 3.',
  `- Salt Flats: lowland, coastal, large; salt marsh, dunes; neighbours ${LONG}, Glass Reach.`,
  '- Glass Reach: highland, inland, small; crystal scree; neighbours Salt Flats.',
].join('\n')

const DISTRIBUTION = {
  candidates: [
    { son_id: 8, name: LONG, world_id: 1, score: 42, protected: false },
    { son_id: 7, name: 'Thalassir', world_id: 1, score: 30, protected: true },
    { son_id: 9, name: 'Kharun the Ashen', world_id: 2, score: 12, protected: false },
  ],
  next_son_id: 8,
  godless_world_ids: [2],
}

const PAIR = {
  first: ref(43, 'Velmora-under-the-Glass'),
  second: ref(44, `The Brine-Singers of ${LONG}`),
  value: -35,
  label: 'hostile',
  blood_feud_since_epoch: 6,
  history: [
    { epoch: 6, event: 'a blood feud was declared', delta: -30 },
    { epoch: 7, event: 'raids on the border', delta: -5 },
  ],
}

const SAMPLE_NAMES = ['Velmora', 'Ashkareth', 'Orrin', 'Thessaly', `Vael${LONG.slice(0, 18)}`, 'Mirevast']

const WRITES = /^\/api\/actions\/(language:(edit|signature|epoch_words)|cosmic:extinguish_star|intuition:discard(_all)?|economy:(resources|cosmic)|addiction:cure|son:outer_bargain|world:map)$/

export function controlsResponse(method: string, url: URL): unknown {
  const route = url.pathname
  if (method === 'POST') {
    if (/^\/api\/languages\/\d+\/sample-names$/.test(route)) return { language_id: 47, names: SAMPLE_NAMES }
    if (/^\/api\/sons\/\d+\/(scheme|scatter-bones)$/.test(route)) return ACCEPTED
    return WRITES.test(route) ? ACCEPTED : undefined
  }
  if (method !== 'GET') return undefined
  if (route === '/api/addictions') {
    const community = Number(url.searchParams.get('community_id'))
    return community ? ADDICTIONS.filter((item) => item.community.id === community) : ADDICTIONS
  }
  if (/^\/api\/worlds\/\d+\/laws$/.test(route)) return LAWS
  if (/^\/api\/worlds\/\d+\/geography$/.test(route)) return { world_id: 3, text: GEOGRAPHY }
  if (route === '/api/sons/distribution-preview') return DISTRIBUTION
  if (/^\/api\/entities\/\d+\/relations\/\d+$/.test(route)) return PAIR
  return undefined
}
