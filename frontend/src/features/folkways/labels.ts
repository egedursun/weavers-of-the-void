import {
  ArrowDown,
  Weight,
  Scissors,
  Waves,
  Cog,
  CarFront,
  Building,
  Wind,
  Snowflake,
  Trophy,
  Package,
  Wrench,
  Anchor,
  Apple,
  Baby,
  Ban,
  Beef,
  Bone,
  Brain,
  Bug,
  CalendarDays,
  Clover,
  Coins,
  Crown,
  Dice5,
  Droplet,
  Dna,
  Droplets,
  Eye,
  FlaskConical,
  Handshake,
  Undo2,
  Flame,
  Gavel,
  Gem,
  Ghost,
  Hammer,
  HandHeart,
  Hand,
  HeartCrack,
  HeartPulse,
  Hash,
  Hourglass,
  Landmark,
  Leaf,
  type LucideIcon,
  MapPin,
  Milk,
  Mountain,
  PawPrint,
  Scale,
  Scroll,
  Shield,
  ShieldAlert,
  Skull,
  Sparkles,
  Sprout,
  Sun,
  Swords,
  Target,
  TrendingDown,
  TrendingUp,
  User,
  Users,
  UtensilsCrossed,
  Wheat,
  Zap,
  EyeOff,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const FOLKWAYS_ICON: LucideIcon = UtensilsCrossed

export const TAB_ICONS = {
  body: Wheat,
  minds: Brain,
  purity: Droplets,
  fortune: Clover,
} as const

export const NUTRIENTS: Record<Schema['Nutrient'], Named> = {
  energy: { label: 'Energy', icon: Zap, tone: 'gold' },
  protein: { label: 'Protein', icon: Beef, tone: 'danger' },
  fat: { label: 'Fats', icon: Milk, tone: 'warning' },
  fresh: { label: 'Fresh food', icon: Apple, tone: 'success' },
  mineral: { label: 'Minerals', icon: Gem, tone: 'info' },
  light: { label: 'Light', icon: Sun, tone: 'gold' },
  essence: { label: 'Essence', icon: Sparkles, tone: 'verdigris' },
  charge: { label: 'Charge', icon: Zap, tone: 'info' },
}

export const DIET_SHARES = [
  { key: 'staple', label: 'Staples', icon: Wheat },
  { key: 'protein', label: 'Protein', icon: Beef },
  { key: 'fat', label: 'Fats', icon: Milk },
  { key: 'fresh', label: 'Fresh food', icon: Apple },
  { key: 'mineral', label: 'Minerals', icon: Gem },
  { key: 'preserved', label: 'Preserved food', icon: Hourglass },
  { key: 'special', label: 'Special food', icon: Sparkles },
] as const

export const BIASES: Record<Schema['DecisionBias'], Named> = {
  overconfidence: { label: 'Overconfidence', icon: Crown, tone: 'gold' },
  sunk_cost: { label: 'Sunk cost', icon: Anchor, tone: 'warning' },
  loss_aversion: { label: 'Loss aversion', icon: ShieldAlert, tone: 'info' },
  confirmation: { label: 'Confirmation', icon: Eye, tone: 'muted' },
  recency: { label: 'Recency', icon: CalendarDays, tone: 'info' },
  groupthink: { label: 'Groupthink', icon: Users, tone: 'muted' },
  hostile_attribution: {
    label: 'Hostile attribution',
    icon: Swords,
    tone: 'danger',
  },
  optimism: { label: 'Optimism', icon: Sun, tone: 'success' },
  status_quo: { label: 'Status quo', icon: Landmark, tone: 'muted' },
  availability: { label: 'Availability', icon: Flame, tone: 'warning' },
  anchoring: { label: 'Anchoring', icon: MapPin, tone: 'info' },
  in_group_favour: { label: 'In-group favour', icon: HandHeart, tone: 'gold' },
  authority_deference: {
    label: 'Authority deference',
    icon: Gavel,
    tone: 'muted',
  },
  scarcity_panic: { label: 'Scarcity panic', icon: Coins, tone: 'danger' },
  fatalism: { label: 'Fatalism', icon: Hourglass, tone: 'muted' },
  risk_seeking: { label: 'Risk seeking', icon: Dice5, tone: 'warning' },
  planning_fallacy: { label: 'Planning fallacy', icon: Scroll, tone: 'info' },
  halo: { label: 'Halo', icon: Sparkles, tone: 'gold' },
  projection: { label: 'Projection', icon: User, tone: 'verdigris' },
  literalism: { label: 'Literalism', icon: Scroll, tone: 'muted' },
  colony_risk_aversion: {
    label: 'Colony risk aversion',
    icon: Shield,
    tone: 'info',
  },
}

export const DECISIONS: Record<Schema['BiasedDecision'], Named> = {
  raid: { label: 'Going raiding', icon: Swords, tone: 'danger' },
  peace: { label: 'Seeking peace', icon: HandHeart, tone: 'success' },
  surrender: { label: 'Yielding a siege', icon: Shield, tone: 'warning' },
  scheme: { label: 'Starting a scheme', icon: Eye, tone: 'muted' },
  belief: { label: 'Believing a rumour', icon: Brain, tone: 'info' },
  conversion: { label: 'Turning to a god', icon: Sparkles, tone: 'gold' },
  migration: { label: 'Leaving home', icon: TrendingUp, tone: 'info' },
  god_goal: { label: 'Taking up a goal', icon: Target, tone: 'gold' },
  war: { label: 'Going to war', icon: Swords, tone: 'danger' },
  retreat: { label: 'Falling back', icon: Undo2, tone: 'warning' },
  trade: { label: 'Opening trade', icon: Coins, tone: 'success' },
  alliance: { label: 'Making an alliance', icon: Handshake, tone: 'info' },
  succession: { label: 'Naming an heir', icon: Crown, tone: 'gold' },
  law: { label: 'Changing the law', icon: Gavel, tone: 'info' },
  research: {
    label: 'Choosing what to learn',
    icon: FlaskConical,
    tone: 'verdigris',
  },
}

export const PURITY_STATES: Record<Schema['PurityState'], Named> = {
  pure: { label: 'Pure', icon: Droplet, tone: 'success' },
  impure: { label: 'Impure', icon: Droplets, tone: 'warning' },
  defiled: { label: 'Defiled', icon: Ban, tone: 'danger' },
}

export const IMPURITY_SOURCES: Record<Schema['ImpuritySource'], Named> = {
  the_dead: { label: 'The dead', icon: Skull, tone: 'muted' },
  birth: { label: 'Birth', icon: Baby, tone: 'gold' },
  bodily_fluids: { label: 'Bodily fluids', icon: Droplet, tone: 'danger' },
  food: { label: 'Foods', icon: UtensilsCrossed, tone: 'warning' },
  species: { label: 'Species', icon: PawPrint, tone: 'verdigris' },
  profession: { label: 'Professions', icon: Hammer, tone: 'info' },
  outsiders: { label: 'Outsiders', icon: Users, tone: 'muted' },
  place: { label: 'Places', icon: Mountain, tone: 'muted' },
  object: { label: 'Objects', icon: Gem, tone: 'warning' },
  act: { label: 'Acts', icon: Gavel, tone: 'danger' },
  made_thing: { label: 'Made things', icon: Hammer, tone: 'info' },
  taboo: { label: 'A broken taboo', icon: Ban, tone: 'danger' },
  wound: { label: 'Wounds', icon: HeartPulse, tone: 'danger' },
  augment: { label: 'Augments', icon: Cog, tone: 'info' },
  designed_body: { label: 'Designed bodies', icon: Dna, tone: 'verdigris' },
}

export const PURIFICATIONS: Record<Schema['Purification'], Named> = {
  time: { label: 'Waiting', icon: Hourglass, tone: 'muted' },
  washing: { label: 'Washing', icon: Droplets, tone: 'info' },
  fasting: { label: 'Fasting', icon: Leaf, tone: 'success' },
  offering: { label: 'An offering', icon: HandHeart, tone: 'gold' },
  rite: { label: 'A rite', icon: Sparkles, tone: 'verdigris' },
  confession: { label: 'Confession', icon: Scroll, tone: 'muted' },
  payment: { label: 'A payment', icon: Coins, tone: 'warning' },
  ordeal: { label: 'An ordeal', icon: Flame, tone: 'danger' },
}

export const MISHAP_KINDS: Record<Schema['MishapKind'], Named> = {
  illness: { label: 'Illness', icon: Bug, tone: 'danger' },
  crop_failure: { label: 'Crop failure', icon: Sprout, tone: 'warning' },
  child_death: { label: 'A child died', icon: HeartCrack, tone: 'danger' },
  livestock_death: { label: 'Herds lost', icon: Bone, tone: 'warning' },
  accident: { label: 'Accident', icon: Target, tone: 'info' },
  bad_luck: { label: 'Bad luck', icon: Dice5, tone: 'muted' },
  fall: { label: 'A fall', icon: ArrowDown, tone: 'warning' },
  crush: { label: 'Crushed', icon: Weight, tone: 'danger' },
  cut: { label: 'A cut', icon: Scissors, tone: 'warning' },
  burn: { label: 'A burn', icon: Flame, tone: 'danger' },
  scald: { label: 'A scald', icon: Droplets, tone: 'warning' },
  drowning: { label: 'Drowning', icon: Waves, tone: 'danger' },
  beast: { label: 'Hurt by a beast', icon: PawPrint, tone: 'warning' },
  tool: { label: 'A tool slipped', icon: Hammer, tone: 'info' },
  machine: { label: 'Caught by a machine', icon: Cog, tone: 'danger' },
  vehicle: { label: 'A vehicle mishap', icon: CarFront, tone: 'warning' },
  collapse: { label: 'A collapse', icon: Building, tone: 'danger' },
  house_fire: { label: 'A house fire', icon: Flame, tone: 'danger' },
  poisoning: { label: 'Poisoning', icon: Skull, tone: 'danger' },
  choking: { label: 'Choking', icon: Wind, tone: 'warning' },
  exposure: { label: 'Exposure', icon: Snowflake, tone: 'warning' },
  lightning: { label: 'Lightning', icon: Zap, tone: 'danger' },
  sport: { label: 'Hurt at play', icon: Trophy, tone: 'info' },
  brawl: { label: 'A brawl', icon: Swords, tone: 'warning' },
  lost_way: { label: 'Lost the way', icon: MapPin, tone: 'info' },
  stores_spoiled: { label: 'Stores spoiled', icon: Apple, tone: 'warning' },
  goods_lost: { label: 'Goods lost', icon: Package, tone: 'warning' },
  purse_lost: { label: 'A purse lost', icon: Coins, tone: 'warning' },
  theft_suffered: { label: 'Robbed', icon: Hand, tone: 'warning' },
  tool_broken: { label: 'A tool broke', icon: Wrench, tone: 'info' },
  near_miss: { label: 'A near miss', icon: Eye, tone: 'muted' },
}

export const ATTRIBUTIONS: Record<Schema['MishapAttribution'], Named> = {
  chance: { label: 'Chance', icon: Dice5, tone: 'muted' },
  known_cause: { label: 'Its known cause', icon: Brain, tone: 'info' },
  witchcraft: { label: 'Witchcraft', icon: Ghost, tone: 'danger' },
  curse: { label: 'A curse', icon: Skull, tone: 'danger' },
  god: { label: 'A god', icon: Sparkles, tone: 'gold' },
  spirit: { label: 'A spirit', icon: Ghost, tone: 'verdigris' },
  ancestor: { label: 'An ancestor', icon: Users, tone: 'muted' },
  omen: { label: 'An omen', icon: Eye, tone: 'warning' },
  fate: { label: 'Fate', icon: Hourglass, tone: 'muted' },
  enemy_scheme: { label: 'An enemy scheme', icon: Swords, tone: 'danger' },
  impurity: { label: 'Impurity', icon: Droplets, tone: 'warning' },
  broken_oath: { label: 'A broken oath', icon: Scale, tone: 'warning' },
  made_mind: { label: 'A made mind', icon: Brain, tone: 'verdigris' },
  hidden_people: { label: 'Those who hide', icon: EyeOff, tone: 'muted' },
}

export const RESPONSES: Record<Schema['MishapResponse'], Named> = {
  nothing: { label: 'Nothing done', icon: Hand, tone: 'muted' },
  rite: { label: 'A rite', icon: Sparkles, tone: 'verdigris' },
  offering: { label: 'An offering', icon: HandHeart, tone: 'gold' },
  charm: { label: 'A charm', icon: Clover, tone: 'success' },
  accusation: { label: 'An accusation', icon: Gavel, tone: 'danger' },
  purification: { label: 'Purification', icon: Droplets, tone: 'info' },
  safety_custom: { label: 'A safety custom', icon: Shield, tone: 'success' },
}

export const LUCK_SIGNS: Record<Schema['LuckSign'], Named> = {
  day: { label: 'A day', icon: CalendarDays, tone: 'gold' },
  number: { label: 'A number', icon: Hash, tone: 'info' },
  sign: { label: 'A sign', icon: Eye, tone: 'verdigris' },
  gesture: { label: 'A gesture', icon: Hand, tone: 'muted' },
  place: { label: 'A place', icon: MapPin, tone: 'muted' },
  act: { label: 'An act', icon: Target, tone: 'warning' },
  person: { label: 'A kind of person', icon: User, tone: 'info' },
}

export const LUCK_REACHES: Record<Schema['LuckReach'], Named> = {
  harvest: { label: 'Harvest', icon: Wheat, tone: 'gold' },
  health: { label: 'Health', icon: HeartPulse, tone: 'success' },
  birth: { label: 'Birth', icon: Baby, tone: 'gold' },
  journey: { label: 'Journeys', icon: MapPin, tone: 'info' },
  battle: { label: 'Battle', icon: Swords, tone: 'danger' },
}

export const CHARM_POWERS: Record<Schema['CharmPower'], Named> = {
  protection: { label: 'Protection', icon: Shield, tone: 'info' },
  fertility: { label: 'Fertility', icon: Baby, tone: 'gold' },
  luck: { label: 'Luck', icon: Clover, tone: 'success' },
  healing: { label: 'Healing', icon: HeartPulse, tone: 'success' },
}

export const OUTCOMES: Record<Schema['AccusationOutcome'], Named> = {
  pending: { label: 'Awaiting trial', icon: Hourglass, tone: 'warning' },
  cleared: { label: 'Cleared', icon: Droplet, tone: 'success' },
  punished: { label: 'Punished', icon: Gavel, tone: 'warning' },
  exiled: { label: 'Exiled', icon: TrendingDown, tone: 'danger' },
  killed: { label: 'Killed', icon: Skull, tone: 'danger' },
}

export const STRAINS: Record<Schema['IdeaStrain'], Named> = {
  none: { label: 'No strain', icon: Hand, tone: 'muted' },
  distraction: { label: 'Distraction', icon: Brain, tone: 'info' },
  focus_loss: { label: 'Loss of focus', icon: Eye, tone: 'warning' },
  obsession: { label: 'Obsession', icon: Flame, tone: 'danger' },
}
