import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FolkwaysSection } from './FolkwaysSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const MORTAL = { id: 32, kind: 'entity' as const, name: 'Orla' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const FOLK = { id: 41, kind: 'entity' as const, name: 'Grimfolk' }

const EMPTY = {
  people: FOLK,
  diet: null,
  nutrition: null,
  needs: [],
  biases: [],
  purity: null,
  ranks: [],
  sources: [],
  methods: [],
  mishaps: [],
  beliefs: [],
  charms: [],
  accusations: [],
  hunts: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 32, name: 'Orla', type: 'mortal', world_id: 4 },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
    { kind: 'entity', id: 41, name: 'Grimfolk', type: 'people', world_id: 4 },
    { kind: 'world', id: 4, name: 'Orvael' },
  ])
}

describe('body, mind, purity and fortune', () => {
  beforeEach(() => resetApi())

  it("shows a mortal's nutrition and purity and makes it pure", async () => {
    serveBase()
    onApi('GET', '/api/folkways/of/32', {
      ...EMPTY,
      node: MORTAL,
      nutrition: {
        energy: 60,
        balance: 40,
        score: 50,
        deficiency: 'fresh',
        childhood: 45,
        grown: true,
        updated_epoch: 5,
        locked: [],
      },
      purity: {
        state: 'impure',
        source: 'the_dead',
        since_epoch: 5,
        until_epoch: 7,
        rank_id: null,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/purity:cleanse', ACCEPTED_ACTION)
    const { screen } = await renderApp(<FolkwaysSection nodeId={32} />)
    await expect.element(screen.getByText('Fed 50 of 100')).toBeVisible()
    await screen.getByRole('tab', { name: /Purity and rank/ }).click()
    await expect
      .element(screen.getByText('Impure', { exact: true }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Make it pure' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/purity:cleanse'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/purity:cleanse')[0].body).toEqual({
      mortal_id: 32,
    })
  })

  it('shows a misfortune blamed on witchcraft and the accusation it brought', async () => {
    serveBase()
    onApi('GET', '/api/folkways/of/40', {
      ...EMPTY,
      node: TOWN,
      mishaps: [
        {
          id: 3,
          town: TOWN,
          victim: MORTAL,
          cause: null,
          kind: 'crop_failure',
          true_cause: 'a hungry year in the region',
          explained: false,
          attribution: 'witchcraft',
          response: 'accusation',
          severity: 1,
          died: false,
          witnesses: [],
          epoch: 5,
          locked: [],
        },
      ],
      accusations: [
        {
          id: 9,
          town: TOWN,
          accuser: MORTAL,
          accused: { id: 33, kind: 'entity', name: 'Morrow' },
          mishap_id: 3,
          hunt_id: null,
          case_id: 2,
          outcome: 'pending',
          guilty_in_truth: false,
          opened_epoch: 5,
          closed_epoch: null,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<FolkwaysSection nodeId={40} />)
    await expect
      .element(screen.getByText('Crop failure in Grimsby'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Morrow accused of witchcraft'))
      .toBeVisible()
  })

  it('keeps biases from a thing that decides nothing', async () => {
    serveBase()
    onApi('GET', '/api/folkways/of/40', { ...EMPTY, node: TOWN })
    const { screen } = await renderApp(<FolkwaysSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Biases/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Set the bias' }))
      .toBeDisabled()
  })
})
