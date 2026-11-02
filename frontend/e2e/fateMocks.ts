const LONG_SON = 'Vaelithrandor of the Ninefold Unspoken Dawn, Keeper of Salt-Tides'
const LONG_RECORD = 'The Crystal Ossuary of Vel, Where the Drowned Kings Sing Beneath the Weeping Salt Marshes'
const LONG_PEOPLE = 'The Grand Confederation of the Seven Glass Harbours and Their Many Allied Free Cities'

export const OPERATOR_NAMES = [
  { kind: 'creator', id: 1, name: 'Aeron', type: 'creator' },
  { kind: 'son', id: 7, name: LONG_SON, type: 'Legendary' },
  { kind: 'son', id: 4, name: 'Ithren', type: 'Rare' },
  { kind: 'world', id: 3, name: 'Velmora, the Drowned Crown of the Western Tides', type: 'world' },
  { kind: 'world', id: 5, name: 'Ashkar', type: 'world' },
  { kind: 'foreign_god', id: 3, name: 'The Hollow Star That Swallowed Its Own Name', type: 'foreign god' },
  { kind: 'entity', id: 42, name: LONG_RECORD, type: 'structure', world_id: 3 },
  { kind: 'entity', id: 43, name: 'Harrowmere', type: 'settlement', world_id: 3 },
  { kind: 'entity', id: 44, name: LONG_PEOPLE, type: 'people', world_id: 3 },
  { kind: 'entity', id: 45, name: 'The Salt Choir', type: 'people', world_id: 5 },
]

const action = (id: string, title: string, mode: 'job' | 'ledgered', cost: string) => ({
  id,
  title,
  group: 'fate',
  mode,
  cost,
  confirmation: null,
  rows: [],
  path: `/api/actions/${id}`,
  method: 'POST',
  input_schema: { type: 'object', properties: {} },
})

export const OPERATOR_ACTIONS = [
  action('fate:retry', 'Retry Fate for the last epoch', 'job', '30 essence'),
  action('fate:rejudge_debt', "Re-judge Fate's debt now", 'job', '30 essence'),
  action('fate:rejudge_limbo', 'Re-judge the creations in limbo', 'job', '30 essence'),
  action('fate:override_verdict', "Overrule Fate's verdict on a creation", 'ledgered', '15 essence'),
  action('voices:retry', 'Run the voices of the peoples again', 'job', '20 essence'),
  action('voices:edit_view', "Amend a historian's account", 'ledgered', '5 essence'),
  action('voices:delete_view', "Strike a historian's account", 'ledgered', '5 essence'),
  action('births:retry', 'Retry the births of sensed worlds', 'job', '25 essence'),
]

const FATE_CONTROLS = {
  last_epoch: 6,
  fate_debt_epoch: 5,
  limbo: [
    {
      entity_id: 42,
      name: LONG_RECORD,
      born_epoch: 5,
      rationale:
        'The ossuary claims the drowned kings of an age that the chronicle never recorded; Fate could not tell whether it contradicts the founding of Harrowmere or simply predates it.',
    },
    { entity_id: 43, name: 'Harrowmere', born_epoch: 6, rationale: null },
  ],
  steps: [
    { step: 'fate_judgment', status: 'failed', error: 'The model did not answer in time; Fate owes epoch 5.' },
    { step: 'chronicle', status: 'failed', error: 'The chronicler stopped before the second world.' },
    { step: 'voices', status: 'done', error: null },
    { step: 'world_birth', status: 'failed', error: null },
  ],
  failed_births: 2,
  views: [
    {
      id: 1,
      people_entity_id: 44,
      historian: 'Ossa the Salt-Tongued, Archivist of the Seventh Harbour',
      text: 'In the sixth epoch the harbours remembered their old oaths. The glass fleets sailed against the marsh-kings, and though the tide favoured them, the songs say the drowned answered with a silence so deep that even the gulls forgot to cry.',
    },
    { id: 2, people_entity_id: 45, historian: null, text: 'We sang, and the salt listened.' },
  ],
}

function onOperatorScreen(referer: string | undefined): boolean {
  if (!referer) return false
  const path = new URL(referer).pathname
  return path.startsWith('/settings/fate') || path.startsWith('/settings/prompts') || path.startsWith('/settings/maintenance') || path === '/epoch'
}

export function fateResponse(method: string, url: URL, referer: string | undefined): unknown {
  const route = url.pathname
  if (method !== 'GET') return undefined
  if (route === '/api/fate/controls') return FATE_CONTROLS
  if (!onOperatorScreen(referer)) return undefined
  if (route === '/api/names') return OPERATOR_NAMES
  if (route === '/api/actions') return OPERATOR_ACTIONS
  return undefined
}
