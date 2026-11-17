import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TransformSection } from './TransformSection'
import { TransformTimelinePanel } from './TransformTimelinePanel'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 9, kind: 'son' as const, name: 'Aster' }
const BODY = { id: 90, kind: 'entity' as const, name: 'Aster the Walker' }
const STAR = { id: 3, kind: 'star' as const, name: 'Hael' }
const PRIEST = { id: 91, kind: 'entity' as const, name: 'Mira' }
const TALE = { id: 92, kind: 'entity' as const, name: 'The Tale of Aster' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function change(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    kind: 'fall',
    epoch: 6,
    trigger: 'council',
    state: 'done',
    subject: SON,
    result: BODY,
    subject_name: 'Aster',
    result_name: 'Aster the Walker',
    text: 'Aster fell from godhood and lives on as the mortal Aster the Walker.',
    revertible: true,
    locked: [],
    ...overrides,
  }
}

function sonView(overrides: Record<string, unknown> = {}) {
  return {
    node: SON,
    end: 'son',
    epoch: 6,
    warn_epochs: 1,
    came_from: [],
    became: [change()],
    prospects: [
      {
        id: 4,
        kind: 'corruption',
        subject_id: 9,
        progress: 60,
        stance: 'open',
        trigger: 'void',
        warned_epoch: 5,
        due_epoch: 6,
        updated_epoch: 6,
        locked: [],
      },
    ],
    open_kinds: ['fall', 'corruption', 'dead_god'],
    forceable: ['fall', 'corruption'],
    son_status: 'fallen',
    sanity: 8,
    corruption_band: 20,
    body: BODY,
    redeemers: [PRIEST],
    legends: [TALE],
    anchor_world: null,
    anchor_star: null,
    star_modifiers: [],
    luminosity_shift: 0,
    luminosity_shift_max: 90,
    ...overrides,
  }
}

describe('transformations', () => {
  beforeEach(() => resetApi())

  it('shows what a son became, warns of corruption and offers every rescue', async () => {
    serveBase()
    onApi('GET', '/api/transformations/of/9', sonView())
    onApi('POST', '/api/actions/transform:revert', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/son:outer_bargain', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/transform:block', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TransformSection nodeId={9} />)
    await expect
      .element(screen.getByText('Fallen into a mortal body'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Save it from corruption'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Undo it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/transform:revert'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Forbid bargains' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/son:outer_bargain'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Block it' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/transform:block'))
      .toHaveLength(1)
  })

  it('changes the light of a star and refuses to force a change that comes at its own moment', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/transformations/of/3',
      sonView({
        node: STAR,
        end: 'star',
        became: [],
        prospects: [],
        open_kinds: ['dead_god'],
        forceable: [],
        son_status: null,
        sanity: null,
        body: null,
        redeemers: [],
        legends: [],
        star_modifiers: [
          {
            id: 2,
            source: 'god_death',
            luminosity_pct: -30,
            age_epochs: 20,
            aged: true,
            decay: 0,
            epoch: 5,
            cause: null,
            locked: [],
          },
        ],
        luminosity_shift: -30,
      })
    )
    onApi('POST', '/api/actions/star_modifier:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TransformSection nodeId={3} />)
    await expect
      .element(screen.getByText('-30 in a hundred of its light'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /Force it now/ }))
      .toBeDisabled()
    await screen.getByRole('button', { name: /Change its light/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/star_modifier:create'))
      .toHaveLength(1)
  })

  it('lists every change across the cosmos and the ways things change', async () => {
    serveBase()
    onApi('GET', '/api/transformations', {
      epoch: 6,
      kinds: [
        {
          kind: 'fall',
          source: 'son',
          target: 'mortal',
          existing: false,
          watched: true,
          warned: true,
        },
      ],
      transformations: [change({ revertible: false, state: 'reverted' })],
      prospects: [
        {
          id: 4,
          kind: 'star_god',
          subject_id: 3,
          progress: 40,
          stance: 'blocked',
          trigger: 'engine',
          warned_epoch: null,
          due_epoch: null,
          updated_epoch: 6,
          locked: [],
        },
      ],
      subjects: [STAR],
    })
    onApi('POST', '/api/actions/transform:release', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TransformTimelinePanel />)
    await expect
      .element(screen.getByText('Son of the Creator into mortal'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Undo it' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Let it come' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/transform:release'))
      .toHaveLength(1)
  })
})
