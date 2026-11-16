import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DivinePowersSection } from './DivinePowersSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 2, kind: 'son' as const, name: 'Ithren' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function power(overrides: Record<string, unknown> = {}) {
  return {
    id: 8,
    name: 'The Mending',
    verb: 'heal',
    object: 'stat',
    object_key: 'health',
    scope: 'community',
    mode: 'passive',
    cost: 'essence',
    cost_amount: 5,
    cooldown: 2,
    strength: 20,
    domains: [],
    son_preset: null,
    foreign_preset: null,
    last_used_epoch: null,
    granted_epoch: 2,
    ready: true,
    locked: [],
    ...overrides,
  }
}

describe('the divine powers section', () => {
  beforeEach(() => resetApi())

  it('shows a power and revokes it', async () => {
    serveBase()
    onApi('GET', '/api/divine/powers/of/2', { node: SON, powers: [power()] })
    onApi('POST', '/api/actions/divine_power:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DivinePowersSection nodeId={2} />)
    await expect.element(screen.getByText(/The Mending/).first()).toBeVisible()
    await screen.getByRole('button', { name: 'Revoke it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_power:delete'))
      .toHaveLength(1)
  })

  it('grants a new power', async () => {
    serveBase()
    onApi('GET', '/api/divine/powers/of/2', { node: SON, powers: [] })
    onApi('POST', '/api/actions/divine_power:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DivinePowersSection nodeId={2} />)
    await expect
      .element(screen.getByText('It holds no divine power'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Grant it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_power:create'))
      .toHaveLength(1)
  })
})
