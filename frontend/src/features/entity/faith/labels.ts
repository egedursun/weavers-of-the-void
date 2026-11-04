import {
  Angry,
  Ban,
  Bird,
  BookOpen,
  Castle,
  Church,
  Circle,
  CircleOff,
  Cloud,
  Crown,
  Droplets,
  Eye,
  EyeOff,
  Flame,
  Footprints,
  Gem,
  Ghost,
  Globe,
  Hammer,
  HandHeart,
  Handshake,
  HeartCrack,
  Leaf,
  Lock,
  Map as MapIcon,
  MapPin,
  Medal,
  Megaphone,
  Moon,
  PawPrint,
  RefreshCw,
  Scale,
  ScrollText,
  Shield,
  Shovel,
  Skull,
  Sparkles,
  Sun,
  Swords,
  Trophy,
  User,
  Users,
  Utensils,
  WandSparkles,
  Wind,
} from 'lucide-react'
import { type Named } from '../realm/labels'

export const TENETS: Record<string, Named> = {
  pacifism: { label: 'Pacifism', icon: Bird, tone: 'success' },
  holy_war: { label: 'Holy war', icon: Swords, tone: 'danger' },
  asceticism: { label: 'Asceticism', icon: Leaf, tone: 'muted' },
  sacred_suffering: {
    label: 'Sacred suffering',
    icon: HeartCrack,
    tone: 'warning',
  },
  purity_of_body: { label: 'Purity of body', icon: Droplets, tone: 'info' },
  ancestor_veneration: {
    label: 'Ancestor veneration',
    icon: Users,
    tone: 'gold',
  },
  human_sacrifice: { label: 'Human sacrifice', icon: Skull, tone: 'danger' },
  animal_sacrifice: {
    label: 'Animal sacrifice',
    icon: PawPrint,
    tone: 'warning',
  },
  celibate_clergy: { label: 'Celibate clergy', icon: Moon, tone: 'verdigris' },
  proselytism: { label: 'Proselytism', icon: Megaphone, tone: 'info' },
  exclusivity: { label: 'Exclusivity', icon: Lock, tone: 'gold' },
  syncretic_openness: {
    label: 'Open to other gods',
    icon: Handshake,
    tone: 'success',
  },
  monastic_learning: {
    label: 'Monastic learning',
    icon: BookOpen,
    tone: 'info',
  },
  anti_magic: { label: 'Against magic', icon: Ban, tone: 'danger' },
  sanctified_magic: {
    label: 'Sanctified magic',
    icon: WandSparkles,
    tone: 'verdigris',
  },
  judgement_by_deeds: { label: 'Judged by deeds', icon: Scale, tone: 'gold' },
  judgement_by_faith: {
    label: 'Judged by faith',
    icon: HandHeart,
    tone: 'gold',
  },
  reincarnation: { label: 'Reincarnation', icon: RefreshCw, tone: 'verdigris' },
  martyrdom_glory: {
    label: 'Glory of martyrdom',
    icon: Medal,
    tone: 'danger',
  },
  divine_kingship: { label: 'Divine kingship', icon: Crown, tone: 'gold' },
  dietary_law: { label: 'Dietary law', icon: Utensils, tone: 'warning' },
  sacred_species: { label: 'Sacred beast', icon: PawPrint, tone: 'success' },
  pilgrimage_duty: {
    label: 'Duty of pilgrimage',
    icon: Footprints,
    tone: 'info',
  },
  souls_rest: { label: 'Souls at rest', icon: Moon, tone: 'muted' },
}

export const JUDGEMENTS: Record<string, Named & { hint: string }> = {
  deeds: {
    label: 'By deeds',
    icon: Scale,
    tone: 'gold',
    hint: 'What they did in life',
  },
  faith: {
    label: 'By faith',
    icon: HandHeart,
    tone: 'info',
    hint: 'How truly they believed',
  },
  rite: {
    label: 'By rite',
    icon: Flame,
    tone: 'warning',
    hint: 'How they were laid to rest',
  },
  favour: {
    label: 'By favour',
    icon: Sparkles,
    tone: 'verdigris',
    hint: 'Whom the god loved',
  },
  none: {
    label: 'No judgement',
    icon: CircleOff,
    tone: 'muted',
    hint: 'All souls fall alike',
  },
}

export const FANATICISMS: Record<string, Named> = {
  inquisition: { label: 'Inquisition', icon: Eye, tone: 'danger' },
  iconoclasm: { label: 'Iconoclasm', icon: Hammer, tone: 'warning' },
  crusade: { label: 'Crusade', icon: Swords, tone: 'danger' },
}

export const CLERGY: Record<string, Named> = {
  high_priest: { label: 'High priest', icon: Crown, tone: 'gold' },
  priest: { label: 'Priest', icon: Church, tone: 'info' },
  monk: { label: 'Monk', icon: BookOpen, tone: 'verdigris' },
  inquisitor: { label: 'Inquisitor', icon: Eye, tone: 'danger' },
}

export const HOLDINGS: Record<string, Named> = {
  temple: { label: 'Temples', icon: Church, tone: 'gold' },
  land: { label: 'Lands', icon: MapIcon, tone: 'success' },
  relic: { label: 'Relics', icon: Gem, tone: 'verdigris' },
  holy_place: { label: 'Holy places', icon: Sparkles, tone: 'gold' },
  monastery: { label: 'Monasteries', icon: BookOpen, tone: 'info' },
}

export const STRATA: Record<string, Named & { depth: number }> = {
  paradise: { label: 'Paradise', icon: Sun, tone: 'gold', depth: 0 },
  warrior_hall: {
    label: 'Hall of warriors',
    icon: Swords,
    tone: 'warning',
    depth: 1,
  },
  ancestor_hall: {
    label: 'Hall of ancestors',
    icon: Users,
    tone: 'verdigris',
    depth: 2,
  },
  plain: { label: 'Grey plain', icon: Cloud, tone: 'muted', depth: 3 },
  torment: { label: 'Torment', icon: Flame, tone: 'danger', depth: 4 },
  oblivion: { label: 'Oblivion', icon: EyeOff, tone: 'muted', depth: 5 },
}

export const SOUL_STATES: Record<string, Named> = {
  wandering: { label: 'Wandering', icon: Footprints, tone: 'warning' },
  judged: { label: 'Judged', icon: Scale, tone: 'info' },
  in_realm: { label: 'At rest', icon: Moon, tone: 'verdigris' },
  reborn: { label: 'Reborn', icon: RefreshCw, tone: 'success' },
  consumed: { label: 'Devoured', icon: Skull, tone: 'danger' },
  released: { label: 'Released', icon: Sparkles, tone: 'gold' },
}

export const ALIGNMENTS: Record<string, Named> = {
  guardian: { label: 'Guardian', icon: Shield, tone: 'success' },
  neutral: { label: 'Neutral', icon: Circle, tone: 'muted' },
  vengeful: { label: 'Vengeful', icon: Angry, tone: 'danger' },
}

export const RITES: Record<string, Named> = {
  burial: { label: 'Buried', icon: Shovel, tone: 'muted' },
  burning: { label: 'Burned', icon: Flame, tone: 'warning' },
  exposure: { label: 'Given to the sky', icon: Wind, tone: 'info' },
  none: { label: 'Unburied', icon: CircleOff, tone: 'danger' },
}

export const BINDINGS: Record<string, Named> = {
  none: { label: 'Unbound', icon: Ghost, tone: 'muted' },
  place: { label: 'A place', icon: MapPin, tone: 'success' },
  item: { label: 'An item', icon: Gem, tone: 'verdigris' },
  structure: { label: 'A building', icon: Castle, tone: 'gold' },
  beast: { label: 'A beast', icon: PawPrint, tone: 'warning' },
  person: { label: 'A person', icon: User, tone: 'info' },
}

export const DEEDS: Record<string, Named> = {
  renown: { label: 'Renown', icon: Trophy, tone: 'gold' },
  honour: { label: 'Honour', icon: Shield, tone: 'success' },
  faith: { label: 'Faith', icon: HandHeart, tone: 'info' },
  violence: { label: 'Violence', icon: Swords, tone: 'danger' },
  infamy: { label: 'Infamy', icon: Skull, tone: 'danger' },
}

export const GATES: Record<string, Named> = {
  tenet: { label: 'By its faith’s tenet', icon: ScrollText, tone: 'verdigris' },
  natural_law: { label: 'By the law of the world', icon: Globe, tone: 'info' },
  rite: { label: 'By a rite', icon: Flame, tone: 'warning' },
  god: { label: 'By a god’s hand', icon: Sparkles, tone: 'gold' },
}

export const SOUL_FIELDS: Record<string, string> = {
  memory_strength: 'Memory of the living',
  veneration: 'Veneration',
  alignment: 'Temper',
}

export const DOCTRINE_FIELDS: Record<string, string> = {
  orthodoxy: 'Orthodoxy',
  tithe_rate: 'Tithe rate',
  treasury: 'Treasury',
  clergy_count: 'Clergy',
  clergy_quality: 'Clergy learning',
  zeal: 'Zeal',
  doctrinal_distance: 'Drift from the founding',
  judgement: 'Judgement of the dead',
}

export function criterion(key: string, value: number | string): string {
  if (key === 'score_at_least') return `Deeds score ${value} or more`
  if (key === 'score_below') return `Deeds score below ${value}`
  if (key === 'score_between') return `Deeds score ${value}`
  if (key === 'no_god') return 'Souls with no god'
  return `${key.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase())} ${value}`
}
