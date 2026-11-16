import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UnitDesigns } from './Designs'
import { Vendettas } from './Vendettas'
import { VesselCard } from './VesselCard'
import { WarMap } from './WarMap'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const IRON = { id: 3, kind: 'entity', name: 'Iron Folk' }
const REED = { id: 4, kind: 'entity', name: 'Reed Folk' }

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 12 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

const DESIGNS = {
  kind: 'unit_design',
  label: 'Unit design',
  creatable: true,
  deletable: true,
  scope: 'owner_entity_id',
  columns: [
    {
      name: 'name',
      kind: 'text',
      options: [],
      nullable: false,
      required: true,
    },
    {
      name: 'melee',
      kind: 'integer',
      options: [],
      nullable: false,
      required: false,
    },
  ],
  rows: [
    {
      id: 9,
      values: {
        id: 9,
        name: 'Glass Lancers',
        base_kind: 'heavy_cavalry',
        family: 'mounted',
        melee: 90,
        missile: 0,
        defence: 60,
        speed: 70,
        mass: 80,
        cost: 9,
        upkeep: 3,
        armour: 'plate',
        shield: 'small',
        terror: 30,
        counters_charge: false,
        flying: false,
        social_class: 'noble',
        owner_entity_id: 3,
        created_epoch: 5,
        retired: false,
      },
      locked: ['melee'],
      refs: {},
    },
  ],
}

describe('military depth surfaces', () => {
  beforeEach(resetApi)

  it('shows a unit design as a card and holds an edited value', async () => {
    serve()
    onApi('GET', '/api/units/kinds', [])
    onApi('GET', '/api/military/records/unit_design', DESIGNS)
    onApi('POST', '/api/actions/military:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <UnitDesigns ownerId={3} blocked={null} />
    )
    await expect.element(screen.getByText('Glass Lancers')).toBeVisible()
    await expect.element(screen.getByText('1 held')).toBeVisible()
    await expect.element(screen.getByText('Plate').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen.getByRole('spinbutton', { name: 'Hand to hand' }).fill('70')
    await screen.getByRole('button', { name: 'Set and hold' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/military:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/military:edit')[0].body).toEqual({
      kind: 'unit_design',
      record_id: 9,
      values: { melee: 70 },
      hold: true,
    })
  })

  it('shows feuds with their intensity and grief', async () => {
    serve()
    onApi('GET', '/api/feuds', [
      {
        id: 1,
        first: IRON,
        second: REED,
        party: 'community',
        intensity: 64,
        grievance: 50,
        generations: 1,
        level: 'blood',
        mediator: null,
        status: 'active',
        cause: 'the blood of Tam',
        since_epoch: 4,
        last_epoch: 11,
        last_action: 'raid',
        ended_epoch: null,
        grief: 40,
        locked: [],
      },
    ])
    const { screen } = await renderApp(
      <Vendettas entityId={null} blocked={null} />
    )
    await expect.element(screen.getByText('Burning')).toBeVisible()
    await expect.element(screen.getByText('the blood of Tam')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Adjust' }))
      .toBeVisible()
  })

  it('shows a vessel card with its frame, arms and repair', async () => {
    serve()
    onApi('GET', '/api/entities/7/vessel', {
      vessel: { id: 7, kind: 'entity', name: 'Grey Gull' },
      owner: IRON,
      captain: null,
      home_port: IRON,
      region: null,
      fleet: null,
      legend: null,
      frame: {
        frame: 'warship',
        label: 'Warship',
        domain: 'water',
        family: 'sailing_ship',
        propulsion: 'sail',
        size: 'large',
        speed: 50,
        range: 70,
        cargo: 120,
        crew: 200,
        troops: 40,
        endurance: 65,
        armour: 30,
        structure: 60,
        slots: 3,
        mounts: ['broadside'],
        sections: [],
        armament: ['rams'],
        branch: 'shipbuilding',
        level: 2,
        tier: 1,
        sky: false,
        living: false,
        strangeness: 0,
      },
      hull_material: 'oak',
      fabric_material: null,
      condition: 60,
      armament: ['rams', 'missiles'],
      seaworthiness: 65,
      cargo_capacity: 120,
      crew: 180,
      seamanship: 40,
      renown: 12,
      strangeness: 0,
      status: 'damaged',
      voyages: 3,
      locked: [],
    })
    onApi('POST', '/api/actions/vessel:repair', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <VesselCard vesselId={7} blocked={null} />
    )
    await expect.element(screen.getByText('Warship').first()).toBeVisible()
    await expect.element(screen.getByText('Missiles')).toBeVisible()
    await screen.getByRole('button', { name: 'Repair at the yard' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/vessel:repair'))
      .toHaveLength(1)
  })

  it('draws the war on the world map, or says the map is not drawn yet', async () => {
    serve()
    const room = {
      war: { id: 2, world_id: 1, started_epoch: 3, sides: [] },
      armies: [],
      fronts: [],
      battles: [],
      sieges: [],
      occupations: [],
    }
    const { screen } = await renderApp(
      <WarMap room={room as unknown as Parameters<typeof WarMap>[0]['room']} />
    )
    await expect.element(screen.getByText('War map')).toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'World map' }))
      .toBeVisible()
  })
})
