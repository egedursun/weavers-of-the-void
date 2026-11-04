import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RegionTerrainSection } from './RegionTerrain'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const HARMS = {
  settlers: 12,
  livestock: 30,
  travellers: 54,
  armies: 3,
  ambush: 42,
  merchants: 60,
}

const TERRAIN = {
  region_id: 5,
  world_id: 1,
  danger: 60,
  harms: HARMS,
  dangers: [
    {
      id: 7,
      source: 'bandits',
      label: 'Bandits',
      strength: 60,
      origin: 'derived',
      held: true,
      source_node_id: null,
      source_node_name: null,
      son_id: null,
      since_epoch: 2,
      harms: HARMS,
    },
  ],
  sacredness: 45,
  sacredness_held: true,
  darkness: 30,
  holiness: 10,
  haunting_pct: 115,
  draws_pilgrims: true,
  pilgrim_sacred_min: 40,
  memories: [
    {
      id: 3,
      kind: 'massacre',
      label: 'Massacre',
      magnitude: 70,
      epoch: 2,
      title: 'The Red Ford',
      origin: 'derived',
      held: false,
      darkness: 100,
      holiness: 0,
      fades: true,
      subject_id: null,
      incident_id: null,
    },
  ],
  knowledge: [
    {
      polity_id: 9,
      polity_name: 'Kingdom of Ash',
      level: 20,
      held: true,
      terrain: false,
      sacred: false,
      minerals: false,
      unmapped: true,
    },
  ],
  realms: [{ id: 9, name: 'Kingdom of Ash' }],
  unmapped_below: 25,
  hazards: [
    {
      id: 1,
      hazard: 'wildfire',
      label: 'Wildfire',
      epoch: 2,
      year: 140,
      season_name: 'Summer',
      deaths: 12,
      injured: 2,
      soldiers_lost: 0,
    },
  ],
  exposure: [{ hazard: 'wildfire', label: 'Wildfire', season: 'hottest' }],
  river_class: 'river',
  river_neighbours: [{ id: 6, name: 'Far Dunes', river_class: 'none' }],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 3 },
  })
  onApi('GET', '/api/regions/5/terrain', TERRAIN)
}

describe('region terrain', () => {
  beforeEach(resetApi)

  it('shows typed dangers, memory, maps and hazards and drives their levers', async () => {
    serve()
    onApi('POST', '/api/actions/region:danger_release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/region:knowledge_release', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/environment:unlock', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/region:memory_delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RegionTerrainSection regionId={5} />)
    await expect.element(screen.getByText('Dangers of the land')).toBeVisible()
    await expect.element(screen.getByText('Draws pilgrims')).toBeVisible()
    await expect
      .element(screen.getByText('Unmapped: armies lose their way'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/region:knowledge_release'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/region:knowledge_release')[0].body
    ).toEqual({ polity_id: 9, region_id: 5 })
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen
      .getByRole('button', { name: 'Let the land decide' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/region:danger_release'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/region:danger_release')[0].body
    ).toEqual({ danger_id: 7 })
  })
})
