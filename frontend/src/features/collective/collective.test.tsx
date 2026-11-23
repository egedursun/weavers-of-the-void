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
import { ACCOUNT_KINDS, STANCES } from './labels'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 20, kind: 'entity' as const, name: 'Ashby' }
const REALM = { id: 30, kind: 'entity' as const, name: 'Varo' }
const KING = { id: 40, kind: 'entity' as const, name: 'Aldric' }

const DRAWING = {
  view_box: '7 5 106 122',
  outline: 'M10 8L110 8L110 62L60 124L10 62Z',
  layers: [
    {
      d: 'M10 8L110 8L110 62L60 124L10 62Z',
      ink: 'red' as const,
      filled: true,
      width: 0,
      opacity: 1,
      evenodd: false,
      clip: null,
      transform: null,
      clipped: true,
    },
  ],
}

const DESIGN = {
  shape: 'heater' as const,
  field: 'red' as const,
  division: 'chevron' as const,
  line: 'straight' as const,
  second: 'gold' as const,
  charge: 'sword' as const,
  charge_tincture: 'silver' as const,
  charge_two: 'none' as const,
  charge_two_tincture: null,
  charge_three: 'none' as const,
  charge_three_tincture: null,
  arrangement: 'two_and_one' as const,
  rim: 'line' as const,
  rim_line: 'straight' as const,
  rim_tincture: null,
  supporter: 'none' as const,
  supporter_pose: 'crossed' as const,
  supporter_tincture: null,
  crest: 'none' as const,
  crest_tincture: null,
}

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
    { kind: 'entity', id: 50, name: 'Gull', type: 'vessel', world_id: 1 },
    { kind: 'entity', id: 60, name: 'Ashfolk', type: 'people', world_id: 1 },
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
        feelings: [
          { feeling: 'anger', level: 80, held: true },
          { feeling: 'hope', level: 30, held: false },
        ],
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
          authenticity: 'genuine',
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
    await expect
      .element(screen.getByText('Rewrites an older account'))
      .toBeVisible()
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

  it('shows a lamenting song tied to a happening and ties it to another', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/30', {
      ...EMPTY,
      node: REALM,
      accounts: [
        {
          id: 12,
          holder: REALM,
          author: null,
          kind: 'song',
          medium: 'book',
          collection_id: null,
          collection_name: null,
          subject: KING,
          structure: null,
          artwork: null,
          fidelity: 50,
          credence: 70,
          distance: 20,
          revised_from_id: null,
          defaced: false,
          authenticity: 'genuine',
          epoch: 6,
          dated: 'the 4th year of the reign of Brannoc',
          happening: 'The flood of Ashby',
          stances: [{ node: KING, stance: 'lament' }],
          locked: [],
        },
      ],
    })
    onApi('GET', '/api/nodes/30/history', {
      node_id: 30,
      offset: 0,
      limit: 50,
      total_incidents: 1,
      incidents: [
        {
          incident_id: 77,
          kind: 'battle.fought',
          group: null,
          moment: null,
          roles: [],
          line: 'Varo fought at the ford.',
          place_id: null,
          place_name: null,
          tier: 'line',
          facts: 0,
        },
      ],
      total_steps: 0,
      steps: [],
      total_changes: 0,
      changes: [],
      kinds: [],
    })
    onApi('POST', '/api/actions/account:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={30} />)
    await expect
      .element(screen.getByText(ACCOUNT_KINDS.song.label, { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText(STANCES.lament.label, { exact: false }).first())
      .toBeVisible()
    await expect.element(screen.getByText('The flood of Ashby')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen.getByRole('combobox', { name: 'Happening it tells' }).click()
    await screen
      .getByRole('option', { name: 'Varo fought at the ford.' })
      .click()
    await screen
      .getByRole('button', { name: 'Hold these values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/account:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/account:edit')[0].body).toEqual({
      account_id: 12,
      values: { incident_id: 77 },
      release: [],
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
        ...DESIGN,
        field: 'blue',
        division: 'per_pale',
        second: 'silver',
        charge: 'tower',
        charge_tincture: 'gold',
        drawing: DRAWING,
        holder_kind: 'polity',
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
    await screen.getByRole('tab', { name: /Arms/ }).click()
    await expect
      .element(screen.getByText('Per pale azure and argent, a tower or'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('img', { name: 'Arms of Varo' }))
      .toBeVisible()
    await screen.getByRole('tab', { name: /Reckoning/ }).click()
    await expect
      .element(
        screen.getByText('It is the 10th year since the founding of Varo')
      )
      .toBeVisible()
  })

  it('casts the dice for a realm’s arms and grants what it drew', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/30', { ...EMPTY, node: REALM })
    onApi('GET', '/api/collective/arms-preview', {
      ...DESIGN,
      blazon: 'Azure, a star or',
      drawing: DRAWING,
    })
    onApi('GET', '/api/collective/arms-roll/30', {
      ...DESIGN,
      shape: 'kite',
      supporter: 'column',
      supporter_pose: 'flanking',
      blazon: 'Gules, a chevron or, a sword argent',
      drawing: DRAWING,
    })
    onApi('POST', '/api/actions/arms:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={30} />)
    await screen.getByRole('tab', { name: /Arms/ }).click()
    await expect
      .element(screen.getByRole('img', { name: 'The arms as drawn' }))
      .toBeVisible()
    await expect.element(screen.getByText('Azure, a star or')).toBeVisible()
    await screen.getByRole('button', { name: 'Cast the dice' }).click()
    await expect
      .element(screen.getByRole('combobox', { name: 'Shield shape' }))
      .toHaveTextContent('Kite shield')
    await screen.getByRole('button', { name: 'Grant them' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/arms:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/arms:set')[0].body).toMatchObject({
      holder_id: 30,
      holder_kind: 'polity',
      shape: 'kite',
      supporter: 'column',
      supporter_pose: 'flanking',
    })
  })

  it('reforges held arms at random through the arms editor', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/30', {
      ...EMPTY,
      node: REALM,
      arms: {
        ...DESIGN,
        drawing: DRAWING,
        holder_kind: 'polity',
        motto: null,
        parent: null,
        quartered: null,
        blazon: 'Gules, a chevron or, a sword argent',
        since_epoch: 2,
        locked: [],
      },
    })
    onApi('GET', '/api/collective/arms-roll/30', {
      ...DESIGN,
      rim: 'beaded',
      crest: 'crown',
      blazon: 'Gules, a chevron or, a sword argent, within a beaded rim or',
      drawing: DRAWING,
    })
    onApi('POST', '/api/actions/arms:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={30} />)
    await screen.getByRole('tab', { name: /Arms/ }).click()
    await screen.getByRole('button', { name: 'Reforge at random' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/arms:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/arms:edit')[0].body).toMatchObject({
      holder_id: 30,
      values: { rim: 'beaded', crest: 'crown', shape: 'heater' },
    })
  })

  it('sets and mends the wear of a part on the vessel in the drawer', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/50', {
      ...EMPTY,
      node: { id: 50, kind: 'entity', name: 'Gull' },
      vessel_design_id: 9,
      designs: [
        {
          id: 9,
          owner: REALM,
          kind: 'vessel',
          hull: 'cog',
          name: 'The Swift',
          designer: null,
          parent_design_id: null,
          mark: 1,
          mass: 40,
          speed: 30,
          range: 30,
          seaworthiness: 60,
          cargo: 50,
          armament: 10,
          crew: 20,
          obsolete: false,
          epoch: 3,
          vessels: 1,
          components: [
            {
              component: 'hull',
              material_id: null,
              material_name: null,
              size: 3,
              quality: 50,
              wear: null,
            },
          ],
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/component_wear:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={50} />)
    await expect
      .element(screen.getByRole('button', { name: 'Make it as good as new' }))
      .toBeDisabled()
    await screen.getByRole('spinbutton', { name: 'Wear' }).fill('35')
    await screen.getByRole('button', { name: 'Set the wear' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/component_wear:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/component_wear:set')[0].body).toEqual({
      vessel_id: 50,
      component: 'hull',
      wear: 35,
    })
  })

  it('keeps crowd controls for other things disabled with their reason', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/40', { ...EMPTY, node: KING })
    const { screen } = await renderApp(<CollectiveSection nodeId={40} />)
    await screen.getByRole('tab', { name: /Crowds/ }).click()
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
      ...DESIGN,
      drawing: DRAWING,
      holder_kind: 'polity',
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

  it('sets, holds and frees each crowd feeling', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', {
      ...EMPTY,
      node: TOWN,
      mood: {
        feelings: [
          { feeling: 'anger', level: 80, held: true },
          { feeling: 'hope', level: 30, held: false },
        ],
        deterrence: 30,
        agitation: 20,
        last_trigger: null,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/crowd_feeling:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await expect
      .element(screen.getByText('Hope', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Keep held' }))
      .toBeVisible()
    await screen.getByRole('spinbutton', { name: 'Set hope' }).fill('55')
    await screen.getByRole('button', { name: 'Set and hold' }).first().click()
    await screen.getByRole('button', { name: 'Set free' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/crowd_feeling:set'))
      .toHaveLength(2)
    expect(
      callsTo('POST', '/api/actions/crowd_feeling:set').map((call) => call.body)
    ).toEqual([
      { town_id: 20, feeling: 'hope', level: 55, hold: true },
      { town_id: 20, feeling: 'anger', level: 80, hold: false },
    ])
  })

  it('stirs a calm town with the one feeling chosen', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', { ...EMPTY, node: TOWN })
    onApi('POST', '/api/actions/crowd_mood:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await screen.getByRole('combobox', { name: 'Feeling' }).click()
    await screen.getByRole('option', { name: 'Grief' }).click()
    await screen.getByRole('button', { name: 'Stir the town' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/crowd_mood:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/crowd_mood:set')[0].body).toEqual({
      town_id: 20,
      feelings: { grief: 40 },
    })
  })

  it('counts the grown folk by sex kind and sets the balance of a town', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', {
      ...EMPTY,
      node: TOWN,
      sex_ratio: {
        counts: [
          { sex_kind: 'bearer', count: 400 },
          { sex_kind: 'begetter', count: 380 },
        ],
        begetters_per_hundred: 95,
        bereaved_partners: 12,
        locked: [],
      },
    })
    onApi('POST', '/api/actions/sex_ratio:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Generations/ }).click()
    await expect.element(screen.getByText('Bearers: 400')).toBeVisible()
    await expect.element(screen.getByText('Begetters: 380')).toBeVisible()
    await screen
      .getByRole('spinbutton', { name: 'Begetters per hundred bearers' })
      .last()
      .fill('90')
    await screen
      .getByRole('spinbutton', { name: 'Bereaved partners' })
      .last()
      .fill('30')
    await screen.getByRole('button', { name: 'Set the balance' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/sex_ratio:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/sex_ratio:set')[0].body).toEqual({
      community_id: 20,
      begetters_per_hundred: 90,
      bereaved_partners: 30,
    })
  })
  it('names who may hold a role by the bearing of young and decrees a role for a people', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/60', {
      ...EMPTY,
      node: { id: 60, kind: 'entity' as const, name: 'Ashfolk' },
      roles: [
        {
          role: 'combat',
          eligibility: 'begetters_preferred',
          min_age: 16,
          classes: [],
          stance: 'acceptable',
          since_epoch: 4,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/role_norm:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={60} />)
    await expect
      .element(screen.getByText('Fighting: those who beget young first'))
      .toBeVisible()
    await expect
      .element(screen.getByText('From age 16 · since epoch 4'))
      .toBeVisible()
    expect(screen.container.textContent).not.toContain('begetters_preferred')
    await screen.getByRole('combobox', { name: 'Who may' }).last().click()
    await screen
      .getByRole('option', { name: 'Those who bear young only' })
      .click()
    await screen.getByRole('button', { name: 'Decree it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/role_norm:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/role_norm:set')[0].body).toEqual({
      holder_id: 60,
      role: 'office',
      eligibility: 'bearers_only',
      min_age: 16,
      classes: [],
    })
  })

  it('keeps the role decree for a town disabled with its reason', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', { ...EMPTY, node: TOWN })
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Customs/ }).click()
    await expect
      .element(screen.getByRole('button', { name: 'Decree it' }))
      .toHaveAccessibleDescription('Only a people sets who may hold its roles')
  })

  it('shows what shaped a generation, a long season among it, and shapes it by contact', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', {
      ...EMPTY,
      node: TOWN,
      generations: [
        {
          generation_epoch: 3,
          formative: ['long_season', 'plague'],
          value_shifts: {},
          alive: 120,
          passed_epoch: null,
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/generation:shape', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Generations/ }).click()
    await expect
      .element(screen.getByText('The generation born from epoch 3'))
      .toBeVisible()
    await expect.element(screen.getByText('A long season')).toBeVisible()
    await expect.element(screen.getByText('A plague')).toBeVisible()
    await expect.element(screen.getByText('120 still living')).toBeVisible()
    await screen.getByRole('combobox', { name: 'Shaped also by' }).click()
    await screen.getByRole('option', { name: 'Contact' }).click()
    await screen.getByRole('button', { name: 'Shape it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/generation:shape'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/generation:shape')[0].body).toEqual({
      community_id: 20,
      generation_epoch: 3,
      formative: ['long_season', 'plague', 'contact'],
      axis: null,
      shift: 10,
    })
  })

  it('says no generation is recorded here', async () => {
    serveBase()
    onApi('GET', '/api/collective/of/20', { ...EMPTY, node: TOWN })
    const { screen } = await renderApp(<CollectiveSection nodeId={20} />)
    await screen.getByRole('tab', { name: /Generations/ }).click()
    await expect
      .element(screen.getByText('No generation is recorded here.'))
      .toBeVisible()
  })
})
