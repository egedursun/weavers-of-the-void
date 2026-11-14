import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CitiesView } from './CitiesScreen'
import { CityPlan2D } from './CityPlan2D'
import { CityPlane } from './CityPlane'
import { CitySection } from './CitySection'
import { LandPlan2D } from './LandPlan2D'
import { LandPlane } from './LandPlane'
import { LandSection } from './LandSection'
import { TypePage } from './TypePages'
import { type CityScene, type LandScene, type StructureTypes } from './api'
import { COVER_FILL, GROUND_FILL } from './labels'

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
      caste: { id: 31, name: 'Keepers', standing: 90 },
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
      caste: null,
      locked: [],
    },
  ],
  castes: [
    { id: 31, name: 'Keepers', standing: 90 },
    { id: 32, name: 'Diggers', standing: 10 },
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
  onApi('GET', '/api/entities', {
    items: [
      {
        ...SUMMARY,
        id: 4,
        name: 'Harrowmere',
        entity_type: 'settlement',
        location_id: 5,
        importance: 9,
      },
      {
        ...SUMMARY,
        id: 5,
        name: 'Ashreach',
        entity_type: 'region',
        importance: 3,
      },
    ],
    total: 2,
  })
}

const SUMMARY = {
  title: null,
  subtype: null,
  status: 'canon',
  world_id: 1,
  location_id: null,
  power_level: 1,
  birth_epoch: 1,
  end_epoch: null,
  favorite: false,
  pending_name: false,
}

describe('city', () => {
  beforeEach(resetApi)

  it('draws the town from the engine and drives the god’s levers from the scene', async () => {
    serve()
    onApi('POST', '/api/actions/district:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/district_urban:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/structure:finish', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CityPlane settlementId={4} blocked={null} />
    )
    await expect
      .element(
        screen.getByRole('img', {
          name: /Plan of Harrowmere: 2 districts and 1 building/,
        })
      )
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Residential · 1 district · 2 hexes · 0 buildings')
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Rule it' }).first().click()
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
    await expect
      .element(screen.getByText('Keepers (standing 90)'))
      .toBeVisible()
    await screen.getByRole('combobox', { name: 'Quarter of the caste' }).click()
    await screen.getByRole('option', { name: 'Diggers' }).click()
    await screen
      .getByRole('button', { name: 'Make it their quarter and hold it' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district_urban:edit'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/district_urban:edit')[1].body).toEqual(
      {
        district_id: 11,
        values: { purity_rank_id: 32 },
        release: [],
      }
    )
    await screen.getByRole('tab', { name: /Buildings/ }).click()
    await screen.getByRole('button', { name: 'Rule it' }).first().click()
    await screen.getByRole('button', { name: 'Finish now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:finish'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/structure:finish')[0].body).toEqual({
      structure_id: 21,
    })
  })

  it('sums the town up in its record and leads to the whole city', async () => {
    serve()
    const { screen } = await renderApp(<CitySection settlementId={4} />)
    await expect.element(screen.getByText('4,200')).toBeVisible()
    const walk = screen.getByRole('link', {
      name: 'Walk the city and rule its districts',
    })
    await expect
      .element(walk)
      .toHaveAttribute('href', '/cities?view=city&town=4')
    await expect
      .element(screen.getByRole('button', { name: 'Raise the district' }))
      .toBeVisible()
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
    expect(picks).toContainEqual({ kind: 'building', id: 21 })
  })

  it('draws the land and lets the god set its deposits and lay new ones', async () => {
    serve()
    onApi('POST', '/api/actions/resource:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <LandPlane regionId={5} blocked={null} />
    )
    await expect
      .element(
        screen.getByRole('img', {
          name: /Land of Ashreach: 3 tiles, 1 settlement, 1 deposit/,
        })
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Forest · 1 of 3 tiles'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Rule it' }).first().click()
    await screen.getByRole('button', { name: 'Set', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/resource:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/resource:set')[0].body).toEqual({
      resource_id: 31,
      reserve: 600,
      fields: { richness: 70 },
    })
    await screen.getByRole('tab', { name: 'Shape' }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Lay it' }))
      .toBeDisabled()
  })

  it('sums the land up in its record and leads to the whole land', async () => {
    serve()
    const { screen } = await renderApp(<LandSection regionId={5} />)
    const walk = screen.getByRole('link', {
      name: 'Walk the land and shape it',
    })
    await expect
      .element(walk)
      .toHaveAttribute('href', '/cities?view=land&region=5')
  })

  it('draws the land in its own colours with its rivers, towns and a legend', async () => {
    serve()
    const { screen } = await renderApp(<LandSection regionId={5} />)
    const plan = screen.getByRole('img', { name: /Land of Ashreach/ })
    await expect.element(plan).toBeVisible()
    const svg = plan.element()
    expect(svg.querySelector('.fill-destructive')).toBeNull()
    expect(svg.querySelectorAll('line.stroke-land-river')).toHaveLength(1)
    expect(
      [...svg.querySelectorAll('text')].map((node) => node.textContent)
    ).toContain('Harrowmere')
    expect(svg.querySelectorAll('pattern').length).toBeGreaterThan(0)
    await expect
      .element(screen.getByRole('list', { name: 'Ground of the land' }))
      .toHaveTextContent(/Diggings · 1 of 3 tiles/)
    await expect
      .element(screen.getByRole('list', { name: 'Symbols on the land' }))
      .toHaveTextContent(/Town.*Place.*Work.*Deposit.*River.*Coast/)
  })

  it('paints every ground and cover from the land palette, never a chart or warning colour', () => {
    for (const fill of [
      ...Object.values(GROUND_FILL),
      ...Object.values(COVER_FILL),
    ])
      expect(fill).toMatch(/^fill-land-/)
  })

  it('names a town below its mark or above it when the space below is taken', async () => {
    const crowded = {
      ...LAND,
      settlements: [
        { node: TOWN, q: 0, r: 0, detail: '4200' },
        {
          node: { id: 9, name: 'Sohranin', entity_type: 'settlement' },
          q: 1,
          r: 0,
          detail: '900',
        },
      ],
    } as unknown as LandScene
    const { screen } = await renderApp(
      <LandPlan2D scene={crowded} selected={null} onPick={() => undefined} />
    )
    const svg = screen.getByRole('img', { name: /Land of Ashreach/ }).element()
    const names = [...svg.querySelectorAll('text')]
    expect(names.map((node) => node.textContent)).toEqual([
      'Harrowmere',
      'Sohranin',
    ])
    expect(names[0].getAttribute('y')).not.toBe(names[1].getAttribute('y'))
  })

  it('chooses the most important town of the world and switches to its land', async () => {
    serve()
    const seen: unknown[] = []
    const { screen } = await renderApp(
      <CitiesView search={{}} onSearch={(patch) => seen.push(patch)} />
    )
    await expect.poll(() => seen).toContainEqual({ town: 4 })
    await expect
      .element(screen.getByRole('img', { name: /Plan of Harrowmere/ }))
      .toBeVisible()
    await screen.getByRole('radio', { name: 'Land' }).click()
    expect(seen).toContainEqual({ view: 'land' })
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
