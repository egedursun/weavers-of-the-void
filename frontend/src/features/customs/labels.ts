import {
  type LucideIcon,
  Anchor,
  Baby,
  BedDouble,
  Beer,
  BookOpen,
  Briefcase,
  Bug,
  CalendarDays,
  Church,
  Coins,
  Cpu,
  Crown,
  Droplets,
  Ear,
  Eye,
  Feather,
  FileText,
  Flame,
  FlaskConical,
  Flower2,
  Footprints,
  Gavel,
  Gem,
  Ghost,
  GraduationCap,
  Hammer,
  HandHeart,
  Heart,
  HeartCrack,
  HeartPulse,
  Home,
  Hourglass,
  Landmark,
  Languages,
  Leaf,
  Link,
  MapPin,
  Medal,
  Moon,
  Paintbrush,
  Palette,
  Pill,
  RefreshCcw,
  Scale,
  School,
  Scissors,
  Scroll,
  ScrollText,
  Shield,
  ShieldCheck,
  Ship,
  Skull,
  Soup,
  Sparkles,
  Sprout,
  Star,
  Stethoscope,
  Swords,
  Tag,
  Tent,
  TreeDeciduous,
  TrendingUp,
  User,
  UserRound,
  Users,
  UserX,
  Vote,
  Warehouse,
  Wheat,
  Wind,
  Wine,
  Zap,
  PaintBucket,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const CUSTOMS_ICON: LucideIcon = Feather

export const TAB_ICONS = {
  folk: Feather,
  body: Tag,
  town: Home,
  civics: Landmark,
} as const

export const WAYS: Record<Schema['RevivalWay'], Named> = {
  restore: { label: 'Restore the old ways', icon: RefreshCcw, tone: 'gold' },
  synthesis: { label: 'Join old and new', icon: Sparkles, tone: 'verdigris' },
  adopt: { label: "Take the rulers' ways", icon: TrendingUp, tone: 'info' },
  await: { label: 'Wait for a sign', icon: Hourglass, tone: 'warning' },
  withdraw: { label: 'Live apart', icon: Tent, tone: 'muted' },
  migrate: {
    label: 'Leave for a land of their own',
    icon: Footprints,
    tone: 'info',
  },
}

export const STAGES: Record<Schema['RevivalStage'], Named> = {
  steady: { label: 'Steady', icon: Anchor, tone: 'muted' },
  stress: { label: 'Stress', icon: Zap, tone: 'warning' },
  distortion: { label: 'Distortion', icon: Wind, tone: 'danger' },
  revitalisation: { label: 'Revival', icon: Sprout, tone: 'success' },
  new_steady: { label: 'A new steady way', icon: Star, tone: 'gold' },
  suppressed: { label: 'Put down', icon: Shield, tone: 'danger' },
}

export const GOALS: Record<Schema['RevivalGoal'], Named> = {
  revive_language: {
    label: 'Revive the language',
    icon: Languages,
    tone: 'info',
  },
  restore_god: { label: 'Restore the old god', icon: Sparkles, tone: 'gold' },
  expel_foreigners: { label: 'Expel foreigners', icon: Swords, tone: 'danger' },
  restore_land: { label: 'Take back the land', icon: MapPin, tone: 'warning' },
  restore_rule: { label: 'Rule itself', icon: Crown, tone: 'gold' },
  restore_law: {
    label: 'Restore the old law',
    icon: Scale,
    tone: 'gold',
  },
}

export const INTOXICANTS: Record<Schema['Intoxicant'], Named> = {
  brew: { label: 'Brew', icon: Beer, tone: 'gold' },
  wine: { label: 'Wine', icon: Wine, tone: 'danger' },
  spirits: { label: 'Spirits', icon: Flame, tone: 'warning' },
  smoke: { label: 'Smoke', icon: Wind, tone: 'muted' },
  leaf: { label: 'Leaf', icon: Leaf, tone: 'success' },
  fungus: { label: 'Fungus', icon: Sprout, tone: 'verdigris' },
  essence: { label: 'Essence', icon: Sparkles, tone: 'info' },
  synthetic: { label: 'Made substance', icon: FlaskConical, tone: 'warning' },
  animal_derived: { label: 'Drawn from beasts', icon: Bug, tone: 'danger' },
  resin: { label: 'Resin', icon: Droplets, tone: 'warning' },
  stimulant: { label: 'Stimulant', icon: Zap, tone: 'warning' },
}

export const USES: Record<Schema['IntoxicantUse'], Named> = {
  daily: { label: 'Daily', icon: CalendarDays, tone: 'warning' },
  feast: { label: 'At feasts', icon: Wine, tone: 'gold' },
  rite: { label: 'In rites', icon: Sparkles, tone: 'verdigris' },
  mourning: { label: 'In mourning', icon: HeartCrack, tone: 'muted' },
  forbidden: { label: 'Forbidden', icon: Shield, tone: 'danger' },
  medicine: { label: 'As medicine', icon: Pill, tone: 'success' },
  hospitality: { label: 'Offered to guests', icon: HandHeart, tone: 'gold' },
  courage: { label: 'For courage', icon: ShieldCheck, tone: 'warning' },
  work: { label: 'At work', icon: Hammer, tone: 'muted' },
}

export const MARK_KINDS: Record<Schema['MarkKind'], Named> = {
  tattoo: { label: 'Tattoo', icon: Paintbrush, tone: 'info' },
  scar: { label: 'Scar', icon: Swords, tone: 'danger' },
  piercing: { label: 'Piercing', icon: Gem, tone: 'gold' },
  shaping: { label: 'Shaping', icon: User, tone: 'muted' },
  filed_teeth: { label: 'Filed teeth', icon: Skull, tone: 'warning' },
  cosmetic: { label: 'Cosmetic', icon: Sparkles, tone: 'verdigris' },
  jewellery: { label: 'Jewellery', icon: Gem, tone: 'gold' },
  brand: { label: 'Brand', icon: Flame, tone: 'danger' },
  hair: { label: 'Hair', icon: Scissors, tone: 'info' },
  implant: { label: 'Implant', icon: Cpu, tone: 'verdigris' },
  paint: { label: 'Paint', icon: PaintBucket, tone: 'info' },
  stain: { label: 'Stain', icon: Palette, tone: 'muted' },
}

export const MEANINGS: Record<Schema['MarkMeaning'], Named> = {
  status: { label: 'Status', icon: Crown, tone: 'gold' },
  clan: { label: 'Clan', icon: Users, tone: 'info' },
  deed: { label: 'Deeds', icon: Swords, tone: 'danger' },
  age_set: { label: 'Age-set', icon: Footprints, tone: 'verdigris' },
  marriage: { label: 'Marriage', icon: Heart, tone: 'gold' },
  mourning: { label: 'Mourning', icon: Moon, tone: 'muted' },
  protection: { label: 'Protection', icon: Shield, tone: 'success' },
  crime: { label: 'Crime', icon: Gavel, tone: 'danger' },
  faith: { label: 'Faith', icon: Church, tone: 'gold' },
  profession: { label: 'Trade', icon: Hammer, tone: 'info' },
  beauty: { label: 'Beauty', icon: Flower2, tone: 'success' },
  bound_labour: { label: 'Bound labour', icon: Link, tone: 'danger' },
  healing: { label: 'Healing', icon: HeartPulse, tone: 'success' },
}

export const PATTERNS: Record<Schema['NamingPattern'], Named> = {
  given: { label: 'A given name', icon: User, tone: 'muted' },
  parent: { label: 'Named for a parent', icon: Users, tone: 'info' },
  clan: { label: 'Named for the clan', icon: Crown, tone: 'gold' },
  teknonym: { label: 'Named for a child', icon: Baby, tone: 'verdigris' },
  place: { label: 'Named for the birthplace', icon: MapPin, tone: 'info' },
  trade: { label: 'Named for the trade', icon: Hammer, tone: 'warning' },
  ancestral: { label: "A forebear's name", icon: TreeDeciduous, tone: 'gold' },
  event: { label: 'The time of birth', icon: CalendarDays, tone: 'info' },
}

export const NAME_FORMS: Record<Schema['NameForm'], Named> = {
  birth: { label: 'Birth name', icon: Baby, tone: 'muted' },
  secret: { label: 'Secret name', icon: Eye, tone: 'danger' },
  deed: { label: 'Deed name', icon: Swords, tone: 'gold' },
  initiation: { label: 'Initiation name', icon: Footprints, tone: 'verdigris' },
  marriage: { label: 'Marriage name', icon: Heart, tone: 'gold' },
  vow: { label: 'Vow name', icon: BookOpen, tone: 'info' },
  ascension: { label: 'Ascension name', icon: Crown, tone: 'gold' },
  posthumous: { label: 'Name after death', icon: Flower2, tone: 'muted' },
  adoption: { label: 'Adoption name', icon: Users, tone: 'info' },
  epithet: { label: 'Epithet', icon: Tag, tone: 'gold' },
}

export const GRADES: Record<Schema['AgeGrade'], Named> = {
  children: { label: 'Children', icon: Baby, tone: 'muted' },
  youths: { label: 'Youths', icon: Footprints, tone: 'info' },
  young_adults: { label: 'Young adults', icon: UserRound, tone: 'info' },
  junior_elders: { label: 'Junior elders', icon: Scroll, tone: 'verdigris' },
  senior_elders: { label: 'Senior elders', icon: Crown, tone: 'gold' },
  ancients: { label: 'Ancients', icon: Landmark, tone: 'muted' },
}

export const DUTIES: Record<Schema['GradeDuty'], Named> = {
  war: { label: 'War', icon: Swords, tone: 'danger' },
  herding: { label: 'Herding', icon: Footprints, tone: 'success' },
  labour: { label: 'Labour', icon: Hammer, tone: 'info' },
  council: { label: 'Council', icon: Landmark, tone: 'gold' },
}

export const PURPOSES: Record<Schema['CoopPurpose'], Named> = {
  mill: { label: 'A mill', icon: Wheat, tone: 'gold' },
  boats: { label: 'Boats', icon: Ship, tone: 'info' },
  irrigation: { label: 'Irrigation', icon: Droplets, tone: 'verdigris' },
  insurance: { label: 'Insurance', icon: Shield, tone: 'success' },
  burial: { label: 'Burial', icon: Ghost, tone: 'muted' },
  credit: { label: 'Credit', icon: Coins, tone: 'warning' },
  granary: { label: 'A shared granary', icon: Warehouse, tone: 'gold' },
  herding: { label: 'Shared herds', icon: Footprints, tone: 'success' },
  school: { label: 'A school', icon: School, tone: 'gold' },
  housing: { label: 'Housing', icon: Home, tone: 'gold' },
}

export const EVIDENCE_KINDS: Record<Schema['EvidenceKind'], Named> = {
  witness: { label: 'A witness', icon: Eye, tone: 'info' },
  trace: { label: 'A trace', icon: Footprints, tone: 'warning' },
  document: { label: 'A document', icon: FileText, tone: 'muted' },
  confession: { label: 'A confession', icon: Scroll, tone: 'danger' },
  divination: { label: 'A divination', icon: Sparkles, tone: 'verdigris' },
  magic: { label: 'Magic', icon: Zap, tone: 'gold' },
  expert: {
    label: 'One skilled in the matter',
    icon: GraduationCap,
    tone: 'info',
  },
  hearsay: { label: 'Hearsay', icon: Ear, tone: 'muted' },
  body: { label: 'What the body shows', icon: Stethoscope, tone: 'info' },
  record: { label: 'A record', icon: ScrollText, tone: 'info' },
}

export const MEMBERSHIPS: Record<Schema['Membership'], Named> = {
  citizen: { label: 'Citizen', icon: Landmark, tone: 'gold' },
  subject: { label: 'Subject', icon: Crown, tone: 'info' },
  resident_foreigner: {
    label: 'Resident foreigner',
    icon: Footprints,
    tone: 'muted',
  },
  protected_minority: {
    label: 'Protected minority',
    icon: Shield,
    tone: 'verdigris',
  },
  bound: { label: 'Bound', icon: Anchor, tone: 'danger' },
  stateless: { label: 'Stateless', icon: UserX, tone: 'gold' },
}

export const RIGHTS: Record<Schema['MemberRight'], Named> = {
  office: { label: 'Office', icon: Briefcase, tone: 'gold' },
  marriage: { label: 'Marriage', icon: Heart, tone: 'info' },
  arms: { label: 'Arms', icon: Swords, tone: 'danger' },
  courts: { label: 'The courts', icon: Gavel, tone: 'verdigris' },
  property: { label: 'Property', icon: Home, tone: 'gold' },
  movement: { label: 'Moving and settling', icon: Footprints, tone: 'info' },
  vote: { label: 'The vote', icon: Vote, tone: 'verdigris' },
  worship: { label: 'Open worship', icon: Sparkles, tone: 'gold' },
  assembly: { label: 'Assembly', icon: Users, tone: 'gold' },
  education: { label: 'Schooling', icon: GraduationCap, tone: 'gold' },
}

export const PATHS: Record<Schema['Naturalisation'], Named> = {
  descent: { label: 'By descent', icon: Users, tone: 'gold' },
  birthplace: { label: 'By birthplace', icon: Home, tone: 'info' },
  residence: { label: 'By residence', icon: Hourglass, tone: 'muted' },
  conversion: { label: 'By conversion', icon: Sparkles, tone: 'verdigris' },
  service: { label: 'By service', icon: Swords, tone: 'danger' },
  purchase: { label: 'By purchase', icon: Coins, tone: 'warning' },
  grant: { label: 'By grant', icon: Crown, tone: 'gold' },
  union: { label: 'By union', icon: Heart, tone: 'verdigris' },
  adoption: { label: 'By adoption', icon: Baby, tone: 'gold' },
}

export const RELIEFS: Record<Schema['ReliefKind'], Named> = {
  granary: { label: 'Granary distribution', icon: Wheat, tone: 'gold' },
  alms: { label: 'Alms', icon: HandHeart, tone: 'success' },
  workhouse: { label: 'Workhouses', icon: Hammer, tone: 'muted' },
  parish: { label: 'Parish relief', icon: Landmark, tone: 'verdigris' },
  foster_care: { label: 'Foster care', icon: Baby, tone: 'success' },
  sick_house: { label: 'Sick house', icon: HeartPulse, tone: 'info' },
  pension: { label: 'Pension', icon: Medal, tone: 'gold' },
  shelter: { label: 'Night shelter', icon: BedDouble, tone: 'gold' },
  public_kitchen: { label: 'Public kitchen', icon: Soup, tone: 'gold' },
}
