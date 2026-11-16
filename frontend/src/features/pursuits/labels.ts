import {
  Anvil,
  Ban,
  Bird,
  BookOpen,
  Bot,
  Brain,
  Briefcase,
  CalendarClock,
  Castle,
  CircleCheck,
  CircleDot,
  CircleHelp,
  CircleX,
  Copy,
  Crown,
  Dumbbell,
  Eye,
  FileSignature,
  Flag,
  Footprints,
  Gavel,
  Gem,
  GraduationCap,
  Hammer,
  Handshake,
  HardHat,
  Heart,
  Infinity as InfinityIcon,
  KeyRound,
  Landmark,
  Link,
  type LucideIcon,
  Map as MapIcon,
  MessageSquare,
  Mountain,
  Network,
  Package,
  Palette,
  PauseCircle,
  Pickaxe,
  Radio,
  Repeat,
  ScrollText,
  Shield,
  ShieldCheck,
  Skull,
  Sparkles,
  Stamp,
  Star,
  Swords,
  Target,
  Timer,
  Trophy,
  Users,
  Wrench,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const PURSUITS_ICON: LucideIcon = Palette

export const TAB_ICONS = {
  works: Palette,
  pastimes: Trophy,
  constructs: Bot,
  fates: Target,
} as const

export const MARKET_ROLES: Record<Schema['ArtMarketRole'], Named> = {
  collector: { label: 'Collector', icon: Gem, tone: 'gold' },
  dealer: { label: 'Dealer', icon: Briefcase, tone: 'info' },
  patron: { label: 'Patron', icon: Crown, tone: 'verdigris' },
  connoisseur: { label: 'Connoisseur', icon: Eye, tone: 'success' },
}

export const FORGERY_KINDS: Record<Schema['ForgeryKind'], Named> = {
  artwork: { label: 'A work of art', icon: Palette, tone: 'gold' },
  relic: { label: 'A relic', icon: Sparkles, tone: 'verdigris' },
  document: { label: 'A charter', icon: FileSignature, tone: 'info' },
  brand: { label: 'A brand', icon: Stamp, tone: 'warning' },
}

export const FORGERY_STATUS: Record<Schema['ForgeryStatus'], Named> = {
  hidden: { label: 'Passes for real', icon: Eye, tone: 'warning' },
  exposed: { label: 'Exposed', icon: CircleX, tone: 'danger' },
}

export const CANON_PATHS: Record<Schema['CanonPath'], Named> = {
  renown: { label: 'By renown', icon: Star, tone: 'gold' },
  institution: { label: 'By an institution', icon: Landmark, tone: 'info' },
  copying: { label: 'By copying', icon: Copy, tone: 'verdigris' },
  teaching: { label: 'By teaching', icon: GraduationCap, tone: 'success' },
  movement: { label: 'By a movement', icon: Flag, tone: 'warning' },
}

export const CLUB_KINDS: Record<Schema['ClubKind'], Named> = {
  team_game: { label: 'Team game', icon: Users, tone: 'info' },
  racing: { label: 'Racing', icon: Footprints, tone: 'success' },
  combat: { label: 'Combat', icon: Swords, tone: 'danger' },
  athletics: { label: 'Athletics', icon: Dumbbell, tone: 'gold' },
}

export const FANDOM_LINES: Record<Schema['FandomLine'], Named> = {
  class: { label: 'Class', icon: Crown, tone: 'gold' },
  district: { label: 'District', icon: MapIcon, tone: 'info' },
  faith: { label: 'Faith', icon: Sparkles, tone: 'verdigris' },
  none: { label: 'No line', icon: CircleDot, tone: 'muted' },
}

export const BINDINGS: Record<Schema['InstructionBinding'], Named> = {
  none: { label: 'Unbound', icon: CircleDot, tone: 'muted' },
  order: { label: 'Order', icon: ScrollText, tone: 'info' },
  oath: { label: 'Oath', icon: Handshake, tone: 'gold' },
  geas: { label: 'Geas', icon: Link, tone: 'warning' },
  seal: { label: 'Seal', icon: Stamp, tone: 'verdigris' },
  ownership: { label: 'Ownership', icon: KeyRound, tone: 'gold' },
  lease: { label: 'Lease', icon: CalendarClock, tone: 'info' },
  symbiosis: { label: 'Symbiosis', icon: Heart, tone: 'success' },
}

export const TOKENS: Record<Schema['CommandToken'], Named> = {
  none: { label: 'No token', icon: CircleDot, tone: 'muted' },
  item: { label: 'A held item', icon: Package, tone: 'gold' },
  word: { label: 'A spoken word', icon: MessageSquare, tone: 'info' },
  bloodline: { label: 'A bloodline', icon: Heart, tone: 'danger' },
  office: { label: 'An office', icon: Crown, tone: 'verdigris' },
  network_key: { label: 'A network key', icon: Network, tone: 'success' },
}

export const ORDERS: Record<Schema['OrderKind'], Named> = {
  guard: { label: 'Guard', icon: Shield, tone: 'info' },
  serve: { label: 'Serve', icon: Hammer, tone: 'success' },
  obey_holder: { label: 'Obey the holder', icon: KeyRound, tone: 'gold' },
  build: { label: 'Build', icon: HardHat, tone: 'gold' },
  gather: { label: 'Gather ore', icon: Pickaxe, tone: 'success' },
  protect: { label: 'Protect', icon: ShieldCheck, tone: 'verdigris' },
  destroy: { label: 'Destroy', icon: Skull, tone: 'danger' },
  report: { label: 'Report', icon: Radio, tone: 'info' },
  maintain: { label: 'Maintain', icon: Wrench, tone: 'muted' },
  replicate: { label: 'Replicate', icon: Repeat, tone: 'warning' },
  hold_still: { label: 'Hold still', icon: PauseCircle, tone: 'muted' },
  follow: { label: 'Follow', icon: Footprints, tone: 'info' },
  forbid: { label: 'Forbid', icon: Ban, tone: 'danger' },
}

export const CONDITIONS: Record<Schema['OrderCondition'], Named> = {
  always: { label: 'Always', icon: InfinityIcon, tone: 'muted' },
  while_maker_lives: {
    label: 'While its maker lives',
    icon: Heart,
    tone: 'warning',
  },
  until_date: { label: 'Until an epoch', icon: Timer, tone: 'info' },
  when_attacked: { label: 'When attacked', icon: Swords, tone: 'danger' },
  when_token_shown: {
    label: 'When the token is shown',
    icon: KeyRound,
    tone: 'gold',
  },
}

export const WILLS: Record<Schema['MindWill'], Named> = {
  none: { label: 'No will', icon: CircleDot, tone: 'muted' },
  instructed: { label: 'Follows orders', icon: ScrollText, tone: 'info' },
  emergent: { label: 'A will stirs', icon: Sparkles, tone: 'info' },
  full: { label: 'A will of its own', icon: Brain, tone: 'verdigris' },
  exceeding: { label: 'Beyond every order', icon: Bird, tone: 'gold' },
}

export const CONTRACT_STATUS: Record<Schema['ContractStatus'], Named> = {
  posted: { label: 'Posted', icon: ScrollText, tone: 'info' },
  taken: { label: 'Taken', icon: Target, tone: 'warning' },
  slain: { label: 'Slain', icon: Trophy, tone: 'success' },
  failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
  withdrawn: { label: 'Withdrawn', icon: Ban, tone: 'muted' },
}

export const INFLUENCES: Record<Schema['SignInfluence'], Named> = {
  real: { label: 'Truly rules', icon: CircleCheck, tone: 'gold' },
  believed: { label: 'Believed only', icon: CircleHelp, tone: 'muted' },
}

export const BUILD_ICON: LucideIcon = Anvil
export const HUNT_ICON: LucideIcon = Mountain
export const SIGN_ICON: LucideIcon = Star
export const REMADE_ICON: LucideIcon = Gavel
export const CANON_ICON: LucideIcon = BookOpen
export const MOVEMENT_ICON: LucideIcon = Castle
