import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TypedModelsSection } from './TypedModelsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const BEAST = { id: 30, kind: 'entity' as const, name: 'Old Greyback' }
const WORLD = { id: 4, kind: 'world' as const, name: 'Aerona' }

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
    node: BEAST,
    is_dimension: false,
    horrors: [
      {
        id: 3,
        world: WORLD,
        name: 'The Long Hush',
        target: 'sound',
        effect: 'take',
        scope: 'world',
        sense: 'absent',
        source: 'unknown',
        source_node: null,
        subject: null,
        duration: 2,
        sanity_cost: 4,
        leak: 2,
        epoch: 5,
        until_epoch: 7,
        locked: [],
      },
    ],
    attacks: [
      {
        id: 8,
        delivery: 'breath',
        effect: 'cold',
        range: 'near',
        recharge: 0,
        permanent: false,
        last_used_epoch: null,
        locked: [],
      },
    ],
    quests: [],
    aspects: [],
    ...overrides,
  }
}

describe('the typed models section', () => {
  beforeEach(() => resetApi())

  it('shows a horror and an attack and takes the attack away', async () => {
    serveBase()
    onApi('GET', '/api/typed/of/30', view())
    onApi('POST', '/api/actions/creature_attack:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TypedModelsSection nodeId={30} />)
    await expect
      .element(screen.getByText('The Long Hush: takes away sound in Aerona'))
      .toBeVisible()
    await expect.element(screen.getByText('Breath of cold')).toBeVisible()
    await screen.getByRole('button', { name: 'Take it away' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/creature_attack:delete'))
      .toHaveLength(1)
  })

  it('keeps the aspect control on screen for a thing that is no dimension, disabled with its reason', async () => {
    serveBase()
    onApi('GET', '/api/typed/of/30', view({ horrors: [], attacks: [] }))
    const { screen } = await renderApp(<TypedModelsSection nodeId={30} />)
    await expect
      .element(screen.getByRole('button', { name: 'Shape it' }))
      .toBeDisabled()
  })
})
