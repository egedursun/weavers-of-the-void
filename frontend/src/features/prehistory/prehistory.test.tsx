import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DeepTimePanel } from './DeepTimePanel'
import { PrehistorySection } from './PrehistorySection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WORLD = { id: 4, kind: 'world' as const, name: 'Velmor' }
const TWIN = { id: 5, kind: 'world' as const, name: 'Romlev' }
const KING = { id: 70, kind: 'entity' as const, name: 'Old King' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function prehistory(overrides: Record<string, unknown> = {}) {
  return {
    node: WORLD,
    world: WORLD,
    world_type: 'mirror',
    kind_of_world: 'mirrored',
    kind: 'mirrored',
    state: 'done',
    source: 'mirrored',
    epochs: 12,
    resolution: 2,
    rounds_done: 12,
    birth_epoch: 6,
    seconds: 40,
    slow_rounds: 1,
    source_world: TWIN,
    locked: [],
    happenings: [
      {
        id: 1,
        round: 3,
        magnitude: 80,
        source: 'mirrored',
        text: 'The Old King fell at the ford.',
        subject: KING,
        source_world: TWIN,
        mirrored: true,
        locked: [],
      },
    ],
    lore_free: false,
    default_epochs: 0,
    default_resolution: 1,
    epochs_max: 1000,
    resolution_max: 20,
    seed_cost: 300,
    absent_reason: null,
    ...overrides,
  }
}

describe('prehistory', () => {
  beforeEach(() => resetApi())

  it('shows a mirrored past round by round and keeps a finished run from being planned again', async () => {
    serveBase()
    onApi('GET', '/api/prehistory/of/4', prehistory())
    onApi('POST', '/api/actions/prehistory_event:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PrehistorySection nodeId={4} />)
    await expect
      .element(
        screen.getByText(
          'Round 3 of the past, magnitude 80, mirrored from the twin'
        )
      )
      .toBeVisible()
    await expect.element(screen.getByText('12 of 12')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: /Plan it/ }))
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: /Seed and run it/ }))
      .toBeDisabled()
    await screen
      .getByRole('button', { name: 'Strike it out of the past' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/prehistory_event:remove'))
      .toHaveLength(1)
  })

  it('plans the past of a world still empty of lore', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/prehistory/of/4',
      prehistory({
        kind: null,
        state: null,
        source: null,
        epochs: 0,
        rounds_done: 0,
        birth_epoch: null,
        source_world: null,
        happenings: [],
        lore_free: true,
      })
    )
    onApi('POST', '/api/actions/prehistory:configure', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PrehistorySection nodeId={4} />)
    await expect.element(screen.getByText('No past is kept here')).toBeVisible()
    await screen.getByRole('button', { name: /Plan it/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/prehistory:configure'))
      .toHaveLength(1)
  })

  it('runs deep time forward and lists a finished run', async () => {
    serveBase()
    onApi('GET', '/api/deep-time', {
      runs: [
        {
          id: 9,
          epochs: 5,
          ran: 5,
          from_epoch: 6,
          to_epoch: 11,
          state: 'done',
          sons_simulated: 15,
          locked: [],
          happenings: [
            {
              id: 2,
              epoch: 8,
              magnitude: 70,
              text: 'A plague crossed the hills.',
              locked: [],
            },
          ],
        },
      ],
      max_epochs: 100,
      cost_per_epoch: 50,
    })
    onApi('POST', '/api/actions/deep_time:run', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DeepTimePanel />)
    await expect
      .element(screen.getByText('From epoch 6 to epoch 11'))
      .toBeVisible()
    await screen.getByRole('button', { name: /Run it forward/ }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/deep_time:run'))
      .toHaveLength(1)
  })
})
