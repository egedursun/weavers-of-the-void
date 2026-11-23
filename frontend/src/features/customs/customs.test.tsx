import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CustomsSection } from './CustomsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MORTAL = { id: 32, kind: 'entity' as const, name: 'Orla' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const INN = { id: 42, kind: 'entity' as const, name: 'The Low Door' }
const FOLK = { id: 41, kind: 'entity' as const, name: 'Grimfolk' }

const EMPTY = {
  people: FOLK,
  revivals: [],
  intoxicants: [],
  mark_customs: [],
  marks: [],
  budgets: [],
  naming: null,
  names: [],
  age_sets: [],
  grade_duties: [],
  age_set_id: null,
  taverns: [],
  welfare: [],
  commute: null,
  cooperative: null,
  evidence: [],
  categories: [],
  membership: null,
  border: null,
  relief: null,
  measures: null,
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 32, name: 'Orla', type: 'mortal', world_id: 4 },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
    { kind: 'entity', id: 41, name: 'Grimfolk', type: 'people', world_id: 4 },
    { kind: 'world', id: 4, name: 'Orvael' },
  ])
}

describe('customs, town life and civics', () => {
  beforeEach(() => resetApi())

  it("shows a mortal's mark and gives it a name", async () => {
    serveBase()
    onApi('GET', '/api/customs/of/32', {
      ...EMPTY,
      node: MORTAL,
      marks: [
        {
          id: 5,
          kind: 'tattoo',
          meaning: 'deed',
          placed_epoch: 4,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/name_form:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CustomsSection nodeId={32} />)
    await expect.element(screen.getByText('Tattoo of deeds')).toBeVisible()
    await screen.getByLabelText('Name given').fill('Far-Walker')
    await screen.getByRole('button', { name: 'Name it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/name_form:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/name_form:set')[0].body).toEqual({
      holder_id: 32,
      form: 'deed',
      name: 'Far-Walker',
    })
  })

  it('shows each year of a class by its time of life, housework and sleep included', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/41', {
      ...EMPTY,
      node: FOLK,
      budgets: [
        {
          social_class: 'farmer',
          life_stage: 'elder',
          work: 30,
          rest: 20,
          worship: 10,
          leisure: 5,
          travel: 0,
          service: 0,
          learning: 0,
          care: 0,
          art: 0,
          housework: 10,
          sleep: 25,
          civic: 0,
          training: 0,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/time_budget:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CustomsSection nodeId={41} />)
    await expect.element(screen.getByText('Farmer, elder')).toBeVisible()
    await expect
      .element(screen.getByText(/housework 10 · sleep 25/))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Year' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/time_budget:set'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/time_budget:set')[0].body
    ).toMatchObject({
      people_id: 41,
      social_class: 'farmer',
      life_stage: 'adult',
      housework: 0,
      sleep: 0,
    })
  })

  it('shows the tavern of a town', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/40', {
      ...EMPTY,
      node: TOWN,
      taverns: [
        {
          structure: INN,
          keeper: MORTAL,
          patrons: 12,
          brawls: 1,
          lodging: 4,
          rumours: 3,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<CustomsSection nodeId={40} />)
    await expect
      .element(screen.getByText('The Low Door', { exact: true }))
      .toBeVisible()
  })

  it('keeps the marks of a thing that is no mortal', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/40', { ...EMPTY, node: TOWN })
    const { screen } = await renderApp(<CustomsSection nodeId={40} />)
    await screen
      .getByRole('tab', { name: /Marks, names and belonging/ })
      .click()
    await expect
      .element(screen.getByRole('button', { name: 'Mark it' }))
      .toBeDisabled()
  })

  it('names the case evidence stands before and offers the cases to lay it in', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/32', {
      ...EMPTY,
      node: MORTAL,
      evidence: [
        {
          id: 1,
          case_id: 2,
          kind: 'trace',
          points_to: MORTAL,
          reliability: 60,
          forged: false,
          found_epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('GET', '/api/justice/32', {
      node_id: 32,
      is_realm: false,
      is_city: false,
      is_mortal: true,
      home: TOWN,
      proposals: [],
      cases: [{ id: 2, crime: 'theft', accused: MORTAL }],
    })
    const { screen } = await renderApp(<CustomsSection nodeId={32} />)
    await screen.getByRole('tab', { name: /Civics/ }).click()
    await expect
      .element(screen.getByText(/Before the case of theft against Orla/))
      .toBeVisible()
  })

  it('shows which grade carries each duty and gives a duty and stirs a movement', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/41', {
      ...EMPTY,
      node: FOLK,
      grade_duties: [{ duty: 'war', grade: 'young_adults', held: true }],
    })
    onApi('POST', '/api/actions/grade_duty:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/revival:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CustomsSection nodeId={41} />)
    await expect
      .element(screen.getByText('Carried by the young adults · held'))
      .toBeVisible()
    await screen.getByRole('combobox', { name: 'Duty', exact: true }).click()
    await screen.getByRole('option', { name: 'Labour' }).click()
    await screen.getByRole('combobox', { name: 'Grade', exact: true }).click()
    await screen.getByRole('option', { name: 'Youths' }).click()
    await screen.getByRole('button', { name: 'Give the duty' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/grade_duty:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/grade_duty:set')[0].body).toEqual({
      people_id: 41,
      duty: 'labour',
      grade: 'youths',
      hold: true,
    })
    await screen.getByRole('combobox', { name: 'Way', exact: true }).click()
    await screen.getByRole('option', { name: 'Live apart' }).click()
    await screen.getByRole('button', { name: 'Stir it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/revival:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/revival:create')[0].body).toEqual({
      people_entity_id: 41,
      way: 'withdraw',
      goal: 'revive_language',
    })
  })
  it('names an intoxicant and its use, shows civic and training time and gives a custom and a year', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/41', {
      ...EMPTY,
      node: FOLK,
      intoxicants: [
        {
          intoxicant: 'animal_derived',
          use: 'hospitality',
          acceptance: 40,
          locked: [],
        },
      ],
      budgets: [
        {
          social_class: 'farmer',
          life_stage: 'adult',
          work: 45,
          rest: 10,
          worship: 5,
          leisure: 5,
          travel: 2,
          service: 1,
          learning: 2,
          care: 2,
          art: 0,
          housework: 5,
          sleep: 10,
          civic: 5,
          training: 8,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/intoxicant_custom:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/time_budget:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CustomsSection nodeId={41} />)
    await expect.element(screen.getByText('Drawn from beasts')).toBeVisible()
    await expect
      .element(screen.getByText('Offered to guests · accepted 40 of 100'))
      .toBeVisible()
    await expect.element(screen.getByText(/civic 5 · training 8/)).toBeVisible()
    expect(screen.container.textContent).not.toContain('animal_derived')
    await screen
      .getByRole('combobox', { name: 'Intoxicant', exact: true })
      .click()
    await screen.getByRole('option', { name: 'Made substance' }).click()
    await screen
      .getByRole('button', { name: 'Intoxicant', exact: true })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/intoxicant_custom:set'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/intoxicant_custom:set')[0].body
    ).toEqual({
      people_id: 41,
      intoxicant: 'synthetic',
      use: 'feast',
      acceptance: 50,
    })
    await screen.getByRole('button', { name: 'Year', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/time_budget:set'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/time_budget:set')[0].body
    ).toMatchObject({
      people_id: 41,
      social_class: 'farmer',
      civic: 0,
      training: 0,
    })
  })

  it('says its people keeps no intoxicant and no year and keeps the custom buttons with the reason while locked', async () => {
    serveBase()
    onApi('GET', '/api/customs/of/41', { ...EMPTY, node: FOLK })
    const { screen } = await renderApp(
      <CustomsSection nodeId={41} readOnlyReason='The world is read only.' />
    )
    await expect
      .element(screen.getByText('Its people keeps no intoxicant custom.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('No year is set for its classes.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Year', exact: true }))
      .toHaveAccessibleDescription('The world is read only.')
  })
})
