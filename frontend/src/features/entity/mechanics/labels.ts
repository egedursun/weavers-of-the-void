import {
  Activity,
  BookOpenText,
  Brain,
  CloudSun,
  Crown,
  Flame,
  Gavel,
  Hand,
  HeartPulse,
  Landmark,
  Lock,
  Mountain,
  Orbit,
  Palette,
  PartyPopper,
  Pause,
  Scale,
  Shield,
  Skull,
  Snowflake,
  Sparkles,
  Sun,
  Wand2,
  Zap,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const MODIFIER_SOURCE: Record<string, Named> = {
  player: { label: 'Your hand', icon: Hand, tone: 'gold' },
  injury: { label: 'Wounds', icon: HeartPulse, tone: 'danger' },
  condition: { label: 'Condition', icon: Activity, tone: 'warning' },
  trait: { label: 'Temperament', icon: Brain, tone: 'info' },
  law: { label: 'Law', icon: Gavel, tone: 'gold' },
  tradition: { label: 'Tradition', icon: PartyPopper, tone: 'verdigris' },
  artwork: { label: 'Artwork', icon: Palette, tone: 'verdigris' },
  doctrine: { label: 'Doctrine', icon: BookOpenText, tone: 'info' },
  treaty: { label: 'Treaty', icon: Scale, tone: 'gold' },
  title: { label: 'Title', icon: Crown, tone: 'gold' },
  structure: { label: 'Structure', icon: Landmark },
  wonder: { label: 'Wonder', icon: Crown, tone: 'gold' },
  terrain: { label: 'Terrain', icon: Mountain },
  weather: { label: 'Weather', icon: CloudSun, tone: 'info' },
  season: { label: 'Season', icon: Snowflake, tone: 'info' },
  natural_law: { label: 'Natural law', icon: Orbit, tone: 'verdigris' },
  law_grammar: {
    label: 'Working of a natural law',
    icon: Orbit,
    tone: 'verdigris',
  },
  god_power: { label: 'God power', icon: Zap, tone: 'gold' },
  blessing: { label: 'Blessing', icon: Sun, tone: 'success' },
  curse: { label: 'Curse', icon: Skull, tone: 'danger' },
  dominion: { label: 'Dominion', icon: Shield },
  phenomenon: { label: 'Phenomenon', icon: Wand2, tone: 'warning' },
  god_death: { label: 'Dead god', icon: Flame, tone: 'danger' },
  perk: { label: 'Gift of a god', icon: Sparkles, tone: 'gold' },
  pin: { label: 'Pin', icon: Lock },
  suppression: { label: 'Held back', icon: Pause },
}

export const FORGEABLE_SOURCES = Object.keys(MODIFIER_SOURCE).filter(
  (key) => key !== 'pin' && key !== 'suppression'
)

export const DERIVED_SOURCES = new Set(
  FORGEABLE_SOURCES.filter((key) => key !== 'player' && key !== 'dominion')
)

export const VIRTUAL_KEYS = ['growth'] as const
