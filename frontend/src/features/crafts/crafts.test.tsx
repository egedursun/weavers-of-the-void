import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CraftsSection } from './CraftsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MORTAL = { id: 32, kind: 'entity' as const, name: 'Orla' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const FOLK = { id: 41, kind: 'entity' as const, name: 'Grimfolk' }
const LAND = { id: 42, kind: 'entity' as const, name: 'Saltmarch' }
const SHOALS = { id: 43, kind: 'entity' as const, name: 'Cold Shoals' }

const EMPTY = {
  people: FOLK,
  region: LAND,
  grounds: [],
  works: [],
  insurer: null,
  policies: [],
  rights: [],
  aids: [],
  clock: null,
  followings: [],
  numbers: null,
  affinities: [],
  links: [],
  spirits: [],
  materials: [],
  games: [],
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

describe('trades, aids, games and magic', () => {
  beforeEach(() => resetApi())

  it("shows a mortal's aid and gives another", async () => {
    serveBase()
    onApi('GET', '/api/crafts/of/32', {
      ...EMPTY,
      node: MORTAL,
      aids: [{ kind: 'cane', quality: 60, since_epoch: 4, locked: [] }],
    })
    onApi('POST', '/api/actions/assistive_aid:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CraftsSection nodeId={32} />)
    await expect
      .element(screen.getByText('Quality 60 · since epoch 4'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Give the aid' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/assistive_aid:set'))
      .toHaveLength(1)
  })

  it('shows the fishing ground and the works of a town', async () => {
    serveBase()
    onApi('GET', '/api/crafts/of/40', {
      ...EMPTY,
      node: TOWN,
      grounds: [
        {
          source: SHOALS,
          region: LAND,
          ground: 'fishery',
          gear: 'nets',
          right: 'commons',
          owner: null,
          effort: 50,
          collapse_at: 20,
          collapsed: true,
          last_catch: 1,
          first_stock: 40,
          locked: [],
        },
      ],
      works: [
        {
          settlement: TOWN,
          product: 'soap',
          output: 40,
          hazard: 10,
          pollution: 5,
          accidents: 1,
          founded_epoch: 3,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<CraftsSection nodeId={40} />)
    await expect.element(screen.getByText('Fishery: Cold Shoals')).toBeVisible()
    await expect.element(screen.getByText('Works for soap')).toBeVisible()
    await expect
      .element(screen.getByText(/1 accident · set up in epoch 3/))
      .toBeVisible()
  })

  it('keeps the aids of a thing that is no mortal', async () => {
    serveBase()
    onApi('GET', '/api/crafts/of/40', { ...EMPTY, node: TOWN })
    const { screen } = await renderApp(<CraftsSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Aids, games and numbers/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Give the aid' }))
      .toBeDisabled()
  })
})
