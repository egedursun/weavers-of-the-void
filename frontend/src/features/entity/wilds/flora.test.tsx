import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RegionCropsSection, WorldLifeSection } from './FloraPanels'
import { SpeciesSection } from './SpeciesSection'
import { CROPS, LIFE, PLANT, serveBasics } from './wildsFixtures'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

describe('flora panels', () => {
  beforeEach(resetApi)

  it('shows a plant, where it is sown and its pests, and reshapes its growth', async () => {
    serveBasics()
    onApi('GET', '/api/entities/8/ecology', PLANT)
    onApi('POST', '/api/actions/plant:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SpeciesSection speciesId={8} />)
    await expect.element(screen.getByText('Kind of life').first()).toBeVisible()
    await expect.element(screen.getByText('Barley Downs').first()).toBeVisible()
    await expect.element(screen.getByText('Grain Moth').first()).toBeVisible()
    await expect.element(screen.getByText('Cultivated').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('tab', { name: 'Growth' }).click()
    await screen.getByRole('spinbutton', { name: 'Soil it needs' }).fill('20')
    await screen.getByRole('button', { name: 'Set' }).nth(1).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/plant:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/plant:edit')[0].body).toEqual({
      species_id: 8,
      values: { soil_need: 20 },
      release: [],
    })
  })

  it('lists a land’s crops and lets a held share drift again', async () => {
    serveBasics()
    onApi('GET', '/api/regions/31/crops', CROPS)
    onApi('POST', '/api/actions/crop:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RegionCropsSection regionId={31} />)
    await expect.element(screen.getByText('Downs Barley')).toBeVisible()
    await expect.element(screen.getByText('91%')).toBeVisible()
    await expect.element(screen.getByText('Fibre')).toBeVisible()
    await screen.getByRole('button', { name: 'Let it drift' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/crop:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/crop:set')[0].body).toEqual({
      region_id: 31,
      plant_id: 8,
      share: null,
      hold: false,
      release: ['share'],
    })
  })

  it('lets a world bear a new kind of life', async () => {
    serveBasics()
    onApi('GET', '/api/worlds/1/life', LIFE)
    onApi('POST', '/api/actions/world:life', ACCEPTED_ACTION)
    const { screen } = await renderApp(<WorldLifeSection worldId={1} />)
    await expect.element(screen.getByText('Lives on any world')).toBeVisible()
    await screen.getByRole('button', { name: 'Let it bear' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/world:life'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/world:life')[0].body).toEqual({
      world_id: 1,
      biochemistry: 'silicon',
      present: true,
    })
  })
})
