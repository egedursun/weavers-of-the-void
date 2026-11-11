import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ArmsCrest } from './ArmsCrest'
import { CollectiveSection } from './CollectiveSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 20, kind: 'entity' as const, name: 'Ashby' }
const REALM = { id: 30, kind: 'entity' as const, name: 'Varo' }
const KING = { id: 40, kind: 'entity' as const, name: 'Aldric' }

const EMPTY = {
  mood: null,
  cascades: [],
  mobs: [],
  movements: [],
  accounts: [],
  strikes: [],
  myth: null,
  commemorations: [],
  lost_lands: [],
  storylets: [],
  norms: [],
  norm_changes: [],
  biases: null,
  lessons: [],
  generations: [],
  diasporas: [],
  transition: null,
  sex_ratio: null,
  roles: [],
  dating: null,
  arms: null,
  designs: [],
  vessel_design_id: null,
  materials: [],
}

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
    { kind: 'entity', id: 40, name: 'Aldric', type: 'mortal', world_id: 1 },
  ])
  onApi('GET', '/api/collective/storylets', [
    {
      storylet: 'hoarded_store',
      title: 'The hoarded store',
      chooser: 'ruler',
      roles: ['town', 'ruler', 'realm'],
      weight: 10,
      steps: [
        {
          text: '{town} is short of food.',
          choices: ['Open the stores to all'],
        },
      ],
    },
  ])
  onApi('GET', '/api/histories', { items: [], total: 0 })
}

describe('crowds, memory, customs and craft', () => {
  beforeEach(() => resetApi())

  it('shows a town’s mood and a raging crowd and disperses it', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', {
      ...EMPTY,
      node: TOWN,
      mood: {
        anger: 80,
        anxiety: 10,
        fervour: 5,
        deterrence: 30,
        agitation: 20,
        last_trigger: 'famine',
        locked: [],
      },
      cascades: [
        {
          id: 3,
          district_name: 'market',
          trigger: 'famine',
          act: 'riot',
          participants: 300,
          share: 40,
          outcome: 'mob',
          deaths: 2,
          fled: 0,
          epoch: 5,
        },
      ],
      mobs: [
        {
          id: 7,
          act: 'riot',
          size: 300,
          anger: 70,
          target: 'granary',
          target_node: null,
          leader: KING,
          status: 'rampaging',
          ended_by: null,
          damage: 14,
          since_epoch: 5,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/mob:disperse', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await expect.element(screen.getByText('The mood of the town')).toBeVisible()
    await expect
      .element(screen.getByText('Last stirred by hunger'))
      .toBeVisible()
    await expect.element(screen.getByText('Riot over hunger')).toBeVisible()
    await screen.getByRole('button', { name: 'Disperse it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/mob:disperse'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/mob:disperse')[0].body).toEqual({
      mob_id: 7,
      by: 'concession',
    })
  })

  it('shows a rewritten account and exposes the older one', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/30', {
      ...EMPTY,
      node: REALM,
      accounts: [
        {
          id: 12,
          holder: REALM,
          author: KING,
          kind: 'official_chronicle',
          medium: 'book',
          collection_id: 4,
          collection_name: 'The crowning of Aldric',
          subject: null,
          structure: null,
          artwork: null,
          fidelity: 40,
          credence: 60,
          distance: 68,
          revised_from_id: 9,
          defaced: false,
          epoch: 6,
          dated: 'the 2nd year of the reign of Brannoc',
          stances: [{ node: KING, stance: 'vilify' }],
          locked: [],
        },
      ],
      strikes: [
        { node: KING, by: REALM, active: true, since_epoch: 6, locked: [] },
      ],
    })
    onApi('POST', '/api/actions/account:expose', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={30} />)
    await expect
      .element(screen.getByText('Official chronicle: The crowning of Aldric'))
      .toBeVisible()
    await expect.element(screen.getByText('Rewrites account 9')).toBeVisible()
    await expect
      .element(screen.getByText('Varo struck Aldric from memory'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Expose the older account' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/account:expose'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/account:expose')[0].body).toEqual({
      account_id: 12,
    })
  })

  it('makes a storylet’s choice for its chooser', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/40', {
      ...EMPTY,
      node: KING,
      storylets: [
        {
          id: 5,
          storylet: 'hoarded_store',
          title: 'The hoarded store',
          world_id: 1,
          cast: [{ role: 'ruler', node: KING }],
          status: 'open',
          chooser: KING,
          choice: null,
          step: 0,
          situation:
            'Ashby is short of food while its stores are kept under the hand of Aldric.',
          choices: [
            { index: 0, text: 'Open the stores to all' },
            { index: 1, text: 'Sell the stores at a high price' },
          ],
          follows_run_id: null,
          collection_id: 8,
          due_epoch: 8,
          opened_epoch: 6,
          resolved_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/storylet:choose', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={40} />)
    await expect
      .element(
        screen.getByText(
          'Ashby is short of food while its stores are kept under the hand of Aldric.'
        )
      )
      .toBeVisible()
    await screen
      .getByRole('button', { name: '2. Sell the stores at a high price' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/storylet:choose'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/storylet:choose')[0].body).toEqual({
      run_id: 5,
      choice: 1,
    })
  })

  it('draws a realm’s arms and its dating', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/30', {
      ...EMPTY,
      node: REALM,
      arms: {
        holder_kind: 'polity',
        field: 'blue',
        division: 'per_pale',
        second: 'silver',
        charge: 'tower',
        charge_tincture: 'gold',
        motto: 'Steady',
        parent: null,
        quartered: null,
        blazon: 'Per pale azure and argent, a tower or',
        since_epoch: 2,
        locked: [],
      },
      dating: {
        kind: 'founding',
        anchor_year: 100,
        label: REALM,
        cycle_years: 60,
        reformed_epoch: null,
        since_epoch: 1,
        today: 'the 10th year since the founding of Varo',
        locked: [],
      },
    })
    const { screen } = await renderApp(<CollectiveSection nodeId={30} />)
    await expect
      .element(screen.getByText('Per pale azure and argent, a tower or'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Arms of Varo' }))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('It is the 10th year since the founding of Varo')
      )
      .toBeVisible()
  })

  it('keeps crowd controls for other things disabled with their reason', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/40', { ...EMPTY, node: KING })
    const { screen } = await renderApp(<CollectiveSection nodeId={40} />)
    await expect
      .element(screen.getByRole('button', { name: 'Raise it' }).first())
      .toBeDisabled()
    await expect
      .element(
        screen.getByText(
          'Crowds gather only in towns; choose a settlement to raise one.'
        )
      )
      .toBeVisible()
  })

  it('says so when the section cannot be read', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/40', failure(500, 'boom'))
    const { screen } = await renderApp(<CollectiveSection nodeId={40} />)
    await expect
      .element(screen.getByText('This could not be read'))
      .toBeVisible()
  })

  it('shows a record’s arms beside its portrait and opens them', async () => {
    serveBase()
    onApi('GET', '/api/collective/arms/30', {
      holder_kind: 'polity',
      field: 'red',
      division: 'chevron',
      second: 'gold',
      charge: 'sword',
      charge_tincture: 'silver',
      motto: 'First into the breach',
      parent: null,
      quartered: null,
      blazon: 'Chevron gules and or, a sword argent',
      since_epoch: 3,
      locked: [],
    })
    const { screen } = await renderApp(<ArmsCrest nodeId={30} name='Varo' />)
    await screen
      .getByRole('button', {
        name: 'Arms of Varo: Chevron gules and or, a sword argent',
      })
      .click()
    await expect
      .element(screen.getByText('First into the breach'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Arms of Varo, drawn large' }))
      .toBeVisible()
  })

  it('draws no crest for a record without arms', async () => {
    serveBase()
    onApi('GET', '/api/collective/arms/40', null)
    const { screen } = await renderApp(
      <div>
        <ArmsCrest nodeId={40} name='Aldric' />
        <span>hero</span>
      </div>
    )
    await expect.element(screen.getByText('hero')).toBeVisible()
    expect(screen.getByRole('img').elements()).toHaveLength(0)
  })
})
