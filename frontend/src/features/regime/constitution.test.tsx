import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConstitutionSection } from './ConstitutionSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const CREED = { id: 44, kind: 'entity' as const, name: 'The Open Hand' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('the constitution section', () => {
  beforeEach(() => resetApi())

  it('shows a realm constitution and tears it up', async () => {
    serveBase()
    onApi('GET', '/api/constitutions/of/20', {
      is_realm: true,
      constitution: {
        ideology: CREED,
        selectorate: 'nobles',
        offices: 4,
        rights: 3,
        written_epoch: 5,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/constitution:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <ConstitutionSection nodeId={20} blocked={null} />
    )
    await expect
      .element(screen.getByText('A constitution written in epoch 5'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Tear it up' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/constitution:delete'))
      .toHaveLength(1)
  })

  it('writes one for a realm that has none', async () => {
    serveBase()
    onApi('GET', '/api/constitutions/of/20', {
      is_realm: true,
      constitution: null,
    })
    onApi('POST', '/api/actions/constitution:write', ACCEPTED_ACTION)
    const { screen } = await renderApp(
      <ConstitutionSection nodeId={20} blocked={null} />
    )
    await screen.getByRole('button', { name: 'Write it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/constitution:write'))
      .toHaveLength(1)
  })

  it('keeps the write control on screen for a thing that is no realm, disabled with its reason', async () => {
    serveBase()
    onApi('GET', '/api/constitutions/of/30', {
      is_realm: false,
      constitution: null,
    })
    const { screen } = await renderApp(
      <ConstitutionSection nodeId={30} blocked={null} />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Write it' }))
      .toBeDisabled()
  })
})
