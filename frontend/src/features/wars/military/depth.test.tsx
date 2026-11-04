import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RecordPanel } from './RecordPanel'
import { Vendettas } from './Vendettas'
import { VesselCard } from './VesselCard'

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
      values: { id: 9, name: 'Glass Lancers', melee: 90 },
      locked: ['melee'],
      refs: {},
    },
  ],
}

describe('military depth surfaces', () => {
  beforeEach(resetApi)

  it('edits and holds a record value from its adjust panel', async () => {
    serve()
    onApi('GET', '/api/military/records/unit_design', DESIGNS)
    onApi('POST', '/api/actions/military:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <RecordPanel
        kind='unit_design'
        scope={null}
        title='Unit designs'
        blocked={null}
      />
    )
    await expect.element(screen.getByText('1 held')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen.getByLabelText('Melee').first().fill('70')
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
    onApi('GET', '/api/military/records/feud', {
      ...DESIGNS,
      kind: 'feud',
      label: 'Feud',
      rows: [],
    })
    const { screen } = await renderApp(
      <Vendettas entityId={null} blocked={null} />
    )
    await expect.element(screen.getByText('Burning')).toBeVisible()
    await expect.element(screen.getByText('Remembered grief')).toBeVisible()
  })

  it('shows a vessel card with hull, arms and repair', async () => {
    serve()
    onApi('GET', '/api/entities/7/vessel', {
      vessel: { id: 7, kind: 'entity', name: 'Grey Gull' },
      owner: IRON,
      captain: null,
      home_port: IRON,
      region: null,
      fleet: null,
      legend: null,
      hull: {
        hull: 'warship',
        label: 'Warship',
        speed: 50,
        range: 70,
        cargo: 120,
        crew: 200,
        seaworthiness: 65,
        slots: 3,
        armament: ['rams'],
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
    onApi('GET', '/api/military/records/vessel', {
      ...DESIGNS,
      kind: 'vessel',
      label: 'Vessel',
      creatable: false,
      deletable: false,
      rows: [],
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
})
