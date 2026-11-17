import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { KindsScreen } from './KindsScreen'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const GOODS_INFO = {
  concept: 'good' as const,
  label: 'Good',
  plural: 'Goods',
  hint: 'Things a people grows, gathers, makes or trades',
  categories: [
    { key: 'grain', label: 'Grain' },
    { key: 'fruit', label: 'Fruit' },
  ],
  properties: [
    {
      column: 'bulk',
      label: 'Bulk',
      hint: 'Room it takes in a store or a hold',
      low: 0,
      high: 100,
      options: [],
    },
    {
      column: 'prestige',
      label: 'Prestige',
      hint: 'Standing it lends to those who hold it',
      low: 0,
      high: 100,
      options: [],
    },
  ],
}

const PEOPLE = { id: 12, kind: 'entity' as const, name: 'The Oru' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }

function goodRecord(overrides: Record<string, unknown> = {}) {
  return {
    id: 3,
    concept: 'good' as const,
    name: 'Ashgrain',
    description: 'A hardy grain of the high fields.',
    category: 'grain',
    category_label: 'Grain',
    world: WORLD,
    origin: PEOPLE,
    derived_from_id: null,
    derived_from_name: null,
    built_in: false,
    retired: false,
    created_epoch: 2,
    locked: [],
    values: [
      { column: 'bulk', value: 30 },
      { column: 'prestige', value: 15 },
    ],
    holders: [PEOPLE],
    ...overrides,
  }
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/kinds/concepts', [GOODS_INFO])
}

describe('the kinds library', () => {
  beforeEach(() => resetApi())

  it('shows a kind with its values, holders and lineage, and edits, holds, retires and unmakes it', async () => {
    serveBase()
    onApi('GET', '/api/kinds/good', [
      goodRecord(),
      goodRecord({
        id: 5,
        name: 'Redgrain',
        derived_from_id: 3,
        derived_from_name: 'Ashgrain',
        holders: [],
      }),
    ])
    for (const lever of ['edit', 'hold', 'retire', 'delete'])
      onApi('POST', `/api/actions/authored_kind:${lever}`, ACCEPTED_ACTION)
    const { screen } = await renderApp(<KindsScreen />)
    await expect.element(screen.getByText('Ashgrain').first()).toBeVisible()
    await expect
      .element(screen.getByText('Developed from Ashgrain'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'The Oru' }).first())
      .toBeVisible()
    await expect.element(screen.getByText('No one holds it now.')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen.getByRole('spinbutton', { name: 'Bulk' }).first().fill('80')
    await screen
      .getByRole('button', { name: 'Hold these values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:edit'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:edit')[0].body
    ).toMatchObject({ concept: 'good', kind_id: 3, values: { bulk: 80 } })
    await screen
      .getByRole('button', { name: 'Hold it against the world' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:hold'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:hold')[0].body
    ).toMatchObject({ concept: 'good', kind_id: 3, hold: true })
    await screen.getByRole('button', { name: 'Retire it' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:retire'))
      .toHaveLength(1)
    await screen
      .getByRole('button', { name: 'Unmake this kind' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:delete'))
      .toHaveLength(1)
  })

  it('makes a new kind once it has a name, and keeps the control disabled until then', async () => {
    serveBase()
    onApi('GET', '/api/kinds/good', [])
    onApi('POST', '/api/actions/authored_kind:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<KindsScreen />)
    await expect.element(screen.getByText('No goods yet')).toBeVisible()
    const make = screen.getByRole('button', { name: 'Make the kind' })
    await expect.element(make).toBeDisabled()
    await screen.getByLabelText('Name of the kind').fill('Saltberry')
    await make.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:create')[0].body
    ).toMatchObject({ concept: 'good', name: 'Saltberry', category: 'grain' })
  })

  it('gives a kind to a holder with its stance and strength', async () => {
    serveBase()
    onApi('GET', '/api/names', [
      {
        id: 12,
        kind: 'entity',
        name: 'The Oru',
        type: 'people',
        status: 'canon',
      },
    ])
    onApi('GET', '/api/kinds/good', [goodRecord({ holders: [] })])
    onApi('POST', '/api/actions/authored_kind:spread', ACCEPTED_ACTION)
    const { screen } = await renderApp(<KindsScreen />)
    const give = screen.getByRole('button', { name: 'Give it to them' })
    await expect.element(give).toBeDisabled()
    await screen.getByRole('combobox', { name: 'Who receives it' }).click()
    await screen.getByRole('option', { name: /The Oru/ }).click()
    await give.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:spread'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:spread')[0].body
    ).toMatchObject({
      concept: 'good',
      kind_id: 3,
      holder_node_id: 12,
      stance: 'uses',
      strength: 50,
    })
  })

  it('says so when the kinds cannot be read', async () => {
    serveBase()
    onApi('GET', '/api/kinds/good', failure(500, 'The archive is closed.'))
    const { screen } = await renderApp(<KindsScreen />)
    await expect
      .element(screen.getByText('The kinds could not be read'))
      .toBeVisible()
  })
})
