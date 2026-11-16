import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TechnologySection } from './TechnologySection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PEOPLE = { id: 12, kind: 'entity' as const, name: 'The Oru' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('the technology section', () => {
  beforeEach(() => resetApi())

  it('sets and holds a level, and releases a held one', async () => {
    serveBase()
    onApi('GET', '/api/technology/of/12', {
      node: PEOPLE,
      families: [
        { family: 'agriculture', level: 4, own: true, held: true },
        { family: 'warfare', level: 2, own: false, held: false },
      ],
    })
    onApi('POST', '/api/actions/technology:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/technology:release', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TechnologySection nodeId={12} />)
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/technology:release'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Set and hold' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/technology:set'))
      .toHaveLength(1)
  })

  it('keeps the strike control on screen, disabled for a level it does not hold itself', async () => {
    serveBase()
    onApi('GET', '/api/technology/of/12', {
      node: PEOPLE,
      families: [{ family: 'warfare', level: 2, own: false, held: false }],
    })
    const { screen } = await renderApp(<TechnologySection nodeId={12} />)
    await expect
      .element(screen.getByRole('button', { name: 'Strike its own level' }))
      .toBeDisabled()
  })
})
