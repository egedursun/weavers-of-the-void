import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FeedLines } from '@/features/chronicle/FeedGroups'
import { EventPage } from './EventPage'
import { HistorySection } from './HistorySection'
import { amountText, momentText } from './format'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MOMENT = { epoch: 6, year: 212, season: 1, day: 4, hour: null }

const STRIKE = {
  id: 31,
  incident_id: 9,
  position: 0,
  round: 0,
  parent_step_id: null,
  moment: MOMENT,
  actor_node_id: 11,
  actor_name: 'Aben',
  target_node_id: 12,
  target_name: 'Corra',
  action: 'strike' as const,
  instrument_kind: 'equipment_model' as const,
  instrument_node_id: null,
  instrument_name: null,
  instrument_key: 'mace',
  locus_kind: 'body_part' as const,
  locus_key: 'left_arm',
  locus_node_id: null,
  locus_name: null,
  damage_type: 'blunt' as const,
  amount: 6,
  unit: 'hp' as const,
  outcome: 'broken' as const,
  record_table: 'injuries',
  record_key: '{"id": 4}',
  states: [{ node_id: 12, node_name: 'Corra', state: 'prone' as const }],
}

const RISE = {
  ...STRIKE,
  id: 32,
  position: 1,
  parent_step_id: 31,
  action: 'rise' as const,
  actor_node_id: 12,
  actor_name: 'Corra',
  target_node_id: null,
  target_name: null,
  instrument_kind: 'none' as const,
  instrument_key: null,
  locus_kind: 'none' as const,
  locus_key: null,
  damage_type: null,
  amount: null,
  unit: null,
  outcome: null,
  record_table: null,
  record_key: null,
  states: [],
}

const CHANGE = {
  id: 70,
  moment: MOMENT,
  table_name: 'settlement_profiles',
  row_key: '{"settlement_entity_id": 40}',
  node_id: 40,
  node_name: 'Long Hall',
  operation: 'update' as const,
  field: 'prosperity',
  before_number: 60,
  after_number: 40,
  before_text: null,
  after_text: null,
  before_node_id: null,
  before_node_name: null,
  after_node_id: null,
  after_node_name: null,
  actor_kind: 'engine' as const,
  actor_node_id: null,
  actor_name: null,
  phase: 'blockade',
  incident_id: 9,
  step_id: null,
  terms: [
    {
      position: 0,
      term: 'blockade',
      op: 'add' as const,
      amount: -12,
      source_node_id: null,
      source_name: null,
      source_incident_id: 8,
      fact_key: null,
    },
  ],
}

const ACCOUNT = {
  id: 9,
  kind: 'duel.honour',
  family: 'duel',
  group: 'single_combat' as const,
  known: true,
  moment: MOMENT,
  world_id: 1,
  place_id: 40,
  place_name: 'Long Hall',
  origin_id: null,
  origin_name: null,
  destination_id: null,
  destination_name: null,
  tier: 'steps' as const,
  locked: [],
  magnitude: 40,
  chronicle_id: 3,
  line: 'Aben broke the arm of Corra with a mace.',
  retold: 'Aben broke the arm of Corra with a mace.',
  note: null,
  thread_id: null,
  participants: [
    {
      node_id: 11,
      name: 'Aben',
      role: 'actor' as const,
      position: 0,
      witness_mode: null,
      fidelity: null,
    },
    {
      node_id: 12,
      name: 'Corra',
      role: 'victim' as const,
      position: 1,
      witness_mode: null,
      fidelity: null,
    },
  ],
  witnesses: [
    {
      node_id: 13,
      name: 'Dell',
      role: 'witness' as const,
      position: 2,
      witness_mode: 'saw' as const,
      fidelity: 90,
    },
  ],
  facts: [
    {
      id: 51,
      key: 'exchanges',
      position: 0,
      node_id: null,
      node_name: null,
      number: 3,
      unit: 'count' as const,
      enum_name: null,
      enum_value: null,
      name: null,
    },
  ],
  steps: [STRIKE, RISE],
  terms: [],
  changes: [CHANGE],
  rumours: [],
  causes: [
    {
      id: 8,
      kind: 'grudges.feud',
      epoch: 5,
      year: 210,
      text: 'The feud began.',
    },
  ],
  effects: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { id: 11, kind: 'entity', name: 'Aben', type: 'mortal' },
    { id: 12, kind: 'entity', name: 'Corra', type: 'mortal' },
    { id: 40, kind: 'entity', name: 'Long Hall', type: 'structure' },
  ])
}

describe('the record of events on screen', () => {
  beforeEach(() => resetApi())

  it('tells moments and amounts plainly', () => {
    expect(momentText(MOMENT)).toBe('Year 212, season 2, day 5, epoch 6')
    expect(amountText(6, 'hp')).toBe('6 health')
    expect(amountText(3, 'count')).toBe('3')
  })

  it('shows the account, nested steps, changes with their terms, and strikes a fact', async () => {
    serveBase()
    onApi('GET', '/api/incidents/9', ACCOUNT)
    onApi('POST', '/api/actions/incident_fact:delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/state_change:revert', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EventPage id='9' />)
    await expect
      .element(
        screen.getByText('Aben broke the arm of Corra with a mace.').first()
      )
      .toBeVisible()
    await expect.element(screen.getByText('Suffered it').first()).toBeVisible()
    await expect.element(screen.getByText('Corra: prone')).toBeVisible()
    await expect.element(screen.getByText('Broken').first()).toBeVisible()
    await expect.element(screen.getByText('6 health')).toBeVisible()
    await expect.element(screen.getByText(/Changed: prosperity/)).toBeVisible()
    await expect.element(screen.getByText('Blockade')).toBeVisible()
    await expect.element(screen.getByText('The feud began.')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Strike', exact: true })
      .first()
      .click()
    await screen
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Strike', exact: true })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/incident_fact:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/incident_fact:delete')[0].body
    ).toEqual({ incident_fact_id: 51 })
  })

  it('holds a part of a happening at once', async () => {
    serveBase()
    onApi('GET', '/api/incidents/9', ACCOUNT)
    onApi('POST', '/api/actions/incident:hold', ACCEPTED_ACTION)
    const { screen } = await renderApp(<EventPage id='9' />)
    await screen.getByRole('button', { name: 'Hold: its steps' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/incident:hold'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/incident:hold')[0].body).toEqual({
      incident_id: 9,
      fields: ['steps'],
      hold: true,
    })
  })

  it('says plainly when a link points at no happening', async () => {
    serveBase()
    const { screen } = await renderApp(<EventPage id='nothing' />)
    await expect.element(screen.getByText('No such happening')).toBeVisible()
  })

  it('lists a history with its roles and offers more of it', async () => {
    serveBase()
    onApi('GET', '/api/nodes/11/history', {
      node_id: 11,
      offset: 0,
      limit: 12,
      total_incidents: 30,
      incidents: [
        {
          incident_id: 9,
          kind: 'duel.honour',
          group: 'single_combat',
          moment: MOMENT,
          roles: ['actor'],
          line: ACCOUNT.line,
          place_id: 40,
          place_name: 'Long Hall',
          tier: 'steps',
          facts: 1,
          steps: 2,
          changes: 1,
        },
      ],
      total_steps: 1,
      steps: [STRIKE],
      total_changes: 0,
      changes: [],
      kinds: ['duel.honour'],
      roles: ['actor'],
    })
    const { screen } = await renderApp(<HistorySection nodeId={11} />)
    await expect.element(screen.getByText(ACCOUNT.line).first()).toBeVisible()
    await expect.element(screen.getByText('Acted').first()).toBeVisible()
    await expect
      .element(screen.getByText('1 fact · 2 steps · 1 change'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Show more of its history' })
      .click()
    await expect
      .poll(() => callsTo('GET', '/api/nodes/11/history').length)
      .toBeGreaterThan(1)
  })

  it('groups lines of one kind as one entry and opens every one', async () => {
    serveBase()
    const line = (id: number, text: string) => ({
      id,
      epoch: 6,
      year: 212,
      kind: 'world' as const,
      son_id: null,
      world_id: 1,
      text,
      created_at: '2026-11-17T09:00:00Z',
      entity_ids: [],
    })
    const lines = [
      line(1, 'A child was born in Long Hall.'),
      line(2, 'A child was born in Aldermere.'),
      line(3, 'A child was born in Corrin.'),
      line(4, 'The river rose.'),
    ]
    const { screen } = await renderApp(
      <FeedLines
        lines={lines}
        groups={[{ epoch: 6, size: 3, line_ids: [1, 2, 3] }]}
        kindLabels={new Map()}
      />
    )
    await expect
      .element(screen.getByText('3 happenings of this kind'))
      .toBeVisible()
    await expect.element(screen.getByText('The river rose.')).toBeVisible()
    await screen.getByRole('button', { name: 'Show every one' }).click()
    await expect
      .element(screen.getByText('A child was born in Corrin.'))
      .toBeVisible()
  })
})
