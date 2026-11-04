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
  offering: { label: 'Offering', icon: Gift, tone: 'gold' },
  pilgrimage: { label: 'Pilgrimage', icon: Footprints, tone: 'verdigris' },
  hospitality_law: { label: 'Hospitality', icon: Handshake, tone: 'success' },
  duel_custom: { label: 'Duel custom', icon: Sword, tone: 'danger' },
  mourning: { label: 'Mourning', icon: Flower2, tone: 'muted' },
  harvest_rite: { label: 'Harvest rite', icon: Wheat, tone: 'success' },
  war_dance: { label: 'War dance', icon: Drum, tone: 'danger' },
  scar_rite: { label: 'Scar rite', icon: Swords, tone: 'warning' },
  ancestor_feast: { label: 'Ancestor feast', icon: Flame, tone: 'warning' },
  siesta: { label: 'Midday rest', icon: Bed, tone: 'info' },
  night_vigil: { label: 'Night vigil', icon: Moon, tone: 'verdigris' },
}

export const CALENDAR_FIELDS: Record<string, string> = {
  axial_tilt: 'Axial tilt',
  year_length_days: 'Days a year',
  day_length_hours: 'Hours a day',
  moon_count: 'Moons',
  tidal_strength: 'Tides',
  season_position: 'Season',
  calendar_entity_id: 'Calendar',
}

export function fieldLabel(key: string): string {
  return CALENDAR_FIELDS[key] ?? key.replaceAll('_', ' ')
}
