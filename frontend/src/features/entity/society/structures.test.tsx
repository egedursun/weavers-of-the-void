import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SettlementStructures, StructureSection } from './Structures'
import { raising, standing } from './structureModel'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TEMPLE = {
  id: 50,
  name: 'The Sun House',
  status: 'canon',
  kind: 'temple',
  group: 'faith',
  label: 'Temple',
  own_effects: [],
  design_id: null,
  design_name: null,
  level: 2,
  capacity: 1000,
  capacity_unit: 'worshippers',
  condition: 70,
  durability: 80,
  construction_state: 'complete',
  progress: 100,
  fire_resistance: 85,
  material: 'stone',
  world_material_id: null,
  material_label: 'Stone',
  host_id: 30,
  host_name: 'Ashford',
  builder_id: 30,
  builder_name: 'Ashford',
  builder_kind: 'community',
  architect_id: null,
  architect_name: null,
  dedicated_son_id: null,
  dedicated_son_name: null,
  style_ornament: 90,
  style_geometry: 50,
  style_colour: 80,
  style_scale: 60,
  style_symmetry: 60,
  on_ley_line: true,
  attuned: true,
  anchor: false,
  splendor: 55,
  function: 60,
  effect_pct: 60,
  staff_pct: 100,
  staff_class: 'priest',
  staff_required: 30,
  staff_allocated: 30,
  staff_held: false,
  upkeep_coin: 16,
  upkeep_goods: 8,
  upkeep_commodity: 'incense',
  unpaid_epochs: 0,
  built_epoch: 40,
  workshop: null,
  min_tier: 'village',
  scale: 'major',
  locked: ['condition'],
  breakdown: {
    base: 60,
    design_pct: 100,
    condition_pct: 100,
    staff_pct: 100,
    ley_pct: 120,
    effect_pct: 60,
    threshold: 40,
  },
  construction: null,
}

const BUILDING = {
  ...TEMPLE,
  id: 51,
  name: 'The Grain Hall',
  kind: 'granary',
  group: 'commerce',
  label: 'Granary',
  construction_state: 'building',
  progress: 40,
  effect_pct: 0,
  locked: [],
  construction: {
    id: 9,
    status: 'active',
    cost: 300,
    work: 120,
    percent: 40,
    funds: 0,
    workers: 60,
    materials_pct: 100,
    stalled_epochs: 0,
    stall_limit: 6,
    generations: 0,
    started_epoch: 49,
    finished_epoch: null,
    player: false,
    locked: [],
  },
}

const HOST = {
  host_id: 30,
  world_id: 1,
  size_tier: 'town',
  slots_total: 9,
  slots_used: 2,
  structures: [TEMPLE, BUILDING],
  kinds: [
    {
      kind: 'shrine',
      group: 'faith',
      label: 'Shrine',
      min_tier: 'hamlet',
      allowed: true,
      scale: 'minor',
      cost: 300,
      capacity_unit: 'worshippers',
      staff_class: 'priest',
      staff_scale: 'few',
      present: 0,
    },
  ],
  designs: [],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
}

describe('structures', () => {
  beforeEach(resetApi)

  it('tells standing works from those being raised', () => {
    expect(standing(TEMPLE as never)).toBe(true)
    expect(raising(BUILDING as never)).toBe(true)
  })

  it('shows a work, its function breakdown, and holds and releases its values', async () => {
    serve()
    onApi('GET', '/api/entities/50/structure', TEMPLE)
    onApi('POST', '/api/actions/structure:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<StructureSection structureId={50} />)
    await expect.element(screen.getByText('Working at 60%')).toBeVisible()
    await expect.element(screen.getByText('Ley line 120%')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Release condition' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/structure:edit')[0].body).toEqual({
      structure_id: 50,
      values: {},
      release: ['condition'],
    })
    await screen.getByRole('spinbutton', { name: 'Level' }).fill('3')
    await screen.getByRole('button', { name: 'Set Level' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:edit'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/structure:edit')[1].body).toEqual({
      structure_id: 50,
      values: { level: 3 },
      release: [],
    })
    await expect
      .element(screen.getByText('Decoration 90 · Colour 80 · Scale 60'))
      .toBeVisible()
    await screen.getByRole('spinbutton', { name: 'Decoration' }).fill('20')
    await screen.getByRole('button', { name: 'Set Decoration' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:edit'))
      .toHaveLength(3)
    expect(callsTo('POST', '/api/actions/structure:edit')[2].body).toEqual({
      structure_id: 50,
      values: { style_ornament: 20 },
      release: [],
    })
  })

  it('lists the works of a town, funds a building site and commissions a new work', async () => {
    serve()
    onApi('GET', '/api/entities/30/structures', HOST)
    onApi('POST', '/api/actions/structure:fund', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/structure:commission', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/structure_design:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <SettlementStructures hostId={30} blocked={null} />
    )
    await expect.element(screen.getByText('The Grain Hall')).toBeVisible()
    await expect.element(screen.getByText('Being raised').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Fund 100' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:fund'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/structure:fund')[0].body).toEqual({
      structure_id: 51,
      amount: 100,
    })
    await screen.getByRole('button', { name: 'Commission it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure:commission'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/structure:commission')[0].body
    ).toMatchObject({ site_id: 30, kind: 'shrine', level: 1 })
    await screen
      .getByRole('textbox', { name: 'Name of the design' })
      .fill('The Sky Granary')
    await screen.getByRole('button', { name: 'Draw up a design' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/structure_design:create'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/structure_design:create')[0].body
    ).toEqual({
      world_id: 1,
      values: { name: 'The Sky Granary', base_kind: 'temple' },
    })
  })
})
