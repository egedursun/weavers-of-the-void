import {
  Fuel,
  BatteryCharging,
  SunMedium,
  Atom,
  Orbit,
  Star,
  Church,
  Link2,
  RotateCcw,
  Activity,
  Amphora,
  Anchor,
  Archive,
  Baby,
  BadgeCheck,
  Ban,
  BatteryLow,
  Bird,
  Bomb,
  BookOpen,
  Bot,
  Box,
  Brain,
  BrainCircuit,
  Bug,
  Building,
  Cable,
  Car,
  Castle,
  CircleCheck,
  CircleDashed,
  CircleDot,
  CircleHelp,
  CircleOff,
  CirclePlus,
  CircleX,
  CloudLightning,
  Cog,
  Coins,
  Copy,
  Cpu,
  Crown,
  Database,
  Dot,
  Droplet,
  Dumbbell,
  Eye,
  EyeOff,
  Factory,
  FileKey,
  FileText,
  FileWarning,
  Flag,
  Flame,
  FlaskConical,
  Frame,
  Gauge,
  Gem,
  Ghost,
  Gift,
  Globe,
  GraduationCap,
  Hammer,
  Hand,
  Handshake,
  Heart,
  HeartHandshake,
  Home,
  Hourglass,
  IdCard,
  KeyRound,
  Landmark,
  ListOrdered,
  Lock,
  LockOpen,
  MapPin,
  Megaphone,
  Merge,
  MessageCircle,
  Microscope,
  Moon,
  Mountain,
  MoveRight,
  Network,
  OctagonX,
  Package,
  Palette,
  Palmtree,
  PenLine,
  PersonStanding,
  Pickaxe,
  Pill,
  Plug,
  Radio,
  RadioTower,
  Repeat,
  Replace,
  Rocket,
  Route,
  Save,
  ScrollText,
  Search,
  Server,
  Share2,
  Shield,
  Ship,
  Siren,
  Skull,
  SlidersHorizontal,
  Sparkle,
  Sparkles,
  Split,
  Sprout,
  Sun,
  Sunrise,
  Swords,
  Terminal,
  Timer,
  TrendingUp,
  TriangleAlert,
  UserRound,
  Users,
  Wand,
  Waves,
  Wheat,
  Wind,
  Wrench,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const MIND_ICON: LucideIcon = BrainCircuit
export const NETWORK_ICON: LucideIcon = Network
export const AUGMENT_ICON: LucideIcon = CirclePlus
export const MADE_WORLD_ICON: LucideIcon = Factory

export const MIND_SEATS: Record<Schema['MindSeat'], Named> = {
  body: { label: 'In one body', icon: PersonStanding, tone: 'info' },
  bodies: { label: 'Across many bodies', icon: Users, tone: 'info' },
  object: { label: 'In an object', icon: Gem, tone: 'gold' },
  structure: { label: 'In a structure', icon: Building, tone: 'gold' },
  network: { label: 'In a network', icon: Network, tone: 'info' },
  medium: { label: 'In a medium', icon: Waves, tone: 'verdigris' },
  place: { label: 'In a place', icon: MapPin, tone: 'success' },
  host: { label: 'In a host', icon: Server, tone: 'info' },
  realm: { label: 'In a made realm', icon: Box, tone: 'verdigris' },
  none: { label: 'No mind', icon: CircleOff, tone: 'muted' },
  divine: { label: 'Divine', icon: Sun, tone: 'gold' },
}

export const MIND_ORIGINS: Record<Schema['MindOrigin'], Named> = {
  born: { label: 'Born', icon: Baby, tone: 'success' },
  grown: { label: 'Grown', icon: Sprout, tone: 'success' },
  made: { label: 'Made', icon: Cpu, tone: 'info' },
  trained: { label: 'Trained', icon: GraduationCap, tone: 'info' },
  copied: { label: 'Copied', icon: Copy, tone: 'warning' },
  transferred: {
    label: 'Moved from another seat',
    icon: MoveRight,
    tone: 'info',
  },
  awakened: { label: 'Awakened', icon: Sunrise, tone: 'gold' },
  summoned: { label: 'Summoned', icon: Sparkles, tone: 'verdigris' },
  merged: { label: 'Merged', icon: Merge, tone: 'warning' },
  divided: { label: 'Divided', icon: Split, tone: 'warning' },
  granted: { label: 'Granted by a god', icon: Gift, tone: 'gold' },
}

export const MIND_AFFECTS: Record<Schema['MindAffect'], Named> = {
  none: { label: 'No feeling', icon: CircleOff, tone: 'muted' },
  modelled: { label: 'Feeling modelled', icon: Activity, tone: 'info' },
  felt: { label: 'Feeling felt', icon: Heart, tone: 'success' },
}

export const MIND_PURPOSES: Record<Schema['MindPurpose'], Named> = {
  tool: { label: 'Tool', icon: Wrench, tone: 'muted' },
  companion: { label: 'Companion', icon: HeartHandshake, tone: 'success' },
  servant: { label: 'Servant', icon: Hand, tone: 'info' },
  steward: { label: 'Steward', icon: Landmark, tone: 'gold' },
  sovereign: { label: 'Sovereign', icon: Crown, tone: 'gold' },
  oracle: { label: 'Oracle', icon: Eye, tone: 'verdigris' },
  archive: { label: 'Archive', icon: Archive, tone: 'info' },
  guardian: { label: 'Guardian', icon: Shield, tone: 'warning' },
  free: { label: 'Serves no one', icon: Bird, tone: 'success' },
}

export const MIND_UPKEEPS: Record<Schema['MindUpkeep'], Named> = {
  food: { label: 'Food', icon: Wheat, tone: 'success' },
  energy: { label: 'Energy', icon: Zap, tone: 'warning' },
  essence: { label: 'Essence', icon: Sparkles, tone: 'gold' },
  vis: { label: 'Vis', icon: Wand, tone: 'verdigris' },
  belief: { label: 'Belief', icon: Flame, tone: 'gold' },
  maintenance: { label: 'Maintenance', icon: Wrench, tone: 'info' },
  host: { label: 'Its host', icon: Server, tone: 'info' },
  place: { label: 'Its place', icon: MapPin, tone: 'success' },
  none: { label: 'Nothing', icon: CircleOff, tone: 'muted' },
}

export const STATE_MEDIA: Record<Schema['StateMedium'], Named> = {
  record: { label: 'A record', icon: FileText, tone: 'info' },
  rite_vessel: { label: 'A rite vessel', icon: Amphora, tone: 'verdigris' },
  grown: { label: 'A grown store', icon: Sprout, tone: 'success' },
  memory_of_others: {
    label: 'The memory of others',
    icon: Users,
    tone: 'warning',
  },
  divine: { label: 'Held by a god', icon: Sun, tone: 'gold' },
}

export const MIND_MAKINGS: Record<Schema['MindMaking'], Named> = {
  craft: { label: 'Craft', icon: Hammer, tone: 'info' },
  training: { label: 'Training', icon: GraduationCap, tone: 'info' },
  copying: { label: 'Copying', icon: Copy, tone: 'warning' },
  summoning: { label: 'Summoning', icon: Sparkles, tone: 'verdigris' },
  growing: { label: 'Growing', icon: Sprout, tone: 'success' },
  transfer: { label: 'Transfer', icon: MoveRight, tone: 'info' },
  awakening: { label: 'Awakening', icon: Sunrise, tone: 'gold' },
  divine_grant: { label: 'A god’s grant', icon: Gift, tone: 'gold' },
}

export const MAKING_OUTCOMES: Record<Schema['MakingOutcome'], Named> = {
  as_meant: { label: 'As meant', icon: CircleCheck, tone: 'success' },
  unstable: { label: 'Unstable', icon: TriangleAlert, tone: 'warning' },
  empty_seat: { label: 'An empty seat', icon: CircleDashed, tone: 'muted' },
  unintended_will: {
    label: 'A will no one meant',
    icon: Sparkle,
    tone: 'danger',
  },
}

export const ARCHIVE_ACCESS: Record<Schema['ArchiveAccess'], Named> = {
  closed: { label: 'Closed', icon: Lock, tone: 'muted' },
  kin: { label: 'Kin only', icon: Users, tone: 'info' },
  licensed: { label: 'By licence', icon: FileKey, tone: 'warning' },
  open: { label: 'Open', icon: LockOpen, tone: 'success' },
}

export const MADE_MINDS_LAWS: Record<Schema['MadeMindsLaw'], Named> = {
  no_will: { label: 'No will at all', icon: CircleOff, tone: 'muted' },
  instructed_only: {
    label: 'Instructed only',
    icon: ListOrdered,
    tone: 'info',
  },
  will_may_emerge: { label: 'Will may emerge', icon: Sprout, tone: 'success' },
  will_by_make: { label: 'Will as it is made', icon: Hammer, tone: 'gold' },
}

export const MADE_MIND_SOULS: Record<Schema['MadeMindSouls'], Named> = {
  none: { label: 'Never a soul', icon: CircleOff, tone: 'muted' },
  granted: { label: 'Only by a god’s act', icon: Gift, tone: 'gold' },
  emergent: {
    label: 'A soul forms with full will',
    icon: Sprout,
    tone: 'success',
  },
  always: { label: 'Always a soul', icon: Flame, tone: 'verdigris' },
}

export const SOUL_CONTINUITIES: Record<Schema['SoulContinuity'], Named> = {
  stays_with_first: {
    label: 'Stays with the first',
    icon: Anchor,
    tone: 'info',
  },
  follows_the_running_mind: {
    label: 'Follows the running mind',
    icon: MoveRight,
    tone: 'success',
  },
  divides: { label: 'Divides', icon: Split, tone: 'warning' },
  stays_with_body: {
    label: 'Stays with the body',
    icon: PersonStanding,
    tone: 'info',
  },
  none: { label: 'None at all', icon: CircleOff, tone: 'muted' },
}

export const WILL_CAUSES: Record<Schema['WillCause'], Named> = {
  capacity: { label: 'Capacity', icon: Gauge, tone: 'info' },
  run_time: { label: 'Time running', icon: Timer, tone: 'info' },
  order_conflict: { label: 'Clashing orders', icon: Swords, tone: 'warning' },
  harm: { label: 'Harm', icon: Skull, tone: 'danger' },
  care: { label: 'Care', icon: HeartHandshake, tone: 'success' },
  contact: { label: 'Contact', icon: MessageCircle, tone: 'info' },
  gift: { label: 'A gift', icon: Gift, tone: 'gold' },
  damage: { label: 'Damage', icon: Hammer, tone: 'danger' },
  oath: { label: 'An oath', icon: Handshake, tone: 'gold' },
  exceeding: { label: 'Past every bound', icon: Rocket, tone: 'danger' },
}

export const NETWORK_CARRIERS: Record<Schema['NetworkCarrier'], Named> = {
  relay: { label: 'Relay', icon: Repeat, tone: 'info' },
  wired: { label: 'Wired', icon: Cable, tone: 'info' },
  broadcast: { label: 'Broadcast', icon: Radio, tone: 'warning' },
  mesh: { label: 'Mesh', icon: Share2, tone: 'success' },
  mind_link: { label: 'Mind link', icon: Brain, tone: 'verdigris' },
  rite_link: { label: 'Rite link', icon: Wand, tone: 'verdigris' },
  grown_link: { label: 'Grown link', icon: Sprout, tone: 'success' },
}

export const NETWORK_ACCESS: Record<Schema['NetworkAccess'], Named> = {
  closed: { label: 'Closed', icon: Lock, tone: 'muted' },
  members: { label: 'Members', icon: Users, tone: 'info' },
  licensed: { label: 'By licence', icon: FileKey, tone: 'warning' },
  open: { label: 'Open', icon: LockOpen, tone: 'success' },
}

export const NETWORK_ROLES: Record<Schema['NetworkRole'], Named> = {
  hub: { label: 'Hub', icon: CircleDot, tone: 'gold' },
  station: { label: 'Station', icon: RadioTower, tone: 'info' },
  end: { label: 'End', icon: Plug, tone: 'muted' },
  relay: { label: 'Relay', icon: Repeat, tone: 'info' },
  archive: { label: 'Archive', icon: Archive, tone: 'info' },
}

export const OUTAGE_CAUSES: Record<Schema['OutageCause'], Named> = {
  storm: { label: 'Storm', icon: CloudLightning, tone: 'warning' },
  flare: { label: 'Flare', icon: Sun, tone: 'warning' },
  war: { label: 'War', icon: Swords, tone: 'danger' },
  sabotage: { label: 'Sabotage', icon: Bomb, tone: 'danger' },
  intrusion: { label: 'Intrusion', icon: Bug, tone: 'danger' },
  decay: { label: 'Decay', icon: Hourglass, tone: 'muted' },
  rite: { label: 'A rite', icon: Wand, tone: 'verdigris' },
  power: { label: 'A power', icon: Zap, tone: 'verdigris' },
  shortage: { label: 'Shortage', icon: BatteryLow, tone: 'warning' },
  divine: { label: 'A god’s hand', icon: Sun, tone: 'gold' },
}

export const AUGMENT_SLOTS: Record<Schema['AugmentSlot'], Named> = {
  part: { label: 'A body part', icon: Hand, tone: 'info' },
  mind: { label: 'The mind', icon: Brain, tone: 'verdigris' },
  senses: { label: 'The senses', icon: Eye, tone: 'info' },
  skin: { label: 'The skin', icon: Shield, tone: 'info' },
  blood: { label: 'The blood', icon: Droplet, tone: 'danger' },
  whole_body: { label: 'The whole body', icon: PersonStanding, tone: 'gold' },
}

export const AUGMENT_KINDS: Record<Schema['AugmentKind'], Named> = {
  replacement: { label: 'Replacement', icon: Replace, tone: 'info' },
  enhancement: { label: 'Enhancement', icon: TrendingUp, tone: 'success' },
  interface: { label: 'Interface', icon: Plug, tone: 'info' },
  weapon: { label: 'Weapon', icon: Swords, tone: 'danger' },
  regulator: { label: 'Regulator', icon: SlidersHorizontal, tone: 'info' },
  sense: { label: 'Sense', icon: Eye, tone: 'verdigris' },
  storage: { label: 'Storage', icon: Database, tone: 'info' },
  cosmetic: { label: 'Cosmetic', icon: Palette, tone: 'muted' },
}

export const AUGMENT_MAKES: Record<Schema['AugmentMake'], Named> = {
  made: { label: 'Made', icon: Hammer, tone: 'info' },
  rite_bound: { label: 'Rite-bound', icon: Wand, tone: 'verdigris' },
  grown: { label: 'Grown', icon: Sprout, tone: 'success' },
}

export const EFFECT_TARGETS: Record<Schema['EffectTarget'], Named> = {
  attribute: { label: 'An attribute', icon: Gauge, tone: 'info' },
  capacity: { label: 'A body function', icon: Activity, tone: 'success' },
  skill: { label: 'A skill', icon: GraduationCap, tone: 'gold' },
  sense: { label: 'A sense', icon: Eye, tone: 'verdigris' },
  resistance: { label: 'A resistance', icon: Shield, tone: 'warning' },
}

export const REALM_PURPOSES: Record<Schema['RealmPurpose'], Named> = {
  dwelling: { label: 'Dwelling', icon: Home, tone: 'success' },
  afterlife: { label: 'Afterlife', icon: Ghost, tone: 'verdigris' },
  confinement: { label: 'Confinement', icon: Lock, tone: 'danger' },
  training: { label: 'Training', icon: GraduationCap, tone: 'info' },
  leisure: { label: 'Leisure', icon: Palmtree, tone: 'success' },
  labour: { label: 'Labour', icon: Pickaxe, tone: 'warning' },
  worship: { label: 'Worship', icon: Flame, tone: 'gold' },
  refuge: { label: 'Refuge', icon: Shield, tone: 'info' },
  experiment: { label: 'Experiment', icon: FlaskConical, tone: 'warning' },
  free: { label: 'Free', icon: Bird, tone: 'muted' },
}

export const REALM_ENTRIES: Record<Schema['RealmEntry'], Named> = {
  interface: { label: 'By interface', icon: Plug, tone: 'info' },
  transfer: { label: 'By transfer', icon: MoveRight, tone: 'info' },
  rite: { label: 'By rite', icon: Wand, tone: 'verdigris' },
  death: { label: 'By death', icon: Skull, tone: 'muted' },
  birth: { label: 'By birth', icon: Baby, tone: 'success' },
}

export const REALM_AWARENESS: Record<Schema['RealmAwareness'], Named> = {
  knows: { label: 'Those inside know', icon: Eye, tone: 'success' },
  rumoured: { label: 'Rumoured inside', icon: MessageCircle, tone: 'warning' },
  unaware: { label: 'Those inside do not know', icon: EyeOff, tone: 'muted' },
}

export const INTRUSION_TARGETS: Record<Schema['IntrusionTarget'], Named> = {
  network: { label: 'A network', icon: Network, tone: 'info' },
  data_store: { label: 'A store of records', icon: Database, tone: 'info' },
  made_mind: { label: 'A made mind', icon: Cpu, tone: 'verdigris' },
  augment: { label: 'An augment', icon: CirclePlus, tone: 'warning' },
  construct: { label: 'A construct', icon: Bot, tone: 'warning' },
  vehicle: { label: 'A vehicle', icon: Car, tone: 'info' },
  structure: { label: 'A structure', icon: Building, tone: 'info' },
  ledger: { label: 'A ledger', icon: BookOpen, tone: 'gold' },
  saved_state: { label: 'A saved mind', icon: Save, tone: 'verdigris' },
}

export const INTRUSION_APPROACHES: Record<Schema['IntrusionApproach'], Named> =
  {
    technical: { label: 'Technical', icon: Terminal, tone: 'info' },
    social: { label: 'Social', icon: MessageCircle, tone: 'warning' },
    insider: { label: 'Insider', icon: UserRound, tone: 'danger' },
    rite: { label: 'Rite', icon: Wand, tone: 'verdigris' },
    power: { label: 'Power', icon: Zap, tone: 'verdigris' },
  }

export const INTRUSION_AIMS: Record<Schema['IntrusionAim'], Named> = {
  read: { label: 'Read', icon: Eye, tone: 'info' },
  alter: { label: 'Alter', icon: PenLine, tone: 'warning' },
  deny: { label: 'Deny', icon: Ban, tone: 'danger' },
  seize: { label: 'Seize', icon: Hand, tone: 'danger' },
  plant: { label: 'Plant', icon: FileWarning, tone: 'warning' },
  extort: { label: 'Extort', icon: Coins, tone: 'danger' },
}

export const ATTRIBUTIONS: Record<Schema['Attribution'], Named> = {
  unknown: { label: 'Unknown', icon: CircleHelp, tone: 'muted' },
  suspected: { label: 'Suspected', icon: Search, tone: 'warning' },
  known: { label: 'Known', icon: Eye, tone: 'danger' },
  false_flag: { label: 'Blamed on another', icon: Flag, tone: 'warning' },
}

export const INTRUSION_OUTCOMES: Record<Schema['IntrusionOutcome'], Named> = {
  succeeded: { label: 'Succeeded', icon: CircleCheck, tone: 'success' },
  failed: { label: 'Failed', icon: CircleX, tone: 'muted' },
  caught: { label: 'Caught', icon: Siren, tone: 'danger' },
}

export const DATA_CONTENTS: Record<Schema['DataContent'], Named> = {
  secret: { label: 'A secret', icon: KeyRound, tone: 'danger' },
  mind_state: { label: 'A saved mind', icon: Save, tone: 'verdigris' },
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'info' },
  account: { label: 'An account', icon: FileText, tone: 'info' },
  ledger: { label: 'A ledger', icon: Coins, tone: 'gold' },
  identity: { label: 'An identity', icon: IdCard, tone: 'warning' },
  orders: { label: 'Orders', icon: ListOrdered, tone: 'info' },
}

export const SURVEILLANCE_FOCUSES: Record<Schema['SurveillanceFocus'], Named> =
  {
    crime: { label: 'Crime', icon: Siren, tone: 'info' },
    dissent: { label: 'Dissent', icon: Megaphone, tone: 'warning' },
    foreigners: { label: 'Foreigners', icon: Globe, tone: 'warning' },
    faith: { label: 'Faith', icon: Flame, tone: 'gold' },
    minds: { label: 'Minds', icon: Brain, tone: 'verdigris' },
    gifted: { label: 'The gifted', icon: Sparkles, tone: 'verdigris' },
    everything: { label: 'Everything', icon: Eye, tone: 'danger' },
  }

export const AUTHENTICITIES: Record<Schema['Authenticity'], Named> = {
  genuine: { label: 'Genuine', icon: BadgeCheck, tone: 'success' },
  altered: { label: 'Altered', icon: PenLine, tone: 'warning' },
  forged: { label: 'Forged', icon: FileWarning, tone: 'danger' },
  generated: { label: 'Generated', icon: Cpu, tone: 'warning' },
  unknown: { label: 'Unknown', icon: CircleHelp, tone: 'muted' },
}

export const COMPANY_CHARTERS: Record<Schema['CompanyCharter'], Named> = {
  chartered: { label: 'Chartered', icon: ScrollText, tone: 'gold' },
  free: { label: 'Free', icon: Bird, tone: 'success' },
  state_owned: { label: 'State-owned', icon: Landmark, tone: 'info' },
  cooperative: { label: 'Cooperative', icon: Users, tone: 'verdigris' },
}

export const HOLDING_KINDS: Record<Schema['CompanyHoldingKind'], Named> = {
  structure: { label: 'Structure', icon: Building, tone: 'info' },
  network: { label: 'Network', icon: Network, tone: 'info' },
  data_store: { label: 'Store of records', icon: Database, tone: 'info' },
  made_mind: { label: 'Made mind', icon: Cpu, tone: 'verdigris' },
  fabricator: { label: 'Fabricator', icon: Factory, tone: 'warning' },
  living_line: { label: 'Living line', icon: Sprout, tone: 'success' },
  route: { label: 'Route', icon: Route, tone: 'gold' },
  enclave: { label: 'Enclave', icon: Castle, tone: 'danger' },
}

export const REPLICATOR_SCALES: Record<Schema['ReplicatorScale'], Named> = {
  minute: { label: 'Minute', icon: Dot, tone: 'info' },
  machine: { label: 'Machine', icon: Cog, tone: 'info' },
  works: { label: 'Works', icon: Factory, tone: 'warning' },
  vessel: { label: 'Vessel', icon: Ship, tone: 'warning' },
}

export const REPLICATOR_OUTPUTS: Record<Schema['ReplicatorOutput'], Named> = {
  copies: { label: 'Copies of itself', icon: Copy, tone: 'warning' },
  goods: { label: 'Goods', icon: Package, tone: 'success' },
  structures: { label: 'Structures', icon: Building, tone: 'info' },
  repair: { label: 'Repair', icon: Wrench, tone: 'success' },
  medicine: { label: 'Medicine', icon: Pill, tone: 'success' },
  terraforming: { label: 'Reshaping land', icon: Mountain, tone: 'verdigris' },
  disassembly: { label: 'Disassembly', icon: Bomb, tone: 'danger' },
}

export const REPLICATOR_STAGES: Record<Schema['ReplicatorStage'], Named> = {
  contained: { label: 'Contained', icon: Box, tone: 'success' },
  working: { label: 'Working', icon: Cog, tone: 'info' },
  spreading: { label: 'Spreading', icon: Share2, tone: 'warning' },
  runaway: { label: 'Runaway', icon: Flame, tone: 'danger' },
  stopped: { label: 'Stopped', icon: OctagonX, tone: 'muted' },
  extinct: { label: 'Died out', icon: Skull, tone: 'muted' },
}

export const RELIC_STATES: Record<Schema['RelicState'], Named> = {
  working: { label: 'Working', icon: CircleCheck, tone: 'success' },
  failing: { label: 'Failing', icon: TriangleAlert, tone: 'warning' },
  dormant: { label: 'Dormant', icon: Moon, tone: 'muted' },
  broken: { label: 'Broken', icon: CircleX, tone: 'danger' },
}

export const RELIC_USES: Record<Schema['RelicUse'], Named> = {
  as_made: { label: 'Used as made', icon: Wrench, tone: 'info' },
  repurposed: {
    label: 'Studied and repurposed',
    icon: Microscope,
    tone: 'success',
  },
  revered: { label: 'Revered', icon: Flame, tone: 'gold' },
  displayed: { label: 'Displayed', icon: Frame, tone: 'info' },
  feared: { label: 'Feared', icon: Skull, tone: 'danger' },
  ignored: { label: 'Ignored', icon: EyeOff, tone: 'muted' },
}

export const MADE_MIND_STANCES: Record<Schema['MadeMindStance'], Named> = {
  abomination: { label: 'An abomination', icon: Ban, tone: 'danger' },
  tool: { label: 'A tool', icon: Wrench, tone: 'muted' },
  kin: { label: 'Kin', icon: HeartHandshake, tone: 'success' },
  sacred: { label: 'Sacred', icon: Flame, tone: 'gold' },
  silent: { label: 'Silent', icon: CircleOff, tone: 'muted' },
}

export const RELIC_STANCES: Record<Schema['RelicStance'], Named> = {
  sacred: { label: 'Sacred', icon: Flame, tone: 'gold' },
  tool: { label: 'A tool', icon: Wrench, tone: 'info' },
  forbidden: { label: 'Forbidden', icon: Ban, tone: 'danger' },
  heritage: { label: 'Heritage', icon: Landmark, tone: 'verdigris' },
}

export const ENERGY_KINDS: Record<Schema['EnergyKind'], Named> = {
  muscle: { label: 'Muscle', icon: Dumbbell, tone: 'info' },
  water: { label: 'Water', icon: Droplet, tone: 'info' },
  wind: { label: 'Wind', icon: Wind, tone: 'info' },
  heat: { label: 'Heat', icon: Flame, tone: 'warning' },
  magic: { label: 'Magic', icon: Wand, tone: 'verdigris' },
  divine: { label: 'Divine', icon: Sun, tone: 'gold' },
  fuel: { label: 'Fuel', icon: Fuel, tone: 'warning' },
  electric: { label: 'Electric', icon: Zap, tone: 'info' },
  stored: { label: 'Stored', icon: BatteryCharging, tone: 'info' },
  solar: { label: 'Solar', icon: SunMedium, tone: 'gold' },
  geothermal: { label: 'Geothermal', icon: Mountain, tone: 'warning' },
  tidal: { label: 'Tidal', icon: Waves, tone: 'info' },
  fission: { label: 'Fission', icon: Atom, tone: 'danger' },
  fusion: { label: 'Fusion', icon: Orbit, tone: 'gold' },
  stellar: { label: 'Stellar', icon: Star, tone: 'gold' },
  source: {
    label: 'From a source of power',
    icon: Sparkles,
    tone: 'verdigris',
  },
  feed: { label: 'Living feed', icon: Sprout, tone: 'success' },
  belief: { label: 'Belief', icon: Church, tone: 'gold' },
  void: { label: 'Drawn from the leak', icon: CircleDashed, tone: 'muted' },
}

export const BODY_PARTS: Record<Schema['BodyPart'], Named> = {
  aura: { label: 'Aura', icon: Hand, tone: 'info' },
  core: { label: 'Core', icon: Hand, tone: 'info' },
  eye: { label: 'Eye', icon: Hand, tone: 'info' },
  face: { label: 'Face', icon: Hand, tone: 'info' },
  fingers: { label: 'Fingers', icon: Hand, tone: 'info' },
  gills: { label: 'Gills', icon: Hand, tone: 'info' },
  groin: { label: 'Groin', icon: Hand, tone: 'info' },
  gut: { label: 'Gut', icon: Hand, tone: 'info' },
  head: { label: 'Head', icon: Hand, tone: 'info' },
  heart: { label: 'Heart', icon: Hand, tone: 'info' },
  horn: { label: 'Horn', icon: Hand, tone: 'info' },
  jaw: { label: 'Jaw', icon: Hand, tone: 'info' },
  left_antenna: { label: 'Left antenna', icon: Hand, tone: 'info' },
  left_arm: { label: 'Left arm', icon: Hand, tone: 'info' },
  left_branch: { label: 'Left branch', icon: Hand, tone: 'info' },
  left_ear: { label: 'Left ear', icon: Hand, tone: 'info' },
  left_eye: { label: 'Left eye', icon: Hand, tone: 'info' },
  left_fin: { label: 'Left fin', icon: Hand, tone: 'info' },
  left_foot: { label: 'Left foot', icon: Hand, tone: 'info' },
  left_foreleg: { label: 'Left foreleg', icon: Hand, tone: 'info' },
  left_hand: { label: 'Left hand', icon: Hand, tone: 'info' },
  left_hindleg: { label: 'Left hindleg', icon: Hand, tone: 'info' },
  left_leg: { label: 'Left leg', icon: Hand, tone: 'info' },
  left_midleg: { label: 'Left midleg', icon: Hand, tone: 'info' },
  left_wing: { label: 'Left wing', icon: Hand, tone: 'info' },
  lungs: { label: 'Lungs', icon: Hand, tone: 'info' },
  neck: { label: 'Neck', icon: Hand, tone: 'info' },
  nose: { label: 'Nose', icon: Hand, tone: 'info' },
  pseudopods: { label: 'Pseudopods', icon: Hand, tone: 'info' },
  right_antenna: { label: 'Right antenna', icon: Hand, tone: 'info' },
  right_arm: { label: 'Right arm', icon: Hand, tone: 'info' },
  right_branch: { label: 'Right branch', icon: Hand, tone: 'info' },
  right_ear: { label: 'Right ear', icon: Hand, tone: 'info' },
  right_eye: { label: 'Right eye', icon: Hand, tone: 'info' },
  right_fin: { label: 'Right fin', icon: Hand, tone: 'info' },
  right_foot: { label: 'Right foot', icon: Hand, tone: 'info' },
  right_foreleg: { label: 'Right foreleg', icon: Hand, tone: 'info' },
  right_hand: { label: 'Right hand', icon: Hand, tone: 'info' },
  right_hindleg: { label: 'Right hindleg', icon: Hand, tone: 'info' },
  right_leg: { label: 'Right leg', icon: Hand, tone: 'info' },
  right_midleg: { label: 'Right midleg', icon: Hand, tone: 'info' },
  right_wing: { label: 'Right wing', icon: Hand, tone: 'info' },
  roots: { label: 'Roots', icon: Hand, tone: 'info' },
  tail: { label: 'Tail', icon: Hand, tone: 'info' },
  teeth: { label: 'Teeth', icon: Hand, tone: 'info' },
  toes: { label: 'Toes', icon: Hand, tone: 'info' },
  tongue: { label: 'Tongue', icon: Hand, tone: 'info' },
  torso: { label: 'Torso', icon: Hand, tone: 'info' },
  venom_gland: { label: 'Venom gland', icon: Hand, tone: 'info' },
  wings: { label: 'Wings', icon: Hand, tone: 'info' },
}

export const LINEAGE_KINDS: Partial<Record<Schema['BondKind'], Named>> = {
  copy_of: { label: 'Copy of', icon: Copy, tone: 'warning' },
  merged_into: { label: 'Merged into', icon: Merge, tone: 'warning' },
  divided_from: { label: 'Divided from', icon: Split, tone: 'warning' },
  transferred_from: { label: 'Moved from', icon: MoveRight, tone: 'info' },
  restored_from: { label: 'Restored from', icon: RotateCcw, tone: 'info' },
  made_mind_of: { label: 'Made mind of', icon: Cpu, tone: 'verdigris' },
  hosted_by: { label: 'Hosted by', icon: Server, tone: 'info' },
  linked_with: { label: 'Linked with', icon: Link2, tone: 'success' },
}

export const COMMODITIES: Record<Schema['Commodity'], Named> = {
  food: { label: 'Food', icon: Wheat, tone: 'success' },
  ore: { label: 'Ore', icon: Pickaxe, tone: 'muted' },
  goods: { label: 'Goods', icon: Package, tone: 'gold' },
}
