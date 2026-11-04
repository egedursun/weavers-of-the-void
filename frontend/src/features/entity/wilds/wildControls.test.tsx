import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { rangeAlpha, rangeBand, rangeShade } from '@/features/map/speciesRange'
import { BeastSection, HerdsSection } from './BeastSection'
import { CreateBeastDialog, CreateSpeciesDialog } from './CreateWilds'
import { SpeciesSection } from './SpeciesSection'
import { TotemSection } from './TotemSection'
import { layoutWeb, tiersOf } from './foodWebLayout'
import {
  BEAST,
  FOLK,
  KIN,
  KIND,
  LAND,
  SPECIES,
  serveBasics,
} from './wildsFixtures'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const POX = { id: 70, kind: 'entity' as const, name: 'Grey Pox' }
const CUP = { id: 80, kind: 'entity', name: 'Gold Cup' }

async function openSpecies(card: object) {
  serveBasics()
  onApi('GET', '/api/entities/7/ecology', card)
  onApi('GET', '/api/use-kinds', [
    {
      id: 3,
      name: 'Grave-guarding',
      base_use: 'guard',
      output_pct: 150,
      description: null,
      locked: [],
      species: [],
    },
  ])
  const view = await renderApp(<SpeciesSection speciesId={7} />)
  await view.screen.getByRole('button', { name: 'Adjust' }).click()
  return view
}

describe('wilds controls', () => {
  beforeEach(resetApi)

  it('forbids a hunt and pins it again', async () => {
    onApi('POST', '/api/actions/species:prey', ACCEPTED_ACTION)
    const { screen } = await openSpecies(SPECIES)
    await screen.getByRole('tab', { name: 'Hunting' }).click()
    await screen.getByRole('button', { name: 'Forbid' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/species:prey'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/species:prey')[0].body).toEqual({
      hunter_id: 7,
      prey_id: KIN.id,
      link: 'barred',
    })
  })

  it('makes a carrier immune, then lets the world decide again', async () => {
    onApi('POST', '/api/actions/species:host', ACCEPTED_ACTION)
    const { screen } = await openSpecies({
      ...SPECIES,
      hosts: [{ disease: POX, immune: true, locked: ['immune'] }],
    })
    await screen.getByRole('tab', { name: 'Sickness' }).click()
    await screen
      .getByRole('button', { name: 'Let the world decide', exact: true })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/species:host'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/species:host')[0].body).toEqual({
      species_id: 7,
      disease_id: POX.id,
      carried: true,
      immune: true,
      release: true,
    })
  })

  it('keeps a kind in a way of your own', async () => {
    onApi('POST', '/api/actions/species:custom_use', ACCEPTED_ACTION)
    const { screen } = await openSpecies(SPECIES)
    await screen.getByRole('tab', { name: 'Ways of keeping' }).click()
    await screen
      .getByRole('switch', { name: 'Keep this kind as Grave-guarding' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/species:custom_use'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/species:custom_use')[0].body).toEqual({
      species_id: 7,
      kind_id: 3,
      held: true,
    })
  })

  it('scatters a herd of the kind', async () => {
    onApi('POST', '/api/actions/herd:drop', ACCEPTED_ACTION)
    serveBasics()
    onApi('GET', '/api/entities/50/herds', [
      { ...SPECIES.herds[0], community: FOLK, species: KIND },
    ])
    const { screen } = await renderApp(<HerdsSection communityId={50} />)
    await screen
      .getByRole('button', { name: `Scatter the herd of ${KIND.name}` })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/herd:drop'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/herd:drop')[0].body).toEqual({
      community_id: 50,
      species_id: KIND.id,
    })
  })

  it('creates a kind with the nature you choose', async () => {
    serveBasics()
    onApi('POST', '/api/actions/species:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <CreateSpeciesDialog regionId={LAND.id} />
    )
    await screen.getByRole('button', { name: 'Create a kind' }).click()
    await screen.getByRole('textbox', { name: 'Name' }).fill('Ashwing')
    await screen.getByRole('button', { name: 'Hunter', exact: true }).click()
    await screen.getByRole('button', { name: 'Let it walk the land' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/species:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/species:create')[0].body
    ).toMatchObject({
      name: 'Ashwing',
      region_id: LAND.id,
      body_plan: 'quadruped',
      size_class: 'medium',
      diet: 'carnivore',
      sociality: 'herd',
      abundance: 40,
    })
  })

  it('calls forth a named beast', async () => {
    serveBasics()
    onApi('POST', '/api/actions/beast:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreateBeastDialog regionId={LAND.id} />)
    await screen.getByRole('button', { name: 'Call forth a beast' }).click()
    await screen.getByRole('textbox', { name: 'Name' }).fill('Vharrun')
    await screen.getByRole('button', { name: 'Call it forth' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/beast:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/beast:create')[0].body).toMatchObject({
      name: 'Vharrun',
      lair_id: LAND.id,
      size_class: 'huge',
      temper: 'sleeping',
      strength: 80,
    })
  })

  it('sets a people’s totem aside', async () => {
    serveBasics()
    onApi('GET', '/api/entities/50/totem', {
      people_id: 50,
      species: KIND,
      tradition: { id: 60, kind: 'entity', name: 'The Feast of the Crawler' },
    })
    onApi('POST', '/api/actions/people:totem', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TotemSection peopleId={50} />)
    await screen.getByRole('button', { name: 'Set it aside' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/people:totem'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/people:totem')[0].body).toEqual({
      people_id: 50,
      species_id: null,
    })
  })

  it('shows what a beast’s abilities do and slays it', async () => {
    serveBasics()
    onApi('GET', '/api/entities/9/beast', {
      ...BEAST,
      treasures: [CUP],
      tributes: [
        {
          town: FOLK,
          treaty: { id: 90, kind: 'entity', name: 'The Tribute of Reed Folk' },
          commodity: 'luxuries',
          units: 10,
          last_kept_epoch: 50,
        },
      ],
    })
    onApi('POST', '/api/actions/beast:slay', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BeastSection beastId={9} />)
    await expect.element(screen.getByText('3 lands')).toBeVisible()
    await expect.element(screen.getByText('Gold Cup').first()).toBeVisible()
    await expect
      .element(screen.getByText('10 luxuries each epoch'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Slay the beast' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/beast:slay'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/beast:slay')[0].body).toEqual({
      beast_id: 9,
      slayer_id: null,
    })
  })
})

describe('wilds layouts', () => {
  it('stacks hunters above their prey', () => {
    const links = [
      { hunter_id: 1, prey_id: 2, kind: 'derived' as const },
      { hunter_id: 2, prey_id: 3, kind: 'pinned' as const },
      { hunter_id: 3, prey_id: 1, kind: 'derived' as const },
    ]
    const tiers = tiersOf([1, 2, 3, 4], links.slice(0, 2))
    expect(tiers.get(3)).toBe(0)
    expect(tiers.get(2)).toBe(1)
    expect(tiers.get(1)).toBe(2)
    expect(tiers.get(4)).toBe(0)
    const looped = tiersOf([1, 2, 3], links)
    expect([...looped.values()].every((tier) => tier <= 3)).toBe(true)
    const layout = layoutWeb({
      region_id: 30,
      nodes: [
        {
          species: { ...KIND, kind: 'entity' as const, id: 1 },
          abundance: 20,
          diet: 'carnivore',
          size_class: 'large',
        },
        {
          species: { ...KIN, kind: 'entity' as const, id: 2 },
          abundance: 60,
          diet: 'omnivore',
          size_class: 'small',
        },
        {
          species: { ...FOLK, kind: 'entity' as const, id: 3 },
          abundance: 90,
          diet: 'herbivore',
          size_class: 'small',
        },
      ],
      links: links.slice(0, 2),
    })
    const y = new Map(layout.nodes.map((node) => [node.id, node.y]))
    expect((y.get(1) ?? 0) < (y.get(2) ?? 0)).toBe(true)
    expect((y.get(2) ?? 0) < (y.get(3) ?? 0)).toBe(true)
    expect(layout.edges).toEqual([
      { from: 1, to: 2, pinned: false },
      { from: 2, to: 3, pinned: true },
    ])
    expect(layout.tiers).toBe(3)
  })

  it('shades a range by its share of the peak', () => {
    expect(rangeBand(0, 80)).toBeNull()
    expect(rangeBand(10, 80)).toBe('trace')
    expect(rangeBand(40, 80)).toBe('common')
    expect(rangeBand(80, 80)).toBe('teeming')
    expect(rangeAlpha('teeming')).toBeGreaterThan(rangeAlpha('trace'))
    const shade = rangeShade([{ region: { id: 4 }, abundance: 30 }], 30)
    expect(shade.cells.get(4)).toBe(30)
  })
})
