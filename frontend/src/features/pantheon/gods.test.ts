import { describe, expect, it } from 'vitest'
import { type components } from '@/api/generated/schema'
import { councilFrequencyText } from '@/features/council/frequency'
import { attitudeBand } from '@/features/foreign-god/attitude'
import { sonHints } from '@/features/son/hints'
import { doomTone } from './doom'
import { worldIdOf } from './fateChoice'
import { humanize, plural, romanNumeral, verbFor } from './labels'
import { opportunitiesOf } from './opportunities'
import { relationLabel, signed } from './relations'
import {
  fadingLeft,
  sortSons,
  starText,
  statusChips,
  xpNeeded,
} from './sonFacts'

type SonPublic = components['schemas']['SonPublic']
type PlayerHints = components['schemas']['PlayerHints']

const RULES: Record<string, number> = {
  'core_rules.relation_sibling': 75,
  'core_rules.relation_close_friend': 45,
  'core_rules.relation_friend': 15,
  'core_rules.relation_cold': 10,
  'core_rules.relation_enemy': 35,
  'core_rules.relation_blood_enemy': 70,
}

const rule = (path: string) => RULES[path]

function view(id: number, patch: Partial<SonPublic['son']>): SonPublic {
  return {
    son: {
      id,
      name: `Son ${id}`,
      rarity: 'rare',
      stars: 1,
      status: 'active',
      chained: false,
      rebel: false,
      fading_epochs: 0,
      existence: 50,
      sleep_epochs_left: 0,
      death_epoch: null,
      ...patch,
    } as SonPublic['son'],
  } as SonPublic
}

const HINTS: PlayerHints = {
  creator: {
    unanswered_prayers: 0,
    unclaimed: [],
    rebel_sons: ['Kharun'],
    fading_sons: [{ name: 'Kharun', existence: 8 }],
    doom: 40,
    doom_threshold: 100,
    godless_worlds: ['Glass'],
    stale_threads: 1,
    essence: 10,
  },
  sons_waiting: ['Thalassir'],
  sons_without_orders: ['Thalassir', 'Mirel'],
  sleeping_sons: [],
  dead_sons: [],
  open_threads: 0,
  sons_without_image: 0,
  unread_notifications: 0,
  epoch_in_progress: false,
}

describe('relations', () => {
  it('labels relations by the rule bands', () => {
    expect(relationLabel(80, rule)).toBe('Kinship')
    expect(relationLabel(50, rule)).toBe('Close friendship')
    expect(relationLabel(20, rule)).toBe('Friendship')
    expect(relationLabel(0, rule)).toBe('Distance')
    expect(relationLabel(-12, rule)).toBe('Coldness')
    expect(relationLabel(-40, rule)).toBe('Enmity')
    expect(relationLabel(-90, rule)).toBe('Blood enmity')
    expect(relationLabel(90, () => undefined)).toBe('Distance')
    expect(signed(5)).toBe('+5')
    expect(signed(-5)).toBe('-5')
  })
})

describe('son facts', () => {
  it('sorts by rarity, then stars, then id', () => {
    const sorted = sortSons([
      view(3, { rarity: 'rare', stars: 1 }),
      view(1, { rarity: 'mythic', stars: 0 }),
      view(2, { rarity: 'rare', stars: 4 }),
      view(4, { rarity: 'rare', stars: 1 }),
    ])
    expect(sorted.map((item) => item.son.id)).toEqual([1, 2, 3, 4])
  })

  it('builds status chips for each state', () => {
    expect(statusChips(view(1, {}), true, 3).map((chip) => chip.key)).toEqual([
      'ready',
    ])
    expect(statusChips(view(1, {}), false, 3).map((chip) => chip.key)).toEqual([
      'acted',
    ])
    expect(
      statusChips(
        view(1, { rebel: true, chained: true, fading_epochs: 1 }),
        true,
        3
      ).map((chip) => chip.key)
    ).toEqual(['chained', 'rebel', 'fading'])
    expect(
      statusChips(view(1, { status: 'dead', death_epoch: 4 }), true, 3)
    ).toEqual([
      { key: 'dead', label: 'Died · Epoch 4', variant: 'destructive' },
    ])
    expect(
      statusChips(
        view(1, { status: 'asleep', sleep_epochs_left: 2 }),
        false,
        3
      )[0].label
    ).toBe('Asleep · 2 epochs')
  })

  it('computes fading, stars and experience', () => {
    expect(fadingLeft(view(1, { fading_epochs: 1 }).son, 3)).toBe(2)
    expect(fadingLeft(view(1, { fading_epochs: 1 }).son, undefined)).toBeNull()
    expect(fadingLeft(view(1, {}).son, 3)).toBeNull()
    expect(starText(3)).toBe('★★★')
    expect(starText(0)).toBe('No star')
    expect(xpNeeded(4, 100)).toBe(400)
    expect(xpNeeded(4, undefined)).toBeNull()
  })
})

describe('hints and opportunities', () => {
  it('builds structured opportunities with correct grammar', () => {
    const items = opportunitiesOf(HINTS)
    const byKey = Object.fromEntries(items.map((item) => [item.key, item.body]))
    expect(byKey.rebels).toBe('Kharun defies you: suppress or forgive them.')
    expect(byKey.godless).toContain('Glass has no patron')
    expect(byKey.orders).toBe('Thalassir, Mirel have no standing order.')
    expect(byKey.stale).toBe(
      '1 story has not moved for a while; advance or close it.'
    )
    expect(byKey.doom).toBeUndefined()
  })

  it('collects the hints that concern one son', () => {
    expect(sonHints(HINTS, 'Thalassir')).toHaveLength(2)
    expect(sonHints(HINTS, 'Kharun')).toHaveLength(2)
    expect(sonHints(undefined, 'Kharun')).toEqual([])
  })
})

describe('gauges and bands', () => {
  it('colours the doom clock by the warning rules', () => {
    expect(doomTone(40, 100, 50, 80)).toBe('default')
    expect(doomTone(60, 100, 50, 80)).toBe('warning')
    expect(doomTone(85, 100, 50, 80)).toBe('destructive')
    expect(doomTone(85, undefined, 50, 80)).toBe('default')
  })

  it('places a foreign god on the attitude scale', () => {
    expect(attitudeBand(-40, 30, 40).label).toBe('Hostile')
    expect(attitudeBand(-10, 30, 40).label).toBe('Suspicious')
    expect(attitudeBand(0, 30, 40).label).toBe('Neutral')
    expect(attitudeBand(20, 30, 40).label).toBe('Close')
    expect(attitudeBand(50, 30, 40).label).toBe('Friend')
  })

  it('describes the council frequency', () => {
    expect(councilFrequencyText(null, 4)).toContain('every 4 epochs')
    expect(councilFrequencyText(0, 4)).toContain('only when you call it')
    expect(councilFrequencyText(undefined, undefined)).toBe(
      'Sons debate an agenda and vote on a motion.'
    )
  })
})

describe('text helpers', () => {
  it('formats plurals, verbs, numerals and keys', () => {
    expect(plural(1, 'prayer')).toBe('1 prayer')
    expect(plural(2, 'story', 'stories')).toBe('2 stories')
    expect(verbFor(['a'], 'is', 'are')).toBe('is')
    expect(verbFor(['a', 'b'], 'is', 'are')).toBe('are')
    expect(romanNumeral(4)).toBe('IV')
    expect(romanNumeral(9)).toBe('IX')
    expect(romanNumeral(12)).toBe('12')
    expect(humanize('killed_by_sibling')).toBe('Killed by sibling')
    expect(worldIdOf('fate')).toBeNull()
    expect(worldIdOf('3')).toBe(3)
  })
})
