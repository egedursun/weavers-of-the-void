import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FortuneSection } from './FortuneSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MORTAL = { id: 30, kind: 'entity' as const, name: 'Ila Venn' }
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

function view(overrides: Record<string, unknown> = {}) {
  return {
    node: MORTAL,
    fortune: 12,
    streak: 3,
    held_values: [],
    law: 'personal',
    world_id: 4,
    sources: [
      {
        id: 6,
        kind: 'blessing',
        strength: 15,
        giver: SON,
        until_epoch: 9,
        since_epoch: 5,
        locked: [],
      },
    ],
    mishaps: [
      {
        id: 1,
        kind: 'fall',
        severity: 2,
        died: false,
        explained: true,
        epoch: 5,
      },
    ],
    cohort: [],
    ...overrides,
  }
}

describe('the fortune section', () => {
  beforeEach(() => resetApi())

  it('shows its fortune and sources and takes a source away', async () => {
    serveBase()
    onApi('GET', '/api/fortune/of/30', view())
    onApi('POST', '/api/actions/fortune_source:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FortuneSection nodeId={30} />)
    await expect.element(screen.getByText('Fortune 12, streak 3')).toBeVisible()
    await screen.getByRole('button', { name: 'Take it away' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/fortune_source:delete'))
      .toHaveLength(1)
  })

  it('lets a mishap befall it', async () => {
    serveBase()
    onApi('GET', '/api/fortune/of/30', view({ sources: [], mishaps: [] }))
    onApi('POST', '/api/actions/mishap:trigger', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FortuneSection nodeId={30} />)
    await expect
      .element(screen.getByText('Nothing turns its fortune'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Let it befall' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mishap:trigger'))
      .toHaveLength(1)
  })

  it('keeps the law control on screen for a thing in no world, disabled with its reason', async () => {
    serveBase()
    onApi('GET', '/api/fortune/of/30', view({ world_id: null }))
    const { screen } = await renderApp(<FortuneSection nodeId={30} />)
    await expect
      .element(screen.getByRole('button', { name: 'Set the law' }))
      .toBeDisabled()
  })
})
