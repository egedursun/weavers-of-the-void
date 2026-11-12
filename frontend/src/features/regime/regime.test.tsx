import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CosmosRegimeSection } from './CosmosRegimeSection'
import { RegimeSection } from './RegimeSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const REALM = { id: 30, kind: 'entity' as const, name: 'Varo' }
const LORD = { id: 40, kind: 'entity' as const, name: 'Ilse' }
const HALL = { id: 50, kind: 'entity' as const, name: 'Hall of Records' }

const EMPTY = {
  regime: null,
  members: [],
  ties: [],
  seats: [],
  offices: [],
  power_base: null,
  bases: [],
  lineage: null,
  kin_lines: [],
  breeding: [],
  examination: null,
  sittings: [],
  credentials: [],
  freedom: null,
  schools: [],
}

const REGIME = {
  selectorate: 'nobles' as const,
  selectorate_size: 400,
  coalition_size: 32,
  coalition_loyalty: 55,
  public_share: 35,
  traditional: 60,
  charismatic: 20,
  rational: 10,
  dominant: 'traditional' as const,
  founder: LORD,
  ruler: LORD,
  routinisation: 'pending' as const,
  crisis_epoch: 5,
  horizon: 30,
  extraction: 130,
  institutions: 25,
  leadership: 'state' as const,
  rotation: true,
  parallel_guard: false,
  loyalty_promotion: false,
  hostages: false,
  updated_epoch: 6,
  locked: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 30, name: 'Varo', type: 'polity', world_id: 1 },
    { kind: 'entity', id: 40, name: 'Ilse', type: 'mortal', world_id: 1 },
    {
      kind: 'entity',
      id: 50,
      name: 'Hall of Records',
      type: 'structure',
      world_id: 1,
    },
  ])
}

describe('rule, patronage, lines and learning', () => {
  beforeEach(() => resetApi())

  it('shows how a realm is ruled and holds its examinations', async () => {
    serveBase()
    onApi('GET', '/api/regime/of/30', {
      ...EMPTY,
      node: REALM,
      regime: REGIME,
      members: [
        {
          polity: REALM,
          mortal: LORD,
          reward: 20,
          loyalty: 40,
          since_epoch: 2,
          locked: [],
        },
      ],
      examination: {
        interval: 2,
        quota: 20,
        pass_mark: 50,
        demand: 40,
        last_epoch: 4,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/coalition:purge', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/examination:sit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RegimeSection nodeId={30} />)
    await expect.element(screen.getByText('Chosen by the nobles')).toBeVisible()
    await expect
      .element(screen.getByText("In crisis over the founder's legacy"))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Purge them' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/coalition:purge'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/coalition:purge')[0].body).toEqual({
      polity_id: 30,
      mortal_id: 40,
    })
    await screen.getByRole('tab', { name: /Learning/ }).click()
    await expect
      .element(screen.getByText('Examinations every 2 epochs'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Hold them now' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/examination:sit'))
      .toHaveLength(1)
  })

  it('sets the freedom of a house of learning', async () => {
    serveBase()
    onApi('GET', '/api/regime/of/50', {
      ...EMPTY,
      node: HALL,
      freedom: {
        structure: HALL,
        level: 20,
        orthodoxy: REALM,
        suppressed: true,
        updated_epoch: 6,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/academic_freedom:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RegimeSection nodeId={50} />)
    await expect
      .element(screen.getByText('Learning is suppressed at Hall of Records'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/academic_freedom:set'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/academic_freedom:set')[0].body
    ).toEqual({
      structure_id: 50,
      level: 60,
    })
  })

  it('reads how every realm is ruled and taught', async () => {
    serveBase()
    onApi('GET', '/api/regime/cosmos', {
      realms: [
        {
          polity: REALM,
          selectorate: 'nobles',
          selectorate_size: 400,
          coalition_size: 32,
          public_share: 35,
          horizon: 30,
          dominant: 'traditional',
          routinisation: 'schism',
          leadership: 'state',
        },
      ],
      bases: [],
      freedoms: [],
      schools: [],
      sittings: [],
    })
    const { screen } = await renderApp(<CosmosRegimeSection />)
    await expect
      .element(screen.getByText('Realms by their rule (1)'))
      .toBeVisible()
    await expect.element(screen.getByText('Split by schism')).toBeVisible()
  })
})
