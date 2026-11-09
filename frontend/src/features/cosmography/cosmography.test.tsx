import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HeavensScreen } from './HeavensScreen'
import { GalaxyView } from './NodePages'
import { RegionClimateControl } from './RegionClimateControl'
import { CATALOG, VIEW } from './cosmographyFixtures'

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
}

describe('the heavens', () => {
  beforeEach(resetApi)

  it('lays out the scale of the cosmos and seals an open rift', async () => {
    serveHeavens()
    onApi('POST', '/api/actions/rift:seal', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HeavensScreen />)
    await expect.element(screen.getByText('The Heavens').first()).toBeVisible()
    await expect.element(screen.getByText('Astral Reach').first()).toBeVisible()
    await expect.element(screen.getByText('Aerona Group').first()).toBeVisible()
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
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
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
