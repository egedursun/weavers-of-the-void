import {
  Biohazard,
  Bomb,
  Bone,
  Bot,
  Brain,
  Building2,
  Circle,
  CircleAlert,
  Clover,
  Cog,
  Coins,
  Compass,
  Crosshair,
  Eye,
  Flame,
  FlaskRound,
  Footprints,
  Gavel,
  Gem,
  Ghost,
  GitBranch,
  GraduationCap,
  Hammer,
  HeartPulse,
  KeyRound,
  Landmark,
  Languages,
  Leaf,
  Megaphone,
  Microscope,
  Moon,
  Network,
  Orbit,
  Palette,
  Pause,
  PawPrint,
  Pill,
  ScrollText,
  Search,
  Ship,
  Shuffle,
  Sparkles,
  Stethoscope,
  Sun,
  Sunrise,
  Swords,
  TrendingDown,
  TrendingUp,
  Trophy,
  Users,
  Wrench,
  Zap,
  BookOpenText,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { MEDIUMS, type LoreNamed } from './model'

type Schemas = components['schemas']

export const GREAT_FIELDS: Record<Schemas['GreatField'], LoreNamed> = {
  scholar: { label: 'Great scholar', icon: GraduationCap, tone: 'info' },
  artist: { label: 'Great artist', icon: Palette, tone: 'verdigris' },
  general: { label: 'Great general', icon: Swords, tone: 'danger' },
  prophet: { label: 'Great prophet', icon: Sparkles, tone: 'gold' },
  engineer: { label: 'Great engineer', icon: Hammer, tone: 'warning' },
  merchant: { label: 'Great merchant', icon: Coins, tone: 'gold' },
  explorer: { label: 'Great explorer', icon: Compass, tone: 'success' },
  healer: { label: 'Great healer', icon: Stethoscope, tone: 'success' },
  lawgiver: { label: 'Great lawgiver', icon: Gavel, tone: 'gold' },
  teacher: { label: 'Great teacher', icon: BookOpenText, tone: 'info' },
  reformer: { label: 'Great reformer', icon: Megaphone, tone: 'warning' },
}

export const INCIDENT_KINDS: Record<Schemas['ResearchIncident'], LoreNamed> = {
  leak: { label: 'The secret leaked', icon: KeyRound, tone: 'warning' },
  released_beast: {
    label: 'A beast got loose',
    icon: PawPrint,
    tone: 'danger',
  },
  plague: { label: 'A sickness got loose', icon: Biohazard, tone: 'danger' },
  backlash: { label: 'A working turned back', icon: Zap, tone: 'verdigris' },
  fire: { label: 'A fire in the workshop', icon: Flame, tone: 'danger' },
  explosion: { label: 'An explosion', icon: Bomb, tone: 'danger' },
  poisoning: { label: 'A poisoning', icon: FlaskRound, tone: 'warning' },
  summoning_gone_wrong: {
    label: 'A summoning gone wrong',
    icon: Ghost,
    tone: 'verdigris',
  },
  stolen: { label: 'Work stolen', icon: Search, tone: 'danger' },
  chance_find: { label: 'Found by chance', icon: Clover, tone: 'success' },
}

export const BLUEPRINT_LOOK: Record<Schemas['BlueprintKind'], LoreNamed> = {
  vessel: { label: 'Ship design', icon: Ship, tone: 'info' },
  siege_engine: {
    label: 'Siege engine design',
    icon: Crosshair,
    tone: 'danger',
  },
  structure: { label: 'Building plan', icon: Building2, tone: 'gold' },
  artifact_pattern: {
    label: 'Pattern of a crafted thing',
    icon: Gem,
    tone: 'verdigris',
  },
  made_body: { label: 'Made body', icon: Bot, tone: 'info' },
  augment: { label: 'Augment', icon: Cog, tone: 'info' },
  line: { label: 'Line', icon: GitBranch, tone: 'info' },
  network: { label: 'Network', icon: Network, tone: 'info' },
  rite_pattern: { label: 'Rite pattern', icon: Sparkles, tone: 'info' },
  process: { label: 'Way of working', icon: Wrench, tone: 'gold' },
  remedy: { label: 'Remedy', icon: Pill, tone: 'success' },
}

export const AGE_LOOK: Record<Schemas['AgeKind'], LoreNamed> = {
  normal: { label: 'An ordinary age', icon: Circle, tone: 'muted' },
  golden: { label: 'A golden age', icon: Sun, tone: 'gold' },
  dark: { label: 'A dark age', icon: Moon, tone: 'danger' },
  heroic: { label: 'A heroic age', icon: Trophy, tone: 'success' },
  rising: { label: 'Rising', icon: TrendingUp, tone: 'muted' },
  declining: { label: 'Declining', icon: TrendingDown, tone: 'muted' },
  transforming: { label: 'Transforming', icon: Shuffle, tone: 'muted' },
  stagnant: { label: 'Stagnant', icon: Pause, tone: 'muted' },
  wandering: { label: 'Wandering', icon: Footprints, tone: 'info' },
  reborn: { label: 'Reborn', icon: Sunrise, tone: 'success' },
}

export const THEORY_DOMAINS: Record<Schemas['TheoryDomain'], LoreNamed> = {
  medicine: { label: 'Medicine', icon: HeartPulse, tone: 'success' },
  cosmology: { label: 'Cosmology', icon: Orbit, tone: 'info' },
  matter: { label: 'Matter', icon: Gem, tone: 'gold' },
  life: { label: 'Life', icon: Leaf, tone: 'success' },
  mind: { label: 'Mind', icon: Brain, tone: 'verdigris' },
  magic: { label: 'Magic', icon: Sparkles, tone: 'verdigris' },
  history: { label: 'History', icon: Landmark, tone: 'gold' },
  society: { label: 'Society', icon: Users, tone: 'info' },
  language: { label: 'Language', icon: Languages, tone: 'verdigris' },
  law: { label: 'Law', icon: Gavel, tone: 'gold' },
}

export const ANOMALY_KINDS: Record<Schemas['AnomalyKind'], LoreNamed> = {
  failed_prediction: {
    label: 'A prediction failed',
    icon: CircleAlert,
    tone: 'warning',
  },
  contrary_cure: {
    label: 'A cure worked against it',
    icon: HeartPulse,
    tone: 'warning',
  },
  observation: {
    label: 'An observation it cannot explain',
    icon: Microscope,
    tone: 'info',
  },
  divine_sign: { label: 'A god showed otherwise', icon: Eye, tone: 'gold' },
  contrary_record: {
    label: 'Old records disagree',
    icon: ScrollText,
    tone: 'warning',
  },
  out_of_place_find: {
    label: 'A find out of place',
    icon: Bone,
    tone: 'warning',
  },
}

export const ART_DISCIPLINES: Record<Schemas['ArtMode'], LoreNamed> = MEDIUMS
