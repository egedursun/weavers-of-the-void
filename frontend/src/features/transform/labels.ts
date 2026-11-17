import {
  ArrowDownToLine,
  ArrowUpFromLine,
  BadgeCheck,
  Ban,
  BookMarked,
  BookOpen,
  Bot,
  Brain,
  Building2,
  CircleDot,
  CircleSlash,
  Cloud,
  Crown,
  Dna,
  Feather,
  Flag,
  Flame,
  Gavel,
  Ghost,
  Globe,
  Hammer,
  HeartCrack,
  Home,
  Landmark,
  Languages,
  Layers,
  Lightbulb,
  type LucideIcon,
  Mountain,
  Orbit,
  PawPrint,
  Repeat,
  RotateCcw,
  Scale,
  ScrollText,
  Shapes,
  Skull,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Tent,
  Trees,
  Undo2,
  User,
  Users,
  Wand2,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const TRANSFORM_ICON: LucideIcon = Repeat

export const TRANSFORM_KINDS: Record<Schema['TransformKind'], Named> = {
  deification: { label: 'Deification', icon: Crown, tone: 'gold' },
  mantling: { label: 'Mantling', icon: Crown, tone: 'gold' },
  spirit_rising: { label: 'Rising as a spirit', icon: Ghost, tone: 'muted' },
  reincarnation: { label: 'Reincarnation', icon: RotateCcw, tone: 'verdigris' },
  possession: { label: 'Possession', icon: Ghost, tone: 'warning' },
  local_god: {
    label: 'A spirit raised to a local god',
    icon: Sparkles,
    tone: 'gold',
  },
  beast_curse: { label: 'Cursed into a beast', icon: PawPrint, tone: 'danger' },
  curse_lifted: {
    label: 'A beast’s curse lifted',
    icon: User,
    tone: 'success',
  },
  uplift: { label: 'Uplift', icon: Brain, tone: 'info' },
  city_state: {
    label: 'A city becomes a state',
    icon: Building2,
    tone: 'info',
  },
  secession: { label: 'Secession', icon: Flag, tone: 'warning' },
  theocracy: { label: 'Theocracy', icon: Landmark, tone: 'gold' },
  title_raised: {
    label: 'A realm raised to a title',
    icon: Crown,
    tone: 'gold',
  },
  realm_from_title: { label: 'A title made a realm', icon: Flag, tone: 'info' },
  manifestation: { label: 'Manifestation', icon: Wand2, tone: 'verdigris' },
  legend_fixed: {
    label: 'A legend fixed into an artwork',
    icon: BookMarked,
    tone: 'info',
  },
  artwork_remembered: {
    label: 'A lost artwork remembered as a legend',
    icon: Feather,
    tone: 'muted',
  },
  event_phenomenon: {
    label: 'An event becomes a phenomenon',
    icon: Zap,
    tone: 'warning',
  },
  dead_god: {
    label: 'The body of a dead god becomes a place',
    icon: Skull,
    tone: 'danger',
  },
  construct: {
    label: 'A made thing wakes as a construct',
    icon: Bot,
    tone: 'info',
  },
  beast_promotion: {
    label: 'A creature raised to a beast',
    icon: PawPrint,
    tone: 'warning',
  },
  language_death: { label: 'A language dies', icon: Languages, tone: 'muted' },
  language_revival: {
    label: 'A dead language revived',
    icon: Languages,
    tone: 'success',
  },
  theory_settled: {
    label: 'A theory settled into knowledge',
    icon: Lightbulb,
    tone: 'info',
  },
  tradition_codified: {
    label: 'A custom codified into law',
    icon: Gavel,
    tone: 'info',
  },
  fall: { label: 'Fall from godhood', icon: ArrowDownToLine, tone: 'danger' },
  restoration: {
    label: 'A fallen god regains godhood',
    icon: ArrowUpFromLine,
    tone: 'gold',
  },
  loss_of_sapience: {
    label: 'Loss of sapience',
    icon: HeartCrack,
    tone: 'danger',
  },
  ethnoreligious: {
    label: 'A faith becomes a people',
    icon: Users,
    tone: 'verdigris',
  },
  nation_building: {
    label: 'A realm forges a people',
    icon: Users,
    tone: 'info',
  },
  house_people: {
    label: 'A house grows into a people',
    icon: Home,
    tone: 'gold',
  },
  pocket_world: {
    label: 'A phenomenon grows into a world',
    icon: Globe,
    tone: 'warning',
  },
  world_soul: { label: 'A world’s soul ascends', icon: Orbit, tone: 'gold' },
  star_god: { label: 'A star raised to godhood', icon: Sun, tone: 'gold' },
  sacralisation: { label: 'Sacralisation', icon: Sparkles, tone: 'gold' },
  secularisation: { label: 'Secularisation', icon: Scale, tone: 'muted' },
  progenitor: {
    label: 'A beast founds a species',
    icon: Dna,
    tone: 'verdigris',
  },
  outer_entry: {
    label: 'An outer being enters the cosmos',
    icon: CircleDot,
    tone: 'danger',
  },
  corruption: {
    label: 'Corruption into an outer being',
    icon: Flame,
    tone: 'danger',
  },
  colossal_corpse: {
    label: 'A colossal corpse becomes a place',
    icon: Mountain,
    tone: 'warning',
  },
}

export const TRANSFORM_ENDS: Record<Schema['TransformEnd'], Named> = {
  son: { label: 'Son of the Creator', icon: Crown, tone: 'gold' },
  mortal: { label: 'Mortal', icon: User, tone: 'info' },
  spirit: { label: 'Spirit', icon: Ghost, tone: 'muted' },
  god: { label: 'God', icon: Sparkles, tone: 'gold' },
  beast: { label: 'Beast', icon: PawPrint, tone: 'warning' },
  species: { label: 'Kind of creature', icon: Dna, tone: 'verdigris' },
  people: { label: 'People', icon: Users, tone: 'info' },
  cult: { label: 'Faith', icon: Landmark, tone: 'gold' },
  polity: { label: 'Realm', icon: Flag, tone: 'info' },
  house: { label: 'House', icon: Home, tone: 'gold' },
  settlement: { label: 'Settlement', icon: Tent, tone: 'info' },
  faction: { label: 'Faction', icon: Swords, tone: 'warning' },
  title: { label: 'Title', icon: Crown, tone: 'gold' },
  legend: { label: 'Legend', icon: BookOpen, tone: 'verdigris' },
  creation: {
    label: 'What a legend made real',
    icon: Wand2,
    tone: 'verdigris',
  },
  artwork: { label: 'Artwork', icon: Shapes, tone: 'info' },
  event: { label: 'Event', icon: Zap, tone: 'warning' },
  phenomenon: { label: 'Phenomenon', icon: Cloud, tone: 'warning' },
  world: { label: 'World', icon: Globe, tone: 'info' },
  star: { label: 'Star', icon: Star, tone: 'gold' },
  ideology: { label: 'Teaching', icon: Scale, tone: 'muted' },
  outer_being: { label: 'Outer being', icon: CircleDot, tone: 'danger' },
  place: { label: 'Place', icon: Mountain, tone: 'muted' },
  made_thing: { label: 'Made thing', icon: Hammer, tone: 'info' },
  language: { label: 'Language', icon: Languages, tone: 'info' },
  knowledge: { label: 'Knowledge', icon: Lightbulb, tone: 'info' },
  theory: { label: 'Theory', icon: Brain, tone: 'muted' },
  tradition: { label: 'Custom', icon: Trees, tone: 'verdigris' },
  law: { label: 'Law', icon: Gavel, tone: 'info' },
}

export const TRANSFORM_STATES: Record<Schema['TransformState'], Named> = {
  done: { label: 'Done', icon: BadgeCheck, tone: 'success' },
  reverted: { label: 'Undone', icon: Undo2, tone: 'muted' },
}

export const TRANSFORM_TRIGGERS: Record<Schema['TransformTrigger'], Named> = {
  engine: { label: 'Its conditions held', icon: Layers, tone: 'info' },
  forced: { label: 'Forced by the Creator', icon: Zap, tone: 'gold' },
  creator: { label: 'Cast down by the Creator', icon: Crown, tone: 'gold' },
  council: { label: 'Ordered by the council', icon: Gavel, tone: 'warning' },
  fading: { label: 'Fading in a mortal body', icon: HeartCrack, tone: 'muted' },
  son: { label: 'Pressed by a son', icon: Sparkles, tone: 'verdigris' },
  curse: { label: 'A curse', icon: Skull, tone: 'danger' },
  void: { label: 'The void', icon: CircleDot, tone: 'danger' },
  dark_age: { label: 'A dark age', icon: CircleSlash, tone: 'muted' },
  punishment: { label: 'A god’s punishment', icon: Flame, tone: 'danger' },
  backfill: {
    label: 'Found in the old record',
    icon: ScrollText,
    tone: 'muted',
  },
}

export const PROSPECT_STANCES: Record<Schema['ProspectStance'], Named> = {
  open: { label: 'Open', icon: Sprout, tone: 'info' },
  blocked: { label: 'Blocked by the Creator', icon: Ban, tone: 'danger' },
  forced: { label: 'Ordered', icon: Zap, tone: 'gold' },
}

export const STAR_MODIFIER_SOURCES: Record<
  Schema['StarModifierSource'],
  Named
> = {
  god_death: { label: 'The death of its god', icon: Skull, tone: 'danger' },
  divine_act: { label: 'The Creator’s hand', icon: Sun, tone: 'gold' },
}
