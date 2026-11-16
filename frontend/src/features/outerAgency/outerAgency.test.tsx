import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OuterAgencySection } from './OuterAgencySection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const BEING = { id: 90, kind: 'entity' as const, name: 'The Unbidden' }
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
    being: BEING,
    fate: 'active',
    unfed_epochs: 1,
    starve_epochs: 8,
    plans: [
      {
        id: 3,
        goal: 'feed',
        stage: 1,
        stages: 3,
        progress: 40,
        target: null,
        state: 'active',
        started_epoch: 4,
        sign_epoch: null,
        locked: [],
      },
    ],
    heralds: [],
    incursions: [],
    pacts: [],
    relations: [],
    seals: [
      {
        id: 6,
        kind: 'seal',
        strength: 50,
        sealer: SON,
        sealed_epoch: 3,
        broken_epoch: null,
        locked: [],
      },
    ],
    ...overrides,
  }
}

describe('the outer agency section', () => {
  beforeEach(() => resetApi())

  it('shows an aim under way and a seal, and breaks the seal', async () => {
    serveBase()
    onApi('GET', '/api/outer-beings/90/agency', view())
    onApi('POST', '/api/actions/outer_seal:break', ACCEPTED_ACTION)
    const { screen } = await renderApp(<OuterAgencySection beingId={90} />)
    await expect
      .element(screen.getByText(/To feed: .*40 of 100/).first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Break it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/outer_seal:break'))
      .toHaveLength(1)
  })

  it('destroys an active being and keeps the control disabled once it has ended', async () => {
    serveBase()
    onApi('GET', '/api/outer-beings/90/agency', view())
    onApi('POST', '/api/actions/outer:destroy', ACCEPTED_ACTION)
    const first = await renderApp(<OuterAgencySection beingId={90} />)
    await first.screen.getByRole('button', { name: 'Destroy it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/outer:destroy'))
      .toHaveLength(1)
  })

  it('keeps the destroy control on screen for a destroyed being, disabled with its reason', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/outer-beings/90/agency',
      view({ fate: 'destroyed', plans: [], seals: [] })
    )
    const { screen } = await renderApp(<OuterAgencySection beingId={90} />)
    await expect
      .element(screen.getByRole('button', { name: 'Destroy it' }))
      .toBeDisabled()
  })
})
