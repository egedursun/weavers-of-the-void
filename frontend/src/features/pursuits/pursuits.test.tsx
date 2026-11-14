import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PursuitsSection } from './PursuitsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 30, kind: 'entity' as const, name: 'Wellbrook' }
const WORK = { id: 33, kind: 'entity' as const, name: 'The Long Stair' }
const MAKER = { id: 32, kind: 'entity' as const, name: 'Orla' }
const BODY = { id: 34, kind: 'entity' as const, name: 'Clay construct of Orla' }
const BEAST = { id: 35, kind: 'entity' as const, name: 'The Grey Hunger' }

const EMPTY = {
  prices: [],
  sales: [],
  collector: null,
  forgeries: [],
  canon: [],
  movement: null,
  clubs: [],
  league: null,
  matches: [],
  bets: [],
  as_construct: null,
  made: [],
  instructions: [],
  remade: null,
  contracts: [],
  sign: null,
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
      name: 'Wellbrook',
      type: 'settlement',
      world_id: 1,
    },
    { kind: 'entity', id: 32, name: 'Orla', type: 'mortal', world_id: 1 },
    {
      kind: 'entity',
      id: 33,
      name: 'The Long Stair',
      type: 'artwork',
      world_id: 1,
    },
    {
      kind: 'entity',
      id: 35,
      name: 'The Grey Hunger',
      type: 'beast',
      world_id: 1,
    },
  ])
}

describe('works, pastimes, constructs and fates', () => {
  beforeEach(() => resetApi())

  it('shows a work’s price and a forgery of it, and exposes the forgery', async () => {
    serveBase()
    onApi('GET', '/api/pursuits/of/33', {
      ...EMPTY,
      node: WORK,
      prices: [
        {
          artwork: WORK,
          price: 140,
          provenance: 2,
          interest: 30,
          last_buyer: TOWN,
          last_sale_epoch: 5,
          updated_epoch: 6,
          locked: [],
        },
      ],
      forgeries: [
        {
          id: 7,
          item: { id: 40, kind: 'entity', name: 'The Long Stair' },
          kind: 'artwork',
          forger: MAKER,
          original: WORK,
          brand_id: null,
          claim_id: null,
          skill: 55,
          status: 'hidden',
          exposed_by: null,
          exposed_epoch: null,
          made_epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/forgery:expose', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PursuitsSection nodeId={33} />)
    await expect
      .element(screen.getByText('The Long Stair: 140, 2 sales, interest 30'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'The Long Stair: a work of art, skill 55, passes for real'
        )
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Expose it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/forgery:expose'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/forgery:expose')[0].body).toEqual({
      forgery_id: 7,
      expert_id: null,
    })
  })

  it('shows a maker’s construct and its orders, and stills it', async () => {
    serveBase()
    onApi('GET', '/api/pursuits/of/32', {
      ...EMPTY,
      node: MAKER,
      made: [
        {
          body: BODY,
          material: 'clay',
          power_source: 'ley',
          power: 70,
          upkeep: 5,
          maker: MAKER,
          decay: 12,
          will: 'instructed',
          soul: null,
          made_epoch: 4,
          locked: [],
        },
      ],
      instructions: [
        {
          id: 3,
          owner: BODY,
          binding: 'order',
          command_token: 'word',
          token: null,
          holder: MAKER,
          kill_switch: false,
          kill_token: null,
          literalness: 90,
          orders: [
            {
              id: 11,
              kind: 'guard',
              target: TOWN,
              priority: 1,
              condition: 'always',
              until_epoch: null,
              lapsed: false,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
      sign: {
        mortal: MAKER,
        season: 2,
        ruling_celestial: null,
        dreaded: false,
        influence: 'believed',
        fortune: 0,
        exposed: false,
        born_epoch: 1,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/construct:unmake', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PursuitsSection nodeId={32} />)
    await screen
      .getByRole('tab', { name: /Constructs and their orders/ })
      .click()
    await expect
      .element(
        screen.getByText(
          'Clay construct of Orla: power 70, wear 12, follows orders'
        )
      )
      .toBeVisible()
    await expect.element(screen.getByText('1. Guard')).toBeVisible()
    await screen.getByRole('button', { name: 'Still it for good' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/construct:unmake'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/construct:unmake')[0].body).toEqual({
      construct_id: 34,
    })
  })

  it('posts a bounty on a beast from its own page', async () => {
    serveBase()
    onApi('GET', '/api/pursuits/of/35', {
      ...EMPTY,
      node: BEAST,
      contracts: [
        {
          id: 5,
          community: TOWN,
          beast: BEAST,
          bounty: 30,
          hunter: MAKER,
          status: 'taken',
          study: 40,
          posted_epoch: 4,
          closed_epoch: null,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<PursuitsSection nodeId={35} />)
    await screen
      .getByRole('tab', { name: /Bounties, signs and remaking/ })
      .click()
    await expect
      .element(screen.getByText('The Grey Hunger: bounty 30, study 40, taken'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Post it' }))
      .toBeDisabled()
  })
})
