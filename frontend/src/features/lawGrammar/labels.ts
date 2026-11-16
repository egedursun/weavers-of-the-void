import {
  Ban,
  BookOpen,
  Brain,
  Copy,
  Crown,
  Divide,
  EyeOff,
  Feather,
  FlipHorizontal,
  Gauge,
  Gem,
  Globe,
  Hammer,
  HeartPulse,
  Languages,
  Link,
  MapPin,
  Moon,
  Mountain,
  Scale,
  Shapes,
  Shield,
  Skull,
  Snowflake,
  Sparkles,
  Sun,
  Swords,
  Ship,
  TriangleAlert,
  User,
  Users,
  Wheat,
  Zap,
  CheckCheck,
  Clock,
  Equal,
  Orbit,
  Dna,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const LAW_GRAMMAR_ICON = Scale

export const LAW_TARGETS: Record<Schema['LawTarget'], Named> = {
  stat: { label: 'A measure of things', icon: Gauge, tone: 'info' },
  life: { label: 'The span of life', icon: HeartPulse, tone: 'success' },
  death: { label: 'Death and what follows', icon: Skull, tone: 'muted' },
  magic: { label: 'Magic', icon: Sparkles, tone: 'verdigris' },
  war: { label: 'War', icon: Swords, tone: 'danger' },
  harvest: { label: 'Harvests', icon: Wheat, tone: 'success' },
  travel: { label: 'Travel', icon: Ship, tone: 'info' },
  language: { label: 'Tongues', icon: Languages, tone: 'info' },
  disaster: { label: 'Disasters', icon: TriangleAlert, tone: 'warning' },
  material: { label: 'Materials', icon: Gem, tone: 'gold' },
  light: { label: 'Light', icon: Sun, tone: 'gold' },
  weight: { label: 'Weight', icon: Mountain, tone: 'muted' },
  season: { label: 'Seasons', icon: Snowflake, tone: 'info' },
  dreams: { label: 'Dreams', icon: Moon, tone: 'verdigris' },
  oaths: { label: 'Oaths', icon: Link, tone: 'gold' },
  made_minds: { label: 'Made minds', icon: Brain, tone: 'info' },
  copies: { label: 'Copies of minds', icon: Copy, tone: 'info' },
  powers: { label: 'Powers', icon: Zap, tone: 'gold' },
  sources: { label: 'Sources of power', icon: Orbit, tone: 'verdigris' },
  concealment: { label: 'Hidden truths', icon: EyeOff, tone: 'muted' },
  living_craft: { label: 'Living craft', icon: Dna, tone: 'success' },
  realms: { label: 'Made realms', icon: Globe, tone: 'info' },
}

export const LAW_OPERATORS: Record<Schema['LawOperator'], Named> = {
  forbid: { label: 'Forbids it', icon: Ban, tone: 'danger' },
  require: { label: 'Requires at least', icon: CheckCheck, tone: 'gold' },
  multiply: { label: 'Multiplies it', icon: Divide, tone: 'info' },
  set: { label: 'Sets it to', icon: Equal, tone: 'info' },
  invert: { label: 'Inverts it', icon: FlipHorizontal, tone: 'warning' },
  bind_to_condition: {
    label: 'Binds it to its condition',
    icon: Link,
    tone: 'verdigris',
  },
}

export const LAW_CONDITIONS: Record<Schema['LawCondition'], Named> = {
  always: { label: 'Always', icon: Clock, tone: 'muted' },
  at_war: {
    label: 'While its peoples are at war',
    icon: Swords,
    tone: 'danger',
  },
  at_peace: {
    label: 'While its peoples are at peace',
    icon: Shield,
    tone: 'success',
  },
  cold_season: { label: 'In the cold season', icon: Snowflake, tone: 'info' },
  doom_rising: {
    label: 'While the doom clock stands past half',
    icon: TriangleAlert,
    tone: 'warning',
  },
  author_worshipped: {
    label: 'Where its author is worshipped',
    icon: Crown,
    tone: 'gold',
  },
  author_forgotten: {
    label: 'Where its author is not worshipped',
    icon: Feather,
    tone: 'muted',
  },
}

export const EXCEPTION_KINDS: Record<Schema['LawExceptionKind'], Named> = {
  person: { label: 'A person', icon: User, tone: 'info' },
  line: { label: 'A house or line', icon: Users, tone: 'gold' },
  people: { label: 'A people', icon: Users, tone: 'verdigris' },
  kind: { label: 'A kind of thing', icon: Shapes, tone: 'muted' },
  place: { label: 'A place', icon: MapPin, tone: 'success' },
}

export const THEORY_ICON = BookOpen
export const WORKS_ICON = Hammer
