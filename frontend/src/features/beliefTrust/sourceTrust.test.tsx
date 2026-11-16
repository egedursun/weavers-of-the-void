import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SourceTrustSection } from './SourceTrustSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MORTAL = { id: 30, kind: 'entity' as const, name: 'Ila Venn' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('the source trust section', () => {
  beforeEach(() => resetApi())

  it('shows how far it trusts a source and starts it afresh', async () => {
    serveBase()
    onApi('GET', '/api/beliefs/trust/of/30', {
      node: MORTAL,
      sources: [
        {
          source: 'network',
          trust: 70,
          right: 5,
          wrong: 1,
          updated_epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/source_trust:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SourceTrustSection nodeId={30} />)
    await expect.element(screen.getByText(/trusted 70/)).toBeVisible()
    await screen.getByRole('button', { name: 'Start afresh' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/source_trust:delete'))
      .toHaveLength(1)
  })

  it('sets trust in a source it has not weighed yet', async () => {
    serveBase()
    onApi('GET', '/api/beliefs/trust/of/30', { node: MORTAL, sources: [] })
    onApi('POST', '/api/actions/source_trust:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<SourceTrustSection nodeId={30} />)
    await expect
      .element(screen.getByText('No source weighed yet'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/source_trust:set'))
      .toHaveLength(1)
  })
})
