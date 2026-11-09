import '@/styles/index.css'
import { describe, expect, it, vi } from 'vitest'
import { render } from 'vitest-browser-react'
import { Cosmos2D } from './Cosmos2D'
import { type CosmosData } from './api'
import { indexCosmos } from './model/cosmosModel'

const DATA: CosmosData = {
  stars: [
    {
      id: 1,
      name: 'Velar Sun',
      star_type: 'yellow_dwarf',
      brightness: 70,
      x: 0,
      y: 0,
      description: null,
      image_prompt: null,
      created_epoch: 1,
      galactic_zone: 'outer_disc',
      age_stage: 'main',
      stability: 70,
      radiation: 20,
      sacredness: 0,
    },
  ],
  worlds: [1, 2].map((id) => ({
    world: {
      id,
      name: id === 1 ? 'Velar' : 'Mirevast',
      world_type: id === 1 ? 'ordinary' : 'ocean',
      star_id: 1,
      parent_world_id: null,
      orbit: id,
      gravity: 'normal',
      atmosphere: 'normal',
      time_factor: 1,
      discovery: id === 1 ? 'known' : 'forgotten',
      danger: 10,
      leakage: 0,
      cosmology: null,
      phonology: null,
      description: null,
      image_prompt: null,
      creator_son_id: null,
      patron_son_id: null,
      patron_automatic: false,
      epoch_star_entity_id: null,
      mirror_twin_id: null,
      mortal_agents: null,
      climate_era: null,
      climate_epochs_left: null,
      climate_since_epoch: null,
      created_epoch: 1,
      terrain_seed: `world-${id}`,
      terrain_sea: 0.4,
      terrain_mountains: 0.2,
      terrain_humidity: 0,
      magnetism: 50,
      radiation: 10,
      biosphere_health: 80,
      age_stage: 'mature',
      mood: 0,
    },
    type_label: id === 1 ? 'Ordinary world' : 'Ocean world',
    counts: {
      regions: 1,
      peoples: 1,
      settlements: 1,
      living: 1,
      population: 100,
    },
    sons: [],
    cover: null,
  })),
  foreign_gods: [],
  routes: [
    {
      id: 1,
      world_a_id: 1,
      world_b_id: 2,
      method: 'light_sail',
      duration_epochs: 3,
      danger: 20,
      known: false,
      controller_entity_id: null,
      vehicle_entity_id: null,
      builder_son_id: null,
      bound_star_id: null,
      description: null,
      created_epoch: 1,
      active: true,
      closure: null,
      temp_open_until_epoch: null,
      temp_closed_until_epoch: null,
      capacity: 100,
      traffic: 0,
      toll_pct: 0,
      piracy: 0,
      wear: 0,
      window_every: 0,
      window_offset: 0,
      status: {
        open: true,
        state: 'open',
        reason: 'The route is open.',
        opens_epoch: null,
        closes_epoch: null,
      },
    },
  ],
  journeys: [],
  sky_events: [],
  world_types: [],
  places: [],
  communities: [],
}

describe('Cosmos2D', () => {
  it('draws stars, worlds and routes and reports selections', async () => {
    const onSelectWorld = vi.fn()
    const onSelectStar = vi.fn()
    const onDescend = vi.fn()
    const screen = await render(
      <Cosmos2D
        index={indexCosmos(DATA)}
        selectedWorldId={1}
        selectedStarId={undefined}
        onSelectWorld={onSelectWorld}
        onSelectStar={onSelectStar}
        onDescend={onDescend}
      />
    )
    await expect
      .element(
        screen.getByRole('group', { name: 'Cosmos: stars, worlds and routes' })
      )
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Mirevast, Ocean world, in mist' })
      .click()
    expect(onSelectWorld).toHaveBeenCalledWith(2)
    await screen
      .getByRole('button', { name: 'Velar Sun, Yellow dwarf' })
      .click()
    expect(onSelectStar).toHaveBeenCalledWith(1)
    await expect
      .element(screen.getByRole('button', { name: 'Velar, Ordinary world' }))
      .toHaveAttribute('aria-pressed', 'true')
    expect(document.querySelector('path title')?.textContent).toContain(
      'a hidden route the mortals do not know'
    )
  })

  it('draws routes as curved paths in their method style, faint when closed and dim when hidden', async () => {
    const base = DATA.routes[0]
    const routes = [
      {
        ...base,
        id: 11,
        known: true,
        active: true,
        method: 'light_sail' as const,
      },
      {
        ...base,
        id: 12,
        known: true,
        active: false,
        method: 'ancient_gate' as const,
        closure: 'severed' as const,
        temp_closed_until_epoch: 9,
        description: 'The void cut the gate',
        status: {
          open: false,
          state: 'severed' as const,
          reason: 'A storm severed the route.',
          opens_epoch: 9,
          closes_epoch: null,
        },
      },
      {
        ...base,
        id: 13,
        known: false,
        active: true,
        method: 'light_sail' as const,
      },
    ]
    await render(
      <Cosmos2D
        index={indexCosmos({ ...DATA, routes })}
        selectedWorldId={undefined}
        selectedStarId={undefined}
        onSelectWorld={vi.fn()}
        onSelectStar={vi.fn()}
        onDescend={vi.fn()}
      />
    )
    const paths = [...document.querySelectorAll('path')].filter((path) =>
      path.querySelector('title')
    )
    expect(paths).toHaveLength(3)
    const [open, closed, hidden] = paths
    expect(open.getAttribute('d')).toMatch(/^M [\d.-]+ [\d.-]+ Q /)
    expect(open.getAttribute('stroke')).toContain('--cosmos-route-light-sail')
    expect(open.getAttribute('stroke-dasharray')).toBe('7 5')
    expect(closed.getAttribute('stroke-dasharray')).toBe('2 6')
    expect(Number(closed.getAttribute('opacity'))).toBeLessThan(
      Number(open.getAttribute('opacity'))
    )
    expect(Number(hidden.getAttribute('opacity'))).toBeLessThan(
      Number(open.getAttribute('opacity'))
    )
    const closedTitle = closed.querySelector('title')?.textContent ?? ''
    expect(closedTitle).toMatch(/^Ancient gate/)
    expect(closedTitle).toContain('opens at the start of epoch 9')
    expect(closedTitle).toContain('The void cut the gate')
    expect(hidden.querySelector('title')?.textContent).toContain(
      'a hidden route the mortals do not know'
    )
  })
})
