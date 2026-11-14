import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CustomsSection } from './CustomsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MORTAL = { id: 32, kind: 'entity' as const, name: 'Orla' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const INN = { id: 42, kind: 'entity' as const, name: 'The Low Door' }
const FOLK = { id: 41, kind: 'entity' as const, name: 'Grimfolk' }

const EMPTY = {
  people: FOLK,
  revivals: [],
  intoxicants: [],
  mark_customs: [],
  marks: [],
  budgets: [],
  naming: null,
  names: [],
  age_sets: [],
  age_set_id: null,
  taverns: [],
  welfare: [],
  commute: null,
  cooperative: null,
  evidence: [],
  categories: [],
  membership: null,
  border: null,
  relief: null,
  measures: null,
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 32, name: 'Orla', type: 'mortal', world_id: 4 },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
    { kind: 'entity', id: 41, name: 'Grimfolk', type: 'people', world_id: 4 },
    { kind: 'world', id: 4, name: 'Orvael' },
  ])
}

describe('customs, town life and civics', () => {
  beforeEach(() => resetApi())

  it("shows a mortal's mark and gives it a name", async () => {
    serveBase()
    onApi('GET', '/api/customs/of/32', {
      ...EMPTY,
      node: MORTAL,
      marks: [
        {
          id: 5,
          kind: 'tattoo',
          meaning: 'deed',
          placed_epoch: 4,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/name_form:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CustomsSection nodeId={32} />)
    await expect.element(screen.getByText('Tattoo of deeds')).toBeVisible()
    await screen.getByLabelText('Name given').fill('Far-Walker')
    await screen.getByRole('button', { name: 'Name it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/name_form:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/name_form:set')[0].body).toEqual({
      holder_id: 32,
      form: 'deed',
      name: 'Far-Walker',
    })
  })

  it('shows the tavern of a town', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/40', {
      ...EMPTY,
      node: TOWN,
      taverns: [
        {
          structure: INN,
          keeper: MORTAL,
          patrons: 12,
          brawls: 1,
          lodging: 4,
          rumours: 3,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<CustomsSection nodeId={40} />)
    await expect
      .element(screen.getByText('The Low Door', { exact: true }))
      .toBeVisible()
  })

  it('keeps the marks of a thing that is no mortal', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/40', { ...EMPTY, node: TOWN })
    const { screen } = await renderApp(<CustomsSection nodeId={40} />)
    await screen
      .getByRole('tab', { name: /Marks, names and belonging/ })
      .click()
    await expect
      .element(screen.getByRole('button', { name: 'Mark it' }))
      .toBeDisabled()
  })
})
