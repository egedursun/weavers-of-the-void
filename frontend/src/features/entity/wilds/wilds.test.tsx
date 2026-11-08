import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BeastSection, FoodWebSection, HerdsSection } from './BeastSection'
import { SpeciesSection } from './SpeciesSection'
import { BEAST, FOLK, KIN, KIND, SPECIES, serveBasics } from './wildsFixtures'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function serve() {
  serveBasics()
}

describe('wilds sections', () => {
  beforeEach(resetApi)

  it('shows a kind as labelled cards and sets a range from the adjust panel', async () => {
    serve()
    onApi('GET', '/api/entities/7/ecology', SPECIES)
    onApi('POST', '/api/actions/species:range', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SpeciesSection speciesId={7} />)
    await expect
      .element(screen.getByText('Small four-legged creature'))
      .toBeVisible()
    await expect.element(screen.getByText('Reads minds')).toBeVisible()
    await expect.element(screen.getByText('Lives in herds')).toBeVisible()
    await expect.element(screen.getByText('Falling')).toBeVisible()
    await expect
      .element(screen.getByText('Hunting pressure').first())
      .toBeVisible()
    expect(screen.getByText('mind_reader').elements()).toHaveLength(0)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await expect.element(screen.getByText('Held: Diet')).toBeVisible()
    await screen.getByRole('tab', { name: 'Lands' }).click()
    await screen.getByRole('spinbutton', { name: 'Abundance' }).fill('40')
    await screen.getByRole('button', { name: 'Set it so' }).nth(1).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/species:range'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/species:range')[0].body).toEqual({
      species_id: 7,
      region_id: 30,
      values: { abundance: 40 },
      release: [],
    })
  })

  it('shows a beast and lets the world decide its held temper again', async () => {
    serve()
    onApi('GET', '/api/entities/9/beast', BEAST)
    onApi('POST', '/api/actions/beast:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BeastSection beastId={9} />)
    await expect
      .element(screen.getByText('Huge four-legged great beast'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Deep cut on the left foreleg'))
      .toBeVisible()
    await expect.element(screen.getByText('Luxuries')).toBeVisible()
    await screen
      .getByRole('button', { name: 'Let the world decide again' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/beast:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/beast:edit')[0].body).toEqual({
      beast_id: 9,
      values: {},
      release: ['temper'],
    })
  })

  it('sets a herd with labelled head, stage and feeding', async () => {
    serve()
    onApi('GET', '/api/entities/50/herds', [
      { ...SPECIES.herds[0], community: FOLK, species: KIND },
    ])
    onApi('POST', '/api/actions/herd:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HerdsSection communityId={50} />)
    await expect.element(screen.getByText('11 head in 1 herd')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust this herd' }).click()
    await screen.getByRole('spinbutton', { name: 'Head count' }).fill('20')
    await screen.getByRole('button', { name: 'Set the herd' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/herd:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/herd:edit')[0].body).toEqual({
      community_id: 50,
      species_id: 7,
      values: {
        head: 20,
        stage: 'tamed',
        fed_epochs: 1,
        training: null,
        trained: 0,
      },
      release: [],
    })
  })

  it('draws who eats whom in a land', async () => {
    serve()
    onApi('GET', '/api/regions/30/food-web', {
      region_id: 30,
      nodes: [
        {
          species: KIND,
          abundance: 40,
          diet: 'carnivore',
          size_class: 'large',
        },
        { species: KIN, abundance: 70, diet: 'herbivore', size_class: 'small' },
      ],
      links: [{ hunter_id: 7, prey_id: 40, kind: 'derived' }],
    })
    const { screen } = await renderApp(<FoodWebSection regionId={30} />)
    await expect
      .element(
        screen.getByRole('img', {
          name: /Food web of 2 kinds in 2 tiers, 1 hunts/,
        })
      )
      .toBeVisible()
    await expect.element(screen.getByText('1 hunt between kinds')).toBeVisible()
    await expect.element(screen.getByText('Large hunter')).toBeVisible()
    await expect.element(screen.getByText('Small grazer')).toBeVisible()
  })
})
