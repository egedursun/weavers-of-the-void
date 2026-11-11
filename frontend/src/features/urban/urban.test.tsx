import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UrbanSection } from './UrbanSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 30, kind: 'entity' as const, name: 'Ashby' }
const FAMILY = { id: 40, kind: 'entity' as const, name: 'Lantern Family' }
const ROAD = { id: 50, kind: 'entity' as const, name: 'Long Road' }

const EMPTY = {
  town: null,
  districts: [],
  placement: null,
  turf: [],
  rackets: [],
  payroll: [],
  stances: [],
  laws: [],
  tribunals: [],
  posts: [],
  convoys: [],
  fleets: [],
  plays: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 30, name: 'Ashby', type: 'settlement', world_id: 1 },
    {
      kind: 'entity',
      id: 40,
      name: 'Lantern Family',
      type: 'faction',
      world_id: 1,
    },
  ])
}

describe('urban', () => {
  beforeEach(() => resetApi())

  it('shows a town’s districts, homeless and convoys and clears its slums', async () => {
    serveBase()
    onApi('GET', '/api/urban/of/30', {
      ...EMPTY,
      node: TOWN,
      town: { morphology: 'concentric', homeless: 140, locked: [] },
      districts: [
        {
          id: 7,
          kind: 'market',
          level: 2,
          housing: 'townhouse',
          desirability: 64,
          land_value: 58,
          services: [{ service: 'watch', coverage: 70, epoch: 5, locked: [] }],
          turf: [
            {
              district_id: 7,
              district_kind: 'market',
              town: TOWN,
              faction: FAMILY,
              strength: 35,
              since_epoch: 4,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
      convoys: [
        {
          id: 3,
          owner: TOWN,
          route: ROAD,
          cargo: { grain: 20 },
          preservation: 'salted',
          animals: 0,
          vehicles: 2,
          guards: 4,
          passengers: { pilgrims: 3 },
          season: 5,
          status: 'travelling',
          region: null,
          capacity: 20,
          departed_epoch: 5,
          arrived_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/slums:clear', ACCEPTED_ACTION)
    const { screen } = await renderApp(<UrbanSection nodeId={30} />)
    await expect.element(screen.getByText('140 without a home')).toBeVisible()
    await expect
      .element(screen.getByText('Lantern Family holds it (35)'))
      .toBeVisible()
    await expect.element(screen.getByText('20 grain')).toBeVisible()
    await screen.getByRole('button', { name: 'Clear the slums' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/slums:clear'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/slums:clear')[0].body).toEqual({
      settlement_id: 30,
    })
  })

  it('sets the coverage of a service a district already has', async () => {
    serveBase()
    onApi('GET', '/api/urban/of/30', {
      ...EMPTY,
      node: TOWN,
      districts: [
        {
          id: 7,
          kind: 'market',
          level: 2,
          housing: 'townhouse',
          desirability: 64,
          land_value: 58,
          services: [{ service: 'watch', coverage: 70, epoch: 5, locked: [] }],
          turf: [],
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/district_service:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<UrbanSection nodeId={30} />)
    await screen.getByRole('spinbutton', { name: 'Coverage' }).fill('40')
    await screen.getByRole('button', { name: 'Set its coverage' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district_service:edit'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/district_service:edit')[0].body
    ).toEqual({
      district_id: 7,
      service: 'watch',
      values: { coverage: 40 },
      release: [],
    })
  })

  it('shows an organisation’s rackets and breaks one', async () => {
    serveBase()
    onApi('GET', '/api/urban/of/40', {
      ...EMPTY,
      node: FAMILY,
      rackets: [
        {
          faction: FAMILY,
          settlement: TOWN,
          racket: 'gambling',
          income: 12,
          since_epoch: 3,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/racket:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<UrbanSection nodeId={40} />)
    await expect.element(screen.getByText('Gambling')).toBeVisible()
    await screen.getByRole('button', { name: 'Break' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/racket:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/racket:delete')[0].body).toEqual({
      faction_id: 40,
      settlement_id: 30,
      racket: 'gambling',
    })
  })

  it('says why the streets could not be read', async () => {
    serveBase()
    onApi('GET', '/api/urban/of/30', failure(500, 'The heavens are silent.'))
    const { screen } = await renderApp(<UrbanSection nodeId={30} />)
    await expect
      .element(screen.getByText('The streets could not be read'))
      .toBeVisible()
  })
})
