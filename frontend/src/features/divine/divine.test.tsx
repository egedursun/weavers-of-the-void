import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CouncilRulingsPanel } from './CouncilRulingsPanel'
import { CreatorDivinityPanel } from './CreatorDivinityPanel'
import { GodDivinitySection } from './GodDivinitySection'
import { LawProfileSection } from './LawProfileSection'
import { OuterProfileSection } from './OuterProfileSection'
import { RegardSection } from './RegardSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 7, kind: 'son', name: 'Ondra' }
const TOWN = { id: 30, kind: 'entity', name: 'Saltmouth' }
const STANDING = {
  community: TOWN,
  god: SON,
  awe: 40,
  love: 60,
  fear: 10,
  neglect: 5,
  epoch: 4,
  locked: [],
}

const DIVINITY = {
  god: SON,
  domains: [
    {
      domain: 'sea',
      label: 'Sea',
      activity: 'voyages',
      activity_label: 'Voyages',
      severed: false,
      hooks: [
        {
          hook: 'sea_calm',
          label: 'Calm seas',
          effect: 'Voyages lose fewer ships.',
          weight: 2,
          pct: 20,
          harmful: false,
        },
      ],
    },
    {
      domain: 'storm',
      label: 'Storm',
      activity: 'battles',
      activity_label: 'Battles',
      severed: true,
      hooks: [
        {
          hook: 'naval_might',
          label: 'Naval might',
          effect: 'Fleets strike harder.',
          weight: 2,
          pct: 20,
          harmful: false,
        },
      ],
    },
  ],
  synergy: {
    label: 'Storms strengthen the faithful fleets',
    hook: 'naval_might',
    hook_label: 'Naval might',
  },
  activity: [
    { epoch: 4, domain: 'sea', activity: 'voyages', count: 3, essence: 2 },
  ],
  goals: [
    {
      id: 11,
      kind: 'be_worshipped',
      label: 'Be worshipped',
      target: null,
      world: null,
      domain: null,
      amount: 5,
      progress: 40,
      state: 'active',
      source: 'engine',
      since_epoch: 3,
      closed_epoch: null,
      locked: [],
    },
  ],
  standing: [STANDING],
  wounds: [
    {
      id: 21,
      kind: 'severed_domain',
      label: 'Severed domain',
      domain: 'storm',
      severity: 50,
      healed: 20,
      cause: 'duel',
      cause_node: null,
      epoch: 3,
      locked: [],
    },
  ],
  avatars: [],
  goal_kinds: ['be_worshipped', 'rebel'],
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { id: 1, name: 'Aeron', essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 5 },
  })
  onApi('GET', '/api/names', [])
  onApi('GET', '/api/sons', [])
  onApi('GET', '/api/foreign-gods', [])
}

describe('the divine panels', () => {
  beforeEach(resetApi)

  it('shows a god’s domains, aims and wounds and heals a wound', async () => {
    serve()
    onApi('GET', '/api/gods/7/divinity', DIVINITY)
    onApi('POST', '/api/actions/divine_wound:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GodDivinitySection godId={7} />)
    await expect.element(screen.getByText('Calm seas')).toBeVisible()
    await expect
      .element(screen.getByText('Severed: its hooks are silent'))
      .toBeVisible()
    await expect
      .element(
        screen.getByText('Storms strengthen the faithful fleets (Naval might)')
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Give this aim' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Heal at once' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_wound:remove'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/divine_wound:remove')[0].body).toEqual(
      { wound_id: 21 }
    )
  })

  it('seals a pact between a son and a foreign god', async () => {
    serve()
    onApi('GET', '/api/foreign-gods', [{ id: 12, name: 'Veyth' }])
    onApi('GET', '/api/gods/7/divinity', DIVINITY)
    onApi('POST', '/api/actions/divine_pact:seal', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GodDivinitySection godId={7} />)
    await expect
      .element(screen.getByRole('button', { name: 'Seal the pact' }))
      .toBeDisabled()
    await screen.getByRole('combobox', { name: 'Foreign god' }).click()
    await screen.getByRole('option', { name: 'Veyth' }).click()
    await screen
      .getByRole('spinbutton', { name: 'Lasting epochs (empty for good)' })
      .fill('5')
    await screen.getByRole('button', { name: 'Seal the pact' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_pact:seal'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/divine_pact:seal')[0].body).toEqual({
      son_id: 7,
      god_id: 12,
      epochs: 5,
    })
  })

  it('shows the form a shattered god returns to and lets it be changed', async () => {
    serve()
    onApi('GET', '/api/gods/7/divinity', {
      ...DIVINITY,
      wounds: [
        {
          id: 22,
          kind: 'shattered_manifestation',
          label: 'Shattered manifestation',
          domain: null,
          severity: 40,
          healed: 10,
          cause: 'avatar_slain',
          cause_node: null,
          epoch: 4,
          prior_mode: 'concrete',
          locked: [],
        },
      ],
    })
    onApi('POST', '/api/actions/divine_wound:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GodDivinitySection godId={7} />)
    await expect
      .element(
        screen.getByText(
          'Its form is scattered; it returns to concrete when healed'
        )
      )
      .toBeVisible()
  })

  it('sets an aim aside and forgets a people’s regard', async () => {
    serve()
    onApi('GET', '/api/gods/7/divinity', DIVINITY)
    onApi('POST', '/api/actions/god_goal:drop', ACCEPTED_ACTION)
    const { screen } = await renderApp(<GodDivinitySection godId={7} />)
    await screen.getByRole('button', { name: 'Set aside' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/god_goal:drop'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/god_goal:drop')[0].body).toEqual({
      goal_id: 11,
    })
  })

  it('shows a community’s regard of the gods', async () => {
    serve()
    onApi('GET', '/api/entities/30/regard', {
      community: TOWN,
      standing: [STANDING],
    })
    onApi('POST', '/api/actions/divine_standing:clear', ACCEPTED_ACTION)
    const { screen } = await renderApp(<RegardSection communityId={30} />)
    await expect.element(screen.getByText('Ondra')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await screen.getByRole('button', { name: 'Forget this regard' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_standing:clear'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/divine_standing:clear')[0].body
    ).toEqual({ community_id: 30, god_id: 7 })
  })

  it('lifts a taboo of the Creator', async () => {
    serve()
    onApi('GET', '/api/creator/divinity', {
      taboos: [
        {
          act: 'torture',
          label: 'Torture',
          severity: 70,
          since_epoch: 2,
          broken: 1,
          last_broken_epoch: 4,
          last_breaker: null,
        },
      ],
      attention: [
        {
          world: { id: 2, kind: 'world', name: 'Aru' },
          attention: 10,
          watched: false,
          far: true,
          epoch: 4,
          locked: [],
        },
      ],
      standing: [],
      far_below: 20,
    })
    onApi('POST', '/api/actions/taboo:remove', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CreatorDivinityPanel creatorId={1} />)
    await expect
      .element(screen.getByText('Far from the eye', { exact: true }))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Lift' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/taboo:remove'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/taboo:remove')[0].body).toEqual({
      act: 'torture',
    })
  })

  it('strikes out a ruling of the council', async () => {
    serve()
    onApi('GET', '/api/council/rulings', {
      rulings: [
        {
          id: 5,
          motion: 'cosmic_truce',
          label: 'Set a cosmic truce',
          target: null,
          world: null,
          school: null,
          punishment: null,
          epoch: 3,
          until_epoch: 9,
          active: true,
          enacted: true,
          note: null,
          locked: [],
        },
      ],
      motions: ['cosmic_truce', 'punish_son'],
    })
    onApi('POST', '/api/actions/ruling:revoke', ACCEPTED_ACTION)
    const { screen } = await renderApp(<CouncilRulingsPanel />)
    await expect.element(screen.getByText('In force').first()).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Lay it down' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Strike out' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/ruling:revoke'))
      .toHaveLength(1)
  })

  it('shows a natural law’s working and an outer being’s hunger', async () => {
    serve()
    onApi('GET', '/api/entities/40/law-profile', {
      law: { id: 40, kind: 'entity', name: 'The Long Summer' },
      effect: 'bounty',
      effect_label: 'Bounty',
      effect_text: 'The fertility of every land rises each epoch.',
      scope: 'world',
      world: null,
      region: null,
      strength: 60,
      stability: 80,
      author: null,
      exception: 'none',
      contested: true,
      updated_epoch: 4,
      locked: [],
    })
    onApi('GET', '/api/entities/50/outer-profile', {
      being: { id: 50, kind: 'entity', name: 'The Far Listener' },
      hunger: 'names',
      hunger_label: 'Names',
      reach: 2,
      fed: 3,
      oppose_cost: 24,
      updated_epoch: 4,
      locked: [],
      breaches: [
        {
          id: 8,
          world: null,
          region: null,
          strength: 30,
          opened_epoch: 3,
          locked: [],
        },
      ],
      bargains: [],
    })
    onApi('POST', '/api/actions/breach:close', ACCEPTED_ACTION)
    const law = await renderApp(<LawProfileSection lawId={40} />)
    await expect
      .element(law.screen.getByText('Deadlocked with a contrary law'))
      .toBeVisible()
    const outer = await renderApp(<OuterProfileSection beingId={50} />)
    await expect
      .element(outer.screen.getByText('Reaches 2 lands'))
      .toBeVisible()
    await outer.screen.getByRole('button', { name: 'Seal' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/breach:close'))
      .toHaveLength(1)
  })
  it('names the dealer of a wound and asks for the mortal behind a mortal deed', async () => {
    serve()
    onApi('GET', '/api/gods/7/divinity', {
      ...DIVINITY,
      wounds: [
        {
          ...DIVINITY.wounds[0],
          kind: 'bound',
          label: 'Binding',
          domain: null,
          cause: 'mortal_slayer',
          cause_node: { id: 31, kind: 'entity', name: 'Vesk' },
        },
      ],
    })
    const { screen } = await renderApp(<GodDivinitySection godId={7} />)
    await expect
      .element(screen.getByText("From a mortal's deed, Vesk, epoch 3"))
      .toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Inflict the wound' }))
      .toHaveAccessibleDescription('Choose a wound')
  })

  it('shows a penance the council set and keeps its deed picker for penances', async () => {
    serve()
    onApi('GET', '/api/council/rulings', {
      rulings: [
        {
          id: 6,
          motion: 'punish_son',
          label: 'Punish a son',
          target: SON,
          world: null,
          school: null,
          punishment: 'penance',
          penance_deed: 'raise_hero',
          epoch: 3,
          until_epoch: 6,
          active: true,
          enacted: true,
          note: null,
          locked: [],
        },
      ],
      motions: ['punish_son'],
    })
    const { screen } = await renderApp(<CouncilRulingsPanel />)
    await expect.element(screen.getByText('Bind to a penance')).toBeVisible()
    await expect
      .element(screen.getByText('Penance: Raise a hero'))
      .toBeVisible()
    await expect
      .element(screen.getByRole('combobox', { name: 'Deed of penance' }))
      .toBeDisabled()
  })
})
