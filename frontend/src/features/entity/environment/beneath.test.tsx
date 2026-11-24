import { failure, onApi, renderApp, resetApi } from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BeneathSection } from './BeneathSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const BENEATH = {
  region_id: 3,
  mined_depth: 40,
  quarry_grade: 'splendid',
  carvable: true,
  layers: [
    {
      id: 1,
      depth_order: 0,
      rock: 'tuff',
      thickness: 30,
      top: 0,
      veins: { copper: 40 },
      reached_epoch: 12,
      hardness: 30,
      porosity: 60,
      solubility: 10,
      workability: 80,
      grade: 'fine',
      locked: ['thickness'],
    },
    {
      id: 2,
      depth_order: 1,
      rock: 'halite',
      thickness: 50,
      top: 30,
      veins: {},
      reached_epoch: null,
      hardness: 20,
      porosity: 5,
      solubility: 90,
      workability: 50,
      grade: 'plain',
      locked: [],
    },
  ],
  strata: [
    {
      id: 9,
      stratum: 'aquifer',
      depth: 60,
      volume: 400,
      pressure: 30,
      reached_epoch: 14,
      breached_epoch: 15,
      tapped_epoch: null,
      name: 'Still Water',
      terrain: 'underground',
      extent: 70,
      light: 0,
      realm: null,
      holder: { id: 31, kind: 'entity', name: 'Deep Realm' },
      dwellers: [{ id: 32, kind: 'entity', name: 'Underhall' }],
      dwellable: false,
      locked: [],
    },
  ],
  passages: [
    {
      id: 5,
      kind: 'opening',
      state: 'flooded',
      origin: 'natural',
      width: 40,
      progress: 100,
      near_stratum: null,
      far_region: { id: 3, kind: 'entity', name: 'Grey Vale' },
      far_stratum: 'aquifer',
      place: { id: 33, kind: 'entity', name: 'Wet Cave' },
      digger: null,
      locked: [],
    },
  ],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [])
}

describe('beneath section', () => {
  beforeEach(resetApi)

  it('shows the rock column, its grades and veins and the depths below', async () => {
    serve()
    onApi('GET', '/api/regions/3/beneath', BENEATH)
    const { screen } = await renderApp(<BeneathSection regionId={3} />)
    await expect.element(screen.getByText('Tuff')).toBeVisible()
    await expect.element(screen.getByText('Halite')).toBeVisible()
    await expect.element(screen.getByText('Splendid stone')).toBeVisible()
    await expect.element(screen.getByText('Fine stone')).toBeVisible()
    await expect
      .element(screen.getByText('The rock can be carved'))
      .toBeVisible()
    await expect.element(screen.getByText('Reached in epoch 12')).toBeVisible()
    await expect.element(screen.getByText('Not reached')).toBeVisible()
    await expect
      .element(screen.getByText('Held', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText('No vein runs through this layer.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Aquifer', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Breached in epoch 15')).toBeVisible()
    await expect.element(screen.getByText('Still Water')).toBeVisible()
    await expect.element(screen.getByText('Held by Deep Realm')).toBeVisible()
    await expect
      .element(screen.getByText('Opening to the surface'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Comes out at Wet Cave'))
      .toBeVisible()
  })

  it('says when a land has no rock column and nothing below it', async () => {
    serve()
    onApi('GET', '/api/regions/3/beneath', {
      ...BENEATH,
      carvable: false,
      layers: [],
      strata: [],
      passages: [],
    })
    const { screen } = await renderApp(<BeneathSection regionId={3} />)
    await expect.element(screen.getByText('No rock column')).toBeVisible()
    await expect.element(screen.getByText('Too hard to carve')).toBeVisible()
    await expect
      .element(screen.getByText('Nothing lies below the rock of this land.'))
      .toBeVisible()
  })

  it('says a land is not surveyed when its ground cannot be read', async () => {
    serve()
    onApi('GET', '/api/regions/3/beneath', failure(404, 'missing'))
    const { screen } = await renderApp(<BeneathSection regionId={3} />)
    await expect.element(screen.getByText('Not surveyed yet')).toBeVisible()
  })
})
