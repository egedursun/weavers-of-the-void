import {
  Bed,
  Cake,
  Flower2,
  Drum,
  Flame,
  Footprints,
  Gift,
  Handshake,
  HeartHandshake,
  Moon,
  PartyPopper,
  Scale,
  Ban,
  Swords,
  Wheat,
  Skull,
  Sparkles,
  Sword,
  FlameKindling,
  Sparkle,
  HandHeart,
} from 'lucide-react'
import type { Named } from '@/features/entity/environment/labels'

export const TRADITION: Record<string, Named> = {
  festival: { label: 'Festival', icon: PartyPopper, tone: 'gold' },
  fast: { label: 'Fast', icon: Scale, tone: 'verdigris' },
  funeral_rite: { label: 'Funeral rite', icon: Skull, tone: 'muted' },
  initiation: { label: 'Initiation', icon: Sparkles, tone: 'info' },
  marriage_rite: { label: 'Marriage rite', icon: HeartHandshake, tone: 'gold' },
  coming_of_age: { label: 'Coming of age', icon: Cake, tone: 'info' },
  taboo: { label: 'Taboo', icon: Ban, tone: 'danger' },
  offering: { label: 'Offering', icon: HandHeart, tone: 'gold' },
  pilgrimage: { label: 'Pilgrimage', icon: Footprints, tone: 'verdigris' },
  hospitality: { label: 'Hospitality', icon: Handshake, tone: 'success' },
  duel_custom: { label: 'Duel custom', icon: Sword, tone: 'danger' },
  mourning: { label: 'Mourning', icon: Flower2, tone: 'muted' },
  seasonal_rite: { label: 'Seasonal rite', icon: Wheat, tone: 'success' },
  martial_display: { label: 'Martial display', icon: Drum, tone: 'danger' },
  body_marking: { label: 'Body marking', icon: Swords, tone: 'warning' },
  ancestral_rite: { label: 'Ancestral rite', icon: Flame, tone: 'warning' },
  rest_custom: { label: 'Custom of rest', icon: Bed, tone: 'info' },
  vigil: { label: 'Vigil', icon: Moon, tone: 'verdigris' },
  gift_custom: { label: 'Custom of gifts', icon: Gift, tone: 'success' },
  purification: { label: 'Purification', icon: Sparkle, tone: 'verdigris' },
  commemoration: { label: 'Commemoration', icon: FlameKindling, tone: 'muted' },
  competition: { label: 'Competition', icon: Swords, tone: 'gold' },
}

export const CALENDAR_FIELDS: Record<string, string> = {
  axial_tilt: 'Axial tilt',
  year_length_days: 'Days a year',
  day_length_hours: 'Hours a day',
  moon_count: 'Moons',
  tidal_strength: 'Tides',
  season_count: 'Number of seasons',
  season_position: 'Season',
  calendar_entity_id: 'Calendar',
}

export function fieldLabel(key: string): string {
  return CALENDAR_FIELDS[key] ?? key.replaceAll('_', ' ')
}
