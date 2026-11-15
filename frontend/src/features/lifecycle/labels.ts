import {
  Archive,
  BookOpen,
  Bone,
  Bug,
  CircleOff,
  Cross,
  Crown,
  Eye,
  Flame,
  Flower2,
  Gem,
  Ghost,
  Hourglass,
  Landmark,
  Leaf,
  type LucideIcon,
  Moon,
  Mountain,
  Orbit,
  Palette,
  PawPrint,
  RefreshCcw,
  RotateCcw,
  Scroll,
  ShieldOff,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Trees,
  Undo2,
  Zap,
} from 'lucide-react'
import { type components, worldTypeValues } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'
import { humanize } from '@/features/pantheon/labels'

type Schema = components['schemas']

export const LIFE_ICON: LucideIcon = Hourglass
export const WORLD_END_ICON: LucideIcon = Orbit
export const FOSSIL_ICON: LucideIcon = Bone
export const GROUNDS_ICON: LucideIcon = Landmark

export const LIFE_KINDS: Record<Schema['LifecycleKind'], Named> = {
  ideology: { label: 'Ideology', icon: Scroll, tone: 'verdigris' },
  theory: { label: 'Theory', icon: BookOpen, tone: 'info' },
  rite: { label: 'Rite', icon: Sparkles, tone: 'gold' },
  disease: { label: 'Disease', icon: Bug, tone: 'danger' },
  outer_being: { label: 'Outer being', icon: Eye, tone: 'danger' },
}

export const LIFE_STATES: Record<Schema['LifecycleState'], Named> = {
  active: { label: 'Alive', icon: Sun, tone: 'success' },
  dormant: { label: 'Dormant', icon: Moon, tone: 'muted' },
  extinct: { label: 'Extinct', icon: CircleOff, tone: 'danger' },
  lost: { label: 'Lost', icon: CircleOff, tone: 'danger' },
  corrupted: { label: 'Corrupted', icon: Zap, tone: 'warning' },
  eradicated: { label: 'Eradicated', icon: ShieldOff, tone: 'success' },
  banished: { label: 'Banished', icon: Undo2, tone: 'info' },
  destroyed: { label: 'Destroyed', icon: Skull, tone: 'danger' },
}

export const LIFE_CAUSES: Record<Schema['LifecycleCause'], Named> = {
  living: { label: 'Still held', icon: Sun, tone: 'success' },
  no_adherents: { label: 'No one holds it', icon: CircleOff, tone: 'muted' },
  no_texts: { label: 'No text survives', icon: Scroll, tone: 'danger' },
  no_practitioners: {
    label: 'No one practises it',
    icon: Sparkles,
    tone: 'muted',
  },
  no_hosts: { label: 'No host is left', icon: Bug, tone: 'success' },
  sealed: { label: 'Sealed out', icon: ShieldOff, tone: 'info' },
  revived: { label: 'Taken up again', icon: RefreshCcw, tone: 'gold' },
  rediscovered: { label: 'Found again', icon: Eye, tone: 'gold' },
  reconstructed: {
    label: 'Rebuilt from a text',
    icon: BookOpen,
    tone: 'warning',
  },
  rereleased: { label: 'Released again', icon: Bug, tone: 'danger' },
  returned: { label: 'Returned', icon: RotateCcw, tone: 'danger' },
  god_act: { label: 'An act of a god', icon: Crown, tone: 'gold' },
}

export const WORLD_ENDS: Record<Schema['WorldEnd'], Named> = {
  shattered: { label: 'Shattered', icon: Mountain, tone: 'danger' },
  swallowed: { label: 'Swallowed', icon: Sun, tone: 'danger' },
  frozen_dead: { label: 'Frozen dead', icon: Snowflake, tone: 'info' },
  sunk_into_void: { label: 'Sunk into the void', icon: Orbit, tone: 'muted' },
  forgotten: { label: 'Forgotten', icon: Ghost, tone: 'muted' },
  transfigured: { label: 'Transfigured', icon: Sparkles, tone: 'gold' },
}

export const WORLD_END_CAUSES: Record<Schema['WorldEndCause'], Named> = {
  impact: { label: 'An impact', icon: Mountain, tone: 'danger' },
  divine_wrath: { label: 'Divine wrath', icon: Flame, tone: 'danger' },
  star_giant: { label: 'Its star swelled', icon: Sun, tone: 'warning' },
  star_death: { label: 'Its star died', icon: Star, tone: 'muted' },
  void: { label: 'The void', icon: Orbit, tone: 'muted' },
  oblivion: { label: 'Oblivion', icon: Ghost, tone: 'muted' },
  belief_drift: { label: 'Belief drifted', icon: Sparkles, tone: 'gold' },
}

export const FOSSIL_SOURCES: Record<Schema['FossilSource'], Named> = {
  extinct_species: { label: 'A kind that died out', icon: Leaf, tone: 'muted' },
  megafauna: { label: 'Great beasts', icon: PawPrint, tone: 'warning' },
  beast: { label: 'A beast', icon: Swords, tone: 'danger' },
  previous_creation: {
    label: 'A previous creation',
    icon: Hourglass,
    tone: 'gold',
  },
  extinct_people: {
    label: 'A people that died out',
    icon: Skull,
    tone: 'muted',
  },
}

export const FOSSIL_READINGS: Record<Schema['FossilReading'], Named> = {
  unread: { label: 'Unread', icon: CircleOff, tone: 'muted' },
  legend: { label: 'Remains of legend', icon: BookOpen, tone: 'gold' },
  relic: { label: 'Sacred relics', icon: Cross, tone: 'verdigris' },
  deep_time: { label: 'Evidence of deep time', icon: Hourglass, tone: 'info' },
}

export const HOARD_KINDS: Record<Schema['HoardKind'], Named> = {
  cabinet: { label: 'Cabinet of curiosities', icon: Archive, tone: 'info' },
  temple_treasury: { label: 'Temple treasury', icon: Cross, tone: 'verdigris' },
  royal_collection: { label: 'Royal collection', icon: Crown, tone: 'gold' },
  museum: { label: 'Museum', icon: Landmark, tone: 'success' },
}

export const PIECE_KINDS: Record<Schema['PieceKind'], Named> = {
  artifact: { label: 'Artifact', icon: Gem, tone: 'gold' },
  relic: { label: 'Relic', icon: Cross, tone: 'verdigris' },
  fossil: { label: 'Fossil', icon: Bone, tone: 'muted' },
  art: { label: 'Work of art', icon: Palette, tone: 'info' },
  specimen: { label: 'Specimen', icon: Leaf, tone: 'success' },
}

export const GARDEN_KINDS: Record<Schema['GardenKind'], Named> = {
  pleasure: { label: 'Pleasure garden', icon: Flower2, tone: 'gold' },
  physic: { label: 'Physic garden', icon: Sprout, tone: 'success' },
  monastery: { label: 'Monastery garden', icon: Cross, tone: 'verdigris' },
  park: { label: 'Park', icon: Trees, tone: 'success' },
  hunting_park: { label: 'Hunting park', icon: PawPrint, tone: 'warning' },
  sacred_grove: { label: 'Sacred grove', icon: Trees, tone: 'verdigris' },
  cemetery: { label: 'Cemetery', icon: Skull, tone: 'muted' },
}

export const WORLD_KINDS: Record<string, Named> = Object.fromEntries(
  worldTypeValues.map((value) => [
    value,
    { label: humanize(value), icon: Orbit, tone: 'info' } satisfies Named,
  ])
)
