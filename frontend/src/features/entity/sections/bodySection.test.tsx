import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BodySection } from './BodySection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WOUND = {
  id: 71,
  part: 'left_leg',
  part_label: 'Left leg',
  kind: 'internal_bleeding',
  damage_type: 'asphyxia',
  severity: 3,
  state: 'gangrenous',
  function_loss: 40,
  cause_kind: 'childbirth',
  cause_node_id: null,
  cause_name: null,
  cause_link: null,
  event_entity_id: null,
  event_name: null,
  epoch: 50,
  year: 12,
  treated_by_node_id: null,
  treated_by_name: null,
  visible: true,
  infected_epochs: 0,
  healed_epoch: null,
  prosthesis: null,
  tissue: null,
  tissue_label: null,
  bleeding: 0,
  nerve: 'none',
  treatments: ['drain'],
  wanted: ['medicate'],
  misdiagnosed: false,
}

const BODY = {
  node_id: 501,
  world_id: 1,
  name: 'Oswin',
  bearer_kind: 'mortal',
  alive: true,
  plan: 'radial',
  plan_label: 'Built round a centre',
  height_class: 'average',
  build: 'average',
  traits: [],
  hp: 40,
  hp_max: 60,
  pain: 20,
  fingers: 10,
  toes: 10,
  teeth: 30,
  blood: 80,
  exertion: 10,
  consciousness: 'awake',
  handedness: 'right',
  digits: [],
  covering: 'skin',
  covering_label: 'Skin',
  armour: { head: 0, torso: 0, limbs: 0 },
  capacities: [
    { key: 'endurance', factor: 80, value: 40, base: 50, locked: false },
    { key: 'perception', factor: 100, value: 55, base: 55, locked: true },
  ],
  functions: [],
  parts: [],
  injuries: [WOUND],
  conditions: [
    {
      id: 81,
      kind: 'paralysis',
      severity: 3,
      part: null,
      source: 'sport',
      source_node_id: null,
      source_name: null,
      source_link: null,
      since_epoch: 49,
      ended_epoch: null,
      variant_id: null,
      visible: true,
      cause: null,
      kind_id: null,
      kind_name: null,
    },
  ],
  condition_kinds: [],
  locked: [],
  patients_healed: 0,
  patients_lost: 0,
  medicine: 'herbs',
  healer_id: null,
  healer_name: null,
  healer_skill: null,
  presence_pct: 100,
  people_id: null,
  people_name: null,
  reading: null,
  wholeness_required: false,
  updated_epoch: 50,
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [
    { id: 501, kind: 'entity', type: 'mortal', name: 'Oswin', world_id: 1 },
  ])
  onApi('GET', '/api/variants', [])
}

describe('body section', () => {
  beforeEach(resetApi)

  it('labels the widened plans, wounds, harms, conditions and capacities', async () => {
    serve()
    onApi('GET', '/api/bodies/501', BODY)
    const { screen } = await renderApp(<BodySection nodeId={501} />)
    await expect
      .element(screen.getByText('Built round a centre').first())
      .toBeVisible()
    await expect
      .element(screen.getByText('Bleeding inside · Left leg'))
      .toBeVisible()
    await expect.element(screen.getByText('Gangrenous')).toBeVisible()
    await expect.element(screen.getByText('Lack of air')).toBeVisible()
    await expect.element(screen.getByText('Giving birth')).toBeVisible()
    await expect.element(screen.getByText('Paralysis')).toBeVisible()
    await expect
      .element(screen.getByText('Endurance', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Perception (held)')).toBeVisible()
    await expect.element(screen.getByText('Drain')).toBeVisible()
  })

  it('gives a wound the treatment it still needs', async () => {
    serve()
    onApi('GET', '/api/bodies/501', BODY)
    onApi('POST', '/api/actions/body:treat', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BodySection nodeId={501} />)
    await screen.getByRole('button', { name: 'Give a remedy' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/body:treat'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/body:treat')[0].body).toEqual({
      injury_id: 71,
      step: 'medicate',
    })
  })

  it('holds the treatment back with its reason in a read-only world', async () => {
    serve()
    onApi('GET', '/api/state', {
      creator: { essence: 500 },
      epoch_running: false,
      read_only: true,
      world: { epoch: 50 },
    })
    onApi('GET', '/api/bodies/501', BODY)
    const { screen } = await renderApp(<BodySection nodeId={501} />)
    await expect
      .element(screen.getByRole('button', { name: 'Give a remedy' }))
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Give a remedy' }))
      .toHaveAccessibleDescription('A guest world is open read-only.')
  })
})
