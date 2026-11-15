import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HonoursSection } from './HonoursSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const REALM = { id: 30, kind: 'entity' as const, name: 'Crown of Grimsby' }
const HOST = { id: 50, kind: 'entity' as const, name: 'First Host' }
const TOWN = { id: 40, kind: 'entity' as const, name: 'Grimsby' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    {
      kind: 'entity',
      id: 30,
      name: 'Crown of Grimsby',
      type: 'polity',
      world_id: 4,
    },
  ])
}

describe('standards and veterans', () => {
  beforeEach(() => resetApi())

  it('shows a named unit with its honours and sets a new honour on its standard', async () => {
    serveBase()
    onApi('GET', '/api/honours/of/50', {
      node: HOST,
      realm: REALM,
      units: [
        {
          id: 1,
          unit_id: 9,
          owner: REALM,
          name: 'The Ford Guard',
          nickname: null,
          raised_from: TOWN,
          esprit: 55,
          battles: 2,
          formed_epoch: 3,
          disbanded_epoch: null,
          honours: [
            {
              id: 4,
              kind: 'victory',
              note: 'the Ford of Reeds',
              epoch: 3,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
      choices: [{ id: 9, label: 'Line infantry', count: 80 }],
      grants: [],
    })
    onApi('POST', '/api/actions/unit_honour:create', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HonoursSection nodeId={50} />)
    await expect
      .element(screen.getByText('The Ford Guard', { exact: true }).first())
      .toBeVisible()
    await expect
      .element(screen.getByText('the Ford of Reeds, epoch 3'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/unit_honour:create'))
      .toHaveLength(1)
  })

  it('shows the pensions a realm granted its veterans', async () => {
    serveBase()
    onApi('GET', '/api/honours/of/30', {
      node: REALM,
      realm: REALM,
      units: [],
      choices: [],
      grants: [
        {
          id: 2,
          polity: REALM,
          kind: 'pension',
          veterans: 60,
          settlement: null,
          war: null,
          epoch: 4,
          locked: [],
        },
      ],
    })
    const { screen } = await renderApp(<HonoursSection nodeId={30} />)
    await expect
      .element(screen.getByText('Pensions for 60 veterans'))
      .toBeVisible()
  })
})
