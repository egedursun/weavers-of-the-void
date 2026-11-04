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

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const LAND = { id: 30, kind: 'entity', name: 'Saltreach' }
const KIN = { id: 40, kind: 'entity', name: 'Dune Hare' }
const FOLK = { id: 50, kind: 'entity', name: 'Reed Folk' }
const KIND = { id: 7, kind: 'entity', name: 'Sand Crawler' }

const SPECIES = {
  species_id: 7,
  body_plan: 'quadruped',
  size_class: 'small',
  lifespan_years: 6,
  maturity_years: 1,
  litter_size: 5,
  breeding_seasons: 2,
  diet: 'omnivore',
  metabolism: 65,
  habitat: { desert: 100 },
  temperature_min: 48,
  temperature_max: 78,
  water_need: 50,
  altitude_min: 0,
  altitude_max: 1523,
  nocturnal: false,
  migratory: false,
  migration_path: [],
  aggression: 65,
  territoriality: 47,
  sociality: 'herd',
  cunning: 67,
  fear_of_people: 45,
  tameability: 60,
  stage: 'wild',
  domesticated_from: null,
  sacred_to: null,
  traits: ['mind_reader', 'stoneskin'],
  uses: ['food', 'companion'],
  yields: [
    { product: 'meat', commodity: 'livestock', material: null, rate: 2 },
  ],
  hosts: [],
  ranges: [
    {
      region: LAND,
      abundance: 68,
      trend: 'falling',
      fit: 76,
      hunted: 1,
      since_epoch: 50,
      locked: [],
    },
  ],
  herds: [
    {
      community: FOLK,
      species: null,
      head: 11,
      stage: 'tamed',
      since_epoch: 50,
      fed_epochs: 1,
      locked: [],
    },
  ],
  hunts: [KIN],
  hunted_by: [],
  descendants: [],
  beasts: [],
  locked: ['diet'],
}

const BEAST = {
  beast_id: 9,
  species: KIND,
  endurance: 72,
  perception: 55,
  willpower: 64,
  intelligence: 38,
  age: 140,
  lifespan: 400,
  size_class: 'huge',
  lair: LAND,
  temper: 'territorial',
  bound_to: null,
  hoard: { luxuries: 40 },
  raids: 7,
  woke_epoch: 44,
  terror: 78,
  renown: 62,
  wounds: [{ by: FOLK, epoch: 48 }],
  injuries: [
    {
      part: 'left_foreleg',
      kind: 'deep_cut',
      severity: 60,
      state: 'healing',
      function_loss: 30,
    },
  ],
  body_plan: 'quadruped',
  hp: 320,
  locked: ['temper'],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
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
      values: { head: 20, stage: 'tamed', fed_epochs: 1 },
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
      links: [{ hunter_id: 7, prey_id: 40 }],
    })
    const { screen } = await renderApp(<FoodWebSection regionId={30} />)
    await expect
      .element(screen.getByText('hunts', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('1 hunt between kinds')).toBeVisible()
    await expect.element(screen.getByText('Large hunter')).toBeVisible()
    await expect.element(screen.getByText('Small grazer')).toBeVisible()
  })
})
