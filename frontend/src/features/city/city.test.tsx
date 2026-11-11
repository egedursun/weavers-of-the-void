import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CityPlan2D } from './CityPlan2D'
import { CitySection } from './CitySection'
import { LandSection } from './LandSection'
import { TypePage } from './TypePages'
import { type CityScene, type LandScene, type StructureTypes } from './api'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

vi.mock('@/features/cosmos/useCosmosViewSettings', async (original) => ({
  ...(await original<object>()),
  hasWebGL2: () => false,
}))

const TOWN = { id: 4, name: 'Harrowmere', entity_type: 'settlement' }

const CITY: CityScene = {
  town: TOWN,
  morphology: 'organic',
  tier: 'town',
  population: 4200,
  homeless: 120,
  shelters: 30,
  walls_level: 2,
  walls_radius: 4,
  roads: 2,
  water: 'well',
  water_side: 2,
  scale: 3,
  districts: [
    {
      id: 11,
      kind: 'residential',
      zone: 'residential',
      level: 2,
      housing: 'cottage',
      condition: 90,
      desirability: 60,
      land_value: 40,
      q: 1,
      r: 0,
      cells: [
        [1, 0],
        [2, 0],
      ],
      residents: 2000,
      dwellings: 400,
      services: [{ service: 'water', coverage: 70 }],
      turf: 0,
      locked: ['hex'],
    },
    {
      id: 12,
      kind: 'gardens',
      zone: 'green',
      level: 1,
      housing: 'hut',
      condition: 100,
      desirability: 80,
      land_value: 30,
      q: 0,
      r: 2,
      cells: [[0, 2]],
      residents: 100,
      dwellings: 20,
      services: [],
      turf: 0,
      locked: [],
    },
  ],
  buildings: [
    {
      node: { id: 21, name: 'Low School', entity_type: 'structure' },
      kind: 'school',
      zone: 'civic',
      civic: 'education',
      service: 'school',
      district_id: 11,
      q: 1,
      r: 0,
      slot: 0,
      level: 1,
      condition: 100,
      state: 'building',
      progress: 40,
      staff_pct: 50,
    },
  ],
  zones: [
    { zone: 'residential', districts: 1, cells: 2, buildings: 0 },
    { zone: 'civic', districts: 0, cells: 0, buildings: 1 },
    { zone: 'green', districts: 1, cells: 1, buildings: 0 },
  ],
} as unknown as CityScene

const LAND: LandScene = {
  region: { id: 5, name: 'Ashreach', entity_type: 'region' },
  terrain: 'plains',
  elevation: 30,
  roughness: 20,
  moisture: 50,
  forest_cover: 40,
  farmed: 30,
  grazed: 10,
  wetland: 5,
  cleared: 5,
  mined: 2,
  built: 3,
  soil_fertility: 60,
  magic_density: 10,
  river: 'river',
  coast: 'none',
  temperature: 'temperate',
  tiles: [
    { q: 0, r: 0, ground: 'lowland', cover: 'built', river: true },
    { q: 1, r: 0, ground: 'lowland', cover: 'forest', river: true },
    { q: 0, r: 1, ground: 'hills', cover: 'mined', river: false },
  ],
  settlements: [{ node: TOWN, q: 0, r: 0, detail: '4200' }],
  places: [],
  works: [],
  resources: [
    {
      node: { id: 31, name: 'Grey Seam', entity_type: 'resource' },
      commodity: 'ore',
      richness: 70,
      reserve: 600,
      initial_reserve: 1000,
      q: 0,
      r: 1,
    },
  ],
} as unknown as LandScene

const TYPES: StructureTypes = {
  world_id: 1,
  structures: [
    {
      kind: 'school',
      label: 'School',
      zone: 'civic',
      group: 'learning',
      civic: 'education',
      service: 'school',
      amenity: true,
      nuisance: false,
      staff: 'priest',
      tier: 'village',
      upkeep: null,
      instances: [
        {
          node: { id: 21, name: 'Low School', entity_type: 'structure' },
          town: TOWN,
          state: 'complete',
          level: 2,
        },
      ],
    },
  ],
  dwellings: [
    { housing: 'cottage', districts: 2, dwellings: 400, towns: [TOWN] },
  ],
} as unknown as StructureTypes

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 3 },
  })
  onApi('GET', '/api/city/4', CITY)
  onApi('GET', '/api/land/5', LAND)
  onApi('GET', '/api/structure-types/1', TYPES)
}

describe('city', () => {
  beforeEach(resetApi)

  it('draws the town from the engine and drives the god’s levers on its districts and buildings', async () => {
    serve()
    onApi('POST', '/api/actions/district:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/district_urban:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/structure:finish', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CitySection settlementId={4} />)
    await expect
      .element(
        screen.getByRole('img', {
          name: /Plan of Harrowmere: 2 districts and 1 buildings/,
        })
      )
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Residential: 1 districts, 2 hexes, 0 buildings')
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Show' }).first().click()
    await screen.getByRole('button', { name: 'Raise a level' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/district:edit')[0].body).toEqual({
      district_id: 11,
      clear_design: false,
      release: [],
      level: 3,
    })
    await screen.getByRole('button', { name: 'Release to the engine' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district_urban:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/district_urban:edit')[0].body).toEqual(
      {
        district_id: 11,
        values: {},
        release: ['hex'],
      }
    )
    await screen.getByRole('button', { name: 'Show' }).nth(2).click()
    await screen.getByRole('button', { name: 'Finish now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:finish'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/structure:finish')[0].body).toEqual({
      structure_id: 21,
    })
  })

  it('picks a district or a building from the flat plan', async () => {
    const picks: unknown[] = []
    const { screen } = await renderApp(
      <CityPlan2D
        scene={CITY}
        selected={null}
        onPick={(pick) => picks.push(pick)}
      />
    )
    await expect
      .element(screen.getByRole('img', { name: /Plan of Harrowmere/ }))
      .toBeVisible()
    expect(document.querySelectorAll('polygon').length).toBeGreaterThanOrEqual(
      3
    )
    document
      .querySelector('circle')
      ?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    document
      .querySelector('polygon')
      ?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(picks).toContainEqual({ kind: 'building', id: 21 })
  })

  it('draws the land and lets the god set its shares and its deposits', async () => {
    serve()
    onApi('POST', '/api/actions/environment:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/resource:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LandSection regionId={5} />)
    await expect
      .element(
        screen.getByRole('img', {
          name: /Land of Ashreach: 3 tiles, 1 settlements, 1 deposits/,
        })
      )
      .toBeVisible()
    await expect.element(screen.getByText('Forest: 1 tiles')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Lay it' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Show' }).first().click()
    await screen.getByRole('button', { name: 'Set', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/resource:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/resource:set')[0].body).toEqual({
      resource_id: 31,
      reserve: 600,
      fields: { richness: 70 },
    })
  })

  it('shows a building type with its values and every building of it, and a home type with its towns', async () => {
    serve()
    const { screen } = await renderApp(
      <TypePage selection={{ kind: 'building', worldId: 1, type: 'school' }} />
    )
    await expect
      .element(screen.getByRole('heading', { name: 'School' }))
      .toBeVisible()
    await expect.element(screen.getByText('Raises desirability')).toBeVisible()
    await expect.element(screen.getByText('Low School')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Begin the work' }))
      .toBeDisabled()
    const homes = await renderApp(
      <TypePage selection={{ kind: 'dwelling', worldId: 1, type: 'cottage' }} />
    )
    await expect
      .element(homes.screen.getByText('Towns with cottages (1)'))
      .toBeVisible()
  })
})
