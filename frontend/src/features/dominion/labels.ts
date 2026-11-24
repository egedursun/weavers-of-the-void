import {
  Activity,
  Ban,
  Biohazard,
  Bird,
  BookOpen,
  Cloud,
  Coins,
  Crown,
  DoorOpen,
  Droplets,
  EyeOff,
  Flame,
  Footprints,
  Gem,
  Hammer,
  HandCoins,
  HandHeart,
  Heart,
  HeartPulse,
  Minus,
  Moon,
  Pause,
  Scale,
  Shield,
  ShieldAlert,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Sun,
  Swords,
  ThumbsDown,
  ThumbsUp,
  Waves,
  Wheat,
  Wind,
  Zap,
  type LucideIcon,
  Eye,
  FlameKindling,
  Gavel,
  GraduationCap,
  Handshake,
  Scale3d,
  Sparkle,
  Star,
  VenetianMask,
  Mail,
  Siren,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }
export type Pole = Named & { opposite: Named }

export const SCALES: Record<Schema['DivineScale'], Pole> = {
  order: {
    label: 'Order',
    icon: Scale,
    tone: 'info',
    opposite: { label: 'Turmoil', icon: Zap, tone: 'danger' },
  },
  productivity: {
    label: 'Productivity',
    icon: Hammer,
    tone: 'gold',
    opposite: { label: 'Sloth', icon: Pause, tone: 'muted' },
  },
  heat: {
    label: 'Heat',
    icon: Flame,
    tone: 'warning',
    opposite: { label: 'Cold', icon: Snowflake, tone: 'info' },
  },
  growth: {
    label: 'Growth',
    icon: Sprout,
    tone: 'success',
    opposite: { label: 'Decay', icon: Skull, tone: 'muted' },
  },
  fortune: {
    label: 'Fortune',
    icon: Coins,
    tone: 'gold',
    opposite: { label: 'Misfortune', icon: Cloud, tone: 'danger' },
  },
  magic: {
    label: 'Magic',
    icon: Sparkles,
    tone: 'verdigris',
    opposite: { label: 'Drain', icon: Droplets, tone: 'muted' },
  },
  peace: {
    label: 'Peace',
    icon: Bird,
    tone: 'success',
    opposite: { label: 'Strife', icon: Swords, tone: 'danger' },
  },
  health: {
    label: 'Health',
    icon: HeartPulse,
    tone: 'success',
    opposite: { label: 'Sickness', icon: Biohazard, tone: 'danger' },
  },
}

export const ALIGNMENTS: Record<Schema['PerceivedAlignment'], Named> = {
  benevolent: { label: 'Benevolent', icon: Sun, tone: 'success' },
  ambivalent: { label: 'Ambivalent', icon: Minus, tone: 'muted' },
  malevolent: { label: 'Malevolent', icon: Moon, tone: 'danger' },
}

export const WORSHIP_MODES: Record<Schema['WorshipMode'], Named> = {
  devotion: { label: 'Devotion', icon: Heart, tone: 'success' },
  appeasement: { label: 'Appeasement', icon: ShieldAlert, tone: 'warning' },
  bargain: { label: 'Bargain', icon: Scale, tone: 'info' },
  union: { label: 'Union', icon: Gavel, tone: 'info' },
  kinship: { label: 'Kinship', icon: Scale3d, tone: 'info' },
}

export const PRAYER_TONES: Record<Schema['PrayerTone'], Named> = {
  thanks: { label: 'Thanks', icon: HandHeart, tone: 'success' },
  mercy: { label: 'A plea for mercy', icon: Shield, tone: 'warning' },
  request: { label: 'A request for a boon', icon: HandCoins, tone: 'info' },
  praise: { label: 'Praise', icon: Sparkles, tone: 'gold' },
  lament: { label: 'Lament', icon: Sparkle, tone: 'gold' },
  confession: { label: 'Confession', icon: Star, tone: 'gold' },
}

export const MANIFESTATIONS: Record<Schema['Manifestation'], Named> = {
  radiant: { label: 'Radiant', icon: Sun, tone: 'gold' },
  serene: { label: 'Serene', icon: Wind, tone: 'info' },
  stern: { label: 'Stern', icon: Scale, tone: 'warning' },
  dreadful: { label: 'Dreadful', icon: Skull, tone: 'danger' },
  veiled: { label: 'Veiled', icon: EyeOff, tone: 'muted' },
  playful: { label: 'Playful', icon: Eye, tone: 'muted' },
  sorrowful: { label: 'Sorrowful', icon: VenetianMask, tone: 'muted' },
}

export const STANCES: Record<Schema['BeliefStance'], Named> = {
  yield: { label: 'Yields to belief', icon: Activity, tone: 'info' },
  resist: { label: 'Resists belief', icon: Ban, tone: 'warning' },
  embrace: { label: 'Embraces belief', icon: Heart, tone: 'success' },
  bargain: { label: 'Bargain', icon: Handshake, tone: 'success' },
}

export const SITE_KINDS: Record<Schema['MagicSiteKind'], Named> = {
  source: { label: 'Source', icon: Gem, tone: 'verdigris' },
  school_seat: { label: 'School seat', icon: BookOpen, tone: 'info' },
  ward: { label: 'Ward', icon: Shield, tone: 'gold' },
  gateway: { label: 'Gateway', icon: DoorOpen, tone: 'warning' },
  tide_point: { label: 'Tide point', icon: Waves, tone: 'verdigris' },
  depletion_scar: { label: 'Depletion scar', icon: Flame, tone: 'verdigris' },
  confluence: { label: 'Confluence', icon: FlameKindling, tone: 'verdigris' },
  null_zone: { label: 'Null zone', icon: Sun, tone: 'verdigris' },
}

export const DEEDS: Record<Schema['CreatureDeed'], Named> = {
  hunt_folk: { label: 'Hunt folk', icon: Skull, tone: 'danger' },
  tend_fields: { label: 'Tend fields', icon: Wheat, tone: 'success' },
  guard_holy_sites: { label: 'Guard holy sites', icon: Shield, tone: 'gold' },
  strike_foes: { label: 'Strike foes', icon: Swords, tone: 'warning' },
  heal_sick: { label: 'Heal the sick', icon: HeartPulse, tone: 'success' },
  wreck_works: { label: 'Wreck works', icon: Hammer, tone: 'danger' },
  wander: { label: 'Wander', icon: Footprints, tone: 'info' },
  rest: { label: 'Rest', icon: Pause, tone: 'muted' },
  trade: { label: 'Trade', icon: Scale, tone: 'muted' },
  carry_messages: {
    label: 'Carry messages',
    icon: Mail,
    tone: 'muted',
  },
  teach: { label: 'Teach', icon: GraduationCap, tone: 'muted' },
}

export const LESSONS: Record<Schema['CreatureLesson'], Named> = {
  reward: { label: 'Reward', icon: ThumbsUp, tone: 'success' },
  punish: { label: 'Punish', icon: ThumbsDown, tone: 'danger' },
  warn: { label: 'Warn', icon: Siren, tone: 'danger' },
}

export const THRONE_ICON = Crown

export function table(
  record: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(record).map(([key, value]) => [key, value.label])
  )
}

export function leaning(scale: Schema['DivineScale'], value: number): Named {
  const pole = SCALES[scale]
  return value < 0 ? pole.opposite : pole
}
