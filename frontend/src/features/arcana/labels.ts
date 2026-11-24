import {
  Anchor,
  AudioLines,
  Ban,
  BookOpen,
  Bot,
  Check,
  CircleDashed,
  Clock,
  Cloud,
  Cog,
  Copy,
  Crown,
  Database,
  Dices,
  DoorOpen,
  Droplets,
  Eye,
  Feather,
  Flame,
  Footprints,
  Gavel,
  Ghost,
  Gift,
  Globe,
  Hammer,
  Hand,
  Heart,
  HeartPulse,
  Hourglass,
  Image,
  Infinity as InfinityIcon,
  KeyRound,
  Landmark,
  Leaf,
  Lightbulb,
  Link,
  Map,
  MapPin,
  Megaphone,
  Moon,
  Mountain,
  Move,
  Music,
  PawPrint,
  Repeat,
  Route,
  Scale,
  ScrollText,
  Shield,
  ShieldAlert,
  Skull,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Target,
  Trash2,
  Users,
  Wand2,
  Wind,
  X,
  Zap,
  type LucideIcon,
  Link2,
  Orbit,
  Lock,
  MessageSquare,
  HandHeart,
  Gem,
  GitBranch,
  Droplet,
  Puzzle,
  UserX,
  Baby,
  Book,
  Earth,
  GraduationCap,
  Handshake,
  LockKeyhole,
  MountainSnow,
  Pyramid,
  Tornado,
  Trophy,
  Users2,
  Waves,
  Layers3,
  MessageCircle,
  Bandage,
  Layers,
  Scale3d,
  ShieldHalf,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const TECHNIQUES: Record<Schema['SpellTechnique'], Named> = {
  create: { label: 'Create', icon: Sprout, tone: 'success' },
  perceive: { label: 'Perceive', icon: Eye, tone: 'info' },
  transform: { label: 'Transform', icon: Repeat, tone: 'verdigris' },
  destroy: { label: 'Destroy', icon: Zap, tone: 'danger' },
  control: { label: 'Control', icon: Hand, tone: 'warning' },
  bind: { label: 'Bind', icon: Link, tone: 'warning' },
  summon: { label: 'Summon', icon: Ghost, tone: 'verdigris' },
  ward: { label: 'Ward', icon: Shield, tone: 'gold' },
  drain: { label: 'Drain', icon: Droplets, tone: 'danger' },
  mimic: { label: 'Mimic', icon: Copy, tone: 'verdigris' },
  heal: { label: 'Heal', icon: Heart, tone: 'verdigris' },
  move: { label: 'Move', icon: Layers, tone: 'verdigris' },
  speak: { label: 'Speak', icon: MessageCircle, tone: 'verdigris' },
}

export const FORMS: Record<Schema['SpellForm'], Named> = {
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  water: { label: 'Water', icon: Droplets, tone: 'info' },
  air: { label: 'Air', icon: Wind, tone: 'info' },
  earth: { label: 'Earth', icon: Mountain, tone: 'muted' },
  plant: { label: 'Plant', icon: Leaf, tone: 'success' },
  animal: { label: 'Animal', icon: PawPrint, tone: 'verdigris' },
  body: { label: 'Body', icon: Heart, tone: 'danger' },
  mind: { label: 'Mind', icon: Lightbulb, tone: 'info' },
  image: { label: 'Image', icon: Image, tone: 'gold' },
  spirit: { label: 'Spirit', icon: Ghost, tone: 'verdigris' },
  time: { label: 'Time', icon: Hourglass, tone: 'warning' },
  void: { label: 'Void', icon: CircleDashed, tone: 'muted' },
  death: { label: 'Death', icon: Skull, tone: 'danger' },
  light: { label: 'Light', icon: Sun, tone: 'gold' },
  space: { label: 'Space', icon: Move, tone: 'info' },
  force: { label: 'Force', icon: Tornado, tone: 'warning' },
  sound: { label: 'Sound', icon: AudioLines, tone: 'info' },
  emotion: { label: 'Emotion', icon: HeartPulse, tone: 'warning' },
  fate: { label: 'Fate', icon: Dices, tone: 'gold' },
  machine: { label: 'Machine', icon: Cog, tone: 'muted' },
  information: { label: 'Information', icon: Database, tone: 'info' },
  law: { label: 'Law', icon: Gavel, tone: 'info' },
  dream: { label: 'Dream', icon: Moon, tone: 'info' },
}

export const RANGES: Record<Schema['SpellRange'], Named> = {
  touch: { label: 'Touch', icon: Hand, tone: 'muted' },
  sight: { label: 'Sight', icon: Eye, tone: 'info' },
  region: { label: 'Region', icon: Map, tone: 'verdigris' },
  world: { label: 'World', icon: Globe, tone: 'gold' },
  linked: { label: 'Through a link', icon: Link2, tone: 'danger' },
  cosmos: { label: 'Beyond the world', icon: Orbit, tone: 'gold' },
  dimension: { label: 'Dimension', icon: Layers3, tone: 'gold' },
}

export const DURATIONS: Record<Schema['SpellDuration'], Named> = {
  instant: { label: 'Instant', icon: Zap, tone: 'muted' },
  season: { label: 'A season', icon: Cloud, tone: 'info' },
  epoch: { label: 'An epoch', icon: Clock, tone: 'verdigris' },
  permanent: { label: 'Permanent', icon: InfinityIcon, tone: 'gold' },
  sustained: { label: 'While sustained', icon: Hourglass, tone: 'warning' },
  until_condition: {
    label: 'Until a condition is met',
    icon: Lock,
    tone: 'danger',
  },
  lifetime: {
    label: 'Lifetime',
    icon: LockKeyhole,
    tone: 'danger',
  },
}

export const RITE_CONDITIONS: Record<Schema['RiteCondition'], Named> = {
  act: {
    label: 'Until its bearer does an act',
    icon: Footprints,
    tone: 'warning',
  },
  time: { label: 'Until a set time', icon: Clock, tone: 'info' },
  word: {
    label: 'Until its caster lifts it by word',
    icon: MessageSquare,
    tone: 'verdigris',
  },
  deed: {
    label: 'Until someone does a deed for its bearer',
    icon: HandHeart,
    tone: 'gold',
  },
}

export const RITE_ENDS: Record<Schema['RiteEnd'], Named> = {
  caster_gone: { label: 'Its caster is gone', icon: Ban, tone: 'muted' },
  caster_struck: { label: 'Its caster was struck', icon: Zap, tone: 'danger' },
  condition_met: {
    label: 'Its condition was met',
    icon: Lock,
    tone: 'verdigris',
  },
  target_gone: {
    label: 'Target gone',
    icon: Target,
    tone: 'verdigris',
  },
}

export const TARGETS: Record<Schema['SpellTarget'], Named> = {
  one: { label: 'One', icon: Target, tone: 'muted' },
  group: { label: 'A group', icon: Users, tone: 'info' },
  structure: { label: 'A structure', icon: Landmark, tone: 'warning' },
  region: { label: 'A region', icon: Map, tone: 'verdigris' },
  item: { label: 'An item', icon: Gem, tone: 'info' },
  line: { label: 'A line of descent', icon: GitBranch, tone: 'warning' },
  world: { label: 'A whole world', icon: Globe, tone: 'gold' },
  species: { label: 'Species', icon: Earth, tone: 'gold' },
  people: { label: 'People', icon: Users2, tone: 'gold' },
}

export const RECHARGES: Record<Schema['RechargeRule'], Named> = {
  site: { label: 'At a magic site', icon: MapPin, tone: 'verdigris' },
  vis: { label: 'From vis', icon: Sparkles, tone: 'gold' },
  moon: { label: 'Under a full moon', icon: Moon, tone: 'info' },
  none: { label: 'Never', icon: Ban, tone: 'muted' },
  sky_event: { label: 'At a sign in the sky', icon: Star, tone: 'info' },
  bodily_offering: {
    label: 'By an offering of the body',
    icon: Droplet,
    tone: 'danger',
  },
  worship: {
    label: 'Worship',
    icon: Droplets,
    tone: 'danger',
  },
  rest: {
    label: 'Rest',
    icon: Waves,
    tone: 'danger',
  },
}

export const LAW_SOURCES: Record<Schema['LawSource'], Named> = {
  authored: { label: 'Authored by a god', icon: ScrollText, tone: 'info' },
  enchantment: { label: 'Global enchantment', icon: Wand2, tone: 'gold' },
}

export const REALMS: Record<Schema['MythicRealm'], Named> = {
  palace: { label: "A god's palace", icon: Crown, tone: 'gold' },
  dead: { label: 'The realm of the dead', icon: Skull, tone: 'muted' },
  dream: { label: 'A dream world', icon: Moon, tone: 'info' },
  sacred_site: {
    label: 'Where the myth happened',
    icon: MapPin,
    tone: 'verdigris',
  },
}

export const QUEST_STATES: Record<Schema['HeroquestState'], Named> = {
  questing: { label: 'Questing', icon: Footprints, tone: 'info' },
  succeeded: { label: 'Succeeded', icon: Check, tone: 'success' },
  failed: { label: 'Failed', icon: X, tone: 'danger' },
  trapped: { label: 'Soul trapped', icon: KeyRound, tone: 'warning' },
  broken: { label: 'Myth broken', icon: Trash2, tone: 'danger' },
}

export const BOONS: Record<Schema['HeroquestBoon'], Named> = {
  blessing: { label: 'A blessing', icon: Sparkles, tone: 'gold' },
  item: { label: 'A magical item', icon: Gift, tone: 'verdigris' },
  rite: { label: 'A rite', icon: Wand2, tone: 'info' },
  lifted_curse: { label: 'A lifted curse', icon: ShieldAlert, tone: 'success' },
  renewed_land: { label: 'A renewed land', icon: Sprout, tone: 'success' },
  favour: { label: "The god's favour", icon: Heart, tone: 'gold' },
  true_name: { label: 'A true name', icon: KeyRound, tone: 'warning' },
  title: { label: 'A title', icon: Crown, tone: 'gold' },
  knowledge: { label: 'Knowledge', icon: Book, tone: 'gold' },
  healing: { label: 'Healing', icon: Bandage, tone: 'gold' },
}

export const TRIALS: Record<Schema['QuestTrial'], Named> = {
  skill: { label: 'A trial of skill', icon: Hammer, tone: 'info' },
  passion: { label: 'A trial of passion', icon: Heart, tone: 'danger' },
  conviction: { label: 'A trial of conviction', icon: Gavel, tone: 'warning' },
  faith: { label: 'A trial of faith', icon: Sparkles, tone: 'gold' },
  cunning: { label: 'A trial of cunning', icon: Puzzle, tone: 'verdigris' },
  endurance: { label: 'A trial of endurance', icon: Mountain, tone: 'warning' },
  sacrifice: { label: 'Sacrifice', icon: MountainSnow, tone: 'warning' },
  mercy: { label: 'Mercy', icon: Pyramid, tone: 'warning' },
}

export const MANTLING_STATES: Record<Schema['MantlingState'], Named> = {
  walking: { label: "Walking a god's path", icon: Footprints, tone: 'info' },
  ascended: { label: 'Ascended', icon: Star, tone: 'gold' },
  replaced: { label: 'Took a god’s place', icon: Crown, tone: 'gold' },
  blocked: { label: 'Blocked', icon: Ban, tone: 'danger' },
  failed: { label: 'Failed', icon: X, tone: 'muted' },
  contested: { label: 'Contested', icon: Trophy, tone: 'muted' },
}

export const ORIGINS: Record<Schema['ServitorOrigin'], Named> = {
  made: { label: 'Made by its god', icon: Hammer, tone: 'gold' },
  raised: {
    label: "Raised from a saint's soul",
    icon: Feather,
    tone: 'success',
  },
  summoned: { label: 'Summoned by a rite', icon: Wand2, tone: 'info' },
  defected: {
    label: 'Come over from another god',
    icon: UserX,
    tone: 'warning',
  },
  born: { label: 'Born to its god', icon: Baby, tone: 'gold' },
  ascended: { label: 'Ascended', icon: Sprout, tone: 'gold' },
  bargained: { label: 'Bargained', icon: Handshake, tone: 'gold' },
}

export const ROLES: Record<Schema['ServitorRole'], Named> = {
  messenger: { label: 'Messenger', icon: Megaphone, tone: 'info' },
  guard: { label: 'Guard', icon: ShieldHalf, tone: 'gold' },
  judge: { label: 'Judge of souls', icon: Scale, tone: 'verdigris' },
  host: { label: 'Host', icon: Swords, tone: 'danger' },
  spy: { label: 'Spy', icon: Eye, tone: 'muted' },
  agent: { label: 'Agent at its post', icon: Feather, tone: 'success' },
  avenger: { label: 'Avenger', icon: Flame, tone: 'danger' },
  guide_of_souls: { label: 'Guide of souls', icon: Route, tone: 'muted' },
  worshipper: { label: 'Worshipper', icon: Music, tone: 'verdigris' },
  warden: { label: 'Warden of its post', icon: Shield, tone: 'gold' },
  scribe: { label: 'Keeper of accounts', icon: ScrollText, tone: 'info' },
  healer: { label: 'Healer', icon: Heart, tone: 'info' },
  teacher: { label: 'Teacher', icon: GraduationCap, tone: 'info' },
}

export const GEAS_MODES: Record<Schema['GeasMode'], Named> = {
  taboo: { label: 'Taboo', icon: Ban, tone: 'danger' },
  duty: { label: 'Duty', icon: Check, tone: 'success' },
  condition: { label: 'Condition', icon: Clock, tone: 'success' },
}

export const GEAS_STATES: Record<Schema['GeasState'], Named> = {
  kept: { label: 'Kept', icon: Shield, tone: 'success' },
  broken: { label: 'Broken', icon: Skull, tone: 'danger' },
}

export const GEAS_LAYERS: Record<Schema['GeasLayer'], Named> = {
  seer: { label: 'A seer', icon: Eye, tone: 'info' },
  god: { label: 'A god', icon: Sun, tone: 'gold' },
  rite: { label: 'A rite', icon: Wand2, tone: 'verdigris' },
  kin: { label: 'Kin', icon: Users, tone: 'warning' },
  self: { label: 'Its bearer, by vow', icon: Hand, tone: 'danger' },
  law: { label: 'Law', icon: Gavel, tone: 'danger' },
}

export const OFFICES: Record<Schema['CosmicOffice'], Named> = {
  dead: { label: 'Office of the dead', icon: Skull, tone: 'muted' },
  gates: { label: 'Office of the gates', icon: Anchor, tone: 'info' },
  stars: { label: 'Office of the stars', icon: Star, tone: 'gold' },
  oaths: { label: 'Office of oaths', icon: Gavel, tone: 'warning' },
  herald: { label: 'Office of the herald', icon: Megaphone, tone: 'verdigris' },
  hunt: { label: 'Office of the hunt', icon: PawPrint, tone: 'success' },
}

export const OFFICE_DUTIES: Record<Schema['OfficeDuty'], Named> = {
  the_dead: { label: 'Duty to the dead', icon: Skull, tone: 'muted' },
  thresholds: { label: 'Duty to thresholds', icon: DoorOpen, tone: 'info' },
  the_sky: { label: 'Duty to the sky', icon: Star, tone: 'gold' },
  oaths: { label: 'Duty to oaths', icon: Gavel, tone: 'warning' },
  messages: { label: 'Duty to messages', icon: Megaphone, tone: 'verdigris' },
  the_hunt: { label: 'Duty to the hunt', icon: PawPrint, tone: 'success' },
  judgement: { label: 'Duty of judgement', icon: Scale, tone: 'warning' },
  memory: { label: 'Duty of memory', icon: BookOpen, tone: 'info' },
  making: { label: 'Duty of making', icon: Hammer, tone: 'gold' },
  healing: { label: 'Duty of healing', icon: HeartPulse, tone: 'success' },
  learning: { label: 'Learning', icon: Book, tone: 'success' },
  trade: { label: 'Trade', icon: Scale3d, tone: 'success' },
}

export const OFFICE_CHOICES: Record<Schema['OfficeChoice'], Named> = {
  council: { label: 'Chosen by the council', icon: Users, tone: 'info' },
  creator: { label: 'Given by the Creator', icon: Sun, tone: 'gold' },
  conquest: { label: 'Taken by conquest', icon: Swords, tone: 'danger' },
  mantling: { label: 'Taken by mantling', icon: Crown, tone: 'gold' },
  inheritance: { label: 'Inheritance', icon: Gem, tone: 'gold' },
}

export const MAGIC_ICON = Wand2
export const MYTH_ICON = BookOpen
export const SERVANT_ICON = Bot

export function table(
  record: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(record).map(([key, value]) => [key, value.label])
  )
}

export function words(value: string): string {
  const plain = value.replaceAll('_', ' ')
  return plain.charAt(0).toUpperCase() + plain.slice(1)
}

export function listed(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}
