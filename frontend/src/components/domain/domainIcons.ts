import {
  Activity,
  BookOpen,
  Brain,
  Building2,
  Castle,
  Church,
  CircleHelp,
  Crown,
  Drama,
  Eye,
  Flame,
  Gavel,
  Gem,
  Ghost,
  Hammer,
  HandHeart,
  Handshake,
  Heart,
  Languages,
  Lightbulb,
  type LucideIcon,
  Map,
  MapPin,
  Moon,
  Mountain,
  Package,
  Paintbrush,
  PawPrint,
  Scale,
  ScrollText,
  Shield,
  Ship,
  Sparkles,
  Swords,
  User,
  Users,
  VolumeX,
  Wheat,
  Wind,
  Zap,
} from 'lucide-react'
import { type components } from '@/api/generated/schema'

type Schemas = components['schemas']

export type IconVocabulary =
  'entity-type' | 'stat' | 'passion' | 'creator-passion' | 'commodity'

export const ENTITY_TYPE_ICON: Record<Schemas['EntityType'], LucideIcon> = {
  region: Map,
  place: MapPin,
  resource: Gem,
  settlement: Building2,
  species: PawPrint,
  people: Users,
  mortal: User,
  item: Package,
  structure: Castle,
  language: Languages,
  legend: BookOpen,
  tradition: ScrollText,
  cult: Church,
  faction: Shield,
  celestial: Moon,
  artwork: Paintbrush,
  law: Gavel,
  spirit: Ghost,
  knowledge: Lightbulb,
  prophecy: Eye,
  event: Zap,
  vessel: Ship,
  outer_being: Brain,
  army: Swords,
  natural_law: Scale,
}

export const STAT_ICON: Record<Schemas['Stat'], LucideIcon> = {
  strength: Swords,
  endurance: Shield,
  agility: Wind,
  wisdom: Lightbulb,
  cunning: Drama,
  will: Flame,
  creativity: Paintbrush,
  charisma: Users,
  might: Crown,
}

export const PASSION_ICON: Record<Schemas['Passion'], LucideIcon> = {
  loyalty: Handshake,
  ambition: Crown,
  wrath: Flame,
  mercy: HandHeart,
}

export const CREATOR_PASSION_ICON: Record<
  Schemas['CreatorPassion'],
  LucideIcon
> = {
  order: Scale,
  chaos: Activity,
  beauty: Sparkles,
  knowledge: BookOpen,
  war: Swords,
  mercy: Heart,
  creation: Hammer,
  silence: VolumeX,
}

export const COMMODITY_ICON: Record<Schemas['Commodity'], LucideIcon> = {
  food: Wheat,
  ore: Mountain,
  goods: Package,
}

export const DOMAIN_ICON_FALLBACK: LucideIcon = CircleHelp

export const ICON_VOCABULARIES: Record<
  IconVocabulary,
  Readonly<Record<string, LucideIcon>>
> = {
  'entity-type': ENTITY_TYPE_ICON,
  stat: STAT_ICON,
  passion: PASSION_ICON,
  'creator-passion': CREATOR_PASSION_ICON,
  commodity: COMMODITY_ICON,
}

export function domainIcon(
  vocabulary: IconVocabulary,
  value: string
): LucideIcon {
  const table = ICON_VOCABULARIES[vocabulary]
  return Object.hasOwn(table, value) ? table[value] : DOMAIN_ICON_FALLBACK
}
