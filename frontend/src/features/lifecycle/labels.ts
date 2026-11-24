import {
  Archive,
  Bone,
  BookOpen,
  Bug,
  Carrot,
  CircleOff,
  Cloud,
  Cog,
  Compass,
  Cross,
  Crown,
  Droplets,
  Eye,
  Flame,
  Flower2,
  Footprints,
  Gem,
  Ghost,
  Hammer,
  Hourglass,
  Landmark,
  Leaf,
  Library,
  Map,
  Moon,
  Mountain,
  Orbit,
  Palette,
  PawPrint,
  Pill,
  RefreshCcw,
  RotateCcw,
  Scroll,
  ScrollText,
  ShieldOff,
  Shovel,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Thermometer,
  Trees,
  Trophy,
  Undo2,
  Waves,
  Zap,
  type LucideIcon,
  Flower,
  MountainSnow,
  Search,
} from 'lucide-react'
import { type components, worldTypeValues } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'
import { wordOf } from '@/features/entity/affairs/labels'

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
  lost: { label: 'Lost', icon: Search, tone: 'danger' },
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
  consumed: { label: 'Consumed by its star', icon: Sun, tone: 'danger' },
  frozen_dead: { label: 'Frozen dead', icon: Snowflake, tone: 'info' },
  sunk_into_void: { label: 'Sunk into the void', icon: Orbit, tone: 'muted' },
  forgotten: { label: 'Forgotten', icon: Ghost, tone: 'muted' },
  transfigured: { label: 'Transfigured', icon: Sparkles, tone: 'gold' },
  drowned: { label: 'Drowned under its seas', icon: Waves, tone: 'info' },
  burned: { label: 'Burned barren', icon: Flame, tone: 'danger' },
  devoured: { label: 'Devoured from outside', icon: Skull, tone: 'danger' },
  merged: { label: 'Merged', icon: Bone, tone: 'danger' },
  emptied: { label: 'Emptied', icon: Cross, tone: 'danger' },
}

export const WORLD_END_CAUSES: Record<Schema['WorldEndCause'], Named> = {
  impact: { label: 'An impact', icon: Mountain, tone: 'danger' },
  divine_wrath: { label: 'Divine wrath', icon: Flame, tone: 'danger' },
  star_giant: { label: 'Its star swelled', icon: Sun, tone: 'warning' },
  star_death: { label: 'Its star died', icon: Star, tone: 'muted' },
  void: { label: 'The void', icon: Orbit, tone: 'muted' },
  oblivion: { label: 'Oblivion', icon: Ghost, tone: 'muted' },
  belief_drift: { label: 'Belief drifted', icon: Sparkles, tone: 'gold' },
  runaway_climate: {
    label: 'Its climate ran away',
    icon: Thermometer,
    tone: 'warning',
  },
  war: { label: 'A war unmade it', icon: Swords, tone: 'danger' },
  outer_hunger: { label: 'An outer hunger', icon: Skull, tone: 'danger' },
  plague: { label: 'Plague', icon: Bone, tone: 'danger' },
  runaway_making: { label: 'Runaway making', icon: Cross, tone: 'danger' },
  structure_failure: {
    label: 'Structure failure',
    icon: Cross,
    tone: 'danger',
  },
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
  god: { label: 'A god that died', icon: Crown, tone: 'gold' },
  buried_dead: { label: 'The buried dead', icon: Shovel, tone: 'muted' },
  made: { label: 'Old made bodies and works', icon: Cog, tone: 'info' },
  ancestor: {
    label: 'Older forms of a living kind',
    icon: Footprints,
    tone: 'gold',
  },
}

export const FOSSIL_READINGS: Record<Schema['FossilReading'], Named> = {
  unread: { label: 'Unread', icon: CircleOff, tone: 'muted' },
  legend: { label: 'Remains of legend', icon: BookOpen, tone: 'gold' },
  relic: { label: 'Sacred relics', icon: Cross, tone: 'verdigris' },
  deep_time: { label: 'Evidence of deep time', icon: Hourglass, tone: 'info' },
  material: { label: 'A substance to work', icon: Hammer, tone: 'warning' },
  medicine: { label: 'A remedy', icon: Pill, tone: 'success' },
  sacred: { label: 'Held sacred', icon: Landmark, tone: 'verdigris' },
  omen: { label: 'An omen', icon: Eye, tone: 'warning' },
}

export const FOSSIL_PRESERVATIONS: Record<Schema['Preservation'], Named> = {
  rock: { label: 'Rock', icon: Mountain, tone: 'muted' },
  amber: { label: 'Amber', icon: Gem, tone: 'gold' },
  ice: { label: 'Ice', icon: Snowflake, tone: 'info' },
  bog: { label: 'Bog', icon: Droplets, tone: 'verdigris' },
  tar: { label: 'Tar', icon: Flame, tone: 'danger' },
  ash: { label: 'Ash', icon: Cloud, tone: 'muted' },
  dry: { label: 'Dry ground', icon: Sun, tone: 'warning' },
  cave: { label: 'Cave', icon: MountainSnow, tone: 'muted' },
}

export const HOARD_KINDS: Record<Schema['HoardKind'], Named> = {
  cabinet: { label: 'Cabinet of curiosities', icon: Archive, tone: 'info' },
  temple_treasury: { label: 'Temple treasury', icon: Cross, tone: 'verdigris' },
  royal_collection: { label: 'Royal collection', icon: Crown, tone: 'gold' },
  museum: { label: 'Museum', icon: Landmark, tone: 'success' },
  trophy_hall: { label: 'Trophy hall', icon: Trophy, tone: 'danger' },
  library: { label: 'Library', icon: Library, tone: 'info' },
}

export const PIECE_KINDS: Record<Schema['PieceKind'], Named> = {
  artifact: { label: 'Artifact', icon: Gem, tone: 'gold' },
  relic: { label: 'Relic', icon: Cross, tone: 'verdigris' },
  fossil: { label: 'Fossil', icon: Bone, tone: 'muted' },
  art: { label: 'Work of art', icon: Palette, tone: 'info' },
  specimen: { label: 'Specimen', icon: Leaf, tone: 'success' },
  manuscript: { label: 'Manuscript', icon: ScrollText, tone: 'info' },
  trophy: { label: 'Trophy of war', icon: Swords, tone: 'danger' },
  regalia: { label: 'Regalia', icon: Crown, tone: 'gold' },
  map: { label: 'Map', icon: Map, tone: 'gold' },
  instrument: { label: 'Instrument', icon: Compass, tone: 'gold' },
}

export const GARDEN_KINDS: Record<Schema['GardenKind'], Named> = {
  pleasure: { label: 'Pleasure garden', icon: Flower2, tone: 'gold' },
  physic: { label: 'Physic garden', icon: Sprout, tone: 'success' },
  monastery: { label: 'Monastery garden', icon: Cross, tone: 'verdigris' },
  park: { label: 'Park', icon: Trees, tone: 'success' },
  hunting_park: { label: 'Hunting park', icon: PawPrint, tone: 'warning' },
  sacred_grove: { label: 'Sacred grove', icon: Trees, tone: 'verdigris' },
  cemetery: { label: 'Cemetery', icon: Skull, tone: 'muted' },
  botanic: { label: 'Botanic garden', icon: Leaf, tone: 'success' },
  menagerie: { label: 'Menagerie', icon: PawPrint, tone: 'gold' },
  kitchen_garden: { label: 'Kitchen garden', icon: Carrot, tone: 'gold' },
  roof_garden: { label: 'Roof garden', icon: Flower, tone: 'gold' },
}

export const WORLD_KINDS: Record<string, Named> = Object.fromEntries(
  worldTypeValues.map((value) => [
    value,
    {
      label: wordOf(worldTypeValues, value),
      icon: Orbit,
      tone: 'info',
    } satisfies Named,
  ])
)
