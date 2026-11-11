import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CosmosCyclesSection } from './CosmosCyclesSection'
import { CyclesSection } from './CyclesSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 20, kind: 'entity' as const, name: 'Ashby' }
const REALM = { id: 30, kind: 'entity' as const, name: 'Varo' }
const KIN = { id: 60, kind: 'entity' as const, name: 'Kethrani' }
const GOD = { id: 70, kind: 'son' as const, name: 'Ithren' }

const EMPTY = {
  stress: null,
  readings: [],
  solidarity: null,
  challenges: [],
  plans: [],
  gifts: [],
  gift_balance: 0,
  debts: [],
  circuits: [],
  kinship: null,
  alliances: [],
  reproduction: null,
  caste: null,
  camp: null,
  confederations: [],
  legacies: [],
  indentures: [],
  market: null,
  manumissions: [],
}

const READINGS = [
  {
    epoch: 4,
    pressure: 20,
    immiseration: 30,
    elite_overproduction: 40,
    fiscal_distress: 20,
    psi: 31,
    phase: 'growth' as const,
  },
  {
    epoch: 5,
    pressure: 70,
    immiseration: 70,
    elite_overproduction: 80,
    fiscal_distress: 60,
    psi: 69,
    phase: 'crisis' as const,
  },
]

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 20, name: 'Ashby', type: 'settlement', world_id: 1 },
    { kind: 'entity', id: 30, name: 'Varo', type: 'polity', world_id: 1 },
    { kind: 'entity', id: 60, name: 'Kethrani', type: 'people', world_id: 1 },
    { kind: 'son', id: 70, name: 'Ithren', world_id: 1 },
  ])
}

describe('cycles, gifts, kin and bound labour', () => {
  beforeEach(() => resetApi())

  it('shows a realm in crisis with its secular cycle and tries it', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/30', {
      ...EMPTY,
      node: REALM,
      stress: {
        parts: [
          { component: 'population_pressure', value: 70 },
          { component: 'immiseration', value: 70 },
          { component: 'elite_overproduction', value: 80 },
          { component: 'fiscal_distress', value: 60 },
        ],
        psi: 69,
        aspirants: 300,
        positions: 100,
        challenge: 20,
        phase: 'crisis',
        updated_epoch: 5,
        locked: [],
      },
      readings: READINGS,
      challenges: [
        {
          id: 3,
          kind: 'plague',
          severity: 30,
          response: 'response',
          source: TOWN,
          epoch: 5,
        },
      ],
    })
    onApi('POST', '/api/actions/challenge:strike', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CyclesSection nodeId={30} />)
    await expect.element(screen.getByText('In crisis')).toBeVisible()
    await expect
      .element(screen.getByText('Elite overproduction').first())
      .toBeVisible()
    await expect.element(screen.getByText('Plague, severity 30')).toBeVisible()
    await screen.getByRole('button', { name: 'Try it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/challenge:strike'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/challenge:strike')[0].body).toEqual({
      polity_id: 30,
      kind: 'famine',
      severity: 30,
    })
  })

  it('answers a gift owed in the ledger', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/20', {
      ...EMPTY,
      node: TOWN,
      gifts: [
        {
          id: 9,
          giver: REALM,
          receiver: TOWN,
          value: 40,
          occasion: 'feast',
          item: null,
          state: 'open',
          answers_gift_id: null,
          due_epoch: 7,
          settled_epoch: null,
          epoch: 5,
          locked: [],
        },
      ],
      gift_balance: -40,
      debts: [
        {
          god: GOD,
          community: TOWN,
          offered: 60,
          answered: 10,
          last_offering_epoch: 5,
          last_answer_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/gift:return', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CyclesSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Gifts/ }).click()
    await expect
      .element(screen.getByText('A rank-claiming feast, worth 40'))
      .toBeVisible()
    await expect
      .element(screen.getByText('50 offered and unanswered'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Answer it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/gift:return'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/gift:return')[0].body).toEqual({
      gift_id: 9,
    })
  })

  it('shows a people’s ways of kin and sets them', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/60', {
      ...EMPTY,
      node: KIN,
      kinship: {
        descent: 'matrilineal',
        residence: 'avunculocal',
        descent_group: 'clan',
        cousin_terms: 'parallel_as_siblings',
        preference: 'cross_cousin',
        payment: 'bride_service',
        payment_value: 20,
        levirate: true,
        sororate: false,
        locked: [],
      },
      reproduction: {
        system: 'caste',
        change_age: 30,
        breeder_pct: 10,
        soldier_pct: 30,
        worker_pct: 60,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/kinship:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CyclesSection nodeId={60} />)
    await expect
      .element(screen.getByText('Matrilineal, through the female line'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Castes of workers, soldiers and breeders').first()
      )
      .toBeVisible()
    await screen.getByRole('button', { name: 'Set them' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/kinship:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/kinship:set')[0].body).toEqual({
      people_id: 60,
      descent: 'bilateral',
      residence: 'neolocal',
      preference: 'none',
      payment: 'none',
    })
  })

  it('reads the cycles of every realm', async () => {
    serveBase()
    onApi('GET', '/api/cycles/cosmos', {
      realms: [
        {
          polity: REALM,
          psi: 69,
          phase: 'crisis',
          challenge: 20,
          readings: READINGS,
        },
      ],
      frontiers: [
        {
          holder: KIN,
          value: 80,
          frontier: 2,
          conflict: 30,
          regions: [{ id: 5, kind: 'entity', name: 'Amberreach' }],
        },
      ],
      circuits: [],
      confederations: [],
      plans: [],
      gifts: [],
    })
    const { screen } = await renderApp(<CosmosCyclesSection />)
    await expect
      .element(screen.getByText('Realms by their stress (1)'))
      .toBeVisible()
    await expect
      .element(screen.getByText('On a meta-ethnic frontier'))
      .toBeVisible()
  })
})
