import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OperationsSection } from './OperationsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const HOST = { id: 50, kind: 'entity' as const, name: 'Vale Host' }
const REALM = { id: 40, kind: 'entity' as const, name: 'Varo' }
const LAND = { id: 20, kind: 'entity' as const, name: 'Long Vale' }
const SCOUT = { id: 60, kind: 'entity' as const, name: 'Ilse' }

const EMPTY = {
  echelons: [],
  stacks: [],
  operation: null,
  flows: [],
  depots: [],
  transport: [],
  theatres: [],
  wars: [],
  admiralty: null,
  ship: null,
  crews: [],
  quirks: [],
  expeditions: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 50, name: 'Vale Host', type: 'army', world_id: 1 },
    { kind: 'entity', id: 40, name: 'Varo', type: 'polity', world_id: 1 },
    { kind: 'entity', id: 20, name: 'Long Vale', type: 'region', world_id: 1 },
    { kind: 'entity', id: 60, name: 'Ilse', type: 'mortal', world_id: 1 },
  ])
}

const BRIGADE = {
  id: 3,
  owner: REALM,
  army: HOST,
  parent_id: 1,
  level: 'brigade',
  name: 'Brigade 1 of Vale Host',
  commander: null,
  hq: LAND,
  staff: 20,
  command_range: 2,
  command_points: 3,
  points_spent: 0,
  order: 'standing',
  in_range: true,
  formed_epoch: 5,
  stacks: 1,
  locked: [],
}

describe('command, supply, ships and expeditions', () => {
  beforeEach(() => resetApi())

  it('draws an army’s order of battle, its supply and puts a stack under a brigade', async () => {
    serveBase()
    onApi('GET', '/api/operations/of/50', {
      ...EMPTY,
      node: HOST,
      echelons: [
        {
          ...BRIGADE,
          id: 1,
          parent_id: null,
          level: 'army',
          name: 'Vale Host',
          order: 'attack',
          command_points: 4,
          points_spent: 1,
          stacks: 0,
        },
        BRIGADE,
      ],
      stacks: [
        {
          id: 9,
          unit_kind: 'levy_infantry',
          count: 300,
          echelon_id: null,
          locked: [],
        },
      ],
      flows: [
        {
          id: 11,
          epoch: 6,
          season: 1,
          owner: REALM,
          army: HOST,
          depot_id: 2,
          produced: 120,
          shipped: 80,
          lost: 12,
          delivered: 72,
          need: 90,
          throughput: 80,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/echelon:assign', ACCEPTED_ACTION)
    const { screen } = await renderApp(<OperationsSection nodeId={50} />)
    const overview = screen.getByRole('list', { name: 'Order of battle' })
    await expect
      .element(overview.getByText('Brigade 1 of Vale Host'))
      .toBeVisible()
    await expect.element(overview.getByText('3 of 4 points left')).toBeVisible()
    await expect
      .element(
        screen
          .getByRole('group', { name: 'The order of battle' })
          .getByText('Brigade 1 of Vale Host')
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Command points left (3 of 4)'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Put it there' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/echelon:assign'))
      .toHaveLength(1)
    await screen.getByRole('tab', { name: /Supply and offensives/ }).click()
    await expect
      .element(screen.getByText('Delivered: 72 of 90 needed'))
      .toBeVisible()
  })

  it('reads a mortal’s expedition and leaves a quirk', async () => {
    serveBase()
    onApi('GET', '/api/operations/of/60', {
      ...EMPTY,
      node: SCOUT,
      expeditions: [
        {
          id: 4,
          name: 'Expedition of Ilse into Long Vale',
          leader: SCOUT,
          sponsor: null,
          target: LAND,
          ground: 'wilds',
          status: 'underway',
          legs_done: 1,
          legs_total: 4,
          provisions: 6,
          light: 0,
          tools: 2,
          medicine: 1,
          darkness: 0,
          danger: 20,
          found: 0,
          started_epoch: 6,
          ended_epoch: null,
          missing_roles: ['healer'],
          members: [
            {
              id: 8,
              mortal: SCOUT,
              role: 'scout',
              stress: 120,
              resolve: 'courageous',
              cold: 10,
              wet: 0,
              hunger: 0,
              fatigue: 30,
              fallen: false,
              locked: [],
            },
          ],
          log: [
            {
              id: 21,
              epoch: 6,
              leg: 1,
              event: 'virtue',
              member: SCOUT,
              provisions_used: 0,
              light_used: 0,
              stress: 120,
              resolve: 'courageous',
              quirk: null,
              locked: [],
            },
          ],
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/quirk:create', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/expedition:advance', ACCEPTED_ACTION)
    const { screen } = await renderApp(<OperationsSection nodeId={60} />)
    await expect
      .element(screen.getByText('Expedition of Ilse into Long Vale'))
      .toBeVisible()
    await expect.element(screen.getByText('No healer')).toBeVisible()
    await expect.element(screen.getByText('Virtue: Ilse')).toBeVisible()
    await screen.getByRole('button', { name: 'Press on a leg' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/expedition:advance'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Leave it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/quirk:create'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/quirk:create')[0].body).toEqual({
      mortal_id: 60,
      kind: 'hardy',
      source_id: null,
    })
  })
})
