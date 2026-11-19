import {
  Cpu,
  Ban,
  BookOpen,
  Building2,
  CalendarClock,
  Castle,
  CircleCheck,
  CircleHelp,
  CircleX,
  Cloud,
  CloudFog,
  Coins,
  Compass,
  Crown,
  Dice5,
  Droplets,
  Eye,
  Feather,
  FileText,
  Flame,
  Footprints,
  Gavel,
  Ghost,
  Heart,
  HeartCrack,
  HeartPulse,
  Home,
  Hourglass,
  Infinity as InfinityIcon,
  Landmark,
  type LucideIcon,
  Megaphone,
  Mic,
  Moon,
  Mountain,
  MountainSnow,
  Orbit,
  PauseCircle,
  Repeat,
  Route,
  Scale,
  Scroll,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Shuffle,
  Signpost,
  Skull,
  Sparkles,
  Sprout,
  Star,
  Sun,
  Swords,
  Tent,
  Trees,
  TreePine,
  Undo2,
  Users,
  Waves,
  Wheat,
  Wind,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const SACRED_ICON: LucideIcon = Sparkles

export const TAB_ICONS = {
  spirits: Landmark,
  mysteries: Eye,
  rites: Scroll,
  omens: Orbit,
  feelings: Heart,
} as const

export const SPIRIT_KINDS: Record<Schema['GeniusLocusKind'], Named> = {
  river: { label: 'River', icon: Waves, tone: 'info' },
  spring: { label: 'Spring', icon: Droplets, tone: 'info' },
  lake: { label: 'Lake', icon: Waves, tone: 'verdigris' },
  well: { label: 'Well', icon: Droplets, tone: 'muted' },
  shore: { label: 'Shore', icon: Waves, tone: 'warning' },
  grove: { label: 'Grove', icon: TreePine, tone: 'success' },
  forest: { label: 'Forest', icon: Trees, tone: 'success' },
  mountain: { label: 'Mountain', icon: MountainSnow, tone: 'muted' },
  cave: { label: 'Cave', icon: Mountain, tone: 'muted' },
  crossroads: { label: 'Crossroads', icon: Signpost, tone: 'gold' },
  wilds: { label: 'Wilds', icon: Compass, tone: 'warning' },
  field: { label: 'Field', icon: Wheat, tone: 'gold' },
  city: { label: 'Town', icon: Building2, tone: 'gold' },
  hearth: { label: 'Hearth', icon: Home, tone: 'danger' },
}

export const OFFENCES: Record<Schema['SpiritOffence'], Named> = {
  pollution: { label: 'Pollution', icon: CloudFog, tone: 'danger' },
  clearing: { label: 'Clearing of the woods', icon: Trees, tone: 'warning' },
  unpaid: { label: 'Offerings left unpaid', icon: Coins, tone: 'warning' },
  taboo: { label: 'A broken taboo', icon: Ban, tone: 'danger' },
}

export const RANKS: Record<Schema['BureauRank'], Named> = {
  hearth: { label: 'Hearth', icon: Home, tone: 'muted' },
  local: { label: 'Local', icon: Signpost, tone: 'info' },
  city: { label: 'Town', icon: Building2, tone: 'verdigris' },
  province: { label: 'Province', icon: Castle, tone: 'gold' },
  ministry: { label: 'Ministry', icon: Crown, tone: 'gold' },
}

export const PETITION_KINDS: Record<Schema['PetitionKind'], Named> = {
  healing: { label: 'Healing', icon: HeartPulse, tone: 'success' },
  harvest: { label: 'A good harvest', icon: Wheat, tone: 'gold' },
  fertility: { label: 'Children', icon: Sprout, tone: 'success' },
  safe_passage: { label: 'Safe passage', icon: Route, tone: 'info' },
  prosperity: { label: 'Prosperity', icon: Coins, tone: 'gold' },
  suit: { label: 'A suit against a spirit', icon: Gavel, tone: 'danger' },
}

export const PETITION_STATUS: Record<Schema['PetitionStatus'], Named> = {
  filed: { label: 'Filed', icon: FileText, tone: 'info' },
  delayed: { label: 'Delayed', icon: Hourglass, tone: 'warning' },
  granted: { label: 'Granted', icon: CircleCheck, tone: 'success' },
  denied: { label: 'Denied', icon: CircleX, tone: 'danger' },
  appealed: { label: 'Appealed', icon: Scale, tone: 'verdigris' },
  dismissed: { label: 'Dismissed', icon: Ban, tone: 'muted' },
}

export const MYSTIC_STATES: Record<Schema['MysticState'], Named> = {
  seeker: { label: 'Seeker', icon: Compass, tone: 'info' },
  visionary: { label: 'Visionary', icon: Eye, tone: 'verdigris' },
  revered: { label: 'Revered', icon: Star, tone: 'gold' },
  persecuted: { label: 'Persecuted', icon: ShieldAlert, tone: 'danger' },
  founder: { label: 'Founder', icon: Landmark, tone: 'gold' },
  lapsed: { label: 'Lapsed', icon: PauseCircle, tone: 'muted' },
}

export const VISION_KINDS: Record<Schema['VisionKind'], Named> = {
  vision: { label: 'Vision', icon: Eye, tone: 'verdigris' },
  union: { label: 'Union', icon: InfinityIcon, tone: 'gold' },
  voice: { label: 'A voice', icon: Mic, tone: 'info' },
  trance: { label: 'Trance', icon: Moon, tone: 'muted' },
}

export const STAGES: Record<Schema['MillenarianStage'], Named> = {
  stirring: { label: 'Stirring', icon: Wind, tone: 'info' },
  gathering: { label: 'Gathering', icon: Users, tone: 'verdigris' },
  vigil: { label: 'In vigil', icon: Tent, tone: 'warning' },
  marching: { label: 'Marching', icon: Footprints, tone: 'danger' },
  redated: { label: 'A new date set', icon: CalendarClock, tone: 'warning' },
  sect: { label: 'Became a sect', icon: Landmark, tone: 'gold' },
  dispersed: { label: 'Dispersed', icon: Shuffle, tone: 'muted' },
}

export const CAUSES: Record<Schema['TheodicyCause'], Named> = {
  plague: { label: 'Plague', icon: Skull, tone: 'danger' },
  famine: { label: 'Famine', icon: Wheat, tone: 'warning' },
  defeat: { label: 'Defeat in battle', icon: Swords, tone: 'danger' },
  disaster: { label: 'Disaster', icon: Flame, tone: 'warning' },
}

export const RESOLUTIONS: Record<Schema['TheodicyResolution'], Named> = {
  pending: { label: 'Unresolved', icon: Hourglass, tone: 'warning' },
  answered: { label: 'Answered by the god', icon: Sun, tone: 'gold' },
  argued: { label: 'Settled by argument', icon: BookOpen, tone: 'info' },
  new_doctrine: { label: 'A new doctrine', icon: Scroll, tone: 'verdigris' },
  conversion: { label: 'Turned away', icon: Undo2, tone: 'danger' },
  secular_drift: { label: 'Drifted from faith', icon: Cloud, tone: 'muted' },
}

export const SACRAMENTS: Record<Schema['SacramentKind'], Named> = {
  birth_blessing: { label: 'Birth blessing', icon: Sprout, tone: 'success' },
  initiation: { label: 'Initiation', icon: Feather, tone: 'info' },
  marriage: { label: 'Marriage', icon: Heart, tone: 'danger' },
  last_rites: { label: 'Last rites', icon: Moon, tone: 'muted' },
}

export const PROTECTIONS: Record<Schema['SacramentProtection'], Named> = {
  routing: { label: 'The soul’s way after death', icon: Route, tone: 'gold' },
  possession: { label: 'Possession', icon: ShieldCheck, tone: 'info' },
  unrest: { label: 'Unrest at death', icon: Ghost, tone: 'verdigris' },
}

export const AFTERLIVES: Record<Schema['AfterlifeModel'], Named> = {
  judged_realms: { label: 'Realms of judgement', icon: Scale, tone: 'gold' },
  common_realm: { label: 'A common realm', icon: Users, tone: 'muted' },
  realm_by_death: {
    label: 'A realm for those who die in battle',
    icon: Swords,
    tone: 'danger',
  },
  realm_of_line: { label: 'A realm of the line', icon: Home, tone: 'info' },
  rebirth: { label: 'Rebirth', icon: Repeat, tone: 'success' },
  wandering: {
    label: 'Wandering among the living',
    icon: Ghost,
    tone: 'verdigris',
  },
  union: { label: 'Union with the divine', icon: InfinityIcon, tone: 'gold' },
  oblivion: { label: 'Oblivion', icon: CircleX, tone: 'muted' },
}

export const DIVINATIONS: Record<Schema['DivinationKind'], Named> = {
  augury: { label: 'Augury', icon: Feather, tone: 'info' },
  haruspicy: { label: 'Haruspicy', icon: HeartCrack, tone: 'danger' },
  astrology: { label: 'Astrology', icon: Star, tone: 'gold' },
  oracle: { label: 'Oracle', icon: Megaphone, tone: 'verdigris' },
  lots: { label: 'Lots', icon: Dice5, tone: 'warning' },
  dream_reading: { label: 'Dream reading', icon: Moon, tone: 'muted' },
}

export const VALIDITIES: Record<Schema['DivinationValidity'], Named> = {
  god_answers: { label: 'A god answers it', icon: Sun, tone: 'gold' },
  seer_gift: { label: 'A seer reads it', icon: Eye, tone: 'verdigris' },
  natural_law: {
    label: 'A law of nature makes it real',
    icon: Orbit,
    tone: 'info',
  },
  noise: { label: 'Noise', icon: CircleHelp, tone: 'muted' },
}

export const QUESTIONS: Record<Schema['DivinationQuestion'], Named> = {
  battle: { label: 'Battle', icon: Swords, tone: 'danger' },
  war: { label: 'War', icon: Shield, tone: 'danger' },
  wedding: { label: 'Wedding', icon: Heart, tone: 'success' },
  coronation: { label: 'Accession', icon: Crown, tone: 'gold' },
  harvest: { label: 'Harvest', icon: Wheat, tone: 'gold' },
}

export const VERDICTS: Record<Schema['OmenVerdict'], Named> = {
  auspicious: { label: 'Auspicious', icon: Sun, tone: 'success' },
  inauspicious: { label: 'Inauspicious', icon: Cloud, tone: 'danger' },
  unclear: { label: 'Unclear', icon: CircleHelp, tone: 'muted' },
}

export const SOURCES: Record<Schema['ForesightSource'], Named> = {
  power: { label: 'A seer’s gift', icon: Eye, tone: 'verdigris' },
  divination: { label: 'A reading of omens', icon: Orbit, tone: 'info' },
  god: { label: 'A god’s showing', icon: Sun, tone: 'gold' },
  made_oracle: { label: 'A made oracle', icon: Cpu, tone: 'info' },
}

export const FORESIGHT_STATUS: Record<Schema['ForesightStatus'], Named> = {
  pending: { label: 'Yet to come', icon: Hourglass, tone: 'warning' },
  fulfilled: { label: 'Came true', icon: CircleCheck, tone: 'success' },
  failed: { label: 'Failed', icon: CircleX, tone: 'danger' },
  clouded: { label: 'Clouded', icon: CloudFog, tone: 'muted' },
}

export const FORESEEN: Record<'dies' | 'falls', Named> = {
  dies: { label: 'Dies', icon: Skull, tone: 'danger' },
  falls: { label: 'Falls', icon: Castle, tone: 'danger' },
}
