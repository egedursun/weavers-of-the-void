import {
  Activity,
  Atom,
  BatteryCharging,
  BookOpen,
  Brain,
  BrainCircuit,
  Bug,
  Church,
  Coins,
  Compass,
  Crosshair,
  Database,
  Drama,
  Dumbbell,
  Eye,
  Feather,
  Flower2,
  Footprints,
  Gavel,
  Glasses,
  HandHeart,
  Handshake,
  HeartPulse,
  Hourglass,
  KeyboardMusic,
  Languages,
  Leaf,
  Lightbulb,
  Medal,
  Move,
  Orbit,
  Palette,
  Puzzle,
  Ruler,
  Scale,
  Shield,
  Sparkles,
  Swords,
  Users,
  Wind,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const SPLIT_ICON = BrainCircuit
export const IDEA_ICON = Lightbulb

export const ATTRIBUTE_ICONS: Record<string, Named> = {
  strength: { label: 'Strength', icon: Dumbbell, tone: 'danger' },
  agility: { label: 'Agility', icon: Wind, tone: 'success' },
  toughness: { label: 'Toughness', icon: Shield, tone: 'muted' },
  endurance: { label: 'Endurance', icon: Footprints, tone: 'warning' },
  recuperation: { label: 'Recuperation', icon: HeartPulse, tone: 'success' },
  disease_resistance: {
    label: 'Disease resistance',
    icon: Bug,
    tone: 'verdigris',
  },
  analytical_ability: {
    label: 'Analytical ability',
    icon: Atom,
    tone: 'info',
  },
  focus: { label: 'Focus', icon: Crosshair, tone: 'info' },
  willpower: { label: 'Willpower', icon: BatteryCharging, tone: 'gold' },
  creativity: { label: 'Creativity', icon: Palette, tone: 'gold' },
  intuition: { label: 'Intuition', icon: Eye, tone: 'verdigris' },
  patience: { label: 'Patience', icon: Hourglass, tone: 'muted' },
  memory: { label: 'Memory', icon: Database, tone: 'info' },
  linguistic_ability: {
    label: 'Linguistic ability',
    icon: Languages,
    tone: 'info',
  },
  spatial_sense: { label: 'Spatial sense', icon: Ruler, tone: 'info' },
  musicality: { label: 'Musicality', icon: KeyboardMusic, tone: 'gold' },
  kinaesthetic_sense: {
    label: 'Kinaesthetic sense',
    icon: Move,
    tone: 'success',
  },
  empathy: { label: 'Empathy', icon: HandHeart, tone: 'success' },
  social_awareness: { label: 'Social awareness', icon: Users, tone: 'gold' },
}

export const FACET_GROUPS: Record<string, Named> = {
  emotional: { label: 'Emotional', icon: HeartPulse, tone: 'danger' },
  social: { label: 'Social', icon: Users, tone: 'gold' },
  drive: { label: 'Drive', icon: Activity, tone: 'warning' },
  mind: { label: 'Mind', icon: Brain, tone: 'info' },
}

export const IDEA_ICONS: Record<string, Named> = {
  rationalism: { label: 'Rationalism', icon: Atom, tone: 'info' },
  mysticism: { label: 'Mysticism', icon: Orbit, tone: 'verdigris' },
  asceticism: { label: 'Asceticism', icon: Feather, tone: 'muted' },
  mercy_for_all: { label: 'Mercy for all', icon: HandHeart, tone: 'success' },
  martial_creed: { label: 'Martial creed', icon: Swords, tone: 'danger' },
  rule_of_law: { label: 'Rule of law', icon: Gavel, tone: 'gold' },
  free_spirit: { label: 'Free spirit', icon: Wind, tone: 'info' },
  kin_first: { label: 'Kin first', icon: Users, tone: 'verdigris' },
  honour_code: { label: 'Honour code', icon: Medal, tone: 'gold' },
  wanderlust: { label: 'Wanderlust', icon: Compass, tone: 'info' },
  materialism: { label: 'Materialism', icon: Coins, tone: 'gold' },
  reverence_for_nature: {
    label: 'Reverence for nature',
    icon: Leaf,
    tone: 'success',
  },
  craft_devotion: { label: 'Devotion to craft', icon: Puzzle, tone: 'warning' },
  beauty_above_all: {
    label: 'Beauty above all',
    icon: Flower2,
    tone: 'gold',
  },
  egalitarianism: { label: 'Equality of all', icon: Scale, tone: 'success' },
  divine_order: { label: 'Divine order', icon: Church, tone: 'gold' },
}

export const IDEA_SOURCES: Record<string, Named> = {
  ideology: { label: 'From an ideology', icon: BookOpen, tone: 'info' },
  doctrine: { label: 'From a doctrine', icon: Church, tone: 'gold' },
  theory: { label: 'From what their people know', icon: Atom, tone: 'info' },
  book: { label: 'From a book', icon: BookOpen, tone: 'muted' },
  teacher: { label: 'From a teacher', icon: Glasses, tone: 'verdigris' },
  divine: { label: 'Planted by a god', icon: Sparkles, tone: 'gold' },
  player: { label: 'Planted by the Creator', icon: Sparkles, tone: 'gold' },
}

export const IDEA_STATES: Record<string, Named> = {
  incubating: { label: 'Turning it over', icon: Hourglass, tone: 'warning' },
  internalised: { label: 'Taken to heart', icon: Handshake, tone: 'success' },
  rejected: { label: 'Let go', icon: Drama, tone: 'muted' },
}
