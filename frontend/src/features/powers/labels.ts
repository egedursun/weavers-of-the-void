import {
  Activity,
  AlertTriangle,
  Anchor,
  Ban,
  BatteryLow,
  BookOpen,
  Brain,
  Bug,
  Calendar,
  CircleDashed,
  CircleOff,
  Clock,
  Cloud,
  Coins,
  Cpu,
  Crown,
  Database,
  Droplets,
  Eye,
  EyeOff,
  Flame,
  Footprints,
  Gavel,
  Gem,
  Ghost,
  Gift,
  GitBranch,
  GraduationCap,
  Hand,
  HandHeart,
  Handshake,
  Heart,
  HeartCrack,
  Hourglass,
  KeyRound,
  Landmark,
  Leaf,
  Link2,
  Lock,
  Megaphone,
  Moon,
  Mountain,
  Orbit,
  Repeat,
  Scale,
  ScrollText,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Skull,
  Sparkles,
  Star,
  Sun,
  Swords,
  Target,
  TrendingDown,
  TrendingUp,
  User,
  Users,
  Waves,
  Wind,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const POWERS_ICON = Sparkles
export const SOURCES_ICON = Waves
export const SYSTEMS_ICON = BookOpen
export const TRUTHS_ICON = EyeOff

export const LOCI: Record<Schema['SourceLocus'], Named> = {
  self: { label: 'The self', icon: User, tone: 'info' },
  others: { label: 'Other beings', icon: Users, tone: 'warning' },
  place: { label: 'The place', icon: Mountain, tone: 'verdigris' },
  sky: { label: 'The sky and its cycles', icon: Moon, tone: 'gold' },
  surroundings: { label: 'The surroundings', icon: Leaf, tone: 'success' },
  made_things: { label: 'Made things', icon: Cpu, tone: 'muted' },
  patron: { label: 'A patron', icon: Crown, tone: 'gold' },
  bond: { label: 'An oath or pact', icon: Handshake, tone: 'info' },
  story: { label: 'Belief, renown or story', icon: ScrollText, tone: 'gold' },
  void: { label: 'The void', icon: CircleDashed, tone: 'muted' },
  substance: { label: 'A consumed substance', icon: Droplets, tone: 'info' },
  life: { label: 'Life nearby', icon: Heart, tone: 'success' },
  death: { label: 'The dead nearby', icon: Skull, tone: 'danger' },
  dream: { label: 'Dreams', icon: Cloud, tone: 'verdigris' },
  emotion: { label: 'Feeling', icon: HeartCrack, tone: 'warning' },
}

export const COSTS: Record<Schema['PowerCost'], Named> = {
  essence: { label: 'Essence', icon: Sparkles, tone: 'gold' },
  hp: { label: 'Health', icon: Heart, tone: 'danger' },
  fatigue: { label: 'Fatigue', icon: BatteryLow, tone: 'warning' },
  strain: { label: 'Strain of the mind', icon: Brain, tone: 'warning' },
  lifespan: { label: 'Years of life', icon: Hourglass, tone: 'danger' },
  memory: { label: 'Memory', icon: CircleOff, tone: 'warning' },
  emotion: { label: 'Feeling', icon: HeartCrack, tone: 'warning' },
  sanity: { label: 'Sanity', icon: AlertTriangle, tone: 'danger' },
  reagent: { label: 'Reagents', icon: Droplets, tone: 'info' },
  material: { label: 'Materials', icon: Gem, tone: 'info' },
  vis: { label: 'Vis', icon: Zap, tone: 'verdigris' },
  belief: { label: 'Belief owed', icon: Landmark, tone: 'gold' },
  renown: { label: 'Renown', icon: Star, tone: 'gold' },
  oath_standing: {
    label: 'Standing under oath',
    icon: Handshake,
    tone: 'info',
  },
  debt: { label: 'A debt to a patron', icon: Coins, tone: 'warning' },
  soul: { label: 'Souls', icon: Ghost, tone: 'danger' },
  time: { label: 'A long working', icon: Clock, tone: 'muted' },
  surroundings: { label: 'The surroundings', icon: Leaf, tone: 'danger' },
  luck: { label: 'Luck', icon: Target, tone: 'warning' },
  warping: { label: 'Warping', icon: Repeat, tone: 'danger' },
  none: { label: 'Nothing', icon: CircleOff, tone: 'muted' },
}

export const RENEWALS: Record<Schema['SourceRenewal'], Named> = {
  rest: { label: 'Rest', icon: Moon, tone: 'info' },
  time: { label: 'Time', icon: Clock, tone: 'muted' },
  season: { label: 'The seasons', icon: Leaf, tone: 'success' },
  sky_cycle: { label: 'The sky’s cycle', icon: Orbit, tone: 'gold' },
  worship: { label: 'Worship', icon: Landmark, tone: 'gold' },
  feeding: { label: 'Feeding', icon: Droplets, tone: 'warning' },
  taking: { label: 'Taking from others', icon: Hand, tone: 'danger' },
  vows_kept: { label: 'Vows kept', icon: Handshake, tone: 'info' },
  return_to_place: {
    label: 'Return to the place',
    icon: Footprints,
    tone: 'verdigris',
  },
  none: { label: 'Never; it runs out', icon: CircleOff, tone: 'danger' },
}

export const ACCESS: Record<Schema['SourceAccess'], Named> = {
  anyone: { label: 'Anyone', icon: Users, tone: 'success' },
  gifted: { label: 'The gifted', icon: Sparkles, tone: 'gold' },
  trained: { label: 'The trained', icon: GraduationCap, tone: 'info' },
  granted: { label: 'Those granted it', icon: Gift, tone: 'gold' },
  bloodline: { label: 'A bloodline', icon: GitBranch, tone: 'verdigris' },
  bonded: { label: 'The bonded', icon: Handshake, tone: 'info' },
  made: { label: 'Through a made part', icon: Cpu, tone: 'muted' },
}

export const RESISTANCES: Record<Schema['ResistanceKind'], Named> = {
  will: { label: 'Will', icon: Brain, tone: 'info' },
  discipline: { label: 'Discipline', icon: Target, tone: 'info' },
  faith: { label: 'Faith', icon: Landmark, tone: 'gold' },
  sanctity: { label: 'Sanctity', icon: Sun, tone: 'gold' },
  material: { label: 'A material', icon: Gem, tone: 'muted' },
  dampener: { label: 'A dampener', icon: ShieldAlert, tone: 'warning' },
  distance: { label: 'Distance', icon: Footprints, tone: 'muted' },
  counter_source: { label: 'A counter source', icon: Repeat, tone: 'warning' },
  none: { label: 'Nothing', icon: CircleOff, tone: 'muted' },
}

export const VISIBILITIES: Record<Schema['PowerVisibility'], Named> = {
  overt: { label: 'Plain to see', icon: Eye, tone: 'warning' },
  subtle: { label: 'Subtle', icon: Wind, tone: 'info' },
  hidden: { label: 'Hidden', icon: EyeOff, tone: 'muted' },
}

export const HAZARDS: Record<Schema['PowerHazard'], Named> = {
  injury: { label: 'Injury', icon: HeartCrack, tone: 'danger' },
  madness: { label: 'Madness', icon: Brain, tone: 'danger' },
  leak: { label: 'A leak', icon: Droplets, tone: 'danger' },
  escape: { label: 'Something gets loose', icon: Ghost, tone: 'danger' },
  depletion: { label: 'Depletion', icon: TrendingDown, tone: 'warning' },
  warping: { label: 'Warping', icon: Repeat, tone: 'warning' },
  burnout: { label: 'The power gives out', icon: Flame, tone: 'warning' },
  dependency: { label: 'Dependency', icon: Link2, tone: 'warning' },
  attention: { label: 'Draws attention', icon: Eye, tone: 'danger' },
}

export const RELATIONS: Record<Schema['SourceRelation'], Named> = {
  suppresses: { label: 'Suppresses', icon: Ban, tone: 'warning' },
  amplifies: { label: 'Amplifies', icon: TrendingUp, tone: 'success' },
  converts_into: { label: 'Turns into', icon: Repeat, tone: 'info' },
  conflicts: { label: 'Conflicts with', icon: Swords, tone: 'danger' },
}

export const CYCLES: Record<Schema['TideCycle'], Named> = {
  season: { label: 'The seasons', icon: Leaf, tone: 'success' },
  sky: { label: 'The sky', icon: Moon, tone: 'gold' },
  epoch: { label: 'The ages', icon: Hourglass, tone: 'info' },
  authored: { label: 'A set period', icon: Calendar, tone: 'muted' },
}

export const STRUCTURES: Record<Schema['PowerStructure'], Named> = {
  rite: { label: 'Learned procedures', icon: ScrollText, tone: 'info' },
  innate: { label: 'Capacities of beings', icon: Sparkles, tone: 'gold' },
  granted: { label: 'Given by patrons', icon: Gift, tone: 'gold' },
  bonded: { label: 'From oaths and pacts', icon: Handshake, tone: 'info' },
  crafted: { label: 'Held in made things', icon: Cpu, tone: 'muted' },
  mixed: { label: 'Mixed', icon: Repeat, tone: 'verdigris' },
}

export const LEARNABILITY: Record<Schema['Learnability'], Named> = {
  anyone: { label: 'Anyone can learn it', icon: Users, tone: 'success' },
  gifted_only: { label: 'Only the gifted', icon: Sparkles, tone: 'gold' },
  granted_only: { label: 'Only by grant', icon: Gift, tone: 'gold' },
  cannot_be_taught: { label: 'Cannot be taught', icon: Lock, tone: 'muted' },
}

export const SYSTEM_RELATIONS: Record<Schema['SystemRelation'], Named> = {
  opposes: { label: 'Opposes', icon: Swords, tone: 'danger' },
  complements: { label: 'Complements', icon: Handshake, tone: 'success' },
  same_root: {
    label: 'Shares a root with',
    icon: GitBranch,
    tone: 'verdigris',
  },
  unaware: { label: 'Knows nothing of', icon: EyeOff, tone: 'muted' },
}

export const ORIGINS: Record<Schema['PowerOrigin'], Named> = {
  born: { label: 'Born with it', icon: Star, tone: 'gold' },
  awakened: { label: 'Woken by a trigger', icon: Zap, tone: 'warning' },
  exposure: { label: 'By exposure', icon: Bug, tone: 'danger' },
  granted: { label: 'Granted', icon: Gift, tone: 'gold' },
  bonded: { label: 'By a bond', icon: Handshake, tone: 'info' },
  discipline: { label: 'By discipline', icon: Target, tone: 'info' },
  made: { label: 'By a made part', icon: Cpu, tone: 'muted' },
  grown: { label: 'By a grown part', icon: Leaf, tone: 'success' },
  bloodline: { label: 'By its line', icon: GitBranch, tone: 'verdigris' },
  held: { label: 'While holding a thing', icon: Gem, tone: 'muted' },
}

export const STATES: Record<Schema['PowerState'], Named> = {
  latent: { label: 'Latent', icon: Moon, tone: 'muted' },
  emerging: { label: 'Emerging', icon: TrendingUp, tone: 'warning' },
  active: { label: 'Awake', icon: Zap, tone: 'success' },
  strained: { label: 'Strained', icon: Activity, tone: 'warning' },
  exhausted: { label: 'Spent', icon: Flame, tone: 'danger' },
  suppressed: { label: 'Stilled', icon: Ban, tone: 'warning' },
  lost: { label: 'Lost', icon: CircleOff, tone: 'muted' },
}

export const TRIGGERS: Record<Schema['PowerTrigger'], Named> = {
  stress: { label: 'Stress', icon: Activity, tone: 'warning' },
  emotion: { label: 'Strong feeling', icon: Heart, tone: 'warning' },
  danger: { label: 'Danger', icon: AlertTriangle, tone: 'danger' },
  will: { label: 'Will', icon: Brain, tone: 'info' },
  contact: { label: 'Contact with another power', icon: Users, tone: 'info' },
  place: { label: 'A dense place', icon: Mountain, tone: 'verdigris' },
  time: { label: 'Coming of age', icon: Hourglass, tone: 'muted' },
}

export const RESTRICTIONS: Record<Schema['RestrictionKind'], Named> = {
  only_in_place: { label: 'Only in one place', icon: Mountain, tone: 'info' },
  only_at_time: { label: 'Only at one time', icon: Clock, tone: 'info' },
  only_against: {
    label: 'Only against one foe',
    icon: Target,
    tone: 'warning',
  },
  spoken_vow: { label: 'Bound to a spoken vow', icon: Megaphone, tone: 'gold' },
  price_each_use: {
    label: 'A price for each use',
    icon: Coins,
    tone: 'warning',
  },
  never_on_self: { label: 'Never on oneself', icon: User, tone: 'muted' },
  forbidden_act: {
    label: 'Lost by a forbidden act',
    icon: Ban,
    tone: 'danger',
  },
  must_be_seen: { label: 'Must be seen', icon: Eye, tone: 'info' },
  must_be_unseen: { label: 'Must be unseen', icon: EyeOff, tone: 'info' },
  must_touch: { label: 'Must touch', icon: Hand, tone: 'info' },
}

export const ATTITUDES: Record<Schema['GiftedAttitude'], Named> = {
  honoured: { label: 'Honoured', icon: Crown, tone: 'gold' },
  feared: { label: 'Feared', icon: AlertTriangle, tone: 'warning' },
  persecuted: { label: 'Persecuted', icon: Gavel, tone: 'danger' },
  regulated: { label: 'Regulated', icon: Scale, tone: 'info' },
  ordinary: { label: 'Ordinary', icon: Users, tone: 'muted' },
}

export const STANCES: Record<Schema['GiftedStance'], Named> = {
  sacred: { label: 'Sacred', icon: Sun, tone: 'gold' },
  tool: { label: 'A tool', icon: Hand, tone: 'info' },
  forbidden: { label: 'Forbidden', icon: Ban, tone: 'danger' },
  suspect: { label: 'Suspect', icon: Search, tone: 'warning' },
  silent: { label: 'Silent', icon: CircleOff, tone: 'muted' },
}

export const BLOODLINES: Record<Schema['BloodlineRule'], Named> = {
  none: { label: 'No power passes', icon: CircleOff, tone: 'muted' },
  eldest: { label: 'To the eldest', icon: Crown, tone: 'gold' },
  all_children: { label: 'To every child', icon: Users, tone: 'success' },
  skipped: { label: 'Skips generations', icon: GitBranch, tone: 'verdigris' },
}

export const SOURCE_LAWS: Record<Schema['SourceLawLevel'], Named> = {
  free: { label: 'Free', icon: ShieldCheck, tone: 'success' },
  licensed: { label: 'Licensed', icon: KeyRound, tone: 'info' },
  banned: { label: 'Banned', icon: Ban, tone: 'danger' },
}

export const TRUTH_KINDS: Record<Schema['HiddenTruthKind'], Named> = {
  existence: { label: 'That it exists', icon: Eye, tone: 'info' },
  nature: { label: 'What it truly is', icon: Search, tone: 'info' },
  presence: { label: 'That it lives among them', icon: Users, tone: 'warning' },
  power: { label: 'That a power exists', icon: Sparkles, tone: 'gold' },
  event: { label: 'What truly happened', icon: ScrollText, tone: 'info' },
  origin: { label: 'Where it came from', icon: GitBranch, tone: 'verdigris' },
  awakening: { label: 'That a made mind woke', icon: Cpu, tone: 'warning' },
  programme: {
    label: 'That a work is under way',
    icon: Activity,
    tone: 'warning',
  },
  cosmic: { label: 'A truth of the cosmos', icon: Orbit, tone: 'danger' },
}

export const SCOPES: Record<Schema['ConcealScope'], Named> = {
  everyone: { label: 'Everyone', icon: Users, tone: 'warning' },
  a_people: { label: 'A people', icon: Users, tone: 'info' },
  a_polity: { label: 'A realm', icon: Landmark, tone: 'info' },
  the_uninitiated: {
    label: 'The uninitiated',
    icon: KeyRound,
    tone: 'verdigris',
  },
  a_world: { label: 'A world', icon: Orbit, tone: 'info' },
  the_cosmos: { label: 'The cosmos', icon: Star, tone: 'gold' },
}

export const KEEPER_ROLES: Record<Schema['KeeperRole'], Named> = {
  enforcer: { label: 'Enforcer', icon: Gavel, tone: 'warning' },
  guardian: { label: 'Guardian', icon: Shield, tone: 'info' },
  member: { label: 'Member', icon: Users, tone: 'muted' },
  patron: { label: 'Patron', icon: Crown, tone: 'gold' },
}

export const AIMS: Record<Schema['SeekerAim'], Named> = {
  expose: { label: 'To expose it', icon: Megaphone, tone: 'warning' },
  exploit: { label: 'To use it', icon: Coins, tone: 'warning' },
  destroy_the_hidden: {
    label: 'To destroy the hidden',
    icon: Swords,
    tone: 'danger',
  },
  join_the_hidden: {
    label: 'To join the hidden',
    icon: HandHeart,
    tone: 'verdigris',
  },
  understand: { label: 'To understand it', icon: Search, tone: 'info' },
}

export const TRUTH_ATTITUDES: Record<Schema['TruthAttitude'], Named> = {
  unknown: { label: 'Unknown', icon: CircleOff, tone: 'muted' },
  rumoured: { label: 'Rumoured', icon: Megaphone, tone: 'info' },
  denied: { label: 'Denied', icon: Ban, tone: 'muted' },
  feared: { label: 'Feared', icon: AlertTriangle, tone: 'warning' },
  revered: { label: 'Revered', icon: Sun, tone: 'gold' },
  accepted: { label: 'Accepted', icon: Handshake, tone: 'success' },
  exploited: { label: 'Used', icon: Coins, tone: 'warning' },
}

export const BREACH_CAUSES: Record<Schema['BreachCause'], Named> = {
  overt_use: {
    label: 'A power used in plain sight',
    icon: Zap,
    tone: 'warning',
  },
  witness: { label: 'A witness', icon: Eye, tone: 'info' },
  defector: { label: 'A defector', icon: Footprints, tone: 'warning' },
  investigator: { label: 'An investigator', icon: Search, tone: 'info' },
  accident: { label: 'An accident', icon: AlertTriangle, tone: 'warning' },
  war: { label: 'War', icon: Swords, tone: 'danger' },
  record_leak: { label: 'A leak of records', icon: Database, tone: 'warning' },
  intrusion: { label: 'An intrusion', icon: Cpu, tone: 'warning' },
  revelation_by_god: { label: 'A god’s revelation', icon: Sun, tone: 'gold' },
}

export const RESPONSES: Record<Schema['KeeperResponse'], Named> = {
  none: { label: 'No answer', icon: CircleOff, tone: 'muted' },
  cover_story: { label: 'A cover story', icon: ScrollText, tone: 'info' },
  memory_removal: { label: 'Memories taken', icon: Brain, tone: 'danger' },
  discrediting: {
    label: 'Witnesses discredited',
    icon: TrendingDown,
    tone: 'warning',
  },
  law: { label: 'The law', icon: Gavel, tone: 'info' },
  silencing: { label: 'Silencing', icon: Ban, tone: 'danger' },
}

export const TRUTH_METHODS: Record<string, Named> = {
  by_oath: { label: 'By oath', icon: Handshake, tone: 'info' },
  by_law: { label: 'By law', icon: Gavel, tone: 'info' },
  by_memory_removal: {
    label: 'By taking memories',
    icon: Brain,
    tone: 'danger',
  },
  by_cover_story: { label: 'By a cover story', icon: ScrollText, tone: 'info' },
  by_discrediting: {
    label: 'By discrediting witnesses',
    icon: TrendingDown,
    tone: 'warning',
  },
  by_isolation: { label: 'By isolation', icon: Anchor, tone: 'muted' },
  by_passing: {
    label: 'By passing among the rest',
    icon: Users,
    tone: 'verdigris',
  },
  by_silencing: { label: 'By silencing', icon: Ban, tone: 'danger' },
  by_neglect: { label: 'By neglect', icon: CircleDashed, tone: 'muted' },
  by_nature: { label: 'By its nature', icon: Eye, tone: 'gold' },
}

export const DEVICE_EFFECTS: Record<Schema['PowerDeviceEffect'], Named> = {
  amplify: { label: 'Strengthens powers', icon: TrendingUp, tone: 'success' },
  dampen: { label: 'Dampens powers', icon: ShieldAlert, tone: 'warning' },
  awaken: { label: 'Wakes latent powers', icon: Zap, tone: 'gold' },
  stabilise: { label: 'Steadies control', icon: Target, tone: 'info' },
  extend_range: { label: 'Extends reach', icon: Footprints, tone: 'info' },
  shield: { label: 'Shields from powers', icon: Shield, tone: 'info' },
  detect: { label: 'Finds the gifted', icon: Search, tone: 'verdigris' },
}
