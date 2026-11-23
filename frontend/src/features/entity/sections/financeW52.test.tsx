import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FinanceSection } from './FinanceSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const HOUSE = { id: 41, kind: 'entity' as const, name: 'House Orrin' }
const TOWN = { id: 42, kind: 'entity' as const, name: 'Ashby' }

const VIEW = {
  node_id: 30,
  name: 'Low Crown',
  realm: null,
  credit: null,
  policies: [],
  hoards: [],
  indicators: [],
  market_access: null,
  black_market: null,
  policy_kinds: [],
  credit_states: [],
  commodities: [],
}

function serve(view: object) {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 8 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 41, name: 'House Orrin', type: 'faction' },
    { kind: 'entity', id: 42, name: 'Ashby', type: 'settlement' },
  ])
  onApi('GET', '/api/finance/30', view)
  onApi('POST', '/api/actions/speculation:edit', ACCEPTED_ACTION)
}

describe('finance of batch 29', () => {
  beforeEach(resetApi)

  it('says when no lender has judged a realm and nothing is hoarded', async () => {
    serve(VIEW)
    const { screen } = await renderApp(<FinanceSection nodeId={30} />)
    await expect
      .element(screen.getByText('No lender has judged this one yet.'))
      .toBeVisible()
    await expect
      .element(screen.getByText('No hoards held by or in this one.'))
      .toBeVisible()
  })

  it('shows a repudiation, a rescuer and a seized hoard and frees the hoard', async () => {
    serve({
      ...VIEW,
      credit: {
        rating: 10,
        state: 'repudiated',
        state_label: 'Repudiated its debts',
        interest_pct: 30,
        reserves: 0,
        defaults: 2,
        restructured_until: null,
        rescuer: HOUSE,
        rescue_terms: 20,
        repudiated_until: 9,
        epoch: 7,
        held: [],
      },
      hoards: [
        {
          id: 5,
          merchant: HOUSE,
          market: TOWN,
          commodity: 'spice',
          commodity_label: 'Spice',
          units: 40,
          price: 12,
          status: 'seized',
          status_label: 'Seized',
          opened_epoch: 6,
          settled_epoch: 7,
          gain: 0,
          held: false,
        },
      ],
    })
    const { screen } = await renderApp(<FinanceSection nodeId={30} />)
    await expect.element(screen.getByText('Repudiated its debts')).toBeVisible()
    await expect
      .element(screen.getByText('Shut out of credit until epoch 9'))
      .toBeVisible()
    await expect.element(screen.getByText('House Orrin').first()).toBeVisible()
    await expect.element(screen.getByText(/on terms of 20/)).toBeVisible()
    await screen.getByRole('button', { name: 'Open the hoard' }).click()
    await screen.getByRole('combobox', { name: 'Status' }).click()
    await screen.getByRole('option', { name: 'Hoarding' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/speculation:edit'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/speculation:edit')[0].body
    ).toMatchObject({ speculation_id: 5, status: 'hoarding' })
  })
})
