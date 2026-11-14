import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BelongingSection } from './BelongingSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }
const FOLK = { id: 41, kind: 'entity' as const, name: 'Grimfolk' }
const REALM = { id: 50, kind: 'entity' as const, name: 'Crown of Grimsby' }
const ORLA = { id: 32, kind: 'entity' as const, name: 'Orla' }
const PELL = { id: 33, kind: 'entity' as const, name: 'Pell' }

const EMPTY = {
  epoch: 6,
  realm: REALM,
  identities: [],
  fault_layer: null,
  peer_groups: [],
  sanctuaries: [],
  sanctuary_law: null,
  satires: [],
  jester: null,
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
    { kind: 'entity', id: 33, name: 'Pell', type: 'mortal', world_id: 4 },
    {
      kind: 'entity',
      id: 40,
      name: 'Grimsby',
      type: 'settlement',
      world_id: 4,
    },
    {
      kind: 'entity',
      id: 50,
      name: 'Crown of Grimsby',
      type: 'polity',
      world_id: 4,
    },
  ])
}

describe('identities, play, sanctuary and satire', () => {
  beforeEach(() => resetApi())

  it('shows how much each identity of a town matters and sets one', async () => {
    serveBase()
    onApi('GET', '/api/belonging/of/40', {
      ...EMPTY,
      node: TOWN,
      identities: [
        {
          layer: 'people',
          value: FOLK,
          value_label: null,
          strength: 50,
          salience: 72,
          driver: 'invasion',
          updated_epoch: 6,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/held_identity:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BelongingSection nodeId={40} />)
    await expect
      .element(screen.getByText('People: Grimfolk', { exact: true }))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          'Matters 72 of 100 · moved by invasion · held at 50 · read in epoch 6'
        )
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/held_identity:set'))
      .toHaveLength(1)
  })

  it('shows a sheltered fugitive and keeps the law control with its reason off a realm', async () => {
    serveBase()
    onApi('GET', '/api/belonging/of/40', {
      ...EMPTY,
      node: TOWN,
      sanctuaries: [
        {
          id: 7,
          fugitive: ORLA,
          host: TOWN,
          kind: 'hospitality',
          fugitive_kind: 'outlaw',
          pursuer: REALM,
          state: 'besieged',
          fee: 2,
          granted_epoch: 5,
          siege_epochs: 1,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<BelongingSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Sanctuary/ }).click()
    await expect
      .element(screen.getByText('Orla in Grimsby', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Make the law' }))
      .toBeDisabled()
  })

  it('shows a jest of the court jester and tells a satire', async () => {
    serveBase()
    onApi('GET', '/api/belonging/of/50', {
      ...EMPTY,
      node: REALM,
      jester: PELL,
      satires: [
        {
          id: 3,
          satirist: PELL,
          target: ORLA,
          polity: REALM,
          work: null,
          source: 'jester',
          bite: 20,
          tolerated: true,
          punished: false,
          judged: true,
          epoch: 6,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/satire:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<BelongingSection nodeId={50} />)
    await screen.getByRole('tab', { name: /Satire and fools/ }).click()
    await expect
      .element(screen.getByText('Pell mocks Orla', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Tell it' }))
      .toBeDisabled()
  })
})
