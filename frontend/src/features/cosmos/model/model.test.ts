import { describe, expect, it } from 'vitest'
import {
  type CosmosData,
  type CosmosWorld,
  type JourneyRecord,
  type RouteRecord,
} from '../api'
import { validateCosmosSearch } from '../cosmosSearch'
import { pick } from '../scene3d/picking'
import { createFrameState } from '../scene3d/sceneContext'
import { routeBends } from '../scene3d/useCosmosLayout'
import {
  crowdedRegions,
  homeWorldId,
  indexCosmos,
  journeyProgress,
  routeState,
  routeStateText,
  sortJourneys,
} from './cosmosModel'
import { fnv1a, seededRandom, unitHash } from './hash'
import { curvedPath, layoutCosmos2D } from './layout2d'
import { bodyRadius, layoutCosmos3D, orbitOffset, orbitUnit } from './layout3d'
import { questBlockers } from './quests'
import { buildRuleBook } from './rules'
import { skyCalendar, skyCalendarText } from './skyCalendar'

function world(
  id: number,
  overrides: Partial<CosmosWorld['world']> = {},
  population = 1000
): CosmosWorld {
  return {
    world: {
      id,
      name: `World ${id}`,
      world_type: 'ordinary',
      star_id: 1,
      parent_world_id: null,
      orbit: 1,
      gravity: 'normal',
      atmosphere: 'normal',
      time_factor: 1,
      discovery: 'known',
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
      consciousness_closed: false,
      ...overrides,
    },
    type_label: 'Ordinary world',
    counts: { regions: 2, peoples: 1, settlements: 1, living: 3, population },
    sons: [],
    cover: null,
  }
}

function route(id: number, overrides: Partial<RouteRecord> = {}): RouteRecord {
  return {
    id,
    world_a_id: 1,
    world_b_id: 2,
    method: 'ancient_gate',
    medium: 'space',
    mechanism: 'gate',
    duration_epochs: 2,
    danger: 20,
    known: true,
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
    ...overrides,
  }
}

function status(
  state: RouteRecord['status']['state'],
  open: boolean,
  epochs: { opens?: number; closes?: number } = {}
): RouteRecord['status'] {
  return {
    open,
    state,
    reason: state,
    opens_epoch: epochs.opens ?? null,
    closes_epoch: epochs.closes ?? null,
  }
}

function journey(
  id: number,
  overrides: Partial<JourneyRecord> = {}
): JourneyRecord {
  return {
    id,
    traveller_entity_id: 9,
    route_id: 1,
    vehicle_entity_id: null,
    origin_world_id: 1,
    destination_world_id: 2,
    intent: 'colony',
    population: 10,
    epochs_left: 1,
    status: 'underway',
    events: [],
    memory_lost: false,
    start_epoch: 3,
    end_epoch: null,
    result_entity_id: null,
    cargo: [],
    passengers: [],
    convoy: 1,
    escorts: 0,
    supplies: 0,
    births: 0,
    deaths: 0,
    ...overrides,
  }
}

function cosmos(overrides: Partial<CosmosData> = {}): CosmosData {
  return {
    stars: [
      {
        id: 1,
        name: 'Sun',
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
      {
        id: 2,
        name: 'Ember',
        star_type: 'dead_star',
        brightness: 10,
        x: 500,
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
    worlds: [
      world(1),
      world(2, { orbit: 2 }),
      world(3, { star_id: null, parent_world_id: 1, orbit: 0.5 }),
      world(4, { star_id: null }),
    ],
    foreign_gods: [],
    routes: [route(1), route(2), route(3, { world_a_id: 2, world_b_id: 1 })],
    journeys: [],
    sky_events: [],
    world_types: [],
    places: [],
    communities: [],
    campaigns: [],
    migrations: [],
    orbits: [],
    ...overrides,
  }
}

describe('route state', () => {
  it('reads the route status the backend derived', () => {
    expect(routeState(route(1)).key).toBe('open')
    const temporary = route(1, {
      status: status('temporary', true, { closes: 9 }),
    })
    expect(routeState(temporary)).toMatchObject({
      key: 'temporary',
      open: true,
      untilEpoch: 9,
    })
    expect(routeState(route(1, { status: status('sealed', false) })).key).toBe(
      'sealed'
    )
    expect(
      routeState(
        route(1, {
          method: 'slingshot_orbit',
          status: status('misaligned', false, { opens: 10 }),
        })
      ).key
    ).toBe('misaligned')
    expect(
      routeState(
        route(1, {
          method: 'wormhole',
          status: status('unstable', false, { opens: 11 }),
        })
      )
    ).toMatchObject({ key: 'unstable', open: false, opensAtEpoch: 11 })
    const severed = route(1, {
      active: false,
      closure: 'severed',
      temp_closed_until_epoch: 14,
      status: status('severed', false, { opens: 14 }),
    })
    expect(routeState(severed)).toMatchObject({
      key: 'severed',
      open: false,
      opensAtEpoch: 14,
    })
    expect(routeStateText(severed)).toBe(
      'Severed, opens at the start of epoch 14'
    )
  })
})

describe('cosmos index', () => {
  it('groups moons, planets, routes and names', () => {
    const index = indexCosmos(cosmos())
    expect(index.moonsOf(1).map((item) => item.world.id)).toEqual([3])
    expect(index.planetsOf(1).map((item) => item.world.id)).toEqual([1, 2])
    expect(index.routesOf(1)).toHaveLength(3)
    expect(index.worldName(99)).toBe('an unknown world')
    expect(homeWorldId(index, null)).toBe(1)
    expect(homeWorldId(index, 2)).toBe(2)
  })

  it('sorts journeys by status then newest and measures progress', () => {
    const list = sortJourneys([
      journey(1, { status: 'lost' }),
      journey(2, { start_epoch: 2 }),
      journey(3, { start_epoch: 5 }),
      journey(4, { status: 'arrived' }),
    ])
    expect(list.map((item) => item.id)).toEqual([3, 2, 4, 1])
    expect(
      journeyProgress(journey(1, { epochs_left: 1 }), route(1))
    ).toBeCloseTo(0.5)
    expect(journeyProgress(journey(1, { status: 'arrived' }), route(1))).toBe(1)
  })

  it('finds the most crowded regions', () => {
    const base = {
      title: null,
      subtype: null,
      status: 'canon' as const,
      world_id: 1,
      power_level: 1,
      birth_epoch: 1,
      end_epoch: null,
      importance: null,
      favorite: false,
      pending_name: false,
    }
    const regions = [
      {
        ...base,
        id: 10,
        name: 'A',
        entity_type: 'region' as const,
        location_id: null,
      },
      {
        ...base,
        id: 11,
        name: 'B',
        entity_type: 'region' as const,
        location_id: null,
      },
    ]
    const people = [10, 11, 11].map((location, slot) => ({
      ...base,
      id: 20 + slot,
      name: `P${slot}`,
      entity_type: 'people' as const,
      location_id: location,
    }))
    expect(
      crowdedRegions(regions, people, 4).map((entry) => [
        entry.region.id,
        entry.count,
      ])
    ).toEqual([
      [11, 2],
      [10, 1],
    ])
  })

  it('knows which legendary quests have no target', () => {
    const blockers = questBlockers(indexCosmos(cosmos()))
    expect(blockers.star).toBeUndefined()
    expect(blockers.route).toBe('No sealed route')
  })
})

describe('2D layout', () => {
  it('places every star and world inside the padded view box', () => {
    const layout = layoutCosmos2D(cosmos())
    expect(layout.stars.size).toBe(2)
    expect(layout.worlds.size).toBe(4)
    for (const point of [...layout.stars.values(), ...layout.worlds.values()]) {
      expect(point.x).toBeGreaterThan(layout.viewBox.x)
      expect(point.x).toBeLessThan(layout.viewBox.x + layout.viewBox.width)
      expect(point.y).toBeGreaterThan(layout.viewBox.y)
      expect(point.y).toBeLessThan(layout.viewBox.y + layout.viewBox.height)
    }
    const moon = layout.worlds.get(3)
    const parent = layout.worlds.get(1)
    expect(
      moon && parent && Math.hypot(moon.x - parent.x, moon.y - parent.y)
    ).toBeCloseTo(20)
  })

  it('draws curved routes as quadratic paths', () => {
    expect(curvedPath({ x: 0, y: 0 }, { x: 10, y: 0 }, 0.5)).toBe(
      'M 0 0 Q 5 5 10 0'
    )
  })
})

describe('3D layout', () => {
  it('derives the orbit unit from star spacing within its bounds', () => {
    expect(orbitUnit(cosmos())).toBeLessThanOrEqual(58)
    expect(orbitUnit(cosmos())).toBeGreaterThanOrEqual(24)
    const crowded = cosmos({
      stars: [
        {
          id: 1,
          name: 'A',
          star_type: 'yellow_dwarf',
          brightness: 50,
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
        {
          id: 2,
          name: 'B',
          star_type: 'yellow_dwarf',
          brightness: 50,
          x: 10,
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
    })
    expect(orbitUnit(crowded)).toBe(24)
  })

  it('makes gas giants larger and moons smaller', () => {
    const plain = bodyRadius(world(1), 50)
    expect(bodyRadius(world(1, { world_type: 'gas' }), 50)).toBeCloseTo(
      plain * 1.75
    )
    expect(bodyRadius(world(1, { parent_world_id: 2 }), 50)).toBeCloseTo(
      plain * 0.55
    )
  })

  it('places planets on their orbit and moons around their parent', () => {
    const data = cosmos()
    const layout = layoutCosmos3D(data)
    const star = layout.stars.get(1)
    const body = layout.worlds.get(1)
    if (!star || !body) throw new Error('missing layout')
    const offset = orbitOffset(body, 0, [0, 0, 0])
    const planet = body.anchor.map((value, axis) => value + (offset[axis] ?? 0))
    const distance = Math.hypot(
      planet[0] - star.position[0],
      planet[1] - star.position[1],
      planet[2] - star.position[2]
    )
    expect(distance).toBeCloseTo(body.orbitRadius)
    expect(layout.worlds.get(3)?.kind).toBe('moon')
    expect(layout.worlds.get(4)?.kind).toBe('free')
    expect(layout.order.indexOf(1)).toBeLessThan(layout.order.indexOf(3))
  })

  it('bends parallel routes apart', () => {
    const bends = routeBends(cosmos())
    expect(bends.get(1)).toBe(0)
    expect(bends.get(2)).toBeCloseTo(-0.2)
    expect(bends.get(3)).toBeCloseTo(0.2)
  })
})

describe('sky calendar', () => {
  it('follows the alignment cycle and forced alignments', () => {
    expect(skyCalendar(10, 5, null)).toMatchObject({
      aligned: true,
      closesEpoch: 11,
    })
    expect(skyCalendar(11, 5, null)).toMatchObject({
      aligned: false,
      opensEpoch: 15,
    })
    expect(skyCalendar(11, 5, 13)).toMatchObject({
      aligned: true,
      forced: true,
      closesEpoch: 13,
    })
    expect(skyCalendarText(skyCalendar(12, 5, null))).toBe(
      'Slingshot routes closed · open at the start of epoch 15'
    )
  })
})

describe('rules and search', () => {
  it('reads rules by name and travel method', () => {
    const book = buildRuleBook({
      'cosmic_costs.seal_gate': 30,
      'travel_methods.light_sail_duration': 3,
    })
    expect(book.get('sealGate')).toBe(30)
    expect(book.methodDuration('light_sail')).toBe(3)
    expect(book.get('igniteStar')).toBeUndefined()
    expect(buildRuleBook(undefined).ready).toBe(false)
  })

  it('keeps only valid cosmos search params', () => {
    expect(
      validateCosmosSearch({
        world: '5',
        star: 'x',
        panel: 'gods',
        section: 'nope',
      })
    ).toEqual({ world: 5, panel: 'gods' })
  })
})

describe('hashing and picking', () => {
  it('hashes deterministically', () => {
    expect(fnv1a('a')).toBe(fnv1a('a'))
    expect(unitHash('world')).toBeGreaterThanOrEqual(0)
    expect(unitHash('world')).toBeLessThan(1)
    const first = seededRandom(7)
    const second = seededRandom(7)
    expect(first()).toBe(second())
  })

  it('picks worlds before stars, voyages and routes', () => {
    const frame = createFrameState()
    frame.worldScreen.set(1, { x: 100, y: 100, radius: 5, visible: true })
    frame.starScreen.set(2, { x: 104, y: 100, radius: 10, visible: true })
    frame.routeScreen.set(3, new Float32Array([0, 300, 400, 300]))
    expect(pick(frame, 102, 100)).toEqual({ kind: 'world', id: 1 })
    expect(pick(frame, 120, 100)).toEqual({ kind: 'star', id: 2 })
    expect(pick(frame, 200, 305)).toEqual({ kind: 'route', id: 3 })
    expect(pick(frame, 200, 200)).toBeNull()
  })
})
