import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CultureDriftSection,
  LoyaltySection,
  MobilitySection,
} from './CultureLoyalty'
import { LabourDepth } from './LabourDepth'
import { ClassWealthSection, NeedsSection } from './Needs'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const STANDING = {
  satisfaction: 50,
  income: 20,
  luxury_pct: 100,
}

const DEPTH = {
  entity_id: 30,
  gini: 41,
  staples: ['fish'],
  needs: [
    {
      social_class: 'farmer',
      commodity: 'medicine',
      effect: 'sickness',
      wanted: 10,
      got: 2,
      held_pct: null,
    },
    {
      social_class: 'noble',
      commodity: 'luxuries',
      effect: 'status',
      wanted: 20,
      got: 20,
      held_pct: 100,
    },
  ],
  classes: [
    {
      ...STANDING,
      social_class: 'farmer',
      share: 70,
      fed_pct: 80,
      needs_met_pct: 40,
      wealth: 700,
      per_head: 10,
      locked: [],
    },
    {
      ...STANDING,
      social_class: 'noble',
      share: 30,
      fed_pct: 100,
      needs_met_pct: 95,
      luxury_pct: 220,
      wealth: 3000,
      per_head: 100,
      locked: ['wealth'],
    },
  ],
  effects: [
    { effect: 'hunger', short_pct: 14 },
    { effect: 'sickness', short_pct: 80 },
  ],
  labour_reasons: [
    {
      job: 'farming',
      reason: 'class',
      workers: 900,
      commodity: null,
      workshop: null,
      price_pct: 100,
    },
    {
      job: 'mining',
      reason: 'no_structure',
      workers: -50,
      commodity: null,
      workshop: null,
      price_pct: 100,
    },
    {
      job: 'crafting',
      reason: 'price',
      workers: 30,
      commodity: 'tools',
      workshop: null,
      price_pct: 240,
    },
  ],
  held_jobs: [],
  prices: [
    { commodity: 'tools', price_pct: 240 },
    { commodity: 'grain', price_pct: 60 },
  ],
  corvee: null,
  drift_causes: [
    { cause: 'famine', axis: 'kinship', amount: 3, total: 9, epoch: 50 },
  ],
  impositions: [
    {
      id: 7,
      cause: 'war_lost',
      axis: 'martial',
      amount: 4,
      epochs_left: 2,
      created_epoch: 49,
    },
  ],
  loyalty: [
    {
      polity_id: 5,
      polity: 'The Salt Crown',
      value_distance: 30,
      distance_penalty: 9,
      grievances: 12,
      benefits: 8,
      satisfaction: -4,
      loyalty: 43,
      autonomy: 20,
      parts: [
        { part: 'weariness', value: 12, grievance: true },
        { part: 'routes', value: 8, grievance: false },
      ],
      locked: ['grievances'],
    },
  ],
  mobility: [
    {
      id: 1,
      event: 'ennobled',
      count: 1,
      mortal_id: 9,
      mortal: 'Brann',
      house_id: 11,
      house: 'House Brann',
      other_id: null,
      other: '',
      by_hand: false,
      epoch: 48,
    },
    {
      id: 2,
      event: 'ordained',
      count: 1,
      mortal_id: 9,
      mortal: 'Brann',
      house_id: null,
      house: '',
      other_id: null,
      other: '',
      by_hand: true,
      epoch: 49,
    },
  ],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 50 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/entities/30/society-depth', DEPTH)
}

describe('society depth sections', () => {
  beforeEach(resetApi)

  it('explains why labour moves and lays a corvee', async () => {
    serve()
    onApi('POST', '/api/actions/labour:corvee', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LabourDepth communityId={30} />)
    await expect.element(screen.getByText('Nothing to work -50')).toBeVisible()
    await expect.element(screen.getByText('Prices +30')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Impose a corvee' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/labour:corvee'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/labour:corvee')[0].body).toEqual({
      community_id: 30,
      share_pct: 20,
      polity_id: null,
      work_id: null,
    })
  })

  it('names the newer kinds of work and holds the workers of the arts', async () => {
    serve()
    onApi('GET', '/api/entities/30/society-depth', {
      ...DEPTH,
      labour_reasons: [
        {
          job: 'gathering',
          reason: 'class',
          workers: 120,
          commodity: null,
          workshop: null,
          price_pct: 100,
        },
        {
          job: 'arts',
          reason: 'class',
          workers: 40,
          commodity: null,
          workshop: null,
          price_pct: 100,
        },
        {
          job: 'administration',
          reason: 'resource',
          workers: 15,
          commodity: null,
          workshop: null,
          price_pct: 100,
        },
      ],
      held_jobs: ['gathering'],
    })
    onApi('POST', '/api/actions/labour:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LabourDepth communityId={30} />)
    await expect
      .element(screen.getByText('Gathering from the wild'))
      .toBeVisible()
    await expect.element(screen.getByText('The arts')).toBeVisible()
    await expect.element(screen.getByText('Keeping the offices')).toBeVisible()
    await expect
      .element(screen.getByText('120 by custom, 120 at work'))
      .toBeVisible()
    expect(screen.container.textContent).not.toContain('administration')
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await expect
      .element(screen.getByText('1 held against the world'))
      .toBeVisible()
    await screen.getByRole('combobox', { name: 'Trade' }).click()
    await screen.getByRole('option', { name: 'The arts' }).click()
    await screen
      .getByRole('spinbutton', { name: 'Workers at the arts' })
      .fill('60')
    await screen
      .getByRole('button', { name: 'Set Workers at the arts' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/labour:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/labour:set')[0].body).toEqual({
      community_id: 30,
      job: 'arts',
      workers: 60,
    })
  })

  it('shows the needs basket and holds a need', async () => {
    serve()
    onApi('POST', '/api/actions/needs:hold', ACCEPTED_ACTION)
    const { screen } = await renderApp(<NeedsSection communityId={30} />)
    await expect.element(screen.getByText('Sickness').first()).toBeVisible()
    await expect.element(screen.getByText('Medicine 20%')).toBeVisible()
    await expect.element(screen.getByText('Fish')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Hold this need' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/needs:hold'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/needs:hold')[0].body).toEqual({
      community_id: 30,
      social_class: 'farmer',
      commodity: 'medicine',
      held_pct: 100,
    })
  })

  it('shows wealth and Gini and releases held wealth', async () => {
    serve()
    onApi('POST', '/api/actions/class:standing', ACCEPTED_ACTION)
    const { screen } = await renderApp(<ClassWealthSection communityId={30} />)
    await expect.element(screen.getByText('41')).toBeVisible()
    await expect.element(screen.getByText('Richest a head')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Release nobles wealth' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/class:standing'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/class:standing')[0].body).toEqual({
      community_id: 30,
      social_class: 'noble',
      values: {},
      release: ['wealth'],
    })
  })

  it('shows drift causes and lifts a pressure', async () => {
    serve()
    onApi('POST', '/api/actions/drift:cancel', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CultureDriftSection communityId={30} />)
    await expect.element(screen.getByText('Clan loyalty +3')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Lift this pressure' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/drift:cancel'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/drift:cancel')[0].body).toEqual({
      imposition_id: 7,
    })
  })

  it('breaks down loyalty and releases a held term', async () => {
    serve()
    onApi('POST', '/api/actions/loyalty:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LoyaltySection communityId={30} />)
    await expect.element(screen.getByText('War weariness −12')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Release grievances' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/loyalty:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/loyalty:edit')[0].body).toEqual({
      polity_id: 5,
      member_id: 30,
      values: {},
      release: ['grievances'],
    })
  })

  it('lists rise and fall and frees the bound', async () => {
    serve()
    onApi('POST', '/api/actions/mobility:manumit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MobilitySection entityId={30} />)
    await expect.element(screen.getByText('Ennobled: Brann')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen
      .getByRole('button', { name: 'Set the bound free into this class' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mobility:manumit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mobility:manumit')[0].body).toEqual({
      community_id: 30,
      count: 50,
      target: 'farmer',
    })
  })

  it('raises a mortal by wealth, ordains them and casts them out', async () => {
    serve()
    onApi('POST', '/api/actions/mobility:move', ACCEPTED_ACTION)
    const { screen } = await renderApp(<MobilitySection entityId={30} mortal />)
    await expect.element(screen.getByText('Ordained: Brann')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).click()
    await screen.getByRole('button', { name: 'Raise them by wealth' }).click()
    await screen.getByRole('button', { name: 'Ordain them' }).click()
    await screen.getByRole('button', { name: 'Cast them out' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mobility:move'))
      .toHaveLength(3)
    expect(
      callsTo('POST', '/api/actions/mobility:move').map((call) => call.body)
    ).toEqual([
      { mortal_id: 30, event: 'enriched' },
      { mortal_id: 30, event: 'ordained' },
      { mortal_id: 30, event: 'outcast' },
    ])
  })
})
