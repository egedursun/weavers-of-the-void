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
          circuit_id: null,
          owed: true,
          owed_back: 40,
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

  it('releases a debt and shows a gift answered with more', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/20', {
      ...EMPTY,
      node: TOWN,
      gifts: [
        {
          id: 11,
          giver: TOWN,
          receiver: REALM,
          value: 30,
          occasion: 'amends',
          item: null,
          state: 'open',
          answers_gift_id: null,
          circuit_id: null,
          owed: true,
          owed_back: 15,
          due_epoch: 8,
          settled_epoch: null,
          epoch: 6,
          locked: [],
        },
        {
          id: 12,
          giver: REALM,
          receiver: TOWN,
          value: 20,
          occasion: 'hospitality',
          item: null,
          state: 'exceeded',
          answers_gift_id: null,
          circuit_id: null,
          owed: false,
          owed_back: 20,
          due_epoch: null,
          settled_epoch: 6,
          epoch: 5,
          locked: [],
        },
      ],
      gift_balance: 15,
    })
    onApi('POST', '/api/actions/gift:release', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CyclesSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Gifts/ }).click()
    await expect
      .element(screen.getByText('Amends for a wrong, worth 30'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Answered with more, the giver now owes'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Release the debt' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/gift:release'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/gift:release')[0].body).toEqual({
      gift_id: 11,
    })
  })

  it('shows a people’s ways of kin and sets them', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/60', {
      ...EMPTY,
      node: KIN,
      kinship: {
        descent: 'through_second_line',
        residence: 'with_kin_of_the_first_line',
        descent_group: 'clan',
        kin_terms: 'bifurcate_merging',
        adoption: 'heir',
        first_side: 'bearer',
        sibling_union_first: true,
        sibling_union_second: false,
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
      .element(screen.getByText('Through the second line'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Castes of workers, soldiers and breeders').first()
      )
      .toBeVisible()
    await expect
      .element(screen.getByText('Adopted as heirs').first())
      .toBeVisible()
    const set = screen.getByRole('button', { name: 'Set them' })
    await expect.element(set).toHaveAttribute('aria-disabled', 'true')
    await screen.getByRole('combobox', { name: 'Which side is first' }).click()
    await screen
      .getByRole('option', { name: 'The begetting side is first' })
      .click()
    await set.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/kinship:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/kinship:set')[0].body).toEqual({
      people_id: 60,
      descent: 'bilateral',
      residence: 'new_household',
      kin_terms: 'lineal',
      adoption: 'foster',
      first_side: 'begetter',
    })
  })

  it('shows a people’s customs of union and reads them anew', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/60', {
      ...EMPTY,
      node: KIN,
      union: {
        form: 'plural',
        plural_side: 'second',
        purpose: 'alliance',
        residence: 'new_household',
        descent: 'through_first',
        exchange: 'service',
        exchange_value: 15,
        arrangement: 'both_consent',
        dissolution: 'by_court',
        endogamy: 'none',
        exogamy: 'moiety',
        kin_match: 'cross_cousin',
        term_epochs: 0,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/union:delete', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/union:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CyclesSection nodeId={60} />)
    await expect
      .element(screen.getByText('Several partners: the second side'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText(
          "The joining partner serves the other's family, worth 15"
        )
      )
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Partners come from another half of the people')
      )
      .toBeVisible()
    await expect
      .element(screen.getByText("A child of a parent's other-side sibling"))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Read anew from their ways' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/union:delete'))
      .toHaveLength(1)
    await screen
      .getByRole('button', { name: 'Set their customs of union' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/union:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/union:set')[0].body).toMatchObject({
      people_id: 60,
      form: 'pair',
      plural_side: 'either',
      exchange: 'none',
      exchange_value: 10,
      kin_match: 'none',
    })
  })

  it('shows the bonds of newcomers and the standing of the freed', async () => {
    serveBase()
    onApi('GET', '/api/cycles/of/20', {
      ...EMPTY,
      node: TOWN,
      indentures: [
        {
          id: 4,
          employer: null,
          regime: 'indenture',
          count: 20,
          term_epochs: 3,
          debt: 100,
          exploitation: 45,
          origin: KIN,
          since_epoch: 5,
          locked: [],
        },
      ],
      manumissions: [
        {
          id: 8,
          count: 30,
          path: 'purchase',
          standing: 40,
          origin: KIN,
          epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/manumission:free', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CyclesSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Bound labour/ }).click()
    await expect
      .element(screen.getByText('30 freed, bought their freedom'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Epoch 5 · standing 40'))
      .toBeVisible()
    await expect
      .element(screen.getByText('Standing among the free').first())
      .toBeVisible()
    await expect.element(screen.getByText('Kethrani').first()).toBeVisible()
    await screen.getByRole('button', { name: 'Free them' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/manumission:free'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/manumission:free')[0].body).toEqual({
      community_id: 20,
      share_pct: 50,
      path: 'law',
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
