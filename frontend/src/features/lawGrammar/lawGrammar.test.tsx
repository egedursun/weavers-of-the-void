import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LawGrammarSection } from './LawGrammarSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const LAW = { id: 70, kind: 'entity' as const, name: 'The Long Life' }
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

function view(overrides: Record<string, unknown> = {}) {
  return {
    law: LAW,
    preset: 'immortality',
    target: 'life',
    operator: 'multiply',
    key: null,
    value: 150,
    condition: 'always',
    until_epoch: null,
    suspended: false,
    contested: false,
    written: 'multiplies life by 150',
    exceptions: [
      { id: 4, kind: 'people', node: PEOPLE, entity_type: null, locked: [] },
    ],
    theories: [
      {
        id: 5,
        holder: PEOPLE,
        believed_operator: 'multiply',
        believed_value: 120,
        confidence: 60,
        adapted_epochs: 2,
        gap: 30,
        updated_epoch: 5,
        locked: [],
      },
    ],
    targets: [{ target: 'life', keys: [] }],
    locked: [],
    ...overrides,
  }
}

describe('the law grammar section', () => {
  beforeEach(() => resetApi())

  it('shows a theory a people holds and lets it be forgotten', async () => {
    serveBase()
    onApi('GET', '/api/natural-laws/70/grammar', view())
    onApi('POST', '/api/actions/law_theory:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LawGrammarSection lawId={70} />)
    await expect
      .element(screen.getByText(/The Oru believe it/).first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Forget it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/law_theory:delete'))
      .toHaveLength(1)
  })

  it('keeps the release control on screen, disabled while nothing is held', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/natural-laws/70/grammar',
      view({ exceptions: [], theories: [] })
    )
    const { screen } = await renderApp(<LawGrammarSection lawId={70} />)
    await expect
      .element(screen.getByRole('button', { name: 'Let the world decide' }))
      .toBeDisabled()
  })
})
