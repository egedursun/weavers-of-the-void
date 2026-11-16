import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Ban,
  BookOpen,
  Brain,
  CircleDot,
  Clock,
  Cloud,
  CloudFog,
  Compass,
  Crosshair,
  Crown,
  DoorClosed,
  DoorOpen,
  Droplet,
  Ear,
  Eye,
  EyeOff,
  Feather,
  Flame,
  Gavel,
  Gem,
  Ghost,
  Gift,
  Globe,
  Hand,
  Handshake,
  Heart,
  HeartPulse,
  Hourglass,
  Infinity as Forever,
  Key,
  Languages,
  Layers,
  Link,
  Map as MapIcon,
  MapPin,
  Moon,
  Mountain,
  Palette,
  Repeat,
  Route,
  Scale,
  Search,
  Shield,
  ShieldCheck,
  Skull,
  Snowflake,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Target,
  Users,
  Volume2,
  Wind,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const HORROR_ICON = Ghost

export const HORROR_TARGETS: Record<Schema['HorrorTarget'], Named> = {
  light: { label: 'Light', icon: Sun, tone: 'gold' },
  sound: { label: 'Sound', icon: Volume2, tone: 'info' },
  weather: { label: 'Weather', icon: Cloud, tone: 'info' },
  time: { label: 'Time', icon: Clock, tone: 'verdigris' },
  memory: { label: 'Memory', icon: Brain, tone: 'warning' },
  language: { label: 'Language', icon: Languages, tone: 'warning' },
  sleep: { label: 'Sleep', icon: Moon, tone: 'info' },
  bodies: { label: 'Bodies', icon: HeartPulse, tone: 'danger' },
  minds: { label: 'Minds', icon: Brain, tone: 'danger' },
  the_dead: { label: 'The dead', icon: Skull, tone: 'muted' },
  place: { label: 'A place', icon: MapPin, tone: 'warning' },
  law: { label: 'A law of the world', icon: Gavel, tone: 'verdigris' },
}

export const HORROR_EFFECTS: Record<Schema['HorrorEffect'], Named> = {
  suppress: { label: 'Suppresses', icon: ArrowDownRight, tone: 'warning' },
  invert: { label: 'Inverts', icon: Repeat, tone: 'warning' },
  distort: { label: 'Distorts', icon: Activity, tone: 'warning' },
  multiply: { label: 'Multiplies', icon: Layers, tone: 'danger' },
  take: { label: 'Takes away', icon: Ban, tone: 'danger' },
  reveal: { label: 'Reveals', icon: Eye, tone: 'info' },
  mark: { label: 'Marks', icon: Target, tone: 'muted' },
}

export const HORROR_SCOPES: Record<Schema['HorrorScope'], Named> = {
  person: { label: 'One person', icon: CircleDot, tone: 'info' },
  community: { label: 'A community', icon: Users, tone: 'info' },
  region: { label: 'A region', icon: MapIcon, tone: 'warning' },
  world: { label: 'The whole world', icon: Globe, tone: 'danger' },
}

export const HORROR_SENSES: Record<Schema['HorrorSense'], Named> = {
  seen: { label: 'Seen', icon: Eye, tone: 'info' },
  heard: { label: 'Heard', icon: Ear, tone: 'info' },
  felt: { label: 'Felt', icon: Hand, tone: 'info' },
  dreamed: { label: 'Dreamed', icon: Moon, tone: 'verdigris' },
  absent: { label: 'Something missing', icon: EyeOff, tone: 'warning' },
  not_perceived: {
    label: 'Not perceived, only its effects',
    icon: Search,
    tone: 'muted',
  },
}

export const HORROR_SOURCES: Record<Schema['HorrorSource'], Named> = {
  outer_being: { label: 'A being from outside', icon: Ghost, tone: 'danger' },
  rift: { label: 'A rift', icon: DoorOpen, tone: 'warning' },
  phenomenon: { label: 'A phenomenon', icon: Sparkles, tone: 'info' },
  god: { label: 'A god', icon: Crown, tone: 'gold' },
  made_thing: { label: 'A made thing', icon: Key, tone: 'info' },
  unknown: { label: 'Unknown', icon: Search, tone: 'muted' },
}

export const QUEST_ICON = Compass

export const AIMS: Record<Schema['QuestAim'], Named> = {
  find: { label: 'Find', icon: Search, tone: 'info' },
  restore: { label: 'Restore', icon: Sprout, tone: 'success' },
  destroy: { label: 'Destroy', icon: Flame, tone: 'danger' },
  free: { label: 'Free', icon: DoorOpen, tone: 'success' },
  bind: { label: 'Bind', icon: Link, tone: 'warning' },
  reach: { label: 'Reach', icon: Route, tone: 'info' },
  learn: { label: 'Learn', icon: BookOpen, tone: 'info' },
  return: { label: 'Bring back', icon: Repeat, tone: 'info' },
  protect: { label: 'Protect', icon: Shield, tone: 'success' },
  avenge: { label: 'Avenge', icon: Swords, tone: 'danger' },
  hunt: { label: 'Hunt', icon: Crosshair, tone: 'warning' },
  deliver: { label: 'Deliver', icon: Gift, tone: 'info' },
  reconcile: { label: 'Reconcile', icon: Handshake, tone: 'success' },
  prove: { label: 'Prove oneself', icon: Star, tone: 'gold' },
  resolve: {
    label: 'Resolve an incident arc',
    icon: Activity,
    tone: 'verdigris',
  },
}

export const QUEST_TARGETS: Record<Schema['QuestTargetKind'], Named> = {
  star: { label: 'A star', icon: Star, tone: 'gold' },
  route: { label: 'A route', icon: Route, tone: 'info' },
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'info' },
  outer_being: { label: 'A being from outside', icon: Ghost, tone: 'danger' },
  species: { label: 'A kind of creature', icon: Feather, tone: 'warning' },
  item: { label: 'An item', icon: Gem, tone: 'gold' },
  person: { label: 'A person', icon: CircleDot, tone: 'info' },
  place: { label: 'A place', icon: MapPin, tone: 'info' },
  incident_arc: { label: 'An incident arc', icon: Activity, tone: 'verdigris' },
}

export const OBSTACLES: Record<Schema['QuestObstacle'], Named> = {
  distance: { label: 'Distance', icon: Route, tone: 'muted' },
  guardian: { label: 'A guardian', icon: Shield, tone: 'warning' },
  riddle: { label: 'A riddle', icon: Key, tone: 'info' },
  rival: { label: 'A rival', icon: Swords, tone: 'danger' },
  law: { label: 'A law', icon: Gavel, tone: 'verdigris' },
  concealment: { label: 'Concealment', icon: EyeOff, tone: 'muted' },
  danger_of_place: {
    label: 'A dangerous place',
    icon: Mountain,
    tone: 'danger',
  },
  cost: { label: 'A cost', icon: Scale, tone: 'warning' },
}

export const REWARDS: Record<Schema['QuestReward'], Named> = {
  renown: { label: 'Renown', icon: Crown, tone: 'gold' },
  power: { label: 'Power', icon: Zap, tone: 'gold' },
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'info' },
  item: { label: 'A prize', icon: Gem, tone: 'gold' },
  standing: { label: 'Standing', icon: Users, tone: 'info' },
  office: { label: 'An office', icon: Gavel, tone: 'info' },
  cure: { label: 'Healing', icon: HeartPulse, tone: 'success' },
  peace: { label: 'Peace', icon: Handshake, tone: 'success' },
}

export const QUEST_STATES: Record<Schema['HeroQuestStatus'], Named> = {
  active: { label: 'Under way', icon: Compass, tone: 'info' },
  succeeded: { label: 'Succeeded', icon: Star, tone: 'success' },
  failed: { label: 'Failed', icon: Ban, tone: 'danger' },
  abandoned: { label: 'Abandoned', icon: Repeat, tone: 'muted' },
  died: { label: 'Ended in death', icon: Skull, tone: 'danger' },
}

export const SCALES: Record<Schema['QuestScale'], Named> = {
  personal: { label: 'Personal', icon: CircleDot, tone: 'info' },
  legendary: { label: 'Legendary', icon: Star, tone: 'gold' },
}

export const ATTACK_ICON = Swords

export const DELIVERIES: Record<Schema['AttackDelivery'], Named> = {
  breath: { label: 'Breath', icon: Wind, tone: 'warning' },
  spit: { label: 'Spit', icon: Droplet, tone: 'warning' },
  spray: { label: 'Spray', icon: CloudFog, tone: 'warning' },
  emanation: { label: 'Emanation', icon: Sparkles, tone: 'info' },
  gaze: { label: 'Gaze', icon: Eye, tone: 'danger' },
  voice: { label: 'Voice', icon: Volume2, tone: 'info' },
  touch: { label: 'Touch', icon: Hand, tone: 'muted' },
  spores: { label: 'Spores', icon: Sprout, tone: 'success' },
  bite: { label: 'Bite', icon: Skull, tone: 'danger' },
  sting: { label: 'Sting', icon: Target, tone: 'danger' },
}

export const ATTACK_EFFECTS: Record<Schema['AttackEffect'], Named> = {
  heat: { label: 'Heat', icon: Flame, tone: 'danger' },
  cold: { label: 'Cold', icon: Snowflake, tone: 'info' },
  corrosion: { label: 'Corrosion', icon: Droplet, tone: 'warning' },
  shock: { label: 'Shock', icon: Zap, tone: 'warning' },
  venom: { label: 'Venom', icon: Droplet, tone: 'success' },
  force: { label: 'Force', icon: Mountain, tone: 'muted' },
  entangle: { label: 'Entangles', icon: Link, tone: 'warning' },
  fear: { label: 'Fear', icon: EyeOff, tone: 'danger' },
  stillness: { label: 'Stillness', icon: Hourglass, tone: 'muted' },
  sleep: { label: 'Sleep', icon: Moon, tone: 'info' },
  confusion: { label: 'Confusion', icon: Brain, tone: 'warning' },
  charm: { label: 'Charm', icon: Heart, tone: 'gold' },
  drain: { label: 'Drain', icon: HeartPulse, tone: 'danger' },
}

export const RANGES: Record<Schema['AttackRange'], Named> = {
  touch: { label: 'Touch', icon: Hand, tone: 'muted' },
  near: { label: 'Near', icon: CircleDot, tone: 'info' },
  far: { label: 'A whole town', icon: Globe, tone: 'warning' },
  sight: { label: 'By sight, a whole town', icon: Eye, tone: 'danger' },
}

export const VALENCES: Record<Schema['StratumValence'], Named> = {
  reward: { label: 'Reward', icon: Sun, tone: 'gold' },
  neutral: { label: 'Neutral', icon: CircleDot, tone: 'muted' },
  punishment: { label: 'Punishment', icon: Flame, tone: 'danger' },
  mixed: { label: 'Mixed', icon: Scale, tone: 'info' },
}

export const PERMANENCES: Record<Schema['StratumPermanence'], Named> = {
  eternal: { label: 'For ever', icon: Forever, tone: 'gold' },
  until_rebirth: { label: 'Until rebirth', icon: Repeat, tone: 'verdigris' },
  until_judgement: { label: 'Until judged again', icon: Gavel, tone: 'info' },
  fading: { label: 'Souls fade', icon: Hourglass, tone: 'muted' },
}

export const ADMISSIONS: Record<Schema['StratumAdmission'], Named> = {
  by_deeds: { label: 'By deeds', icon: Scale, tone: 'info' },
  by_faith: { label: 'By faith', icon: Sun, tone: 'gold' },
  by_manner_of_death: {
    label: 'By manner of death',
    icon: Swords,
    tone: 'warning',
  },
  by_line: { label: 'By line', icon: Users, tone: 'verdigris' },
  by_rites: { label: 'By rites', icon: Sparkles, tone: 'info' },
  by_choice: { label: 'By choice', icon: Hand, tone: 'success' },
  all: { label: 'All the dead', icon: Globe, tone: 'muted' },
}

export const ACTIVITIES: Record<Schema['StratumActivity'], Named> = {
  rest: { label: 'Rest', icon: Moon, tone: 'info' },
  service: { label: 'Service', icon: Crown, tone: 'gold' },
  struggle: { label: 'Struggle', icon: Swords, tone: 'warning' },
  reunion: { label: 'Reunion', icon: Users, tone: 'success' },
  learning: { label: 'Learning', icon: BookOpen, tone: 'info' },
  dissolution: { label: 'Dissolution', icon: CloudFog, tone: 'muted' },
}

export const CONTACTS: Record<Schema['StratumContact'], Named> = {
  open: { label: 'The living can reach it', icon: DoorOpen, tone: 'success' },
  by_rite: { label: 'Only by rite', icon: Key, tone: 'info' },
  closed: { label: 'Closed to the living', icon: DoorClosed, tone: 'muted' },
}

export const PALETTE_SUBSYSTEMS: Record<Schema['PaletteSubsystem'], Named> = {
  war: { label: 'War', icon: Swords, tone: 'danger' },
  faith: { label: 'Faith', icon: Sun, tone: 'gold' },
  economy: { label: 'Economy', icon: Scale, tone: 'info' },
  ecology: { label: 'Ecology', icon: Sprout, tone: 'success' },
  disease: { label: 'Disease', icon: HeartPulse, tone: 'danger' },
  climate: { label: 'Climate', icon: Cloud, tone: 'info' },
  cosmos: { label: 'Cosmos', icon: Star, tone: 'verdigris' },
  made_minds: { label: 'Made minds', icon: Brain, tone: 'info' },
  networks: { label: 'Networks', icon: Link, tone: 'info' },
  replicators: { label: 'Replicators', icon: Layers, tone: 'warning' },
  powers: { label: 'Powers', icon: Zap, tone: 'gold' },
  sources: { label: 'Sources of power', icon: Sparkles, tone: 'gold' },
  concealment: { label: 'Concealment', icon: EyeOff, tone: 'muted' },
  living_craft: { label: 'Living craft', icon: Sprout, tone: 'verdigris' },
  gods: { label: 'Gods', icon: Crown, tone: 'gold' },
  outer_beings: { label: 'Beings from outside', icon: Ghost, tone: 'danger' },
  households: { label: 'Households', icon: Users, tone: 'info' },
  migration: { label: 'Migration', icon: Route, tone: 'info' },
  ideology: { label: 'Ideology', icon: BookOpen, tone: 'warning' },
  art: { label: 'Art', icon: Palette, tone: 'gold' },
}

export const DIRECTIONS: Record<Schema['PaletteDirection'], Named> = {
  disruption: { label: 'Disruption', icon: ArrowDownRight, tone: 'danger' },
  recovery: { label: 'Recovery', icon: ArrowUpRight, tone: 'success' },
}

export const ASPECT_ICON = ShieldCheck
