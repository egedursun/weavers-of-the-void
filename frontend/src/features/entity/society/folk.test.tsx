import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '@/api/generated/schema'
import { PeopleProfileSection } from './Demography'
import { effectTone, folkLabel } from './folkLabels'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const VIEW = {
  entity_id: 12,
  people_id: 12,
  cohorts: [],
  labour: [],
  flows: [],
  pressures: [],
  classes: [],
  biology: {
    maturity_years: 16,
    adult_years: 40,
    elder_years: 15,
    fertility_pct: 100,
    acclimatised: 'cold',
    staple: 'fish',
    traits: ['winged', 'keen_senses'],
    immunities: [{ id: 40, name: 'the grey cough' }],
    body_plan: 'avian',
    size_class: 'small',
    diet: 'piscivore',
    edible: ['fish'],
    effects: {
      food_pct: 63,
      room_pct: 56,
      strength_pct: 75,
      disease_pct: 100,
      fleet_pct: 50,
      mount: 'flies',
      hunger_pct: 20,
      work: [{ job: 'trade', pct: 138 }],
    },
    biochemistry: 'carbon_water',
    air: 'oxygen',
    gravity_low: 50,
    gravity_high: 160,
    habitability: 60,
    locked: ['body_plan'],
  },
  culture: {
    cohesion: 60,
    literacy: 20,
    urbanisation: 40,
    aesthetic: 'celestial',
    martial_style: 'skirmisher',
    marriage: 'polyandry',
    endogamous: true,
    inheritance: 'ultimogeniture',
    slavery_lawful: false,
    staples: ['fish'],
    liturgical_language: { id: 50, name: 'Old Aerie' },
    trade_language: { id: 51, name: 'Harbour Cant' },
    funeral_rite: 'sky_burial',
    funeral_tradition: { id: 60, name: 'The Sky Burial of the Wingkin' },
    martial_record: [{ style: 'skirmisher', wins: 3, losses: 1 }],
    martial_net: 2,
    locked: ['funeral_rite'],
  },
  values: [],
  neighbours: [],
  inequality: 0,
  mobilisation_pct: 100,
  afflictions: [],
  named: [],
  held: [],
} satisfies components['schemas']['DemographyView']

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 7, name: 'Vale', type: 'region', status: 'canon' },
    { kind: 'entity', id: 51, name: 'Harbour Cant', type: 'language' },
  ])
  onApi('GET', '/api/entities/12/demography', VIEW)
  onApi('POST', '/api/actions/people:edit', ACCEPTED_ACTION)
  onApi('POST', '/api/actions/people:found', ACCEPTED_ACTION)
}

describe('folk and customs', () => {
  beforeEach(resetApi)

  it('labels fields and tones effects', () => {
    expect(folkLabel('trade_language_id')).toBe('Tongue of trade')
    expect(folkLabel('cohesion')).toBe('Cohesion')
    expect(effectTone(150, 'high')).toBe('success')
    expect(effectTone(150, 'low')).toBe('warning')
    expect(effectTone(100, 'low')).toBe('muted')
  })

  it('shows body, diet, tongues, rite and record in human words', async () => {
    serve()
    const { screen } = await renderApp(<PeopleProfileSection peopleId={12} />)
    await expect.element(screen.getByText('Winged folk').first()).toBeVisible()
    await expect
      .element(screen.getByText('Breathes oxygen').first())
      .toBeVisible()
    await expect.element(screen.getByText('50% to 160%').first()).toBeVisible()
    await expect.element(screen.getByText('Fish eaters').first()).toBeVisible()
    await expect
      .element(screen.getByText('Take to the air').first())
      .toBeVisible()
    await expect.element(screen.getByText('Old Aerie')).toBeVisible()
    await expect.element(screen.getByText('Harbour Cant').first()).toBeVisible()
    await expect.element(screen.getByText('Sky burial').first()).toBeVisible()
    await expect.element(screen.getByText('3 won · 1 lost')).toBeVisible()
    await expect.element(screen.getByText('the grey cough')).toBeVisible()
  })

  it('founds a new people with its chosen body and customs', async () => {
    serve()
    const { screen } = await renderApp(<PeopleProfileSection peopleId={12} />)
    await screen.getByRole('button', { name: 'Found a people' }).click()
    await screen.getByLabelText('Name').fill('Stonekin')
    await screen.getByRole('combobox', { name: 'Land they rise in' }).click()
    await screen.getByRole('option', { name: 'Vale' }).click()
    await screen.getByRole('button', { name: 'Found them' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/people:found'))
      .toHaveLength(1)
    const body = callsTo('POST', '/api/actions/people:found')[0].body as {
      name: string
      region_id: number
      values: Record<string, unknown>
    }
    expect(body.name).toBe('Stonekin')
    expect(body.region_id).toBe(7)
    expect(body.values.body_plan).toBe('avian')
    expect(body.values.funeral_rite).toBe('sky_burial')
  })
  it('edits the record and releases a hold', async () => {
    serve()
    const { screen } = await renderApp(<PeopleProfileSection peopleId={12} />)
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Release funeral rite' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/people:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/people:edit')[0].body).toEqual({
      people_id: 12,
      values: {},
      release: ['funeral_rite'],
    })
    await screen
      .getByRole('spinbutton', { name: 'Victories as skirmishers' })
      .fill('5')
    await screen
      .getByRole('button', { name: 'Set Victories as skirmishers' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/people:edit'))
      .toHaveLength(2)
    expect(callsTo('POST', '/api/actions/people:edit')[1].body).toEqual({
      people_id: 12,
      values: { martial_wins: 5 },
      release: [],
    })
  })
})
