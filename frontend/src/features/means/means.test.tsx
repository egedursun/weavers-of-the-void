import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MeansSection } from './MeansSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const FOLK = { id: 7, kind: 'entity' as const, name: 'Grimfolk' }
const QUAY = { id: 41, kind: 'entity' as const, name: 'Grimsby Quay' }
const BOOK = { id: 42, kind: 'entity' as const, name: 'The Reed Book' }

const EMPTY = {
  town: TOWN,
  people: FOLK,
  custom: null,
  works: [],
  vaults: [],
  lifts: [],
  kits: [],
  accuracy: 0,
  containers: [],
  building: null,
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
  ])
}

describe('means of craft', () => {
  beforeEach(() => resetApi())

  it('shows what a town writes on, how it lifts water and raises devices', async () => {
    serveBase()
    onApi('GET', '/api/means/of/40', {
      ...EMPTY,
      node: TOWN,
      custom: { people: FOLK, medium: 'papyrus', since_epoch: 3, locked: [] },
      works: [
        {
          work: BOOK,
          medium: 'papyrus',
          condition: 61,
          copies: 2,
          written_epoch: 4,
          locked: [],
        },
      ],
      lifts: [
        { device: 'noria', count: 2, capacity: 6, since_epoch: 5, locked: [] },
      ],
      kits: [
        {
          aid: 'compass',
          quality: 40,
          works: false,
          since_epoch: 5,
          locked: [],
        },
      ],
      containers: [
        {
          kind: 'amphora',
          count: 12,
          broken: 3,
          capacity: 240,
          sealed: true,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/water_lift:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MeansSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Writing/ }).click()
    await expect
      .element(screen.getByText('Grimfolk write on papyrus'))
      .toBeVisible()
    await screen.getByRole('tab', { name: /Water lifting/ }).click()
    await expect.element(screen.getByText('2 noria')).toBeVisible()
    await screen.getByRole('button', { name: 'Raise them' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/water_lift:set'))
      .toHaveLength(1)
    await screen.getByRole('tab', { name: /Pilots/ }).click()
    await expect
      .element(screen.getByText('Useless in this world, since epoch 5'))
      .toBeVisible()
    await screen.getByRole('tab', { name: /Containers/ }).click()
    await expect.element(screen.getByText('12 amphora')).toBeVisible()
  })

  it('reads the material of a structure and keeps the building control with its reason elsewhere', async () => {
    serveBase()
    onApi('GET', '/api/means/of/41', {
      ...EMPTY,
      node: QUAY,
      building: {
        material: 'mud_brick',
        water_resistance: 10,
        needs: 'aqueduct',
        can_repair: false,
        weathering_pct: 190,
      },
    })
    const { screen } = await renderApp(<MeansSection nodeId={41} />)
    await screen.getByRole('tab', { name: /Building material/ }).click()
    await expect
      .element(screen.getByText('No, its makers forgot how'))
      .toBeVisible()
    await expect
      .element(screen.getByText('190% of the decay of its material'))
      .toBeVisible()
  })
})
