import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EntityEconomy } from './EntityEconomy'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const COMMUNITY = 960

const ECONOMY = {
  community_id: COMMUNITY,
  epoch: 51,
  stocks: [
    {
      id: 165,
      commodity: 'grain',
      material: null,
      world_material_id: null,
      label: 'Grain',
      quantity: 2329,
      quality: 50,
    },
    {
      id: 1581,
      commodity: 'cloth',
      material: 'leather',
      world_material_id: null,
      label: 'Leather cloth',
      quantity: 21,
      quality: 25,
    },
  ],
  supply: { food: 295, ore: 9, goods: 120 },
  storage: { food: 250, ore: 250, goods: 250 },
  workshops: [
    {
      kind: 'granary',
      label: 'Granary',
      level: 1,
      fleet: 0,
      idle_epochs: 0,
      built_epoch: 50,
      structure_id: null,
    },
    {
      kind: 'tannery',
      label: 'Tannery',
      level: 2,
      fleet: 0,
      idle_epochs: 3,
      built_epoch: 40,
      structure_id: null,
    },
  ],
  chain: [
    {
      key: 'tan_hides',
      label: 'Tanning hides',
      workshop: 'tannery',
      inputs: { livestock: 1 },
      output: 'cloth',
      output_qty: 1,
      made: 21,
      quality: 25,
      material: 'leather',
      bottleneck: null,
      runs: true,
    },
    {
      key: 'leather_armour',
      label: 'Sewing leather armour',
      workshop: 'tannery',
      inputs: { cloth: 2 },
      output: 'armour',
      output_qty: 1,
      made: 0,
      quality: 0,
      material: null,
      bottleneck: 'cloth',
      runs: true,
    },
  ],
  flows: [
    { commodity: 'grain', flow: 'overflow', quantity: -663 },
    { commodity: 'grain', flow: 'harvest', quantity: 1957 },
  ],
  quotes: [],
  currency_id: null,
  market: true,
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', `/api/communities/${COMMUNITY}/economy`, ECONOMY)
  onApi('GET', '/api/currencies', [])
  onApi('POST', '/api/actions/stock:grant', ACCEPTED_ACTION)
}

describe('stores and production', () => {
  beforeEach(resetApi)

  it('shows an over-cap store as overflowing and blocked steps with their reason', async () => {
    serve()
    const { screen } = await renderApp(
      <EntityEconomy communityId={COMMUNITY} />
    )
    await expect.element(screen.getByText('Overflowing by 45')).toBeVisible()
    await expect
      .element(screen.getByText('663 spoiled last epoch'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Stood idle for want of cloth: no armour was made.')
      )
      .toBeVisible()
    await expect.element(screen.getByText('Idle 3 epochs')).toBeVisible()
    expect(screen.getByText('overflow', { exact: true }).query()).toBeNull()
  })

  it('keeps the stores editable behind the adjust panel', async () => {
    serve()
    const { screen } = await renderApp(
      <EntityEconomy communityId={COMMUNITY} />
    )
    await screen.getByRole('button', { name: 'Adjust the stores' }).click()
    await screen.getByRole('spinbutton', { name: 'Amount' }).fill('40')
    await screen.getByRole('button', { name: 'Add to the stores' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/stock:grant').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/stock:grant')[0]?.body).toEqual({
      community_id: COMMUNITY,
      commodity: 'grain',
      quantity: 40,
      quality: 50,
    })
  })
})
