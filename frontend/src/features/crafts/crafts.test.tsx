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
  numbers: null,
  affinities: [],
  links: [],
  spirits: [],
  materials: [],
}

const GAME_INFO = {
  concept: 'game' as const,
  label: 'Game',
  plural: 'Games and sports',
  hint: 'The games and sports a people plays and watches',
  categories: [
    { key: 'board', label: 'Board game' },
    { key: 'ball', label: 'Ball game' },
  ],
  properties: [
    {
      column: 'chance_share',
      label: 'Chance',
      hint: 'How much of the outcome is left to chance',
      low: 0,
      high: 100,
      options: [],
    },
  ],
}

const HURL = {
  id: 7,
  concept: 'game' as const,
  name: 'Hurl',
  description: null,
  category: 'ball',
  category_label: 'Ball game',
  world: null,
  origin: FOLK,
  derived_from_id: null,
  derived_from_name: null,
  built_in: false,
  retired: false,
  created_epoch: 2,
  locked: [],
  values: [
    { column: 'chance_share', value: 20, option: null, option_label: null },
  ],
  holders: [FOLK],
}

function serveGames(held: boolean) {
  onApi('GET', '/api/kinds/concepts', [GAME_INFO])
  onApi('GET', '/api/kinds/game', [HURL])
  onApi('GET', '/api/kinds/of/41', {
    node: FOLK,
    holdings: held
      ? [
          {
            id: 9,
            concept: 'game',
            kind_id: 7,
            kind_name: 'Hurl',
            category_label: 'Ball game',
            stance: 'makes',
            strength: 70,
            spread: 'invented',
            since_epoch: 2,
            locked: [],
          },
        ]
      : [],
    made: [],
  })
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  serveGames(false)
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

  it("shows its people's games and makes a new one through the kinds levers", async () => {
    serveBase()
    serveGames(true)
    onApi('GET', '/api/crafts/of/40', { ...EMPTY, node: TOWN })
    onApi('POST', '/api/actions/authored_kind:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CraftsSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Aids, games and numbers/ }).click()
    await expect
      .element(screen.getByText(/Hurl: ball game, strength 70/))
      .toBeVisible()
    const make = screen.getByRole('button', { name: 'Make the game' })
    await expect.element(make).toBeDisabled()
    await screen.getByLabelText('Game name').fill('Ringstone')
    await make.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/authored_kind:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/authored_kind:create')[0].body
    ).toMatchObject({
      concept: 'game',
      name: 'Ringstone',
      category: 'board',
      origin_node_id: 41,
    })
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
