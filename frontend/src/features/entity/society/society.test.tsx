import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DiseaseSection } from './DiseaseCard'
import { SettlementPlanSection } from './SettlementPlan'
import { badTone, goodTone } from './tones'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const DISEASE = {
  entity_id: 40,
  name: 'the summer weeping sores',
  primary_route: 'contact',
  primary_share: 100,
  routes: [],
  virulence: 59,
  lethality: 42,
  chronic_rate: 18,
  incubation: 0,
  target_functions: ['skin'],
  affinity_warmth: 'warm',
  affinity_moisture: 'any',
  host_species_id: null,
  immunity_epochs: 10,
  mutation_rate: 9,
  stigma: 73,
  cure_level: 6,
  generation: 0,
  parent_id: null,
  origin_region_id: 7,
  emerged_epoch: 50,
  locked: ['lethality'],
  strains: [],
  outbreaks: [
    {
      id: 1,
      disease_id: 40,
      disease: 'the summer weeping sores',
      region_id: 7,
      region: 'Vale',
      source_region_id: null,
      path: 'origin',
      status: 'active',
      severity: 51,
      infected: 1000,
      dead: 250,
      started_epoch: 50,
      ended_epoch: null,
      quarantined: false,
      event_id: null,
      locked: [],
      unseen_pct: 0,
    },
  ],
  endemic: [],
  cures: [],
  immunities: [],
  origin_incident_id: null,
  origin: null,
  incidents: [],
  hosts: [],
  unseen_pct: 0,
  sick: 0,
}

const EFFECTS = {
  housing: 1500,
  food_store: 0,
  goods_store: 300,
  harbour: 0,
  order: 0,
  sanitation: 0,
  piety_floor: 0,
  admin_pct: 0,
  policing: 0,
  investment_pct: 0,
  tension_relief_pct: 0,
}

const PLAN = {
  entity_id: 30,
  world_id: 1,
  admin_capacity: 72,
  admin: {
    base: 50,
    literacy: 10,
    scribes: 6,
    writing: 6,
    palace: 0,
    total: 72,
  },
  food_storage: { districts: 0, workshops: 5000, other: 0, total: 5000 },
  goods_storage: { districts: 300, workshops: 0, other: 0, total: 300 },
  defences: {
    wall_pct: 56,
    tower_pct: 4,
    batter_pct: 60,
    gate_weakness_pct: 0,
  },
  district_effects: { ...EFFECTS, order: 4 },
  prestige_pull_pct: 8,
  prestige_investment_pct: 4,
  designs: [
    {
      id: 9,
      name: 'Lantern Quay',
      description: 'A lit quay.',
      base_kind: 'harbour',
      parameters: {
        ...Object.fromEntries(Object.keys(EFFECTS).map((key) => [key, null])),
        harbour: 900,
      },
      defaults: { ...EFFECTS, goods_store: 0, harbour: 200 },
      created_epoch: 40,
    },
  ],
  kind_defaults: {
    farmland: EFFECTS,
    market: EFFECTS,
    craft_quarter: EFFECTS,
    temple_quarter: EFFECTS,
    harbour: { ...EFFECTS, harbour: 200 },
    citadel: EFFECTS,
    slums: EFFECTS,
    palace: { ...EFFECTS, order: 4, admin_pct: 10 },
    foreign_quarter: EFFECTS,
    necropolis: EFFECTS,
  },
  armies: [{ id: 77, name: 'the Wall Guard', size: 400 }],
  size_tier: 'town',
  treasury: 28,
  tax_rate: 10,
  public_order: 65,
  crime: 14,
  unrest: 20,
  sanitation: 42,
  fire_risk: 48,
  wealth: 97,
  prestige: 21,
  militia: 496,
  garrison_id: null,
  free_city: false,
  charter_id: null,
  siege_supplies: 365,
  siege_water: 120,
  siege_disease: 0,
  investment_pool: 0,
  construction_capacity: 100,
  hauling_capacity: 200,
  rationing: false,
  district_slots: 3,
  housing: 1000,
  locked: ['crime'],
  foreigners: [],
  infrastructure: {
    walls_level: 2,
    walls_material: 'stone',
    walls_condition: 90,
    gates: 1,
    roads: 3,
    water: 'well',
    sewers: false,
    granary_capacity: 400,
    warehouse_capacity: 40,
    harbour_capacity: 0,
    towers: 2,
    locked: [],
  },
  districts: [
    {
      id: 4,
      kind: 'craft_quarter',
      level: 1,
      condition: 70,
      material: 'timber',
      built_epoch: 50,
      design_id: null,
      locked: ['condition'],
      effects: { housing: 1500, goods_store: 300 },
    },
  ],
  treasury_ledger: [],
  history: [],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [])
}

describe('society sections', () => {
  beforeEach(resetApi)

  it('reads tones from a value', () => {
    expect(goodTone(80)).toBe('success')
    expect(goodTone(10)).toBe('danger')
    expect(badTone(80)).toBe('danger')
    expect(badTone(0)).toBe('success')
  })

  it('shows a sickness with human labels and reshapes it from the controls', async () => {
    serve()
    onApi('GET', '/api/entities/40/disease', DISEASE)
    onApi('POST', '/api/actions/disease:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/outbreak:end', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DiseaseSection diseaseId={40} />)
    await expect.element(screen.getByText('Spreads by touch')).toBeVisible()
    await expect.element(screen.getByText('Strikes the skin')).toBeVisible()
    await expect
      .element(screen.getByText('Raging', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Rose here')).toBeVisible()
    await screen.getByRole('button', { name: 'End it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/outbreak:end'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen
      .getByRole('spinbutton', { name: 'Virulence', exact: true })
      .fill('70')
    await screen.getByRole('button', { name: 'Set Virulence' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/disease:edit')[0].body).toEqual({
      disease_id: 40,
      values: { virulence: 70 },
      hold: true,
    })
    await expect.element(screen.getByText('Held').first()).toBeVisible()
  })

  it('shows the city and governs it field by field', async () => {
    serve()
    onApi('GET', '/api/entities/30/settlement-plan', PLAN)
    onApi('POST', '/api/actions/settlement:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/district:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <SettlementPlanSection settlementId={30} />
    )
    await expect.element(screen.getByText('Craft quarter')).toBeVisible()
    await expect.element(screen.getByText('2 open plots')).toBeVisible()
    await screen.getByRole('button', { name: 'Repair' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/district:edit')[0].body).toEqual({
      district_id: 4,
      clear_design: false,
      clear_world_material: false,
      condition: 100,
    })
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Release crime' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/settlement:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/settlement:edit')[0].body).toEqual({
      settlement_id: 30,
      values: {},
      release: ['crime'],
    })
    await screen.getByRole('spinbutton', { name: 'Militia' }).fill('600')
    await screen.getByRole('button', { name: 'Set Militia' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/settlement:edit'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/settlement:edit')[1].body).toEqual({
      settlement_id: 30,
      values: { militia: 600 },
      release: [],
    })
  })

  it('explains how the city runs and devises district designs', async () => {
    serve()
    onApi('GET', '/api/entities/30/settlement-plan', PLAN)
    onApi('POST', '/api/actions/district:edit', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/district:design', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/district:design_delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/settlement:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <SettlementPlanSection settlementId={30} />
    )
    await expect.element(screen.getByText('Administrative reach')).toBeVisible()
    await expect.element(screen.getByText('Lantern Quay')).toBeVisible()
    await expect.element(screen.getByText('Repair held')).toBeVisible()
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/district:edit')[0].body).toEqual({
      district_id: 4,
      clear_design: false,
      clear_world_material: false,
      release: ['condition'],
    })
    await screen.getByRole('button', { name: 'Strike' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district:design_delete'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByLabelText('Name').fill('Night Market')
    await screen.getByLabelText('Order per level').fill('5')
    await screen.getByRole('button', { name: 'Design it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/district:design'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/district:design')[0].body).toEqual({
      world_id: 1,
      name: 'Night Market',
      base_kind: 'market',
      description: null,
      values: { order: 5 },
    })
  })
})
