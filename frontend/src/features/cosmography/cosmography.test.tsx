import { useState } from 'react'
import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { page } from 'vitest/browser'
import { HeavensView } from './HeavensScreen'
import { RegionClimateControl } from './RegionClimateControl'
import { CATALOG, VIEW } from './cosmographyFixtures'
import { CreateGalaxyStudio } from './create/CreateStudio'
import { type HeavensSearch } from './heavensSearch'
import { ladderOf } from './ladder'
import { ClusterView } from './wiki/ClusterWiki'
import { DimensionLaws } from './wiki/DimensionLaws'
import { GalaxyView } from './wiki/GalaxyWiki'
import { HostedStrata } from './wiki/HostedStrata'
import { SkyWorship } from './wiki/SkyWorship'

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
    timeline_total: 0,
  })
  onApi('GET', '/api/cosmography/nodes/301/worship', {
    node_id: 301,
    sky: 'galaxy',
    name: 'Aerona',
    worshippers: [],
    candidates: [],
  })
  onApi('GET', '/api/cosmography/nodes/201/wiki', {
    node_id: 201,
    kind: 'cluster',
    cover: null,
    images: [],
    timeline: [],
    timeline_total: 0,
  })
}

function LiveHeavens() {
  const [search, setSearch] = useState<HeavensSearch>({})
  return (
    <HeavensView
      search={search}
      onSearch={(patch) => setSearch((previous) => ({ ...previous, ...patch }))}
    />
  )
}

describe('the heavens', () => {
  beforeEach(resetApi)

  it('brings the creation studio into sight from the shape the heavens button', async () => {
    serveHeavens()
    await page.viewport(1280, 720)
    const { screen } = await renderApp(<LiveHeavens />)
    await screen.getByRole('button', { name: 'Shape the heavens' }).click()
    await expect
      .element(screen.getByRole('tab', { name: /Create/ }))
      .toHaveAttribute('aria-selected', 'true')
    await expect.element(screen.getByRole('tabpanel').first()).toBeInViewport()
  })

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
    await expect.element(screen.getByText('Arms 2–4')).toBeVisible()
    await expect.element(screen.getByText('Dormant nucleus 75%')).toBeVisible()
    await expect.element(screen.getByText('Quasar 1%')).toBeVisible()
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

  it('shows the laws of a dimension and releases one bound across it', async () => {
    serveHeavens()
    onApi('POST', '/api/actions/dimension:release_law', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <DimensionLaws
        dimension={VIEW.dimensions[0]}
        worldCount={0}
        laws={[
          {
            law: 'the_dead_speak',
            label: 'The dead speak',
            description: 'The dead can be heard.',
            entity_id: null,
            name: null,
            strength: 100,
          },
          {
            law: 'bounty',
            label: 'Bounty',
            description: 'Harvests swell.',
            entity_id: 77,
            name: 'Long Summer',
            strength: 60,
          },
        ]}
      />
    )
    await expect.element(screen.getByText('By its kind')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /Bind it/ }))
      .toHaveAttribute('aria-disabled', 'true')
    await screen.getByRole('button', { name: /Release/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/dimension:release_law'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/dimension:release_law')[0].body
    ).toEqual({ law_id: 77 })
  })

  it('lists the peoples that worship a star and turns them away or toward it', async () => {
    serveHeavens()
    onApi('GET', '/api/cosmography/nodes/9/worship', {
      node_id: 9,
      sky: 'star',
      name: 'Homesun',
      worshippers: [
        {
          id: 41,
          name: 'Sunward Folk',
          entity_type: 'people',
          world_id: 1,
          piety: 70,
        },
      ],
      candidates: [
        {
          id: 42,
          name: 'Valley Town',
          entity_type: 'settlement',
          world_id: 1,
          piety: 30,
        },
      ],
    })
    onApi('POST', '/api/actions/heavens:worship', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SkyWorship nodeId={9} />)
    await expect.element(screen.getByText('Sunward Folk')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /Make them worship it/ }))
      .toHaveAttribute('aria-disabled', 'true')
    await screen.getByRole('button', { name: /Turn away/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/heavens:worship'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/heavens:worship')[0].body).toEqual({
      community_id: 41,
      sky: 'star',
      worships: false,
      dimension_id: null,
    })
    await screen.getByRole('combobox', { name: 'People to turn' }).click()
    await screen.getByRole('option', { name: 'Valley Town' }).click()
    await screen.getByRole('button', { name: /Make them worship it/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/heavens:worship'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/heavens:worship')[1].body).toEqual({
      community_id: 42,
      sky: 'star',
      worships: true,
      dimension_id: null,
    })
  })

  it('names the central galaxy of a cluster', async () => {
    serveHeavens()
    const { screen } = await renderApp(<ClusterView clusterId={201} />)
    await expect
      .element(screen.getByText(/Central galaxy, which draws the others/))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Aerona' }).first())
      .toBeVisible()
  })

  it('names the strata of the dead that lie in a dimension', async () => {
    serveHeavens()
    const { screen } = await renderApp(
      <HostedStrata
        name='The Below'
        strata={[
          {
            id: 5,
            name: 'Grey Field',
            kind: 'common',
            population: 12,
            realm: { id: 88, kind: 'entity', name: 'Hall of Shades' },
          },
        ]}
      />
    )
    await expect.element(screen.getByText('Grey Field')).toBeVisible()
    await expect.element(screen.getByText('12 souls')).toBeVisible()
    await expect.element(screen.getByText('Hall of Shades')).toBeVisible()
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
