import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HeavensView } from './HeavensScreen'
import { RegionClimateControl } from './RegionClimateControl'
import { CATALOG, VIEW } from './cosmographyFixtures'
import { CreateGalaxyStudio } from './create/CreateStudio'
import { ladderOf } from './ladder'
import { GalaxyView } from './wiki/GalaxyWiki'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function serveHeavens() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 12 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
  onApi('GET', '/api/cosmography', VIEW)
  onApi('GET', '/api/cosmography/catalog', CATALOG)
  onApi('GET', '/api/cosmos', {
    stars: [],
    worlds: [],
    foreign_gods: [],
    routes: [],
    journeys: [],
    sky_events: [],
    world_types: [],
    places: [],
    communities: [],
  })
  onApi('GET', '/api/cosmography/nodes/301/wiki', {
    node_id: 301,
    kind: 'galaxy',
    cover: null,
    images: [],
    timeline: [],
  })
}

describe('the heavens', () => {
  beforeEach(resetApi)

  it('lays out the scale of the cosmos and seals an open rift', async () => {
    serveHeavens()
    onApi('POST', '/api/actions/rift:seal', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <HeavensView search={{ pane: 'rifts' }} onSearch={() => undefined} />
    )
    await expect.element(screen.getByText('The Heavens').first()).toBeVisible()
    await expect.element(screen.getByText('Astral Reach').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Seal' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/rift:seal'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/rift:seal')[0].body).toEqual({
      rift_id: 501,
    })
  })

  it('reshapes a galaxy and holds the value', async () => {
    serveHeavens()
    onApi('POST', '/api/actions/galaxy:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GalaxyView galaxyId={301} />)
    await expect
      .element(screen.getByRole('link', { name: 'Homesun' }).first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).nth(2).click()
    await screen
      .getByRole('spinbutton', { name: 'Star formation' })
      .first()
      .fill('80')
    await screen
      .getByRole('button', { name: 'Hold these values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/galaxy:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/galaxy:edit')[0].body).toEqual({
      galaxy_id: 301,
      values: { star_formation: 80 },
      release: [],
    })
  })

  it('sets a new galaxy turning from the chosen form', async () => {
    serveHeavens()
    onApi('POST', '/api/actions/galaxy:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreateGalaxyStudio ladder={ladderOf(VIEW)} catalog={CATALOG} />
    )
    await screen.getByRole('radio', { name: 'Spiral galaxy' }).click()
    await screen.getByRole('textbox', { name: 'Name' }).fill('Far Wheel')
    await screen.getByRole('button', { name: 'Set it turning' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/galaxy:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/galaxy:create')[0].body).toEqual({
      name: 'Far Wheel',
      galaxy_type: 'spiral',
      cluster_id: null,
      dimension_id: null,
    })
  })

  it('turns the climate of a region', async () => {
    serveHeavens()
    onApi('POST', '/api/actions/region_climate:turn', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <RegionClimateControl
        ground={{
          region_id: 7,
          leak: 12,
          current: 'cold',
          temperature_shift: -10,
          rainfall_shift: 5,
        }}
        refresh={['region', 7]}
      />
    )
    await expect.element(screen.getByText('Cold current').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Make it warmer' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/region_climate:turn'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/region_climate:turn')[0].body).toEqual(
      { region_id: 7, turn: 'warmer' }
    )
  })
})
