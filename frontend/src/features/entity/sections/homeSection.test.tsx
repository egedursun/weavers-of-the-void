import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HomeSection } from './HomeSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const OSWIN = { id: 501, name: 'Oswin', kind: 'entity', type: 'mortal' }
const FENWICK = { id: 30, name: 'Fenwick', kind: 'entity', type: 'settlement' }

const DWELLING = {
  dwelling_kind_id: 4,
  kind_name: 'Stilt house',
  level: 'cottage',
  quality: 55,
  effective_quality: 50,
  expected_quality: 40,
  rooms: 3,
  district_id: null,
  district_kind: null,
  settlement: FENWICK,
  furnishings: [],
  tenure: 'owned',
  heating: null,
  light: null,
  crowding: 20,
  built_epoch: 44,
  held: [],
}

const HOUSEHOLD = {
  id: 12,
  name: 'House of Oswin',
  head: OSWIN,
  settlement: FENWICK,
  social_class: 'farmer',
  wealth: 30,
  income: 12,
  expenses: 9,
  servants: 0,
  dependents: 2,
  burden: 10,
  debts: [],
  last_decision: null,
  last_decision_label: null,
  decided_epoch: null,
  formed_epoch: 40,
  form: 'stem',
  members: [
    {
      mortal: OSWIN,
      role: 'head',
      role_label: 'Head',
      cares_for: null,
      joined_epoch: 40,
      held: false,
    },
  ],
  dwelling: DWELLING,
  held: [],
}

const HOME = {
  node_id: 501,
  node_kind: 'mortal',
  can_hold_household: true,
  can_hold_aggregates: false,
  reason: null,
  will: null,
  household: HOUSEHOLD,
  households: [],
  aggregates: [],
  roles: [
    { key: 'head', label: 'Head' },
    { key: 'heir', label: 'Heir' },
  ],
  dwellings: [
    { id: 4, name: 'Stilt house', level: 'cottage', built_in: true },
    { id: 7, name: 'Burrow', level: 'hut', built_in: true },
    { id: 9, name: 'Reed hall', level: 'house', built_in: false },
  ],
  classes: [
    { key: 'farmer', label: 'Farmer' },
    { key: 'artisan', label: 'Artisan' },
  ],
  neighbours: [],
}

function serve(readOnly = false) {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: readOnly,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [
    { ...OSWIN, world_id: 1 },
    { ...FENWICK, world_id: 1 },
  ])
}

describe('household and home', () => {
  beforeEach(resetApi)

  it('shows the home by its kind and the class by its label and moves the household into a burrow', async () => {
    serve()
    onApi('GET', '/api/home/501', HOME)
    onApi('POST', '/api/actions/dwelling:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HomeSection nodeId={501} />)
    await expect
      .element(screen.getByText('Stilt house of 3 rooms'))
      .toBeVisible()
    await expect.element(screen.getByText('In Fenwick')).toBeVisible()
    await expect.element(screen.getByText('Farmer')).toBeVisible()
    await expect.element(screen.getByText('A source of pride')).toBeVisible()
    await screen.getByRole('button', { name: 'Open the home' }).click()
    await screen.getByRole('combobox', { name: 'Kind of home' }).click()
    await expect
      .element(
        screen.getByRole('option', {
          name: 'Reed hall · houses · a kind of its own',
        })
      )
      .toBeVisible()
    await screen.getByRole('option', { name: 'Burrow · huts' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/dwelling:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/dwelling:set')[0].body).toEqual({
      household_id: 12,
      dwelling_kind_id: 7,
      clear_district: false,
      hold: true,
    })
  })

  it('founds a household for a mortal without one', async () => {
    serve()
    onApi('GET', '/api/home/501', { ...HOME, household: null })
    onApi('POST', '/api/actions/household:found', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HomeSection nodeId={501} />)
    await expect
      .element(screen.getByText('Not yet part of any household.'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Found a household for them' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/household:found'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/household:found')[0].body).toEqual({
      head_id: 501,
    })
  })

  it('gives a roofless household a hut and keeps it with the read-only reason', async () => {
    serve(true)
    onApi('GET', '/api/home/501', {
      ...HOME,
      household: { ...HOUSEHOLD, dwelling: null },
    })
    const { screen } = await renderApp(<HomeSection nodeId={501} />)
    await expect
      .element(screen.getByText('This household has no roof of its own.'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Give it a hut' }))
      .toHaveAccessibleDescription('A guest world is open read-only.')
  })

  it('says why a thing keeps no household', async () => {
    serve()
    onApi('GET', '/api/home/4', {
      ...HOME,
      node_id: 4,
      node_kind: 'world',
      can_hold_household: false,
      household: null,
      reason: 'A world keeps no household; its peoples do.',
    })
    const { screen } = await renderApp(<HomeSection nodeId={4} />)
    await expect.element(screen.getByText('No household here')).toBeVisible()
    await expect
      .element(screen.getByText('A world keeps no household; its peoples do.'))
      .toBeVisible()
  })
})
