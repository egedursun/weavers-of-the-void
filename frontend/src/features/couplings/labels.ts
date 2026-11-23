import {
  type LucideIcon,
  Anchor,
  ArrowDownToLine,
  Ban,
  BookOpen,
  Brain,
  Castle,
  Cog,
  Crown,
  Eye,
  EyeOff,
  Feather,
  Flag,
  Flame,
  Footprints,
  Gem,
  Ghost,
  Hammer,
  Hand,
  HandHelping,
  Handshake,
  Hourglass,
  Languages,
  Link2,
  Lock,
  MapIcon,
  MapPin,
  Megaphone,
  MicOff,
  Music,
  PenLine,
  Repeat,
  ScrollText,
  Shield,
  ShieldOff,
  Shovel,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Swords,
  Target,
  Users,
  Waves,
  Wind,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const COUPLINGS_ICON: LucideIcon = Link2

export const RITE_COMPONENTS: Record<Schema['RiteComponent'], Named> = {
  spoken: { label: 'Spoken', icon: Megaphone, tone: 'info' },
  gestured: { label: 'Gestured', icon: Hand, tone: 'info' },
  inscribed: { label: 'Inscribed', icon: PenLine, tone: 'verdigris' },
  sung: { label: 'Sung', icon: Music, tone: 'gold' },
  danced: { label: 'Danced', icon: Footprints, tone: 'gold' },
  material: { label: 'Material', icon: Gem, tone: 'warning' },
  mental: { label: 'Of the mind', icon: Brain, tone: 'muted' },
}

export const RESTRAINTS: Record<Schema['RestraintKind'], Named> = {
  gag: { label: 'Gagged', icon: MicOff, tone: 'danger' },
  bound_hands: { label: 'Hands bound', icon: Lock, tone: 'danger' },
  blindfold: { label: 'Blindfolded', icon: EyeOff, tone: 'danger' },
}

export const SOCIOLECT_KINDS: Record<Schema['SociolectKind'], Named> = {
  class: { label: 'Speech of a class', icon: Users, tone: 'info' },
  caste: { label: 'Speech of a caste', icon: Shield, tone: 'muted' },
  guild: { label: 'Speech of a trade', icon: Hammer, tone: 'gold' },
  court: { label: 'Speech of the court', icon: Crown, tone: 'gold' },
  cant: { label: 'Secret cant', icon: EyeOff, tone: 'danger' },
  sailors: { label: 'Speech of sailors', icon: Anchor, tone: 'verdigris' },
  youth: { label: 'Speech of the young', icon: Sprout, tone: 'success' },
  soldiers: { label: 'Speech of soldiers', icon: Swords, tone: 'warning' },
}

export const SIGN_CAUSES: Record<Schema['SignCause'], Named> = {
  deafness: { label: 'Many who cannot hear', icon: EyeOff, tone: 'info' },
  silence_vow: { label: 'A vow of silence', icon: MicOff, tone: 'gold' },
  hunting_silence: {
    label: 'Silence on the hunt',
    icon: Footprints,
    tone: 'verdigris',
  },
  mutilation: { label: 'Many who cannot speak', icon: Skull, tone: 'danger' },
  trade: { label: 'Trade between many tongues', icon: Handshake, tone: 'gold' },
}

export const TEACHING_KINDS: Record<Schema['KnowledgeKind'], Named> = {
  song: { label: 'A song', icon: Music, tone: 'gold' },
  art_form: { label: 'An art form', icon: Feather, tone: 'gold' },
  rite: { label: 'A rite', icon: Sparkles, tone: 'verdigris' },
  technique: { label: 'A craft', icon: Hammer, tone: 'info' },
  true_name: { label: 'A true name', icon: ScrollText, tone: 'danger' },
  prophecy: { label: 'A prophecy', icon: Eye, tone: 'warning' },
  treasure: { label: 'Where a treasure lies', icon: MapPin, tone: 'gold' },
  language: { label: 'A language', icon: Languages, tone: 'info' },
  account: { label: 'The memory of an age', icon: BookOpen, tone: 'muted' },
  site: { label: 'A hidden site', icon: MapPin, tone: 'verdigris' },
  map: { label: 'Knowledge of a land', icon: MapIcon, tone: 'info' },
  weakness: { label: 'A weakness', icon: Target, tone: 'danger' },
  pattern: { label: 'A pattern of a made thing', icon: Cog, tone: 'muted' },
  source: { label: 'Where a source of power lies', icon: Zap, tone: 'gold' },
  secret: { label: 'A secret', icon: EyeOff, tone: 'warning' },
}

export const TEACHING_STATES: Record<Schema['TeachingState'], Named> = {
  taught: { label: 'Taught', icon: HandHelping, tone: 'success' },
  blocked: { label: 'Forbidden by the Creator', icon: Ban, tone: 'danger' },
  sold: { label: 'Sold', icon: Gem, tone: 'warning' },
}

export const AGREEMENT_KINDS: Record<Schema['FieldAgreementKind'], Named> = {
  parley: { label: 'Parley', icon: Megaphone, tone: 'info' },
  truce: { label: 'Truce', icon: Handshake, tone: 'success' },
  surrender: { label: 'Surrender terms', icon: Flag, tone: 'gold' },
  exchange: {
    label: 'Exchange of captives and the dead',
    icon: Repeat,
    tone: 'verdigris',
  },
  safe_conduct: { label: 'Safe conduct', icon: Shield, tone: 'info' },
  fraternisation: { label: 'Fraternisation', icon: Users, tone: 'muted' },
}

export const AGREEMENT_STATES: Record<Schema['FieldAgreementState'], Named> = {
  kept: { label: 'Kept', icon: Handshake, tone: 'success' },
  ended: { label: 'Ended', icon: Hourglass, tone: 'muted' },
  broken: { label: 'Broken', icon: Swords, tone: 'danger' },
  repudiated: { label: 'Repudiated', icon: Ban, tone: 'warning' },
}

export const SEAL_KINDS: Record<Schema['SealKind'], Named> = {
  structure: { label: 'Walls and gates', icon: Castle, tone: 'info' },
  rite: { label: 'A warding rite', icon: Sparkles, tone: 'verdigris' },
  divine: { label: 'A god’s hand', icon: Crown, tone: 'gold' },
  power: { label: 'An innate power', icon: Zap, tone: 'warning' },
  living: { label: 'A grown barrier', icon: Sprout, tone: 'success' },
  pact: {
    label: 'A sworn pact',
    icon: Handshake,
    tone: 'verdigris',
  },
}

export const CARRION_ICON: LucideIcon = Wind
export const SEAL_ICON: LucideIcon = ShieldOff
export const SPIRIT_ICON: LucideIcon = Ghost

export const CARRION_RESTS: Record<Schema['CarrionRest'], Named> = {
  rotting: { label: 'Rotting where they lie', icon: Skull, tone: 'danger' },
  mummified: { label: 'Dried out by the land', icon: Hourglass, tone: 'gold' },
  frozen: { label: 'Frozen where they fell', icon: Snowflake, tone: 'info' },
  drifting: {
    label: 'Fallen to the depths',
    icon: ArrowDownToLine,
    tone: 'muted',
  },
  floating: { label: 'Floating where they died', icon: Ghost, tone: 'warning' },
  buried: { label: 'Buried', icon: Shovel, tone: 'muted' },
  burned: { label: 'Burned', icon: Flame, tone: 'warning' },
  sunk: { label: 'Sunk to the floor of the waters', icon: Waves, tone: 'info' },
}
