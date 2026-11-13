import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type components, vehicleFrameValues } from '@/api/generated/schema'
import {
  allKeys,
  buildAtlasTree,
  flattenVisible,
  matchesEntity,
} from '@/features/atlas/atlasModel'
import { Facts } from '@/features/cosmography/parts'
import {
  type CosmosView,
  type EntitySummary,
  type WorldState,
} from '@/features/entity/api/types'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { IntegrityDiagram } from './IntegrityDiagram'
import { MadeEntitySection } from './KindPages'
import { MadeKindsSection } from './MadeKindsSection'
import { BLUEPRINTS, buildingShape, vehicleShape } from './blueprints'
import { worst } from './model'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const REALM = { id: 40, kind: 'entity' as const, name: 'Varo' }

const SECTION = {
  section: 'wheels' as const,
  function: 'propulsion' as const,
  criticality: 'major' as const,
  share: 20,
  exposure: 30,
  armour: 10,
  hazard: 'none' as const,
  neighbours: ['axle' as const],
  material_id: null,
  material_name: null,
  size: 3,
  quality: 50,
  locked: [],
}

const WAGON = {
  id: 5,
  entity_id: 900,
  name: 'Tall Wagon',
  description: null,
  world_id: 1,
  origin: REALM,
  owner: REALM,
  designer: null,
  kind: 'land_vehicle' as const,
  frame: 'wagon' as const,
  frame_label: 'Wagon',
  domain: 'land' as const,
  family: 'wagon' as const,
  propulsion: 'draft_animals' as const,
  size_class: 'medium' as const,
  mass: 10,
  speed: 30,
  range: 40,
  seaworthiness: 0,
  cargo: 60,
  armament: 5,
  crew: 2,
  troops: 6,
  armour: 10,
  structure: 30,
  fuel: null,
  fuel_use: 0,
  cost: 40,
  upkeep: 4,
  tech_level: 1,
  strangeness: 0,
  fire_control: 'manual' as const,
  parent_design_id: null,
  obsolete: false,
  epoch: 3,
  built: 4,
  sections: [
    SECTION,
    {
      ...SECTION,
      section: 'chassis' as const,
      criticality: 'critical' as const,
      neighbours: [],
    },
  ],
  mounts: [],
  techniques: [],
  locked: [],
}

const KINDS: components['schemas']['WorldKindsView'] = {
  world_id: 1,
  vehicle_types: [WAGON],
  unit_types: [],
  equipment_models: [],
  dishes: [],
  building_types: [],
}

const THING = {
  node: REALM,
  world_id: 1,
  vehicle_groups: [
    {
      id: 9,
      holder: REALM,
      design_id: 5,
      design_name: 'Tall Wagon',
      frame: 'wagon' as const,
      family: 'wagon' as const,
      domain: 'land' as const,
      count: 4,
      crewed: 4,
      condition: 80,
      fuel: 100,
      status: 'ready' as const,
      region: null,
      built_epoch: 3,
      firepower: 20,
      armour: 10,
      pace: 30,
      troops: 24,
      cargo: 240,
      crew_needed: 8,
      sections: [
        {
          section: 'wheels' as const,
          criticality: 'major' as const,
          damaged: 1,
          disabled: 1,
          destroyed: 0,
          locked: [],
        },
      ],
      locked: [],
    },
  ],
  stores: [],
  stacks: [],
  pace: null,
  vessel_sections: [],
  cooking: [],
  sections: [],
  megastructure: null,
  attraction: null,
  being: null,
  own: {
    vehicle_types: [
      { id: 5, entity_id: 900, name: 'Tall Wagon', family: 'Wagon' },
    ],
    unit_types: [],
    equipment_models: [],
    dishes: [],
    building_types: [],
  },
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 40, name: 'Varo', type: 'polity', world_id: 1 },
  ])
  onApi('GET', '/api/made-kinds/world/1', KINDS)
}

describe('made kinds', () => {
  beforeEach(() => resetApi())

  it('files a made type in the atlas like any other record of its world', () => {
    const wagon = {
      id: 900,
      name: 'Tall Wagon',
      title: null,
      entity_type: 'vehicle_type',
      subtype: null,
      status: 'canon',
      world_id: 1,
      location_id: null,
      power_level: 1,
      birth_epoch: 3,
      end_epoch: null,
      importance: null,
      favorite: true,
      pending_name: false,
    } as EntitySummary
    const tree = buildAtlasTree({
      entities: [wagon],
      state: { creator: null, sons: [], worlds: [] } as unknown as WorldState,
      cosmos: {
        stars: [],
        worlds: [
          {
            world: {
              id: 1,
              name: 'Aerona',
              star_id: null,
              parent_world_id: null,
            },
            type_label: 'World',
          },
        ],
        foreign_gods: [],
      } as unknown as CosmosView,
      types: [],
    })
    const keys = flattenVisible(tree, new Set(allKeys(tree))).map(
      (row) => row.node.key
    )
    expect(keys).toContain('entity:900')
    expect(keys).toContain('group:1:vehicle_type')
    expect(keys).not.toContain('group:1:made-kinds')
    expect(
      matchesEntity(wagon, {
        q: 'tall',
        type: 'vehicle_type',
        status: 'visible',
        favorites: true,
        world: 1,
      })
    ).toBe(true)
  })

  it('lays the inner sections of a vessel inside its hull and names them in full', async () => {
    const part = (key: string, share: number) => ({
      key,
      state: 'sound' as const,
      criticality: 'major' as const,
      share,
      hazard: 'none' as const,
    })
    const zones: Record<string, 'top' | 'front' | 'body' | 'rear'> = {
      deck: 'top',
      gun_deck: 'top',
      rigging: 'top',
      navigation: 'front',
      crew_quarters: 'body',
      hold: 'body',
      magazine: 'body',
      rudder: 'rear',
    }
    const parts = Object.keys(zones).map((key) => part(key, 10))
    const { screen } = await renderApp(
      <div className='w-56'>
        <IntegrityDiagram
          title='Sections of a carrack'
          shape='three_master'
          parts={parts}
          zoneOf={(key) => zones[key] ?? 'body'}
        />
      </div>
    )
    const diagram = screen.getByRole('img', { name: 'Sections of a carrack' })
    await expect.element(diagram).toBeVisible()
    const inside = [
      ...diagram.element().querySelectorAll('rect[data-section]'),
    ].map((node) => node.getAttribute('data-section'))
    expect(inside.sort()).toEqual(
      ['crew_quarters', 'hold', 'magazine', 'navigation'].sort()
    )
    const labels = [...diagram.element().querySelectorAll('text')].map(
      (node) => node.textContent
    )
    expect(labels.some((label) => label?.includes('…'))).toBe(false)
  })

  it('keeps the sections a made type cannot hold out of its entry and says why', async () => {
    const { screen } = await renderApp(
      <ThingSections nodeId={900} scope='made' />
    )
    await expect
      .element(screen.getByText(/A made type is a design its makers/))
      .toBeVisible()
    for (const id of [
      'section-dominion',
      'section-feelings',
      'section-tastes',
      'section-ethics',
      'section-tongues',
      'section-arcana',
    ])
      expect(document.getElementById(id)).toBeNull()
  })

  it('gives every frame a drawing of its own', () => {
    expect(
      vehicleFrameValues.every(
        (frame) => vehicleShape(frame, null) in BLUEPRINTS
      )
    ).toBe(true)
    const distinct = (frames: (typeof vehicleFrameValues)[number][]) =>
      new Set(frames.map((frame) => vehicleShape(frame, null))).size
    expect(
      distinct(['riding_mount', 'pack_mount', 'beast_carrier', 'wagon'])
    ).toBe(4)
    expect(
      distinct([
        'cart',
        'handcart',
        'travois',
        'sledge',
        'covered_wagon',
        'carriage',
      ])
    ).toBe(6)
    expect(
      distinct([
        'space_fighter',
        'freighter',
        'dreadnought',
        'shuttle',
        'orbital_lander',
        'generation_ship',
        'galley',
      ])
    ).toBe(7)
    expect(
      distinct(['motor_car', 'motor_truck', 'motorcycle', 'tank', 'locomotive'])
    ).toBe(5)
    expect(buildingShape(null)).toBe('flat')
  })

  it('draws every frame and form of other settings in a silhouette of its own', () => {
    const modern = [
      'bicycle',
      'rickshaw',
      'palanquin',
      'tram',
      'maglev',
      'bus',
      'tractor',
      'apc',
      'self_propelled_gun',
      'missile_carrier',
      'motorboat',
      'hydrofoil',
      'container_ship',
      'tanker',
      'destroyer',
      'cruiser',
      'icebreaker',
      'vtol',
      'spaceplane',
      'escape_pod',
      'space_tug',
      'mothership',
      'battle_mech',
      'bioship',
    ] as const
    const shapes = new Set(modern.map((frame) => vehicleShape(frame, null)))
    expect(shapes.size).toBe(modern.length)
    expect(modern.every((frame) => vehicleShape(frame, null) === frame)).toBe(
      true
    )
    const forms = [
      'high_rise',
      'arcology',
      'bunker',
      'floating',
      'geodesic',
      'modular',
      'grown',
      'carved',
    ] as const
    expect(new Set(forms.map((form) => buildingShape(form))).size).toBe(
      forms.length
    )
  })

  it('keeps a structure drawing at the proportions of its blueprint', async () => {
    const { screen } = await renderApp(
      <div className='w-2xl'>
        <IntegrityDiagram
          title='Sections of a shrine'
          shape='hall'
          parts={['sanctum', 'foundation', 'vault'].map((key) => ({
            key,
            state: 'sound' as const,
            criticality: 'major' as const,
            share: 30,
            hazard: 'none' as const,
          }))}
          zoneOf={(key) => (key === 'foundation' ? 'under' : 'body')}
        />
      </div>
    )
    const diagram = screen.getByRole('img', { name: 'Sections of a shrine' })
    await expect.element(diagram).toBeVisible()
    const box = diagram.element().getBoundingClientRect()
    expect(Math.abs(box.height / box.width - 308 / 588)).toBeLessThan(0.02)
  })

  it('lays the values of a kind in one column with whole labels in a narrow pane', async () => {
    const { screen } = await renderApp(
      <div className='w-72'>
        <Facts
          items={[
            ['Made by', 'the Chiefdom of Nemhalet'],
            ['Fielded by', 'the Chiefdom of Nemhalet'],
            ['Epochs of training', 1],
          ]}
        />
      </div>
    )
    await expect.element(screen.getByText('Fielded by')).toBeVisible()
    const terms = [...document.querySelectorAll('dt')].map((node) =>
      node.getBoundingClientRect()
    )
    expect(new Set(terms.map((box) => box.left)).size).toBe(1)
    const line = terms[0].height
    expect(terms.every((box) => box.height === line)).toBe(true)
  })

  it('reads the worst state of a section across a group', () => {
    expect(worst(4, 0, 0, 0)).toBe('sound')
    expect(worst(4, 2, 0, 0)).toBe('damaged')
    expect(worst(4, 0, 1, 1)).toBe('disabled')
    expect(worst(4, 0, 0, 4)).toBe('destroyed')
  })

  it('shows the vehicles a realm holds with their damage and mends them', async () => {
    serveBase()
    onApi('GET', '/api/made-kinds/thing/40', THING)
    onApi('POST', '/api/actions/vehicle_group:repair', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MadeKindsSection nodeId={40} />)
    await expect.element(screen.getByText('4 × Tall Wagon')).toBeVisible()
    await expect
      .element(screen.getByText('1 damaged · 1 disabled · 0 destroyed of 4'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Mend at a yard' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/vehicle_group:repair'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/vehicle_group:repair')[0].body
    ).toEqual({ group_id: 9, points: 100 })
  })

  it('opens the wounds of a cosmic being from its link and strikes it', async () => {
    serveBase()
    onApi('GET', '/api/made-kinds/thing/40', {
      ...THING,
      being: {
        grown: true,
        hp: 30,
        hp_max: 100,
        might: 60,
        effective_might: 25,
        vital: 40,
        mobility: 20,
        sight: 70,
        roams: false,
        sees: true,
        wounds: 2,
        held: false,
      },
    })
    onApi('POST', '/api/actions/cosmic_wound:strike', ACCEPTED_ACTION)
    window.history.replaceState(null, '', '#made-kinds-wounds')
    const { screen } = await renderApp(<MadeKindsSection nodeId={40} />)
    await expect.element(screen.getByText('Too hurt to roam')).toBeVisible()
    await expect.element(screen.getByText('25 of 60')).toBeVisible()
    await screen.getByRole('button', { name: 'Strike it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/cosmic_wound:strike'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/cosmic_wound:strike')[0].body).toEqual(
      { being_id: 40, force: 1 }
    )
    window.history.replaceState(null, '', '#')
  })

  it('shows the make of a vehicle type in its drawer and takes a section out', async () => {
    serveBase()
    onApi('GET', '/api/worlds/1/materials', {
      world_id: 1,
      materials: [],
      commodities: [],
    })
    onApi('POST', '/api/actions/design_section:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <MadeEntitySection entityId={900} entityType='vehicle_type' worldId={1} />
    )
    await expect
      .element(screen.getByRole('img', { name: 'Sections of Tall Wagon' }))
      .toBeVisible()
    await expect.element(screen.getByText('Wheels').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Take it out' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/design_section:delete'))
      .toHaveLength(1)
  })
})
