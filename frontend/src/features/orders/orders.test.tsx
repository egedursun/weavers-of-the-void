import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OrdersSection } from './OrdersSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const REALM = { id: 30, kind: 'entity' as const, name: 'Crown of Grimsby' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }

const EMPTY = {
  realm: REALM,
  orders: [],
  kinds: [],
  transitions: [],
  households: [],
  savings: [],
  hoards: [],
  coins: [],
  rates: [],
  bills: [],
  putting_out: [],
  chains: [],
  flows: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    {
      kind: 'entity',
      id: 30,
      name: 'Crown of Grimsby',
      type: 'polity',
      world_id: 4,
    },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
  ])
}

describe('economic life', () => {
  beforeEach(() => resetApi())

  it('shows the economic order of a realm and its change of order, and pushes the change on', async () => {
    serveBase()
    onApi('GET', '/api/orders/of/30', {
      ...EMPTY,
      node: REALM,
      orders: [
        {
          id: 1,
          sector: null,
          ownership: 'temple',
          allocation: 'redistribution',
          labour: 'corvee',
          distribution: 'by_office',
          planning_capacity: 35,
          kind_id: 2,
          kind_name: 'Redistributive order',
          since_epoch: 4,
          locked: [],
        },
      ],
      kinds: [
        {
          id: 2,
          name: 'Redistributive order',
          ownership: 'temple',
          allocation: 'redistribution',
          labour: 'corvee',
          distribution: 'by_office',
          built_in: true,
          locked: [],
        },
      ],
      transitions: [
        {
          id: 3,
          sector: null,
          kind: 'land_reform',
          stage: 'transferring',
          compensation: 'none',
          resistance: 30,
          transferred: 2,
          from_axes: {
            ownership: 'temple',
            allocation: null,
            labour: null,
            distribution: null,
          },
          to_axes: {
            ownership: 'household',
            allocation: null,
            labour: null,
            distribution: null,
          },
          started_epoch: 5,
          ended_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/order_transition:advance', ACCEPTED_ACTION)
    const { screen } = await renderApp(<OrdersSection nodeId={30} />)
    await expect
      .element(screen.getByText('The whole realm: Redistributive order'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Land reform: moving holdings'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Push it on' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/order_transition:advance'))
      .toHaveLength(1)
  })

  it('shows what households save and keeps the saving control with its reason when no household lives here', async () => {
    serveBase()
    onApi('GET', '/api/orders/of/40', {
      ...EMPTY,
      node: TOWN,
      hoards: [
        {
          id: 5,
          holder: null,
          place: TOWN,
          amount: 30,
          state: 'lost',
          hidden_epoch: 2,
          found_by: null,
          found_epoch: null,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<OrdersSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Saving and hoards/ }).click()
    await expect.element(screen.getByText('30 coin, lost')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Set it' }))
      .toBeDisabled()
  })
})
