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
  vector: 'touch',
  virulence: 59,
  lethality: 42,
  chronic_rate: 18,
  incubation: 0,
  target_functions: ['skin'],
  climate_affinity: 'warm',
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
    },
  ],
  endemic: [],
  cures: [],
  immunities: [],
}

const PLAN = {
  entity_id: 30,
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
    await screen.getByRole('spinbutton', { name: 'Virulence' }).fill('70')
    await screen.getByRole('button', { name: 'Set Virulence' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/disease:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/disease:edit')[0].body).toEqual({
      disease_id: 40,
      values: { virulence: 70 },
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
})
