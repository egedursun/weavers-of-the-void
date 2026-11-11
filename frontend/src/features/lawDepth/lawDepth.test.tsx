import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LawDepthSection } from './LawDepthSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const REALM = { id: 30, kind: 'entity' as const, name: 'Varo' }
const MORTAL = { id: 40, kind: 'entity' as const, name: 'Ilse' }
const SPYMASTER = { id: 41, kind: 'entity' as const, name: 'Teodor' }

const EMPTY = {
  system: null,
  precedents: [],
  appeals: [],
  oracle_cases: [],
  registries: [],
  jurisdictions: [],
  pardons: [],
  outlaws: [],
  prison: null,
  prisons_here: [],
  prisoners: [],
  agents: [],
  cells: [],
  networks: [],
  hunts: [],
  defections: [],
  killings: [],
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
  ])
}

describe('law depth', () => {
  beforeEach(() => resetApi())

  it('shows a realm’s system, case law and outlaws and lifts an outlawry', async () => {
    serveBase()
    onApi('GET', '/api/law/of/30', {
      ...EMPTY,
      node: REALM,
      system: { system: 'precedent', since_epoch: 2, locked: [] },
      precedents: [
        {
          id: 5,
          crime: 'theft',
          verdict: 'guilty',
          court: 'high',
          case_id: 9,
          authority: 60,
          overturned: false,
          epoch: 3,
          locked: [],
        },
      ],
      outlaws: [
        {
          mortal: MORTAL,
          polity: REALM,
          bounty: 30,
          private_bounty: 5,
          renown: 12,
          declared_epoch: 4,
          locked: [],
        },
      ],
      hunts: [
        {
          id: 2,
          polity: REALM,
          spymaster: SPYMASTER,
          suspect: MORTAL,
          mole: false,
          outcome: 'purged',
          epoch: 5,
        },
      ],
    })
    onApi('POST', '/api/actions/outlaw:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LawDepthSection nodeId={30} />)
    await expect
      .element(screen.getByText('Case law', { exact: true }))
      .toBeVisible()
    await expect.element(screen.getByText('Theft: Guilty')).toBeVisible()
    await expect.element(screen.getByText('Purged the innocent')).toBeVisible()
    await screen.getByRole('button', { name: 'Lift the outlawry' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/outlaw:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/outlaw:delete')[0].body).toEqual({
      mortal_id: 40,
    })
  })

  it('answers an oracle trial for the god', async () => {
    serveBase()
    onApi('GET', '/api/law/of/30', {
      ...EMPTY,
      node: REALM,
      system: { system: 'oracle', since_epoch: 1, locked: [] },
      oracle_cases: [
        { case_id: 11, accused: MORTAL, crime: 'murder', oracle_answer: null },
      ],
    })
    onApi('POST', '/api/actions/oracle:answer', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LawDepthSection nodeId={30} />)
    await screen.getByRole('button', { name: 'Give the answer' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/oracle:answer'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/oracle:answer')[0].body).toEqual({
      case_id: 11,
      verdict: null,
    })
  })

  it('frees a prisoner', async () => {
    serveBase()
    onApi('GET', '/api/law/of/40', {
      ...EMPTY,
      node: MORTAL,
      prisoners: [
        {
          mortal: MORTAL,
          prison: { id: 70, kind: 'entity', name: 'The Keep' },
          case_id: null,
          term: 2,
          gang_rank: 30,
          since_epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/prisoner:free', ACCEPTED_ACTION)
    const { screen } = await renderApp(<LawDepthSection nodeId={40} />)
    await screen.getByRole('button', { name: 'Free' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/prisoner:free'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/prisoner:free')[0].body).toEqual({
      mortal_id: 40,
    })
  })

  it('draws a spy network with its cells and agents', async () => {
    serveBase()
    onApi('GET', '/api/law/of/30', {
      ...EMPTY,
      node: REALM,
      networks: [{ id: 4, owner: REALM, target: MORTAL }],
      cells: [
        {
          id: 9,
          network_id: 4,
          handler: MORTAL,
          safe_house: null,
          dead_drops: 2,
          locked: [],
        },
      ],
      agents: [
        {
          agent_id: 1,
          mortal: MORTAL,
          network_id: 4,
          motive: 'ideology',
          loyalty: 85,
          cell_id: 9,
        },
        {
          agent_id: 2,
          mortal: SPYMASTER,
          network_id: 4,
          motive: 'money',
          loyalty: 35,
          cell_id: null,
        },
      ],
    })
    const { screen } = await renderApp(<LawDepthSection nodeId={30} />)
    await expect
      .element(
        screen.getByRole('img', {
          name: 'Varo spying on Ilse: 1 cells and 2 agents',
        })
      )
      .toBeVisible()
  })

  it('says why the courts could not be read', async () => {
    serveBase()
    onApi('GET', '/api/law/of/30', failure(500, 'The heavens are silent.'))
    const { screen } = await renderApp(<LawDepthSection nodeId={30} />)
    await expect
      .element(screen.getByText('The courts could not be read'))
      .toBeVisible()
  })
})
