import { callsTo, onApi, renderApp, resetApi } from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EconomyLedger } from './EconomyScreen'
import { economyWorldId } from './economyTabs'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PRIMARY = 4
const SAVE_ROW = 1

const ROUTE = {
  route_id: 4206,
  name: 'Torvanael',
  world_id: PRIMARY,
  first_id: 32,
  first_name: 'Nevrahim',
  second_id: 46,
  second_name: 'Hesmarak',
  mode: 'road',
  status: 'open',
  length: 1,
  capacity: 602,
  danger: 30,
  renown: 4,
  culture: 0,
  path: [30],
  tolls: [
    {
      region_id: 30,
      region_name: 'Vehrael',
      controller_id: 346,
      controller_name: 'Ehmarael',
      rate_pct: 5,
      set_by_player: false,
      controller_held: false,
      polity_id: null,
      polity_name: '',
    },
  ],
  controller_id: 346,
  blockaded_by_id: null,
  founded_epoch: 9,
  last_traffic_epoch: 50,
  volume: 17,
  closed_by_player: false,
  closed_by_son_id: null,
  closed_by_son_name: '',
  dangers: {
    bandits: 18,
    beasts: 7,
    weather: 5,
    sea: 0,
    officials: 0,
    spoilage: 0,
    pilferage: 0,
  },
  season_pct: 80,
  closed_season: null,
  seasons: {},
  carrier: null,
  chokepoint: false,
  locked: [],
  untolled: [],
  region_names: { '30': 'Vehrael' },
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { id: SAVE_ROW, epoch: 51, primary_world_id: PRIMARY },
  })
  onApi('GET', '/api/cosmos', {
    worlds: [
      { world: { id: 5, name: 'Dazbush' } },
      { world: { id: PRIMARY, name: 'Orvael' } },
    ],
  })
  onApi('GET', '/api/trade-routes', (call: { search: URLSearchParams }) =>
    call.search.get('world_id') === String(PRIMARY) ? [ROUTE] : []
  )
  onApi('GET', '/api/currencies', [])
  onApi('GET', '/api/ledger/debts', { loans: [], debts: [] })
}

describe('economy world choice', () => {
  it('falls back to the primary planet, never the save row id', () => {
    expect(economyWorldId('', PRIMARY, [PRIMARY, 5])).toBe(PRIMARY)
    expect(economyWorldId('', SAVE_ROW, [PRIMARY, 5])).toBe(PRIMARY)
    expect(economyWorldId('5', PRIMARY, [PRIMARY, 5])).toBe(5)
    expect(economyWorldId('9', PRIMARY, [PRIMARY, 5])).toBe(PRIMARY)
    expect(economyWorldId('', null, [])).toBeNull()
  })
})

describe('economy ledger', () => {
  beforeEach(resetApi)

  it('opens on the primary world and lists its trade routes', async () => {
    serve()
    const { screen } = await renderApp(
      <EconomyLedger tab='routes' onTab={vi.fn()} />
    )
    await expect
      .element(screen.getByRole('combobox', { name: 'World' }))
      .toHaveTextContent('Orvael')
    await expect.element(screen.getByText('Torvanael')).toBeVisible()
    expect(screen.getByText('No trade routes yet').query()).toBeNull()
    const scoped = callsTo('GET', '/api/trade-routes').map((call) =>
      call.search.get('world_id')
    )
    expect(scoped.length).toBeGreaterThan(0)
    expect(scoped.every((value) => value === String(PRIMARY))).toBe(true)
  })
})
