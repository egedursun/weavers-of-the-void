import {
  Activity,
  Baby,
  Ban,
  Biohazard,
  Bomb,
  Bone,
  BookOpen,
  BookOpenCheck,
  Brain,
  Briefcase,
  Bug,
  CalendarCheck,
  CalendarClock,
  CalendarX,
  Castle,
  Clapperboard,
  CloudSun,
  Crown,
  DoorOpen,
  Drama,
  Droplets,
  Eye,
  Feather,
  Flag,
  Flame,
  Footprints,
  Gavel,
  Gem,
  Ghost,
  Hammer,
  Gift,
  Handshake,
  Heart,
  HeartCrack,
  Home,
  Hourglass,
  KeyRound,
  Landmark,
  Layers,
  Library,
  Link2,
  Lock,
  Map,
  MapPin,
  Megaphone,
  Minus,
  Mountain,
  Music,
  Network,
  Orbit,
  PartyPopper,
  Puzzle,
  RadioTower,
  Repeat,
  Rocket,
  Route,
  Scale,
  ScanSearch,
  ScrollText,
  Search,
  Shield,
  ShieldAlert,
  Shovel,
  Shuffle,
  Skull,
  Smile,
  Sparkles,
  Sprout,
  Star,
  Store,
  Sun,
  Sunrise,
  Swords,
  Tent,
  TrendingUp,
  Trophy,
  type LucideIcon,
  Users,
  Utensils,
  Vote,
  Waves,
  Waypoints,
  Wheat,
  Wind,
  Zap,
  Award,
  Building2,
  Compass,
  Diamond,
  FlameKindling,
  Sword,
  UsersRound,
  Bandage,
  Coins,
  Scroll,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const GATHERING_KINDS: Record<Schema['GatheringKind'], Named> = {
  feast: { label: 'Feast', icon: Utensils, tone: 'gold' },
  wedding: { label: 'Wedding', icon: Heart, tone: 'success' },
  funeral: { label: 'Funeral', icon: Skull, tone: 'muted' },
  coronation: { label: 'Accession', icon: Crown, tone: 'gold' },
  tournament: { label: 'Tournament', icon: Trophy, tone: 'warning' },
  hunt: { label: 'Hunt', icon: Footprints, tone: 'verdigris' },
  pilgrimage: { label: 'Pilgrimage', icon: Route, tone: 'info' },
  council: { label: 'Council', icon: Users, tone: 'info' },
  summit: { label: 'Summit', icon: Handshake, tone: 'success' },
  festival: { label: 'Festival', icon: PartyPopper, tone: 'gold' },
  fair: { label: 'Fair', icon: Coins, tone: 'verdigris' },
  games: { label: 'Games', icon: Flag, tone: 'warning' },
  performance: { label: 'Performance', icon: Drama, tone: 'info' },
  trial: { label: 'Trial', icon: Gavel, tone: 'warning' },
  execution: { label: 'Execution', icon: Ban, tone: 'danger' },
  procession: { label: 'Procession', icon: Megaphone, tone: 'info' },
  milestone: { label: 'Milestone', icon: Star, tone: 'success' },
  wake: { label: 'Wake', icon: Hourglass, tone: 'muted' },
  examination: { label: 'Examination', icon: BookOpenCheck, tone: 'info' },
  election: { label: 'Election', icon: Vote, tone: 'info' },
  rally: { label: 'Rally', icon: Megaphone, tone: 'warning' },
  strike: { label: 'Strike', icon: Bandage, tone: 'danger' },
  convention: { label: 'Convention', icon: Briefcase, tone: 'verdigris' },
  launch: { label: 'Launch', icon: Rocket, tone: 'gold' },
  broadcast: { label: 'Broadcast', icon: RadioTower, tone: 'info' },
  testing: { label: 'Testing for gifts', icon: ScanSearch, tone: 'verdigris' },
  exhibition: { label: 'Exhibition', icon: Landmark, tone: 'info' },
  trade_fair: { label: 'Trade fair', icon: Store, tone: 'gold' },
  summit_of_gods: { label: 'Summit of the gods', icon: Sparkles, tone: 'gold' },
  network_gathering: {
    label: 'Gathering through a network',
    icon: Network,
    tone: 'verdigris',
  },
  realm_gathering: {
    label: 'Gathering in a made realm',
    icon: Orbit,
    tone: 'verdigris',
  },
  mourning: { label: 'Mourning', icon: HeartCrack, tone: 'muted' },
  initiation: { label: 'Initiation', icon: KeyRound, tone: 'info' },
  sport_match: { label: 'Match', icon: Trophy, tone: 'warning' },
  commemoration: { label: 'Commemoration', icon: Building2, tone: 'muted' },
  muster: { label: 'Muster', icon: Swords, tone: 'warning' },
  gift_exchange: { label: 'Gift exchange', icon: Gift, tone: 'gold' },
  reunion: { label: 'Reunion', icon: UsersRound, tone: 'success' },
}

export const GATHERING_STATUSES: Record<Schema['GatheringStatus'], Named> = {
  planned: { label: 'Planned', icon: CalendarClock, tone: 'info' },
  held: { label: 'Held', icon: CalendarCheck, tone: 'success' },
  disrupted: { label: 'Disrupted', icon: Zap, tone: 'danger' },
  cancelled: { label: 'Cancelled', icon: CalendarX, tone: 'muted' },
}

export const GATHERING_OUTCOMES: Record<Schema['GatheringOutcome'], Named> = {
  convivial: { label: 'Convivial', icon: Smile, tone: 'success' },
  uneventful: { label: 'Uneventful', icon: Minus, tone: 'muted' },
  quarrelsome: { label: 'Quarrelsome', icon: HeartCrack, tone: 'warning' },
  violent: { label: 'Violent', icon: Swords, tone: 'danger' },
  massacre: { label: 'Massacre', icon: Skull, tone: 'danger' },
}

export const MILESTONES: Record<Schema['Milestone'], Named> = {
  birth: { label: 'A birth', icon: Baby, tone: 'success' },
  coming_of_age: { label: 'Coming of age', icon: Sprout, tone: 'verdigris' },
  anniversary: { label: 'An anniversary', icon: Repeat, tone: 'gold' },
}

export const ATTENDANCE_REASONS: Record<Schema['AttendanceReason'], Named> = {
  host: { label: 'Host', icon: Home, tone: 'gold' },
  kin: { label: 'Kin', icon: Users, tone: 'success' },
  friend: { label: 'Friend', icon: Smile, tone: 'success' },
  obligation: { label: 'Obligation', icon: Scale, tone: 'info' },
  faith: { label: 'Faith', icon: Sparkles, tone: 'info' },
  renown: { label: 'Renown', icon: Star, tone: 'gold' },
  neighbour: { label: 'Neighbour', icon: MapPin, tone: 'verdigris' },
  summoned: { label: 'Summoned by the gods', icon: Sun, tone: 'warning' },
}

export const GUEST_ROLES: Record<Schema['GuestRole'], Named> = {
  host: { label: 'Host', icon: Home, tone: 'gold' },
  guest: { label: 'Guest', icon: Users, tone: 'info' },
  honoured: { label: 'Honoured', icon: Star, tone: 'gold' },
  contestant: { label: 'Contestant', icon: Trophy, tone: 'warning' },
  performer: { label: 'Performer', icon: Music, tone: 'info' },
  accused: { label: 'Accused', icon: Gavel, tone: 'danger' },
  mourned: { label: 'Mourned', icon: Hourglass, tone: 'muted' },
  wedded: { label: 'Wedded', icon: Heart, tone: 'success' },
  crowned: { label: 'New ruler', icon: Crown, tone: 'gold' },
  envoy: { label: 'Envoy', icon: Handshake, tone: 'verdigris' },
}

export const COLLECTION_KINDS: Record<Schema['CollectionKind'], Named> = {
  war: { label: 'War', icon: Sword, tone: 'danger' },
  battle: { label: 'Battle', icon: Swords, tone: 'danger' },
  siege: { label: 'Siege', icon: Castle, tone: 'danger' },
  duel: { label: 'Duel', icon: Swords, tone: 'warning' },
  abduction: { label: 'Abduction', icon: KeyRound, tone: 'danger' },
  beast_attack: { label: 'Beast attack', icon: Footprints, tone: 'danger' },
  raid: { label: 'Raid', icon: FlameKindling, tone: 'danger' },
  persecution: { label: 'Persecution', icon: ShieldAlert, tone: 'danger' },
  purge: { label: 'Purge', icon: Ban, tone: 'danger' },
  insurrection: { label: 'Insurrection', icon: Flag, tone: 'warning' },
  coup: { label: 'Coup', icon: Crown, tone: 'warning' },
  succession_crisis: {
    label: 'Succession crisis',
    icon: Award,
    tone: 'warning',
  },
  occupation: { label: 'Occupation', icon: Shield, tone: 'warning' },
  journey: { label: 'Journey', icon: Map, tone: 'info' },
  pilgrimage: { label: 'Pilgrimage', icon: Route, tone: 'info' },
  competition: { label: 'Competition', icon: Trophy, tone: 'gold' },
  performance: { label: 'Performance', icon: Drama, tone: 'info' },
  procession: { label: 'Procession', icon: Megaphone, tone: 'info' },
  ceremony: { label: 'Ceremony', icon: Sparkles, tone: 'gold' },
  wedding: { label: 'Wedding', icon: Heart, tone: 'success' },
  funeral: { label: 'Funeral', icon: Skull, tone: 'muted' },
  coronation: { label: 'Accession', icon: Crown, tone: 'gold' },
  feast: { label: 'Feast', icon: Utensils, tone: 'gold' },
  tournament: { label: 'Tournament', icon: Trophy, tone: 'warning' },
  hunt: { label: 'Hunt', icon: Compass, tone: 'verdigris' },
  council: { label: 'Council', icon: Users, tone: 'info' },
  summit: { label: 'Summit', icon: Handshake, tone: 'success' },
  plague: { label: 'Plague', icon: Bug, tone: 'danger' },
  famine: { label: 'Famine', icon: Wheat, tone: 'warning' },
  migration: { label: 'Migration', icon: Tent, tone: 'info' },
  founding: { label: 'Founding', icon: Landmark, tone: 'success' },
  theft: { label: 'Theft', icon: Gem, tone: 'warning' },
  investigation: { label: 'Investigation', icon: Search, tone: 'info' },
  trial: { label: 'Trial', icon: Gavel, tone: 'warning' },
  conversion_wave: {
    label: 'Wave of conversion',
    icon: Sparkles,
    tone: 'info',
  },
  schism: { label: 'Schism', icon: Shuffle, tone: 'warning' },
  excavation: { label: 'Excavation', icon: Shovel, tone: 'verdigris' },
  heroquest: { label: 'Heroquest', icon: Route, tone: 'gold' },
  riot: { label: 'Riot', icon: Flame, tone: 'danger' },
  panic: { label: 'Panic', icon: Wind, tone: 'warning' },
  movement: { label: 'Movement', icon: Flag, tone: 'gold' },
  storylet: { label: 'Storylet', icon: Drama, tone: 'verdigris' },
}

export const COLLECTION_ROLES: Record<Schema['CollectionRole'], Named> = {
  leader: { label: 'Leader', icon: Crown, tone: 'gold' },
  member: { label: 'Member', icon: UsersRound, tone: 'info' },
  victim: { label: 'Victim', icon: HeartCrack, tone: 'danger' },
  witness: { label: 'Witness', icon: Eye, tone: 'muted' },
  host: { label: 'Host', icon: Home, tone: 'gold' },
  guest: { label: 'Guest', icon: Users, tone: 'info' },
  winner: { label: 'Winner', icon: Trophy, tone: 'success' },
  loser: { label: 'Loser', icon: Flag, tone: 'warning' },
  founder: { label: 'Founder', icon: Landmark, tone: 'success' },
  accused: { label: 'Accused', icon: Gavel, tone: 'danger' },
  finder: { label: 'Finder', icon: Search, tone: 'verdigris' },
  place: { label: 'Place', icon: MapPin, tone: 'verdigris' },
}

export const STORYTELLER_PROFILES: Record<
  Schema['StorytellerProfile'],
  Named & { hint: string }
> = {
  steady: {
    label: 'Steady',
    icon: Minus,
    tone: 'info',
    hint: 'The aim stays at one level all along.',
  },
  rising: {
    label: 'Rising',
    icon: TrendingUp,
    tone: 'warning',
    hint: 'The aim climbs with the ages.',
  },
  cyclic: {
    label: 'Cyclic',
    icon: Repeat,
    tone: 'verdigris',
    hint: 'The aim rises and falls in turn.',
  },
  chaotic: {
    label: 'Chaotic',
    icon: Shuffle,
    tone: 'danger',
    hint: 'The aim jumps without warning.',
  },
  slow_burn: {
    label: 'Slow burn',
    icon: Flame,
    tone: 'warning',
    hint: 'The aim starts low and climbs a little every epoch.',
  },
  episodic: {
    label: 'Episodic',
    icon: Clapperboard,
    tone: 'info',
    hint: 'Quiet stretches broken by a sharp peak at the end of each episode.',
  },
  gentle: {
    label: 'Gentle',
    icon: Feather,
    tone: 'success',
    hint: 'Keeps tension low and leans toward recoveries',
  },
  seasonal: {
    label: 'Seasonal',
    icon: CloudSun,
    tone: 'verdigris',
    hint: 'Raises and lowers tension with the turn of the seasons',
  },
}

export const TENSION_BANDS: Record<Schema['TensionBand'], Named> = {
  quiet: { label: 'Quiet', icon: Feather, tone: 'info' },
  in_band: { label: 'On its aim', icon: Activity, tone: 'success' },
  heated: { label: 'Heated', icon: Flame, tone: 'danger' },
}

export const SPONTANEOUS_KINDS: Record<Schema['SpontaneousKind'], Named> = {
  beast_awakening: {
    label: 'Beasts awakened',
    icon: Footprints,
    tone: 'danger',
  },
  raid: { label: 'Raids', icon: Flame, tone: 'danger' },
  comet: { label: 'Comets', icon: Star, tone: 'warning' },
  plague: { label: 'Plagues', icon: Bug, tone: 'danger' },
  claimant: { label: 'Claimants', icon: Crown, tone: 'warning' },
}

export const ROOM_KINDS: Record<Schema['SiteRoomKind'], Named> = {
  gate: { label: 'Gate', icon: DoorOpen, tone: 'muted' },
  hall: { label: 'Hall', icon: Landmark, tone: 'info' },
  stair: { label: 'Stair', icon: Layers, tone: 'muted' },
  cell: { label: 'Cell', icon: KeyRound, tone: 'warning' },
  chamber: { label: 'Chamber', icon: DoorOpen, tone: 'info' },
  vault: { label: 'Vault', icon: Gem, tone: 'gold' },
  shrine: { label: 'Shrine', icon: Sparkles, tone: 'info' },
  lair: { label: 'Lair', icon: Footprints, tone: 'danger' },
  library: { label: 'Library', icon: Library, tone: 'verdigris' },
  armoury: { label: 'Armoury', icon: Shield, tone: 'warning' },
  crypt: { label: 'Crypt', icon: Skull, tone: 'muted' },
  laboratory: { label: 'Laboratory', icon: BookOpen, tone: 'verdigris' },
  house: { label: 'House', icon: Home, tone: 'success' },
  store: { label: 'Store', icon: Store, tone: 'gold' },
  heart: { label: 'Heart of the site', icon: Heart, tone: 'danger' },
  cistern: { label: 'Cistern', icon: Droplets, tone: 'info' },
  forge: { label: 'Forge', icon: Hammer, tone: 'warning' },
}

export const CHALLENGES: Record<Schema['SiteChallenge'], Named> = {
  none: { label: 'No challenge', icon: Minus, tone: 'muted' },
  trap: { label: 'Trap', icon: Zap, tone: 'danger' },
  guardian: { label: 'Guardian', icon: Shield, tone: 'danger' },
  puzzle: { label: 'Puzzle', icon: Puzzle, tone: 'info' },
  hazard: { label: 'Hazard', icon: ShieldAlert, tone: 'warning' },
  seal: { label: 'Seal', icon: Lock, tone: 'gold' },
  maze: { label: 'Maze', icon: Waypoints, tone: 'verdigris' },
}

export const CONTENT_KINDS: Record<Schema['RoomContentKind'], Named> = {
  item: { label: 'Item', icon: Diamond, tone: 'gold' },
  spirit: { label: 'Spirit', icon: Ghost, tone: 'info' },
  beast: { label: 'Beast', icon: Footprints, tone: 'danger' },
  trap: { label: 'Trap', icon: Zap, tone: 'warning' },
  mind: { label: 'Mind', icon: Brain, tone: 'gold' },
  relic: { label: 'Relic', icon: Gem, tone: 'gold' },
  realm_gate: { label: 'Realm gate', icon: DoorOpen, tone: 'gold' },
  records: { label: 'Records', icon: ScrollText, tone: 'verdigris' },
}

export const DIG_STAGES: Record<Schema['ExcavationStage'], Named> = {
  survey: { label: 'Survey', icon: Search, tone: 'info' },
  clearing: { label: 'Clearing', icon: Shovel, tone: 'verdigris' },
  digging: { label: 'Digging', icon: Shovel, tone: 'warning' },
  deep_layers: { label: 'Deep layers', icon: Layers, tone: 'warning' },
  inner_sanctum: { label: 'Inner sanctum', icon: KeyRound, tone: 'gold' },
}

export const DIG_STATUSES: Record<Schema['ExcavationStatus'], Named> = {
  open: { label: 'Open', icon: Shovel, tone: 'success' },
  stalled: { label: 'Stalled', icon: Hourglass, tone: 'warning' },
  finished: { label: 'Finished', icon: CalendarCheck, tone: 'gold' },
  collapsed: { label: 'Collapsed', icon: Mountain, tone: 'danger' },
  abandoned: { label: 'Abandoned', icon: CalendarX, tone: 'muted' },
}

export const DIG_RISKS: Record<Schema['ExcavationRisk'], Named> = {
  none: { label: 'No risk', icon: Minus, tone: 'muted' },
  curse: { label: 'Curse', icon: Skull, tone: 'danger' },
  spirit: { label: 'Spirit', icon: Ghost, tone: 'warning' },
  collapse: { label: 'Collapse', icon: Mountain, tone: 'danger' },
  flooding: { label: 'Flooding', icon: Waves, tone: 'info' },
  gas: { label: 'Bad air', icon: Wind, tone: 'warning' },
  disease: { label: 'Sealed sickness', icon: Biohazard, tone: 'danger' },
}

export const DIG_FINDS: Record<Schema['ExcavationFind'], Named> = {
  nothing: { label: 'Nothing', icon: Minus, tone: 'muted' },
  artifact: { label: 'Artifact', icon: Gem, tone: 'gold' },
  book: { label: 'Book', icon: BookOpen, tone: 'verdigris' },
  technique: { label: 'Lost technique', icon: ScrollText, tone: 'info' },
  regalia: { label: 'Regalia', icon: Crown, tone: 'gold' },
  route_map: { label: 'Map of a route', icon: Map, tone: 'success' },
  waking: { label: 'Sleepers woken', icon: Sunrise, tone: 'info' },
  remains: { label: 'Remains', icon: Bone, tone: 'muted' },
  records: { label: 'Records', icon: Scroll, tone: 'verdigris' },
}

export const BATTLEFIELD_FEATURES: Record<Schema['BattlefieldFeature'], Named> =
  {
    mass_grave: { label: 'Mass grave', icon: Skull, tone: 'muted' },
    salvage_field: { label: 'Field of salvage', icon: Link2, tone: 'warning' },
    earthworks: { label: 'Old earthworks', icon: Shield, tone: 'info' },
    ordnance: { label: 'Remnants of arms', icon: Bomb, tone: 'danger' },
    memorial: { label: 'Memorial', icon: Landmark, tone: 'gold' },
  }

export function table(
  record: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(record).map(([key, value]) => [key, value.label])
  )
}

export function words(value: string): string {
  return value.replaceAll('_', ' ')
}
