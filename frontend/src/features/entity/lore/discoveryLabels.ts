import {
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
}

export const AGE_LOOK: Record<Schemas['AgeKind'], LoreNamed> = {
  normal: { label: 'An ordinary age', icon: Circle, tone: 'muted' },
  golden: { label: 'A golden age', icon: Sun, tone: 'gold' },
  dark: { label: 'A dark age', icon: Moon, tone: 'danger' },
  heroic: { label: 'A heroic age', icon: Trophy, tone: 'success' },
}
