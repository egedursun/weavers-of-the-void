import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PantheonSection } from './PantheonSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 2, kind: 'son' as const, name: 'Ithren' }
const GOD = { id: 7, kind: 'foreign_god' as const, name: 'Ussamar' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }
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
    node: SON,
    is_god: true,
    pantheon: {
      world: WORLD,
      structure: 'court',
      head: SON,
      since_epoch: 2,
      locked: [],
    },
    ties: [{ god: SON, other: GOD, tie: 'rival', since_epoch: 3, locked: [] }],
    syncretisms: [
      {
        id: 5,
        foreign_god: GOD,
        son: SON,
        people: PEOPLE,
        dominant: SON,
        since_epoch: 4,
        locked: [],
      },
    ],
    ...overrides,
  }
}

describe('the pantheon section', () => {
  beforeEach(() => resetApi())

  it('shows the pantheon, its ties and a joined worship, and undoes a tie', async () => {
    serveBase()
    onApi('GET', '/api/pantheon/of/2', view())
    onApi('POST', '/api/actions/pantheon_tie:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PantheonSection nodeId={2} />)
    await expect
      .element(screen.getByText('The gods of Velmor: a ruler and a court'))
      .toBeVisible()
    await expect
      .element(screen.getByText('The Oru hold Ithren and Ussamar as one'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Undo the tie' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/pantheon_tie:delete'))
      .toHaveLength(1)
  })

  it('keeps the tie control on screen for a thing that is no god, disabled with its reason', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/pantheon/of/12',
      view({ node: PEOPLE, is_god: false, ties: [], syncretisms: [] })
    )
    const { screen } = await renderApp(<PantheonSection nodeId={12} />)
    await expect
      .element(screen.getByRole('button', { name: 'Tie them' }))
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Join them' }))
      .toBeDisabled()
  })
})
