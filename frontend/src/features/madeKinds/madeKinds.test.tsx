import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  allKeys,
  buildAtlasTree,
  flattenVisible,
} from '@/features/atlas/atlasModel'
import { type CosmosView, type WorldState } from '@/features/entity/api/types'
import { KindPage } from './KindPages'
import { MadeKindsSection } from './MadeKindsSection'
import { type WorldKinds } from './api'
import { kindKey, parseKindKey } from './kindKeys'
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

const KINDS: WorldKinds = {
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
  own: {
    vehicle_types: [{ id: 5, name: 'Tall Wagon', family: 'Wagon' }],
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

  it('files every made type in the atlas under its world, never its instances', () => {
    const tree = buildAtlasTree({
      entities: [],
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
      kinds: new Map([[1, KINDS]]),
    })
    const keys = flattenVisible(tree, new Set(allKeys(tree))).map(
      (row) => row.node.key
    )
    expect(keys).toContain(kindKey('vehicle', 1, 5))
    expect(keys).toContain('group:1:made-kinds')
    expect(parseKindKey(kindKey('vehicle', 1, 5))).toEqual({
      kind: 'vehicle',
      worldId: 1,
      id: 5,
    })
    expect(parseKindKey('made:vehicle:0:5')).toBeNull()
    expect(parseKindKey('building-type:1:school')).toBeNull()
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

  it('opens a vehicle type in the atlas with its sections and takes one out', async () => {
    serveBase()
    onApi('GET', '/api/worlds/1/materials', {
      world_id: 1,
      materials: [],
      commodities: [],
    })
    onApi('POST', '/api/actions/design_section:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <KindPage selection={{ kind: 'vehicle', worldId: 1, id: 5 }} />
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
