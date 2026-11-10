import type { components } from '../src/api/generated/schema'

type Schemas = components['schemas']

export const NODE_MECHANICS: Schemas['NodeMechanicsView'] = {
  node_id: 45,
  epoch: 12,
  acting: [
    {
      key: 'injuries',
      title: 'Typed injuries on body parts',
      subsystem: 'body',
      spec_item: 'F4.2',
      fields: ['hp'],
      reads: ['hp', 'strength'],
      writes: ['hp'],
      affects: ['mind', 'war'],
      suppressed: false,
      last_text: 'Arn lost an eye at the ford.',
      last_epoch: 11,
    },
  ],
  modifiers: [
    {
      id: 3,
      key: 'strength',
      op: 'multiply',
      magnitude: 0.85,
      source_kind: 'condition',
      source_subsystem: 'body',
      source_node_id: null,
      source_name: null,
      reason_key: 'modifier.condition.chronic_illness',
      reason: 'a lingering illness saps their strength',
      stacking_group: 'condition.chronic_illness',
      start_epoch: 12,
      end_epoch: null,
      decay_pct: null,
    held: false,
    },
  ],
  effective: [{ key: 'strength', base: 60, value: 51, applied: [3], ignored: [] }],
  pins: [],
  suppressions: [],
  incidents: [
    {
      id: 7,
      kind: 'injury.gouged',
      epoch: 11,
      year: 552,
      role: 'target',
      magnitude: 45,
      cause_incident_id: 6,
      chronicle_id: 70,
      text: 'Arn lost an eye at the ford.',
      note: null,
      thread_id: null,
      causes: ['Varn and Osk met at the ford.'],
      consequences: [],
    },
  ],
}

export function mechanicsResponse(method: string, url: URL): unknown {
  if (method === 'GET' && /^\/api\/nodes\/\d+\/mechanics$/.test(url.pathname)) return NODE_MECHANICS
  return undefined
}
