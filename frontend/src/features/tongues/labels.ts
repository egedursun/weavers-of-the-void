import {
  Plus,
  Merge,
  AudioWaveform,
  ArrowLeftRight,
  FlaskConical,
  Binary,
  ArrowRightLeft,
  Asterisk,
  BookA,
  BookOpen,
  Brain,
  Crown,
  Droplet,
  Ear,
  Eraser,
  EyeOff,
  Flame,
  Gavel,
  GitBranch,
  GitMerge,
  Hand,
  Handshake,
  Heart,
  Languages,
  type LucideIcon,
  Megaphone,
  Minus,
  Mountain,
  Palette,
  Pencil,
  Plane,
  Recycle,
  Scale,
  ScrollText,
  Shrink,
  Sparkles,
  Sun,
  ThumbsDown,
  ThumbsUp,
  Users,
  Wand2,
  Waves,
  Wind,
  Wrench,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain/KpiTile'

type Schema = components['schemas']
export type Named = { label: string; icon: LucideIcon; tone: KpiTone }

export const TONGUE_ICON: LucideIcon = Languages

export const CHANGE_KINDS: Record<Schema['SoundChangeKind'], Named> = {
  shift: { label: 'Shift', icon: ArrowRightLeft, tone: 'info' },
  lenition: { label: 'Softening', icon: Wind, tone: 'verdigris' },
  vowel_shift: { label: 'Vowel shift', icon: Waves, tone: 'info' },
  merger: { label: 'Merger', icon: GitMerge, tone: 'warning' },
  loss: { label: 'Loss', icon: Minus, tone: 'danger' },
  metathesis: { label: 'Metathesis', icon: ArrowLeftRight, tone: 'info' },
  epenthesis: { label: 'Epenthesis', icon: Plus, tone: 'info' },
  assimilation: { label: 'Assimilation', icon: Merge, tone: 'info' },
  palatalisation: {
    label: 'Palatalisation',
    icon: ArrowRightLeft,
    tone: 'info',
  },
  tonogenesis: { label: 'Tonogenesis', icon: AudioWaveform, tone: 'info' },
}

export const ENVIRONMENTS: Record<Schema['SoundEnvironment'], Named> = {
  anywhere: { label: 'Anywhere in a word', icon: Asterisk, tone: 'muted' },
  initial: { label: 'At the start of a word', icon: Plane, tone: 'info' },
  final: { label: 'At the end of a word', icon: Mountain, tone: 'info' },
  between_vowels: { label: 'Between vowels', icon: Droplet, tone: 'verdigris' },
}

export const CAUSES: Record<Schema['SoundChangeCause'], Named> = {
  contact: {
    label: 'Contact with other tongues',
    icon: Handshake,
    tone: 'info',
  },
  prestige: { label: 'A prestigious neighbour', icon: Crown, tone: 'gold' },
  migration: { label: 'A move to new lands', icon: Plane, tone: 'warning' },
  drift: { label: 'Drift of time', icon: Wind, tone: 'muted' },
  inherited: {
    label: 'Inherited from its parent',
    icon: GitBranch,
    tone: 'verdigris',
  },
  decree: { label: 'A divine decree', icon: Sun, tone: 'gold' },
}

export const WORD_ORDERS: Record<Schema['WordOrder'], Named> = {
  sov: { label: 'Subject, object, verb', icon: ArrowRightLeft, tone: 'info' },
  svo: { label: 'Subject, verb, object', icon: ArrowRightLeft, tone: 'info' },
  vso: { label: 'Verb, subject, object', icon: ArrowRightLeft, tone: 'info' },
  vos: { label: 'Verb, object, subject', icon: ArrowRightLeft, tone: 'info' },
  ovs: { label: 'Object, verb, subject', icon: ArrowRightLeft, tone: 'info' },
  osv: { label: 'Object, subject, verb', icon: ArrowRightLeft, tone: 'info' },
  free: { label: 'Free order', icon: Recycle, tone: 'muted' },
}

export const MORPHOLOGIES: Record<Schema['MorphologyType'], Named> = {
  isolating: { label: 'Isolating', icon: Shrink, tone: 'muted' },
  agglutinative: { label: 'Agglutinative', icon: GitMerge, tone: 'verdigris' },
  fusional: { label: 'Fusional', icon: Flame, tone: 'warning' },
  polysynthetic: { label: 'Polysynthetic', icon: Sparkles, tone: 'gold' },
}

export const NUMBERS: Record<Schema['NumberSystem'], Named> = {
  none: { label: 'No number', icon: Minus, tone: 'muted' },
  singular_plural: { label: 'Singular and plural', icon: Users, tone: 'info' },
  dual: { label: 'With a dual', icon: Users, tone: 'verdigris' },
  trial: { label: 'With a trial', icon: Users, tone: 'warning' },
  paucal: { label: 'With a paucal', icon: Users, tone: 'gold' },
}

export const SHIFTS: Record<Schema['SenseShift'], Named> = {
  broadened: { label: 'Broadened', icon: ArrowRightLeft, tone: 'info' },
  narrowed: { label: 'Narrowed', icon: Shrink, tone: 'verdigris' },
  pejorative: { label: 'Grew darker', icon: ThumbsDown, tone: 'danger' },
  ameliorative: { label: 'Grew kinder', icon: ThumbsUp, tone: 'success' },
  euphemism: { label: 'Said instead of a name', icon: EyeOff, tone: 'warning' },
  restored: { label: 'Restored', icon: Recycle, tone: 'muted' },
}

export const REGISTERS: Record<Schema['WordRegister'], Named> = {
  common: { label: 'Common speech', icon: Megaphone, tone: 'muted' },
  sacred: { label: 'Sacred speech', icon: Sun, tone: 'gold' },
  poetic: { label: 'Poetry', icon: Heart, tone: 'verdigris' },
  archaic: { label: 'Archaic', icon: ScrollText, tone: 'warning' },
}

export const SCRIPT_CAUSES: Record<Schema['ScriptChangeCause'], Named> = {
  invention: { label: 'Invented', icon: Pencil, tone: 'gold' },
  reform: { label: 'Reformed', icon: Gavel, tone: 'info' },
  simplification: { label: 'Worn simpler', icon: Eraser, tone: 'verdigris' },
  borrowing: { label: 'Borrowed', icon: Handshake, tone: 'warning' },
}

export const SYSTEMS: Record<Schema['WritingSystem'], Named> = {
  pictographic: { label: 'Pictographic', icon: Palette, tone: 'gold' },
  logographic: { label: 'Logographic', icon: BookA, tone: 'gold' },
  mixed: { label: 'Mixed', icon: GitMerge, tone: 'info' },
  syllabary: { label: 'Syllabary', icon: BookOpen, tone: 'info' },
  abjad: { label: 'Abjad', icon: Pencil, tone: 'verdigris' },
  alphabet: { label: 'Alphabet', icon: Languages, tone: 'verdigris' },
  knot: { label: 'Knot records', icon: Wrench, tone: 'warning' },
  notch: { label: 'Notch records', icon: Minus, tone: 'warning' },
}

export const MODALITIES: Record<Schema['LanguageModality'], Named> = {
  vocal: { label: 'Spoken', icon: Ear, tone: 'info' },
  sign: { label: 'Signed', icon: Hand, tone: 'verdigris' },
  scent: { label: 'Scent', icon: Wind, tone: 'warning' },
  colour: { label: 'Colour pattern', icon: Palette, tone: 'gold' },
  telepathic: { label: 'Thought', icon: Brain, tone: 'gold' },
  data: { label: 'Data', icon: Binary, tone: 'info' },
  chemical: {
    label: 'Chemical signals',
    icon: FlaskConical,
    tone: 'verdigris',
  },
}

export const STAGES: Record<Schema['LanguageStage'], Named> = {
  natural: { label: 'A natural tongue', icon: Languages, tone: 'muted' },
  pidgin: { label: 'A pidgin', icon: Handshake, tone: 'warning' },
  creole: { label: 'A creole', icon: GitMerge, tone: 'verdigris' },
  divine: { label: 'A divine tongue', icon: Sun, tone: 'gold' },
}

export const POLICIES: Record<Schema['LanguagePolicy'], Named> = {
  official: { label: 'Official', icon: Scale, tone: 'info' },
  liturgical: { label: 'Sacred', icon: Sun, tone: 'gold' },
  suppressed: { label: 'Suppressed', icon: EyeOff, tone: 'danger' },
  revival: { label: 'Revived', icon: Wand2, tone: 'success' },
}
