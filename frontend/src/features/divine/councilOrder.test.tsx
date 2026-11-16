import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CouncilOrderPanel } from './CouncilOrderPanel'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 2, kind: 'son' as const, name: 'Ithren' }
const GOD = { id: 7, kind: 'foreign_god' as const, name: 'Ussamar' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/council/rulings', { rulings: [], motions: [] })
}

function order(overrides: Record<string, unknown> = {}) {
  return {
    procedure: {
      quorum_pct: 50,
      voting_rule: 'majority',
      creator_veto: true,
      term_epochs: 6,
      veto_cost: 20,
      locked: [],
    },
    seats: [
      {
        god: SON,
        is_son: true,
        seat: 'by_right',
        since_epoch: 1,
        excluded_until: null,
        sitting: true,
        locked: [],
      },
      {
        god: GOD,
        is_son: false,
        seat: 'invited',
        since_epoch: 4,
        excluded_until: null,
        sitting: true,
        locked: [],
      },
    ],
    violations: [
      {
        id: 9,
        ruling_id: 3,
        ruling_motion: 'cosmic_truce',
        violator: SON,
        epoch: 5,
        step: 'censure',
        locked: [],
      },
    ],
    ...overrides,
  }
}

describe('the council order panel', () => {
  beforeEach(() => resetApi())

  it('shows the procedure, seats and a breach, and strikes the breach', async () => {
    serveBase()
    onApi('GET', '/api/council/order', order())
    onApi('POST', '/api/actions/council_violation:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CouncilOrderPanel />)
    await expect
      .element(
        screen.getByText(
          /Rulings hold 6 epochs; the Creator may veto for 20 essence/
        )
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Strike the breach' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/council_violation:delete'))
      .toHaveLength(1)
  })

  it('returns the procedure to the rules of the world', async () => {
    serveBase()
    onApi('GET', '/api/council/order', order({ violations: [] }))
    onApi('POST', '/api/actions/council_procedure:reset', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CouncilOrderPanel />)
    await screen
      .getByRole('button', { name: 'Return to the rules of the world' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/council_procedure:reset'))
      .toHaveLength(1)
  })
})
