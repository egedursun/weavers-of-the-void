import { useCallback, useMemo } from 'react'
import {
  Brain,
  Dumbbell,
  Eye,
  Feather,
  Flame,
  type LucideIcon,
  Mountain,
  Palette,
  Shield,
  Sparkle,
  Swords,
  Wind,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type StatKey, useCatalogue } from './api'
import { type BadgeVariant } from './badgeVariant'

type SonStatus = components['schemas']['SonStatus']
type ReputationLabel = components['schemas']['ReputationLabel']
type MoodLabel = components['schemas']['CreatorMoodLabel']
type ExistenceBand = components['schemas']['ExistenceBand']
type PowerEffect = components['schemas']['PowerEffect']
type ChatAttitude = components['schemas']['ChatAttitude']
type ForeignGodStatus = components['schemas']['ForeignGodStatus']
type SonPassion = 'loyalty' | 'ambition' | 'wrath' | 'mercy'

export type StatGroup = 'Body' | 'Mind' | 'Soul'

export type StatInfo = {
  key: StatKey
  label: string
  abbr: string
  group: StatGroup
  icon: LucideIcon
  effect: string
}

export const STATS: StatInfo[] = [
  {
    key: 'strength',
    label: 'Strength',
    abbr: 'STR',
    group: 'Body',
    icon: Dumbbell,
    effect: 'Wins duels and raw contests of force.',
  },
  {
    key: 'endurance',
    label: 'Endurance',
    abbr: 'END',
    group: 'Body',
    icon: Shield,
    effect: 'Raises maximum life and healing between epochs.',
  },
  {
    key: 'agility',
    label: 'Agility',
    abbr: 'AGI',
    group: 'Body',
    icon: Wind,
    effect: 'Acts first and slips away from danger.',
  },
  {
    key: 'wisdom',
    label: 'Wisdom',
    abbr: 'WIS',
    group: 'Mind',
    icon: Eye,
    effect: 'Sees further and errs less in judgement.',
  },
  {
    key: 'cunning',
    label: 'Cunning',
    abbr: 'CUN',
    group: 'Mind',
    icon: Brain,
    effect: 'Schemes, deceives and outwits siblings.',
  },
  {
    key: 'will',
    label: 'Will',
    abbr: 'WIL',
    group: 'Mind',
    icon: Mountain,
    effect: "Resists punishment and the Creator's commands.",
  },
  {
    key: 'creativity',
    label: 'Creativity',
    abbr: 'CRE',
    group: 'Soul',
    icon: Palette,
    effect: 'Lowers the cost of every creation.',
  },
  {
    key: 'charisma',
    label: 'Charisma',
    abbr: 'CHA',
    group: 'Soul',
    icon: Feather,
    effect: 'Draws worshippers and sways councils.',
  },
  {
    key: 'might',
    label: 'Might',
    abbr: 'MIG',
    group: 'Soul',
    icon: Zap,
    effect: 'Raises maximum essence and the power of creations.',
  },
]

export const STAT_GROUPS: StatGroup[] = ['Body', 'Mind', 'Soul']

export const SON_PASSIONS: {
  key: SonPassion
  label: string
  icon: LucideIcon
}[] = [
  { key: 'loyalty', label: 'Loyalty', icon: Shield },
  { key: 'ambition', label: 'Ambition', icon: Sparkle },
  { key: 'wrath', label: 'Wrath', icon: Flame },
  { key: 'mercy', label: 'Mercy', icon: Swords },
]

export const SON_STATUS_LABEL: Record<SonStatus, string> = {
  active: 'Active',
  asleep: 'Asleep',
  exiled: 'In exile',
  dead: 'Dead',
}

export const REPUTATION_LABEL: Record<ReputationLabel, string> = {
  loved: 'Loved',
  respected: 'Respected',
  feared: 'Feared',
  hated: 'Hated',
  forgotten: 'Forgotten',
  distant: 'Distant',
  acknowledged: 'Known',
}

export const REPUTATION_BADGE: Record<ReputationLabel, BadgeVariant> = {
  loved: 'success',
  respected: 'default',
  feared: 'warning',
  hated: 'destructive',
  forgotten: 'secondary',
  distant: 'secondary',
  acknowledged: 'outline',
}

export function isReputationLabel(value: unknown): value is ReputationLabel {
  return typeof value === 'string' && value in REPUTATION_LABEL
}

export const MOOD_LABEL: Record<MoodLabel, string> = {
  angry: 'Angry',
  distant: 'Distant and silent',
  lonely: 'Lonely',
  content: 'Pleased',
  uneasy: 'Restless',
  serene: 'Serene',
}

export const MOOD_EXPLANATION: Record<MoodLabel, string> = {
  angry: 'The sky darkens; godless homes should fear.',
  distant: 'The Creator looks away; the sons feel abandoned.',
  lonely: "The Creator's light falls into the dreams of seers.",
  content: 'Grace falls on those who worship.',
  uneasy: 'Something stirs; the Creator is watching closely.',
  serene: 'The heavens are calm.',
}

export const MOOD_BADGE: Record<MoodLabel, BadgeVariant> = {
  angry: 'destructive',
  distant: 'secondary',
  lonely: 'outline',
  content: 'default',
  uneasy: 'warning',
  serene: 'success',
}

export const BAND_LABEL: Record<ExistenceBand, string> = {
  radiant: 'Radiant',
  solid: 'Solid',
  faded: 'Pale',
  being_forgotten: 'Fading',
}

export const BAND_TONE: Record<
  ExistenceBand,
  'success' | 'epic' | 'warning' | 'destructive'
> = {
  radiant: 'success',
  solid: 'epic',
  faded: 'warning',
  being_forgotten: 'destructive',
}

export const POWER_EFFECT_LABEL: Record<PowerEffect, string> = {
  cheap_creation: 'Cheap creation',
  duel_master: 'Duel master',
  essence_spring: 'Essence spring',
  worshipped: 'Worshipped',
  tireless: 'Tireless',
  untouchable: 'Untouchable',
  dream_whisper: 'Dream whisper',
  war_father: 'Warbringer',
  harvester: 'Harvester',
  seer: 'Seer',
  reviving: 'Reviving',
  bounty_giver: 'Bounty giver',
  curser: 'Curser',
}

export const ATTITUDE_LABEL: Record<ChatAttitude, string> = {
  loyal: 'Loyal',
  grateful: 'Grateful',
  distant: 'Distant',
  afraid: 'Frightened',
  rebellious: 'Rebellious',
  mocking: 'Mocking',
}

export const ATTITUDE_BADGE: Record<ChatAttitude, BadgeVariant> = {
  loyal: 'success',
  grateful: 'success',
  distant: 'secondary',
  afraid: 'warning',
  rebellious: 'destructive',
  mocking: 'outline',
}

export const FOREIGN_STATUS_LABEL: Record<ForeignGodStatus, string> = {
  awake: 'Awake',
  asleep: 'Asleep',
  defeated: 'Defeated',
  dead: 'Dead',
}

export const FOREIGN_STATUS_BADGE: Record<ForeignGodStatus, BadgeVariant> = {
  awake: 'warning',
  asleep: 'secondary',
  defeated: 'outline',
  dead: 'destructive',
}

export function humanize(value: string): string {
  const spaced = value.replace(/[_:]+/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function useLabels() {
  const catalogue = useCatalogue()
  const tables = useMemo(() => {
    const data = catalogue.data
    const pairs = (items: { key: string; label: string }[] | undefined) =>
      new Map((items ?? []).map((item) => [item.key, item.label]))
    return {
      domains: pairs(data?.domains),
      entityTypes: pairs(data?.entity_types),
      bondKinds: pairs(data?.bond_kinds),
      worldTypes: pairs(data?.world_types),
      passions: pairs(data?.passions),
      chronicleKinds: pairs(data?.chronicle_kinds),
    }
  }, [catalogue.data])
  const domain = useCallback(
    (key: string) => tables.domains.get(key) ?? humanize(key),
    [tables]
  )
  const entityType = useCallback(
    (key: string) => tables.entityTypes.get(key) ?? humanize(key),
    [tables]
  )
  const bondKind = useCallback(
    (key: string) => tables.bondKinds.get(key) ?? humanize(key),
    [tables]
  )
  const worldType = useCallback(
    (key: string) => tables.worldTypes.get(key) ?? humanize(key),
    [tables]
  )
  return {
    domain,
    entityType,
    bondKind,
    worldType,
    catalogue: catalogue.data,
  }
}

export function romanNumeral(value: number): string {
  const numerals: [number, string][] = [
    [10, 'X'],
    [9, 'IX'],
    [5, 'V'],
    [4, 'IV'],
    [1, 'I'],
  ]
  if (value > 10 || value < 1) return String(value)
  let rest = value
  let text = ''
  for (const [amount, glyph] of numerals) {
    while (rest >= amount) {
      text += glyph
      rest -= amount
    }
  }
  return text
}

export function plural(
  count: number,
  singular: string,
  pluralForm = `${singular}s`
): string {
  return `${count} ${count === 1 ? singular : pluralForm}`
}

export function verbFor(
  names: string[],
  singular: string,
  pluralForm: string
): string {
  return names.length === 1 ? singular : pluralForm
}
