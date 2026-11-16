import {
  TrendingUp,
  TrendingDown,
  Shuffle,
  Pause,
  Network,
  GitBranch,
  Cog,
  Bot,
  Brain,
  CircleAlert,
  Eye,
  Feather,
  Footprints,
  HeartPulse,
  Landmark,
  Leaf,
  Microscope,
  Music,
  Orbit,
  Paintbrush,
  PenTool,
  Shirt,
  Theater,
  Users,
  Biohazard,
  Bomb,
  Building2,
  Circle,
  Coins,
  Compass,
  Crosshair,
  Flame,
  FlaskRound,
  Gem,
  Ghost,
  GraduationCap,
  Hammer,
  KeyRound,
  Moon,
  Palette,
  PawPrint,
  Ship,
  Sparkles,
  Sun,
  Swords,
  Trophy,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type LoreNamed } from './model'

type Schemas = components['schemas']

export const GREAT_FIELDS: Record<Schemas['GreatField'], LoreNamed> = {
  scholar: { label: 'Great scholar', icon: GraduationCap, tone: 'info' },
  artist: { label: 'Great artist', icon: Palette, tone: 'verdigris' },
  general: { label: 'Great general', icon: Swords, tone: 'danger' },
  prophet: { label: 'Great prophet', icon: Sparkles, tone: 'gold' },
  engineer: { label: 'Great engineer', icon: Hammer, tone: 'warning' },
  merchant: { label: 'Great merchant', icon: Coins, tone: 'gold' },
  explorer: { label: 'Great explorer', icon: Compass, tone: 'success' },
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
}

export const ART_DISCIPLINES: Record<Schemas['ArtDiscipline'], LoreNamed> = {
  music: { label: 'Music', icon: Music, tone: 'verdigris' },
  poetry: { label: 'Poetry', icon: Feather, tone: 'gold' },
  dance: { label: 'Dance', icon: Footprints, tone: 'info' },
  theatre: { label: 'Theatre', icon: Theater, tone: 'warning' },
  painting: { label: 'Painting', icon: Paintbrush, tone: 'info' },
  sculpture: { label: 'Sculpture', icon: Gem, tone: 'gold' },
  architecture_style: {
    label: 'Style of building',
    icon: Building2,
    tone: 'gold',
  },
  textile: { label: 'Textile', icon: Shirt, tone: 'verdigris' },
  calligraphy: { label: 'Calligraphy', icon: PenTool, tone: 'info' },
}
