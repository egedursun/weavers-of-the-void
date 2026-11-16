import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CreatorBondsSection } from './CreatorBondsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PEOPLE = { id: 12, kind: 'entity' as const, name: 'The Oru' }
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

function view(overrides: Record<string, unknown> = {}) {
  return {
    node: PEOPLE,
    is_people: true,
    standing: {
      awe: 40,
      love: 55,
      dread: 10,
      gratitude: 20,
      resentment: 5,
      ignorance: 10,
      stance: 'worship',
      heresy: 'none',
      updated_epoch: 5,
      locked: [],
    },
    depiction: {
      name: 'The First Voice',
      nature: 'maker',
      aspect: null,
      updated_epoch: 5,
      locked: [],
    },
    covenants: [
      {
        id: 3,
        duty: 'peace',
        promise: 'plenty',
        seal_sign: 'covenant_offer',
        state: 'sealed',
        since_epoch: 4,
        until_epoch: 10,
        breaches: 1,
        locked: [],
      },
    ],
    chosen: null,
    far_epochs: 0,
    ...overrides,
  }
}

describe('the Creator bonds section', () => {
  beforeEach(() => resetApi())

  it('shows how a people holds the Creator and strikes a covenant', async () => {
    serveBase()
    onApi('GET', '/api/creator/bonds/of/12', view())
    onApi('POST', '/api/actions/covenant:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreatorBondsSection nodeId={12} />)
    await expect
      .element(screen.getByText('They call the Creator The First Voice'))
      .toBeVisible()
    await expect
      .element(screen.getByText('To keep the peace for plenty: sealed'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Strike it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/covenant:delete'))
      .toHaveLength(1)
  })

  it('offers a covenant to a people', async () => {
    serveBase()
    onApi('GET', '/api/creator/bonds/of/12', view({ covenants: [] }))
    onApi('POST', '/api/actions/covenant:offer', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreatorBondsSection nodeId={12} />)
    await screen.getByRole('button', { name: 'Offer it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/covenant:offer'))
      .toHaveLength(1)
  })

  it('lets any thing be chosen and says why only peoples hold a view', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/creator/bonds/of/30',
      view({
        node: MORTAL,
        is_people: false,
        standing: null,
        depiction: null,
        covenants: [],
        far_epochs: null,
      })
    )
    onApi('POST', '/api/actions/chosen:choose', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreatorBondsSection nodeId={30} />)
    await expect
      .element(screen.getByText('No view to weigh here'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Choose it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/chosen:choose'))
      .toHaveLength(1)
  })
})
