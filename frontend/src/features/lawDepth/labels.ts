import {
  Anchor,
  Baby,
  BadgeCheck,
  BookMarked,
  BookOpen,
  Brain,
  Building2,
  Church,
  Coins,
  Crown,
  Eye,
  EyeOff,
  FileBadge,
  FileSignature,
  Flame,
  Footprints,
  Gavel,
  Gem,
  GitBranch,
  Globe,
  Hammer,
  HandCoins,
  Handshake,
  Heart,
  KeyRound,
  Landmark,
  Link2,
  MapPinned,
  Scale,
  ScrollText,
  Shapes,
  Shuffle,
  Skull,
  Sparkles,
  Sword,
  Swords,
  UserCheck,
  UserX,
  Users,
  Wind,
  type LucideIcon,
  Banknote,
  FileCheck,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const LAW_DEPTH_ICON: LucideIcon = Landmark

export const LEGAL_SYSTEMS: Record<Schema['LegalSystem'], Named> = {
  customary: { label: 'Custom and sworn oaths', icon: Users, tone: 'muted' },
  codified: { label: 'A written code', icon: BookOpen, tone: 'info' },
  religious: { label: 'Sacred law', icon: Church, tone: 'gold' },
  precedent: { label: 'Case law', icon: BookMarked, tone: 'verdigris' },
  oracle: { label: 'The answer of a god', icon: Sparkles, tone: 'gold' },
  mixed: { label: 'Sacred law and a code', icon: Scale, tone: 'info' },
}

export const COURTS: Record<Schema['CourtLevel'], Named> = {
  local: { label: 'Local court', icon: Gavel, tone: 'muted' },
  provincial: { label: 'Provincial court', icon: MapPinned, tone: 'info' },
  high: { label: 'High court', icon: Crown, tone: 'gold' },
  religious: { label: 'Court of the faith', icon: Church, tone: 'gold' },
  guild: { label: 'Guild court', icon: Hammer, tone: 'info' },
  military: { label: 'Military court', icon: Swords, tone: 'danger' },
  consular: { label: 'Court of foreigners', icon: Globe, tone: 'verdigris' },
  appellate: { label: 'Court of appeal', icon: Scale, tone: 'muted' },
}

export const REGISTRY_KINDS: Record<Schema['RegistryKind'], Named> = {
  land_title: { label: 'Title to land', icon: MapPinned, tone: 'gold' },
  debt: { label: 'Debt', icon: Banknote, tone: 'warning' },
  sale: { label: 'Sale', icon: HandCoins, tone: 'info' },
  union_payment: {
    label: 'Payment made at a union',
    icon: Heart,
    tone: 'verdigris',
  },
  indenture: { label: 'Indenture', icon: Hammer, tone: 'muted' },
  patent: { label: 'Patent', icon: FileBadge, tone: 'gold' },
  pattern: { label: 'Pattern', icon: Shapes, tone: 'gold' },
  mind_state: { label: 'Mind state', icon: Brain, tone: 'gold' },
  line: { label: 'Line', icon: GitBranch, tone: 'gold' },
  company: { label: 'Company', icon: Coins, tone: 'gold' },
  birth: { label: 'Birth', icon: Baby, tone: 'gold' },
  death: { label: 'Death', icon: Skull, tone: 'gold' },
  citizenship: { label: 'Citizenship', icon: BadgeCheck, tone: 'gold' },
  licence: { label: 'Licence', icon: FileCheck, tone: 'gold' },
  will: { label: 'Will', icon: ScrollText, tone: 'gold' },
}

export const CLAIMS: Record<Schema['JurisdictionClaim'], Named> = {
  clergy: { label: 'Courts of the clergy', icon: Church, tone: 'gold' },
  guild: { label: 'Courts of an association', icon: Building2, tone: 'info' },
  foreign: { label: 'Courts of a foreign realm', icon: Globe, tone: 'warning' },
}

export const MOTIVES: Record<Schema['RecruitMotive'], Named> = {
  money: { label: 'For money', icon: Coins, tone: 'warning' },
  ideology: { label: 'For belief', icon: Brain, tone: 'success' },
  compromise: { label: 'Under a hook', icon: Link2, tone: 'danger' },
  ego: { label: 'For pride', icon: Gem, tone: 'info' },
  love: { label: 'For love of a handler', icon: Heart, tone: 'success' },
  revenge: { label: 'For revenge', icon: Swords, tone: 'danger' },
  faith: { label: 'For faith', icon: Church, tone: 'warning' },
}

export const HUNT_OUTCOMES: Record<Schema['MoleHuntOutcome'], Named> = {
  caught: { label: 'Caught a mole', icon: UserCheck, tone: 'success' },
  cleared: { label: 'Cleared the accused', icon: Scale, tone: 'info' },
  purged: { label: 'Purged the innocent', icon: UserX, tone: 'danger' },
  defected: { label: 'Drove one to defect', icon: Shuffle, tone: 'warning' },
}

export const KILL_METHODS: Record<Schema['KillMethod'], Named> = {
  blade: { label: 'By the blade', icon: Sword, tone: 'danger' },
  poison: { label: 'By poison', icon: Skull, tone: 'warning' },
  accident: { label: 'A staged accident', icon: Wind, tone: 'muted' },
  disease: { label: 'A deliberate infection', icon: Flame, tone: 'warning' },
  curse: { label: 'By a curse', icon: Sparkles, tone: 'gold' },
}

export const SEEN: Record<'true' | 'false', Named> = {
  true: { label: 'Seen as murder', icon: Eye, tone: 'danger' },
  false: { label: 'Passed unseen', icon: EyeOff, tone: 'muted' },
}

export const PROTECTED: Record<'true' | 'false', Named> = {
  true: { label: 'Protected', icon: Anchor, tone: 'success' },
  false: { label: 'Unprotected', icon: Footprints, tone: 'danger' },
}

export const YES_NO: Record<string, string> = { true: 'Yes', false: 'No' }

export const OUTLAW_ICON: LucideIcon = Footprints
export const PRISON_ICON: LucideIcon = KeyRound
export const PARDON_ICON: LucideIcon = Handshake
export const CELL_ICON: LucideIcon = Users
export const DEED_ICON: LucideIcon = FileSignature
export const PRECEDENT_ICON: LucideIcon = ScrollText
