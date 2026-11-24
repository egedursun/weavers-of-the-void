import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PolityProduction } from './PolityProduction'
import { TradeRouteSection } from './RouteAndMarket'
import { FoundRouteDialog } from './RouteControls'
import { SentientPacts } from './SentientPact'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const ROUTE = 4100
const FIRST = 11
const SECOND = 12
const KEEPER = 13
const REALM = 4200
const RESOURCE = 4300
const PACT = 4301

const VIEW = {
  route_id: ROUTE,
  name: 'Dust Road of Brennhold and Ashwick',
  world_id: 1,
  first_id: FIRST,
  first_name: 'Brennhold',
  second_id: SECOND,
  second_name: 'Ashwick',
  mode: 'road',
  status: 'seasonal',
  length: 2,
  capacity: 900,
  danger: 47,
  renown: 10,
  culture: 4,
  path: [21, 22, 23],
  path_strata: [null, 'cavern_upper', null],
  tolls: [
    {
      region_id: 22,
      region_name: 'Greenvale',
      controller_id: KEEPER,
      controller_name: 'Midbridge',
      rate_pct: 9,
      set_by_player: false,
      controller_held: true,
      polity_id: REALM,
      polity_name: 'Crown of Vale',
    },
  ],
  controller_id: KEEPER,
  blockaded_by_id: null,
  founded_epoch: 3,
  last_traffic_epoch: 7,
  volume: 300,
  closed_by_player: false,
  closed_by_son_id: 5,
  closed_by_son_name: 'Ithren',
  dangers: {
    bandits: 20,
    beasts: 15,
    weather: 12,
    sea: 0,
    officials: 9,
    spoilage: 4,
    pilferage: 6,
  },
  season_pct: 62,
  closed_season: 1,
  seasons: { '0': 'Thaw', '1': 'Deep Cold' },
  carrier: 'pack_animals',
  chokepoint: true,
  locked: ['mode'],
  untolled: [23],
  region_names: { '21': 'Amberreach', '22': 'Greenvale', '23': 'Stonefold' },
}

const DETAIL = {
  ...VIEW,
  flows: [],
  losses: [
    {
      epoch: 7,
      commodity: 'grain',
      cause: 'beasts',
      units: 30,
      culprit_id: 77,
      culprit_name: 'Graveljaw',
    },
  ],
}

const NAMES = [
  { kind: 'entity', id: FIRST, name: 'Brennhold', type: 'settlement' },
  { kind: 'entity', id: SECOND, name: 'Ashwick', type: 'settlement' },
  { kind: 'entity', id: KEEPER, name: 'Midbridge', type: 'settlement' },
]

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 8 },
  })
  onApi('GET', '/api/names', NAMES)
  onApi('GET', `/api/trade-routes/${ROUTE}`, DETAIL)
  onApi('POST', '/api/actions/trade_route:edit', ACCEPTED_ACTION)
  onApi('POST', '/api/actions/trade_route:toll_remove', ACCEPTED_ACTION)
  onApi('POST', '/api/actions/trade_route:found', ACCEPTED_ACTION)
  onApi('POST', '/api/actions/resource:pact', ACCEPTED_ACTION)
  onApi('POST', '/api/actions/resource:pact_terms', ACCEPTED_ACTION)
}

describe('trade route command', () => {
  beforeEach(resetApi)

  it('shows each danger, the worst season, the toll treasury and the closure', async () => {
    serve()
    const { screen } = await renderApp(<TradeRouteSection routeId={ROUTE} />)
    await expect
      .element(screen.getByText('What threatens the cargo'))
      .toBeVisible()
    await expect.element(screen.getByText('30 lost to Graveljaw')).toBeVisible()
    await expect.element(screen.getByText('Closed by Ithren')).toBeVisible()
    await expect
      .element(screen.getByText('62% in the worst season'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Crown of Vale').first())
      .toBeVisible()
    await expect.element(screen.getByText('A chokepoint')).toBeVisible()
  })

  it('holds and releases route values and forbids a toll', async () => {
    serve()
    const { screen } = await renderApp(<TradeRouteSection routeId={ROUTE} />)
    await screen.getByRole('button', { name: 'Adjust the route' }).click()
    await screen.getByRole('spinbutton', { name: 'Weather danger' }).fill('33')
    await screen.getByRole('button', { name: 'Hold weather danger' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/trade_route:edit').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/trade_route:edit')[0]?.body).toEqual({
      route_id: ROUTE,
      values: { danger_weather: 33 },
    })
    await screen.getByRole('button', { name: 'Release way of travel' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/trade_route:edit').length)
      .toBe(2)
    expect(callsTo('POST', '/api/actions/trade_route:edit')[1]?.body).toEqual({
      route_id: ROUTE,
      release: ['mode'],
    })
    await screen.getByRole('button', { name: 'Forbid any toll here' }).click()
    await expect
      .poll(
        () => callsTo('POST', '/api/actions/trade_route:toll_remove').length
      )
      .toBe(1)
    await screen
      .getByRole('button', { name: 'Allow tolls in Stonefold again' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/trade_route:edit').length)
      .toBe(3)
    expect(callsTo('POST', '/api/actions/trade_route:edit')[2]?.body).toEqual({
      route_id: ROUTE,
      release: ['untolled.23'],
    })
  })

  it('shows the closed season, the carrier and the three new losses', async () => {
    serve()
    const { screen } = await renderApp(<TradeRouteSection routeId={ROUTE} />)
    await expect.element(screen.getByText('Shut in Deep Cold')).toBeVisible()
    await expect
      .element(screen.getByText('Carried by pack animals'))
      .toBeVisible()
    await expect.element(screen.getByText('Officials')).toBeVisible()
    await expect.element(screen.getByText('Spoilage')).toBeVisible()
    await expect.element(screen.getByText('Pilferage')).toBeVisible()
  })

  it('holds a closed season and a carrier', async () => {
    serve()
    const { screen } = await renderApp(<TradeRouteSection routeId={ROUTE} />)
    await screen.getByRole('button', { name: 'Adjust the route' }).click()
    await screen.getByRole('combobox', { name: 'Closed season' }).click()
    await screen.getByRole('option', { name: 'Open all year' }).click()
    await screen.getByRole('button', { name: 'Hold the closed season' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/trade_route:edit').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/trade_route:edit')[0]?.body).toEqual({
      route_id: ROUTE,
      values: { closed_season: null },
    })
    await screen.getByRole('combobox', { name: 'Carried by' }).click()
    await screen.getByRole('option', { name: 'Porters' }).click()
    await screen.getByRole('button', { name: 'Hold the carrier' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/trade_route:edit').length)
      .toBe(2)
    expect(callsTo('POST', '/api/actions/trade_route:edit')[1]?.body).toEqual({
      route_id: ROUTE,
      values: { carrier: 'porters' },
    })
  })

  it('lays out a new route with its way of travel', async () => {
    serve()
    const { screen } = await renderApp(<FoundRouteDialog firstId={FIRST} />)
    await screen.getByRole('button', { name: 'Lay out a new route' }).click()
    await screen.getByRole('combobox', { name: 'Second market' }).click()
    await screen.getByRole('option', { name: /Ashwick/ }).click()
    await screen.getByRole('button', { name: 'Lay the road' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/trade_route:found').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/trade_route:found')[0]?.body).toEqual({
      first_id: FIRST,
      second_id: SECOND,
      mode: null,
      controller_id: null,
      toll_pct: null,
      name: null,
      title: null,
      description: null,
    })
  })
})

describe('the realm at work', () => {
  beforeEach(resetApi)

  it('gathers the members chain with its bottlenecks', async () => {
    serve()
    onApi('GET', `/api/polities/${REALM}/production`, {
      polity_id: REALM,
      name: 'Crown of Vale',
      epoch: 8,
      members: [
        {
          community_id: FIRST,
          name: 'Brennhold',
          epoch: 7,
          made: 12,
          bottlenecks: 0,
          workshops: 1,
        },
        {
          community_id: SECOND,
          name: 'Ashwick',
          epoch: 7,
          made: 0,
          bottlenecks: 1,
          workshops: 0,
        },
      ],
      chain: [
        {
          key: 'forge_tools',
          label: 'Forging tools',
          workshop: 'forge',
          inputs: { ore: 1, fuel: 1 },
          output: 'tools',
          output_qty: 2,
          made: 12,
          quality: 60,
          material: null,
          bottleneck: 'fuel',
          starved_ids: [SECOND],
          running_ids: [FIRST],
          able_ids: [FIRST],
        },
      ],
      stocks: [{ commodity: 'grain', quantity: 400, quality: 52 }],
      workshops: { forge: 2 },
    })
    const { screen } = await renderApp(<PolityProduction polityId={REALM} />)
    await expect
      .element(screen.getByText('Production chain of the realm'))
      .toBeVisible()
    await expect.element(screen.getByText('Short of fuel in')).toBeVisible()
    await expect
      .element(screen.getByText('Metal works in 1 of 2 members'))
      .toBeVisible()
    await expect.element(screen.getByText('1 short')).toBeVisible()
  })
})

describe('pacts with a living resource', () => {
  beforeEach(resetApi)

  it('shows a pact and changes its terms', async () => {
    serve()
    onApi('GET', `/api/resources/${RESOURCE}/profile`, {
      resource_id: RESOURCE,
      params: [{ mechanic: 'sentient', magnitude: 5, epochs: null }],
      owners: [FIRST],
    })
    onApi('GET', `/api/resources/${RESOURCE}/pacts`, [
      {
        treaty_id: PACT,
        name: 'the Tribute of Brennhold and the Seam',
        status: 'in_force',
        owner_id: FIRST,
        owner_name: 'Brennhold',
        demand: 'a song each dawn',
        commodity: 'luxuries',
        units: 9,
        cost: 4,
        every: 2,
        paid_epoch: 6,
        signed_epoch: 4,
        until_epoch: 10,
        misread: false,
      },
    ])
    const { screen } = await renderApp(<SentientPacts resourceId={RESOURCE} />)
    await expect
      .element(screen.getByText('It asks a song each dawn.'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Change the terms' }).click()
    await screen.getByRole('spinbutton', { name: 'Loads given' }).fill('3')
    await screen.getByRole('button', { name: 'Set the terms' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/resource:pact_terms').length)
      .toBe(1)
    expect(
      callsTo('POST', '/api/actions/resource:pact_terms')[0]?.body
    ).toEqual({
      treaty_id: PACT,
      terms: {
        demand: 'a song each dawn',
        commodity: 'luxuries',
        units: 3,
        cost: 4,
        every: 2,
      },
    })
  })
})
