import {
  Coins,
  Atom,
  GitBranch,
  Network,
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
  Skull,
  Sparkles,
  Sun,
  Swords,
  Trophy,
  User,
  Users,
  Utensils,
  WandSparkles,
  GraduationCap,
  School,
  Binoculars,
  Heart,
  Hospital,
} from 'lucide-react'
import {
  FUNERAL_SPEC,
  type FuneralCustom,
} from '@/features/entity/society/folkLabels'
import { type Named } from '../realm/labels'

export const TENETS: Record<string, Named> = {
  pacifism: { label: 'Pacifism', icon: Bird, tone: 'success' },
  holy_war: { label: 'Holy war', icon: Swords, tone: 'danger' },
  asceticism: { label: 'Asceticism', icon: Leaf, tone: 'muted' },
  hidden_god: { label: 'Hidden god', icon: EyeOff, tone: 'muted' },
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
  sacrifice_of_people: {
    label: 'Sacrifice of people',
    icon: Skull,
    tone: 'danger',
  },
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
  divine_rule: { label: 'Divine rule', icon: Crown, tone: 'gold' },
  dietary_law: { label: 'Dietary law', icon: Utensils, tone: 'warning' },
  sacred_species: { label: 'Sacred beast', icon: PawPrint, tone: 'success' },
  pilgrimage_duty: {
    label: 'Duty of pilgrimage',
    icon: Footprints,
    tone: 'info',
  },
  souls_rest: { label: 'Souls at rest', icon: Moon, tone: 'muted' },
  void_communion: {
    label: 'Communion with the outside',
    icon: EyeOff,
    tone: 'danger',
  },
  feeding_the_hunger: {
    label: 'Feeding the outer hunger',
    icon: Flame,
    tone: 'danger',
  },
  whispered_secrets: {
    label: 'Secrets from outside',
    icon: Eye,
    tone: 'warning',
  },
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
  remembrance: {
    label: 'By remembrance',
    icon: ScrollText,
    tone: 'info',
    hint: 'By the memory the living keep of them; forgetting harms them',
  },
}

export const FANATICISMS: Record<string, Named> = {
  inquisition: { label: 'Inquisition', icon: Eye, tone: 'danger' },
  iconoclasm: { label: 'Iconoclasm', icon: Hammer, tone: 'warning' },
  crusade: { label: 'Crusade', icon: Swords, tone: 'danger' },
}

export const CLERGY: Record<string, Named> = {
  leader: { label: 'Leader of the faith', icon: Crown, tone: 'gold' },
  celebrant: { label: 'Celebrant', icon: Church, tone: 'info' },
  ascetic: { label: 'Ascetic', icon: BookOpen, tone: 'verdigris' },
  guardian_of_doctrine: {
    label: 'Guardian of doctrine',
    icon: Eye,
    tone: 'danger',
  },
  teacher: { label: 'Teacher', icon: GraduationCap, tone: 'info' },
  healer: { label: 'Healer', icon: Heart, tone: 'success' },
  seer: { label: 'Seer', icon: Binoculars, tone: 'verdigris' },
  keeper_of_sites: {
    label: 'Keeper of holy sites',
    icon: Church,
    tone: 'gold',
  },
  missionary: { label: 'Missionary', icon: BookOpen, tone: 'warning' },
  judge: { label: 'Judge', icon: Crown, tone: 'info' },
  scribe: { label: 'Clerk', icon: BookOpen, tone: 'muted' },
}

export const HOLDINGS: Record<string, Named> = {
  temple: { label: 'Temples', icon: Church, tone: 'gold' },
  land: { label: 'Lands', icon: MapIcon, tone: 'success' },
  relic: { label: 'Relics', icon: Gem, tone: 'verdigris' },
  holy_place: { label: 'Holy places', icon: Sparkles, tone: 'gold' },
  monastery: { label: 'Monasteries', icon: BookOpen, tone: 'info' },
  network: { label: 'Networks', icon: Network, tone: 'info' },
  shares: { label: 'Shares in companies', icon: Coins, tone: 'gold' },
  lines: { label: 'Holy lines', icon: GitBranch, tone: 'verdigris' },
  school: { label: 'School', icon: School, tone: 'verdigris' },
  hospital: { label: 'Hospital', icon: Hospital, tone: 'verdigris' },
}

export const STRATA: Record<string, Named & { depth: number }> = {
  reward: { label: 'Realm of reward', icon: Sun, tone: 'gold', depth: 0 },
  by_manner_of_death: {
    label: 'Realm of those who die in battle',
    icon: Swords,
    tone: 'warning',
    depth: 1,
  },
  by_line: {
    label: 'Realm of the line',
    icon: Users,
    tone: 'verdigris',
    depth: 2,
  },
  common: { label: 'Common realm', icon: Cloud, tone: 'muted', depth: 3 },
  punishment: {
    label: 'Realm of punishment',
    icon: Flame,
    tone: 'danger',
    depth: 4,
  },
  dissolution: {
    label: 'Realm where souls dissolve',
    icon: EyeOff,
    tone: 'muted',
    depth: 5,
  },
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

export const RITES: Record<FuneralCustom, Named> = FUNERAL_SPEC

export const REBIRTH_PATHS: Record<string, Named & { hint: string }> = {
  people: {
    label: 'Among its people',
    icon: Users,
    tone: 'verdigris',
    hint: 'Born again where it lived',
  },
  house: {
    label: 'Into its house',
    icon: Castle,
    tone: 'gold',
    hint: 'Born again to its own blood',
  },
  merit: {
    label: 'By merit',
    icon: Scale,
    tone: 'info',
    hint: 'The worthy to the rich, the wicked to the poor',
  },
  kind: {
    label: 'As another kind',
    icon: PawPrint,
    tone: 'success',
    hint: 'Born again as a creature of its land',
  },
  place: {
    label: 'By place',
    icon: MapIcon,
    tone: 'verdigris',
    hint: 'Born again tied to the place it died or was laid',
  },
}

export const LIVING_STATES: Record<string, Named> = {
  wandering: { label: 'Wandering', icon: Footprints, tone: 'warning' },
  judged: { label: 'Judged, unplaced', icon: Scale, tone: 'info' },
  in_realm: { label: 'At rest', icon: Moon, tone: 'verdigris' },
}

export const CRITERIA_FLOORS: Record<string, Named> = {
  renown_at_least: { label: 'Renown at least', icon: Trophy, tone: 'gold' },
  honour_at_least: { label: 'Honour at least', icon: Shield, tone: 'success' },
  faith_at_least: { label: 'Faith at least', icon: HandHeart, tone: 'info' },
  violence_at_least: {
    label: 'Violence at least',
    icon: Swords,
    tone: 'danger',
  },
  infamy_at_least: { label: 'Infamy at least', icon: Skull, tone: 'danger' },
}

export const BINDINGS: Record<string, Named> = {
  none: { label: 'Unbound', icon: Ghost, tone: 'muted' },
  place: { label: 'A place', icon: MapPin, tone: 'success' },
  item: { label: 'An item', icon: Gem, tone: 'verdigris' },
  structure: { label: 'A building', icon: Castle, tone: 'gold' },
  beast: { label: 'A beast', icon: PawPrint, tone: 'warning' },
  person: { label: 'A person', icon: User, tone: 'info' },
  realm: { label: 'A realm', icon: Crown, tone: 'gold' },
  network: { label: 'A network', icon: Network, tone: 'info' },
  line: { label: 'A line of descent', icon: GitBranch, tone: 'verdigris' },
  tenet: { label: 'A tenet', icon: ScrollText, tone: 'gold' },
  natural_law: { label: 'A law of nature', icon: Atom, tone: 'verdigris' },
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
  deeds: 'Deeds',
  imprint: 'Imprint',
  traits: 'Traits',
  rite: 'Funeral rite',
  state: 'State',
  patron_son_id: 'Patron god',
  sealed: 'Seal',
  seal_strength: 'Seal strength',
  binding: 'Binding',
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
  rebirth_path: 'Path of rebirth',
  devotion: 'Devotion',
  liturgical_language_id: 'Liturgy',
  parent_cult_id: 'Mother church',
  fanaticism: 'Fanaticism',
  excommunicated: 'The cast out',
  zeal_parts: 'Forces on the zeal',
}

type Criteria = {
  priority?: number
  no_god?: boolean
  needs_rite?: boolean
  score_at_least?: number | null
  score_below?: number | null
  renown_at_least?: number | null
  honour_at_least?: number | null
  faith_at_least?: number | null
  violence_at_least?: number | null
  infamy_at_least?: number | null
  rites?: readonly string[]
  tenets_any?: readonly string[]
}

export function criteriaText(criteria: Criteria): string[] {
  const lines: string[] = []
  if (criteria.no_god) lines.push('Souls with no god')
  if (criteria.score_at_least != null)
    lines.push(`Score ${criteria.score_at_least} or more`)
  if (criteria.score_below != null)
    lines.push(`Score below ${criteria.score_below}`)
  for (const [key, spec] of Object.entries(CRITERIA_FLOORS)) {
    const value = criteria[key as keyof Criteria]
    if (typeof value === 'number') lines.push(`${spec.label} ${value}`)
  }
  if (criteria.needs_rite) lines.push('Given its rites')
  if (criteria.rites && criteria.rites.length > 0)
    lines.push(
      `Rite: ${criteria.rites.map((rite) => (RITES as Record<string, Named>)[rite]?.label ?? rite).join(', ')}`
    )
  if (criteria.tenets_any && criteria.tenets_any.length > 0)
    lines.push(
      `Faith holds ${criteria.tenets_any.map((tenet) => TENETS[tenet]?.label ?? tenet).join(' or ')}`
    )
  return lines.length > 0 ? lines : ['Any soul with a god']
}
