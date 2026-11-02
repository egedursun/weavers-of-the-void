const LONG = 'The Grand Confederation of the Seven Glass Harbours and Their Many Allied Free Cities'

const ref = (id: number, name: string) => ({ id, kind: 'entity', name })

const WAR = {
  id: 1,
  event: ref(80, 'The Salt War'),
  world_id: 1,
  status: 'ongoing',
  cause: 'declared',
  cause_text: null,
  started_epoch: 4,
  ended_epoch: null,
  last_clash_epoch: 8,
  battles: 3,
  score: 2,
  violence: 40,
  ending: null,
  victor: null,
  loser: null,
  sides: [
    { entity: ref(43, 'Harrowmere'), side: 'attacker', joined_epoch: 4, left_epoch: null },
    { entity: ref(44, LONG), side: 'defender', joined_epoch: 4, left_epoch: null },
  ],
}

const page = (items: unknown[]) => ({ items, total: items.length, offset: 0, limit: 20 })

const PHASES = [
  ['dead_bonds_opening', 'tick', true, false],
  ['diplomacy', 'tick', true, false],
  ['campaigns', 'tick', true, true],
  ['monster_raids', 'tick', false, true],
  ['local_gods', 'pre_transition', true, false],
  ['population_growth', 'transition', true, true],
  ['advance_epoch', 'transition', true, true],
  ['goals', 'post_transition', true, false],
].map(([name, stage, enabled, heavy]) => ({
  name,
  stage,
  enabled,
  essential: name === 'advance_epoch',
  heavy,
  runnable: name !== 'advance_epoch',
  rule_key: name,
}))

const ACCEPTED = {
  action: 'engine:run_phase',
  message: 'The diplomacy step ran now: relations 3.',
  essence_spent: 0,
  essence_gained: 0,
  target_node_id: null,
  created_ids: [],
  ledger_entry_id: null,
  values: {},
  job_id: null,
}

const RELATION = {
  other: ref(44, LONG),
  value: -35,
  label: 'hostile',
  blood_feud_since_epoch: 6,
  history: [
    { epoch: 6, event: 'a blood feud was declared', delta: -30 },
    { epoch: 7, event: 'raids on the border', delta: -5 },
  ],
}

export function warsResponse(method: string, url: URL): unknown {
  const route = url.pathname
  if (method !== 'GET') {
    if (route === '/api/actions/engine:run_phase') return ACCEPTED
    if (/^\/api\/integrity\//.test(route)) return { task: 'dead_bonds', counters: { closed: 2, transferred: 1 }, message: 'Closed 2 bonds of the dead and passed 1 to heirs.' }
    if (/^\/api\/entities\/\d+\/relations\//.test(route)) return { ...ACCEPTED, action: 'relation:set', message: 'The relation was set.' }
    return undefined
  }
  if (route === '/api/engine/phases') return { phases: PHASES }
  if (route === '/api/integrity/tasks')
    return {
      tasks: [
        { task: 'dead_bonds', title: 'Dead-bond sweep', description: 'Close the living bonds of the dead and destroyed, passing inheritable ones to heirs.', changes_world: true },
        { task: 'checkpoint', title: 'Checkpoint the log', description: 'Fold the write-ahead log into the main database file.', changes_world: false },
      ],
    }
  if (route === '/api/wars') return page(url.searchParams.get('status') === 'ended' ? [] : [WAR])
  if (/^\/api\/wars\/\d+$/.test(route)) return WAR
  if (/^\/api\/entities\/\d+\/wars$/.test(route)) return page([WAR])
  if (/^\/api\/entities\/\d+\/heroes$/.test(route)) return [{ hero: ref(45, 'Hadric the Unbowed'), role: 'warrior', entity_type: 'mortal', power: 3 }]
  if (/^\/api\/entities\/\d+\/relations$/.test(route)) return { entity_id: 43, relations: [RELATION] }
  if (/^\/api\/wars\/\d+\/battles$/.test(route))
    return page([{ id: 1, war_id: 1, epoch: 8, sequence: 1, record: null, place: ref(42, 'Salt Flats'), winner: ref(43, 'Harrowmere'), loser: ref(44, LONG), outcome: 'field_victory', gap: 1.5, siege_id: null }])
  if (/^\/api\/wars\/\d+\/armies$/.test(route))
    return page([{ army: ref(81, 'Harrowmere Host'), war_id: 1, owner: ref(43, 'Harrowmere'), commander: ref(45, 'Hadric the Unbowed'), raised_epoch: 4, disbanded_epoch: null }])
  if (/^\/api\/wars\/\d+\/sieges$/.test(route))
    return page([{ id: 1, war_id: 1, besieged: ref(44, LONG), besieger: ref(43, 'Harrowmere'), status: 'ongoing', started_epoch: 7, ended_epoch: null, rounds: 2 }])
  if (route === '/api/captives')
    return page([{ id: 1, captive: ref(45, 'Hadric the Unbowed'), captor: ref(44, LONG), home: ref(43, 'Harrowmere'), war_id: 1, status: 'held', taken_epoch: 8, released_epoch: null, ransom_paid: null }])
  if (route === '/api/tributes')
    return page([{ id: 1, payer: ref(44, LONG), receiver: ref(43, 'Harrowmere'), war_id: 1, status: 'active', since_epoch: 8, ended_epoch: null }])
  return undefined
}
