import {
  Ban,
  Bird,
  Brain,
  BrainCircuit,
  Bug,
  CircleCheck,
  CircleDashed,
  Copy,
  Dna,
  Droplets,
  Dumbbell,
  Feather,
  FlaskConical,
  Flame,
  Gauge,
  Gift,
  GitMerge,
  Hand,
  HandHeart,
  Heart,
  HeartPulse,
  Hourglass,
  Leaf,
  Link2,
  Moon,
  Orbit,
  Ruler,
  Scale,
  Scissors,
  Shield,
  ShieldAlert,
  Shirt,
  Skull,
  Sparkles,
  Sprout,
  Sun,
  ThermometerSun,
  TreeDeciduous,
  TriangleAlert,
  Waves,
  Wheat,
  Wind,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const LIVING_ICON = Sprout

export const METHODS: Record<Schema['CultivationMethod'], Named> = {
  selective_breeding: {
    label: 'Selective breeding',
    icon: GitMerge,
    tone: 'success',
  },
  cultivation: { label: 'Cultivation', icon: Sprout, tone: 'success' },
  shaping: { label: 'Shaping', icon: Hand, tone: 'warning' },
  engineering: { label: 'Engineering', icon: Dna, tone: 'info' },
  synthesis: { label: 'Synthesis', icon: FlaskConical, tone: 'info' },
  binding: { label: 'Binding', icon: Link2, tone: 'verdigris' },
  cloning: { label: 'Cloning', icon: Copy, tone: 'info' },
  chimera: { label: 'Chimera', icon: Orbit, tone: 'warning' },
  induction: { label: 'Induction', icon: Zap, tone: 'gold' },
}

export const METABOLISMS: Record<Schema['Metabolism'], Named> = {
  feeding: { label: 'Eats food', icon: Wheat, tone: 'info' },
  light: { label: 'Lives on light', icon: Sun, tone: 'gold' },
  chemical: { label: 'Lives on minerals', icon: FlaskConical, tone: 'info' },
  host: { label: 'Draws on its host', icon: Bug, tone: 'warning' },
  source: { label: 'Draws on a source', icon: Sparkles, tone: 'gold' },
  partner: { label: 'Fed by a partner', icon: HandHeart, tone: 'success' },
  dormant: { label: 'Dormant', icon: Moon, tone: 'muted' },
}

export const STAGES: Record<Schema['GrowthStage'], Named> = {
  seed: { label: 'Seed', icon: CircleDashed, tone: 'muted' },
  young: { label: 'Young', icon: Sprout, tone: 'info' },
  grown: { label: 'Grown', icon: TreeDeciduous, tone: 'success' },
  prime: { label: 'In its prime', icon: Sparkles, tone: 'gold' },
  old: { label: 'Old', icon: Hourglass, tone: 'warning' },
  dying: { label: 'Dying', icon: TriangleAlert, tone: 'danger' },
  dead: { label: 'Dead', icon: Skull, tone: 'danger' },
}

export const FERTILITIES: Record<Schema['Fertility'], Named> = {
  sterile: { label: 'Sterile', icon: Ban, tone: 'muted' },
  breeds_true: { label: 'Breeds true', icon: CircleCheck, tone: 'success' },
  breeds_wild: { label: 'Breeds wild', icon: Wind, tone: 'warning' },
  needs_maker: { label: 'Needs its maker', icon: Hand, tone: 'info' },
}

export const PLACEMENTS: Record<Schema['HostPlacement'], Named> = {
  skin: { label: 'On the skin', icon: Shirt, tone: 'info' },
  blood: { label: 'In the blood', icon: Droplets, tone: 'danger' },
  organ: { label: 'In an organ', icon: Heart, tone: 'warning' },
  nerve: { label: 'In the nerves', icon: Zap, tone: 'warning' },
  mind: { label: 'In the mind', icon: Brain, tone: 'gold' },
}

export const RELATIONS: Record<Schema['HostRelation'], Named> = {
  mutual: { label: 'Mutual', icon: HandHeart, tone: 'success' },
  commensal: { label: 'Living alongside', icon: Scale, tone: 'info' },
  parasitic: { label: 'Parasitic', icon: Bug, tone: 'danger' },
  controlling: { label: 'Controlling', icon: BrainCircuit, tone: 'danger' },
}

export const STANCES: Record<Schema['LivingCraftStance'], Named> = {
  abomination: { label: 'An abomination', icon: ShieldAlert, tone: 'danger' },
  permitted: { label: 'Permitted', icon: CircleCheck, tone: 'info' },
  sacred_duty: { label: 'A sacred duty', icon: Sparkles, tone: 'gold' },
  silent: { label: 'Silent on it', icon: CircleDashed, tone: 'muted' },
}

export const TRAITS: Record<Schema['LineTrait'], Named> = {
  yield: { label: 'Yield', icon: Wheat, tone: 'success' },
  hardiness: { label: 'Hardiness', icon: Shield, tone: 'info' },
  climate_tolerance: {
    label: 'Climate tolerance',
    icon: ThermometerSun,
    tone: 'info',
  },
  disease_resistance: {
    label: 'Disease resistance',
    icon: ShieldAlert,
    tone: 'success',
  },
  strength: { label: 'Strength', icon: Dumbbell, tone: 'warning' },
  speed: { label: 'Speed', icon: Gauge, tone: 'info' },
  size: { label: 'Size', icon: Ruler, tone: 'info' },
  regeneration: { label: 'Regeneration', icon: HeartPulse, tone: 'success' },
  lifespan: { label: 'Lifespan', icon: Hourglass, tone: 'gold' },
  docility: { label: 'Docility', icon: HandHeart, tone: 'success' },
  potency: { label: 'Potency', icon: FlaskConical, tone: 'gold' },
  fibre: { label: 'Fibre', icon: Scissors, tone: 'info' },
  venom: { label: 'Venom', icon: Flame, tone: 'danger' },
  flight: { label: 'Flight', icon: Feather, tone: 'info' },
  aquatic: { label: 'Living in water', icon: Waves, tone: 'info' },
  void_hardy: { label: 'Hardy in the void', icon: Orbit, tone: 'verdigris' },
  gift: { label: 'A gift of power', icon: Gift, tone: 'gold' },
  nervous_system: { label: 'Nervous system', icon: Brain, tone: 'warning' },
  sapience: { label: 'Thought', icon: BrainCircuit, tone: 'gold' },
}

export const OUTCOMES: Record<Schema['LineOutcome'], Named> = {
  as_meant: { label: 'As meant', icon: CircleCheck, tone: 'success' },
  unstable: { label: 'Unstable', icon: TriangleAlert, tone: 'warning' },
  sterile: { label: 'Sterile', icon: Ban, tone: 'muted' },
  side_effects: { label: 'With side effects', icon: Bird, tone: 'warning' },
  non_viable: { label: 'Not viable', icon: Skull, tone: 'danger' },
  escaped: { label: 'Escaped', icon: Leaf, tone: 'danger' },
}
