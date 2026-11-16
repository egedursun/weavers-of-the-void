import { callsTo, onApi, renderApp, resetApi } from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { IntegrityFindings } from './IntegrityFindings'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const FINDING = {
  check: 'enum_values',
  invariant: null,
  table: 'covenants',
  column: 'duty',
  key: 'covenant_3',
  problem: 'the duty holds a value outside its list',
  resolution: 'set to its default',
  remedy: 'report',
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('the integrity findings', () => {
  beforeEach(() => resetApi())

  it('shows a finding that waits for the god and resolves it', async () => {
    serveBase()
    onApi('GET', '/api/integrity/findings', { findings: [FINDING] })
    onApi('POST', '/api/integrity/findings/resolve', { findings: [] })
    const { screen } = await renderApp(
      <IntegrityFindings readOnlyReason={null} />
    )
    await expect
      .element(screen.getByText(/the duty holds a value outside its list/))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Resolve' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/integrity/findings/resolve'))
      .toHaveLength(1)
  })

  it('says every table holds to its rules when nothing waits', async () => {
    serveBase()
    onApi('GET', '/api/integrity/findings', { findings: [] })
    const { screen } = await renderApp(
      <IntegrityFindings readOnlyReason={null} />
    )
    await expect
      .element(screen.getByText('Every table holds to its rules'))
      .toBeVisible()
  })

  it('keeps the resolve control on screen while the world is read only, disabled with its reason', async () => {
    serveBase()
    onApi('GET', '/api/integrity/findings', { findings: [FINDING] })
    const { screen } = await renderApp(
      <IntegrityFindings readOnlyReason='The world is being shown, not changed.' />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Resolve' }))
      .toBeDisabled()
  })
})
