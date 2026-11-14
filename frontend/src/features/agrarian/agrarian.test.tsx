import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AgrarianSection } from './AgrarianSection'
import { CosmosAgrarianSection } from './CosmosAgrarianSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const VALE = { id: 20, kind: 'entity' as const, name: 'Long Vale' }
const TOWN = { id: 30, kind: 'entity' as const, name: 'Hollin' }
const REALM = { id: 40, kind: 'entity' as const, name: 'Varo' }
const WORLD = { id: 1, kind: 'world' as const, name: 'Aster' }

const EMPTY = {
  world: WORLD,
  ring: null,
  nutrients: [],
  intensity: null,
  perennials: [],
  commons: [],
  reserves: [],
  famine: null,
  central_place: null,
  works: [],
  aid: [],
  rebuilds: [],
  keystones: [],
  brands: [],
  workshops: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 20, name: 'Long Vale', type: 'region', world_id: 1 },
    { kind: 'entity', id: 30, name: 'Hollin', type: 'settlement', world_id: 1 },
    { kind: 'entity', id: 40, name: 'Varo', type: 'polity', world_id: 1 },
  ])
}

describe('land, harvest, readiness and staples', () => {
  beforeEach(() => resetApi())

  it('shows a land’s ring and salting soil and encloses its common', async () => {
    serveBase()
    onApi('GET', '/api/agrarian/of/20', {
      ...EMPTY,
      node: VALE,
      ring: {
        region: VALE,
        market: TOWN,
        ring: 'grain',
        distance: 140,
        by_water: true,
        gap: 10,
        updated_epoch: 6,
        locked: [],
      },
      nutrients: [
        {
          nutrient: 'salinity',
          stock: 45,
          trend: 3,
          updated_epoch: 6,
          locked: [],
        },
      ],
      commons: [
        {
          id: 7,
          region: VALE,
          kind: 'pasture',
          rule: 'customary',
          condition: 40,
          use: 90,
          steward: TOWN,
          encloser: null,
          enclosed_epoch: null,
          dispossessed: 0,
          since_epoch: 2,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/commons:enclose', ACCEPTED_ACTION)
    const { screen } = await renderApp(<AgrarianSection nodeId={20} />)
    await expect.element(screen.getByText('Long Vale: Grain')).toBeVisible()
    await expect
      .element(screen.getByText('+3 last epoch · read in epoch 6'))
      .toBeVisible()
    await screen
      .getByRole('tab', { name: /Plantings, commons and game/ })
      .click()
    await expect
      .element(screen.getByText('Common pasture of Long Vale'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Enclose it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/commons:enclose'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/commons:enclose')[0].body).toEqual({
      commons_id: 7,
      encloser_id: 20,
    })
  })

  it('raises a town’s levees and finishes its rebuilding', async () => {
    serveBase()
    onApi('GET', '/api/agrarian/of/30', {
      ...EMPTY,
      node: TOWN,
      rebuilds: [
        {
          id: 3,
          settlement: TOWN,
          cause: 'fire',
          plan: 'planned',
          cost: 540,
          paid: 200,
          progress: 50,
          planner: null,
          seized_by: REALM,
          seized: 12,
          started_epoch: 5,
          finished_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/preparedness:build', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/reconstruction:finish', ACCEPTED_ACTION)
    const { screen } = await renderApp(<AgrarianSection nodeId={30} />)
    await expect
      .element(screen.getByText('Hollin rebuilding after a fire'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Finish it now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/reconstruction:finish'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Raise the work' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/preparedness:build'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/preparedness:build')[0].body).toEqual({
      settlement_id: 30,
      kind: 'levee',
      level: 1,
    })
  })

  it('reads the keystones and markets of every world', async () => {
    serveBase()
    onApi('GET', '/api/agrarian/cosmos', {
      rings: [],
      central_places: [
        {
          settlement: TOWN,
          rank: 'weekly',
          catchment: 4000,
          served_by: null,
          centrality: 55,
          updated_epoch: 6,
          locked: [],
        },
      ],
      keystones: [
        {
          id: 1,
          world: WORLD,
          name: 'The First Yield',
          producer: null,
          source: VALE,
          commodity: null,
          use: 'rite',
          cult: null,
          controller: REALM,
          harvest: 20,
          supply: 25,
          price: 137,
          designated_epoch: 4,
          designated_by: null,
          locked: [],
        },
      ],
      brands: [],
      aid: [],
      rebuilds: [],
      commons: [],
      reserves: [],
    })
    const { screen } = await renderApp(<CosmosAgrarianSection />)
    await expect
      .element(screen.getByText('Keystones of the worlds (1)'))
      .toBeVisible()
    await expect.element(screen.getByText('Held by Varo')).toBeVisible()
    await expect
      .element(screen.getByText('Weekly market for 4,000 buyers'))
      .toBeVisible()
  })
})
