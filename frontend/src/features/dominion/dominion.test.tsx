import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DominionSection } from './DominionSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const SON = { id: 7, kind: 'son' as const, name: 'Thalen' }
const VALE = { id: 30, kind: 'entity' as const, name: 'Low Vale' }
const WORLD = { id: 2, kind: 'world' as const, name: 'Orun' }
const BEAST = { id: 60, kind: 'entity' as const, name: 'Harrow' }

const CLAIM = {
  god: SON,
  region: VALE,
  strength: 64,
  temples: 20,
  holy_sites: 10,
  prophets: 0,
  miracles: 4,
  worship: 30,
  spread: 0,
  epoch: 5,
  ruling: true,
  locked: [],
}

const THRONE = {
  id: 3,
  world: WORLD,
  place: VALE,
  power: 70,
  holder: SON,
  since_epoch: 4,
  locked: [],
}

const SITE = {
  id: 9,
  place: VALE,
  kind: 'gateway' as const,
  school: 'life' as const,
  strength: 55,
  found_epoch: null,
  found_by: null,
  holder: null,
  output: 0,
  target_world: null,
  locked: [],
}

const CREATURE = {
  creature: BEAST,
  god: SON,
  weights: [
    { deed: 'heal_sick' as const, weight: 140 },
    { deed: 'hunt_folk' as const, weight: 60 },
  ],
  hunger: 30,
  neglect_epochs: 1,
  last_deed: 'heal_sick' as const,
  deeds: 3,
  since_epoch: 2,
  lessons: [
    {
      id: 1,
      deed: 'heal_sick' as const,
      lesson: 'reward' as const,
      strength: 20,
      epoch: 4,
    },
  ],
  locked: [],
}

const SCALES = (
  ['order', 'productivity', 'heat', 'growth', 'fortune', 'magic'] as const
).map((scale) => ({
  scale,
  value: scale === 'order' ? -2 : 0,
  stored: scale === 'order',
  locked: scale === 'order' ? ['value'] : [],
}))

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

describe('dominion', () => {
  beforeEach(() => resetApi())

  it('shows a god’s dominion, scales, design, image, creatures and thrones and leans a scale', async () => {
    serveBase()
    onApi('GET', '/api/dominion/of/7', {
      node: SON,
      claims: [CLAIM],
      scales: SCALES,
      design: {
        budget: 60,
        spent: 45,
        dominion_strength: 50,
        magic_aptitude: 40,
        manifestation_strength: 30,
        stats_pct: 80,
        rank: 1,
        checked_epoch: 5,
        locked: [],
      },
      image: {
        believed_alignment: 'malevolent',
        believed_wrath: 80,
        believed_mercy: 20,
        believed_domain: 'storm',
        manifestation: 'dreadful',
        intensity: 70,
        worship_share: 60,
        crisis: 30,
        malleability: 40,
        pull: 6,
        domain_pressure: 20,
        stance: 'resist',
        epoch: 5,
        locked: [],
      },
      miracles: [
        {
          id: 4,
          god: SON,
          kind: 'heal',
          epoch: 5,
          target: BEAST,
          region: VALE,
          magnitude: 60,
          witnesses: 40,
          need: 50,
          novelty: 100,
          legibility: 100,
          belief: 22,
          credited: SON,
          locked: [],
        },
      ],
      credited: [],
      creatures: [CREATURE],
      thrones: [THRONE],
      sites: [],
    })
    onApi('POST', '/api/actions/god_scale:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/divine_creature:teach', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DominionSection nodeId={7} />)
    await expect.element(screen.getByText('Low Vale').first()).toBeVisible()
    await expect.element(screen.getByText('Turmoil 2')).toBeVisible()
    await expect.element(screen.getByText('Malevolent').first()).toBeVisible()
    await expect.element(screen.getByText('Resists belief')).toBeVisible()
    await expect.element(screen.getByText('Harrow').first()).toBeVisible()
    await expect
      .element(screen.getByText('80% of their full measure'))
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Lean turmoil toward order' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/god_scale:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/god_scale:set')[0].body).toEqual({
      god_id: 7,
      scale: 'order',
      value: -1,
      hold: true,
    })
    await screen.getByRole('button', { name: 'Reward' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_creature:teach'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/divine_creature:teach')[0].body
    ).toEqual({ creature_id: 60, deed: 'heal_sick', lesson: 'reward' })
  })

  it('shows the thrones and hidden sites of a place and reveals a site', async () => {
    serveBase()
    onApi('GET', '/api/dominion/of/30', {
      node: VALE,
      claims: [],
      scales: SCALES,
      design: null,
      image: null,
      miracles: [],
      credited: [],
      creatures: [],
      thrones: [],
      sites: [],
    })
    onApi('GET', '/api/dominion/place/30', {
      place: VALE,
      rule: { region: VALE, god: SON, share: 80, rivals: 1, epoch: 5 },
      claims: [CLAIM],
      thrones: [THRONE],
      sites: [SITE],
      creatures: [],
    })
    onApi('POST', '/api/actions/magic_site:reveal', ACCEPTED_ACTION)
    const { screen } = await renderApp(<DominionSection nodeId={30} />)
    await expect.element(screen.getByText('Gateway of Life')).toBeVisible()
    await expect.element(screen.getByText('Still hidden')).toBeVisible()
    await expect.element(screen.getByText('80%')).toBeVisible()
    await screen.getByRole('button', { name: 'Reveal it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/magic_site:reveal'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/magic_site:reveal')[0].body).toEqual({
      site_id: 9,
      finder_id: null,
    })
  })

  it('lists who rules the lands of a world', async () => {
    serveBase()
    onApi('GET', '/api/dominion/of/2', {
      node: WORLD,
      claims: [],
      scales: SCALES,
      design: null,
      image: null,
      miracles: [],
      credited: [],
      creatures: [],
      thrones: [],
      sites: [],
    })
    onApi('GET', '/api/dominion/world/2', {
      world: WORLD,
      rules: [{ region: VALE, god: SON, share: 80, rivals: 0, epoch: 5 }],
      thrones: [THRONE],
      sites: [],
    })
    const { screen } = await renderApp(<DominionSection nodeId={2} />)
    await expect.element(screen.getByText('Who rules which land')).toBeVisible()
    await expect.element(screen.getByText('1 of 1')).toBeVisible()
  })

  it('says why the dominion could not be read', async () => {
    serveBase()
    onApi('GET', '/api/dominion/of/7', failure(500, 'The heavens are silent.'))
    const { screen } = await renderApp(<DominionSection nodeId={7} />)
    await expect
      .element(screen.getByText('The dominion could not be read'))
      .toBeVisible()
  })
})
