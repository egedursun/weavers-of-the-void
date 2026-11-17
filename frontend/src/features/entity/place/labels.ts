import {
  DoorOpen,
  Brain,
  Users,
  Anchor,
  BookOpen,
  Castle,
  CircleDot,
  Compass,
  Droplet,
  Droplets,
  Eye,
  Flame,
  Footprints,
  Gem,
  Ghost,
  Hammer,
  Landmark,
  Lock,
  Mountain,
  MountainSnow,
  PawPrint,
  Pickaxe,
  Route,
  Scroll,
  Search,
  Shell,
  Skull,
  Sparkles,
  Sprout,
  Swords,
  Trees,
  TreePine,
  Waves,
  Waypoints,
  Wand,
  Sun,
  type LucideIcon,
  Building2,
  Orbit,
  Snowflake,
  Wind,
  CloudFog,
} from 'lucide-react'
import { type Named, plain } from '../environment/labels'

export const PLACE_ICON: LucideIcon = Landmark

export const KIND: Record<string, Named & { hint: string }> = {
  mountain: {
    label: 'Mountain',
    icon: Mountain,
    tone: 'muted',
    hint: 'High ground with deep seams below',
  },
  peak: {
    label: 'Peak',
    icon: MountainSnow,
    tone: 'info',
    hint: 'A summit where rites are kept',
  },
  pass: {
    label: 'Pass',
    icon: Route,
    tone: 'warning',
    hint: 'A chokepoint that draws battles',
  },
  forest: {
    label: 'Forest',
    icon: Trees,
    tone: 'success',
    hint: 'Heavy cover for ambushes',
  },
  grove: {
    label: 'Grove',
    icon: TreePine,
    tone: 'verdigris',
    hint: 'A notable wood, half holy',
  },
  river: {
    label: 'River',
    icon: Waves,
    tone: 'info',
    hint: 'Running water and a crossing to hold',
  },
  ford: {
    label: 'Ford',
    icon: Footprints,
    tone: 'info',
    hint: 'A crossing armies fight for',
  },
  lake: {
    label: 'Lake',
    icon: Droplets,
    tone: 'info',
    hint: 'Still water that hides things',
  },
  spring: {
    label: 'Spring',
    icon: Droplet,
    tone: 'verdigris',
    hint: 'Fresh water, often revered',
  },
  cave: {
    label: 'Cave',
    icon: CircleDot,
    tone: 'muted',
    hint: 'A hollow under the earth',
  },
  cavern_system: {
    label: 'Cavern system',
    icon: CircleDot,
    tone: 'danger',
    hint: 'Deep halls that reach the underworld',
  },
  ruin: {
    label: 'Ruin',
    icon: Castle,
    tone: 'warning',
    hint: 'Broken walls: heavy cover and buried things',
  },
  island: {
    label: 'Island',
    icon: Shell,
    tone: 'info',
    hint: 'Land ringed by water',
  },
  swamp: {
    label: 'Swamp',
    icon: Sprout,
    tone: 'muted',
    hint: 'Wet ground where spirits linger',
  },
  well: {
    label: 'Well',
    icon: CircleDot,
    tone: 'verdigris',
    hint: 'A deep shaft, often sacred',
  },
  valley: {
    label: 'Valley',
    icon: Sun,
    tone: 'success',
    hint: 'Open, fertile ground',
  },
  cliff: {
    label: 'Cliff',
    icon: Mountain,
    tone: 'warning',
    hint: 'A sheer face and a chokepoint',
  },
  volcano: {
    label: 'Volcano',
    icon: Flame,
    tone: 'danger',
    hint: 'Fire mountain with rich seams',
  },
  crater: {
    label: 'Crater',
    icon: CircleDot,
    tone: 'warning',
    hint: 'A wound in the land',
  },
  battlefield: {
    label: 'Battlefield',
    icon: Swords,
    tone: 'danger',
    hint: 'Ground worn by many battles',
  },
  burial_ground: {
    label: 'Burial ground',
    icon: Skull,
    tone: 'gold',
    hint: 'Holy ground of the dead',
  },
  lair: {
    label: 'Lair',
    icon: PawPrint,
    tone: 'danger',
    hint: 'Where a beast dwells',
  },
  nexus: {
    label: 'Ley nexus',
    icon: Waypoints,
    tone: 'verdigris',
    hint: 'Where ley lines meet',
  },
  shrine_site: {
    label: 'Shrine site',
    icon: Landmark,
    tone: 'gold',
    hint: 'A holy place of worship',
  },
  dead_god_site: {
    label: 'Where a god died',
    icon: Sparkles,
    tone: 'gold',
    hint: 'Where a god fell',
  },
  mine_site: {
    label: 'Mine site',
    icon: Pickaxe,
    tone: 'warning',
    hint: 'Dug for ore, deep enough to break seals',
  },
  harbour_site: {
    label: 'Harbour site',
    icon: Anchor,
    tone: 'info',
    hint: 'A sheltered landing',
  },
  crossroads: {
    label: 'Crossroads',
    icon: Compass,
    tone: 'warning',
    hint: 'Where roads meet and armies clash',
  },
  wreck_site: {
    label: 'Wreck site',
    icon: Anchor,
    tone: 'warning',
    hint: 'Where wrecks lie and salvage waits',
  },
  megastructure_ruin: {
    label: 'Megastructure ruin',
    icon: Building2,
    tone: 'verdigris',
    hint: 'The fallen remains of a great work',
  },
  anomaly: {
    label: 'Anomaly',
    icon: Sparkles,
    tone: 'verdigris',
    hint: 'Where the ordinary rules of the world fail',
  },
  debris_field: {
    label: 'Debris field',
    icon: Orbit,
    tone: 'warning',
    hint: 'Wreckage drifting where vessels were lost',
  },
  reef: {
    label: 'Reef',
    icon: Waves,
    tone: 'info',
    hint: 'Shallows that feed fish and break hulls',
  },
  glacier: {
    label: 'Glacier',
    icon: Snowflake,
    tone: 'info',
    hint: 'A slow river of ice',
  },
  dunes: {
    label: 'Dunes',
    icon: Wind,
    tone: 'warning',
    hint: 'Shifting hills of sand',
  },
  canyon: {
    label: 'Canyon',
    icon: Mountain,
    tone: 'muted',
    hint: 'A deep cut through the land',
  },
  oasis: {
    label: 'Oasis',
    icon: Droplets,
    tone: 'success',
    hint: 'Water and green in dry land',
  },
  geyser: {
    label: 'Geyser',
    icon: CloudFog,
    tone: 'warning',
    hint: 'Ground that throws up hot water',
  },
}

export const SECRET: Record<string, Named & { hint: string }> = {
  hidden_resource: {
    label: 'Hidden seam',
    icon: Gem,
    tone: 'gold',
    hint: 'Found, it becomes a resource and a mineral layer',
  },
  buried_relic: {
    label: 'Buried relic',
    icon: Hammer,
    tone: 'warning',
    hint: 'Dug up, it becomes an item, sometimes cursed',
  },
  sealed_spirit: {
    label: 'Sealed spirit',
    icon: Ghost,
    tone: 'danger',
    hint: 'Broken free, it haunts the region',
  },
  lost_knowledge: {
    label: 'Lost knowledge',
    icon: BookOpen,
    tone: 'info',
    hint: 'Found, it is taught to the finder',
  },
  lost_rite: {
    label: 'Lost rite',
    icon: Wand,
    tone: 'verdigris',
    hint: 'Found, the finder learns or devises it',
  },
  underworld_entrance: {
    label: 'Way below',
    icon: Skull,
    tone: 'danger',
    hint: 'Opened, the dead walk near it',
  },
  hidden_people: {
    label: 'Hidden people',
    icon: Users,
    tone: 'info',
    hint: "Found, a people comes into the finder's knowledge",
  },
  dormant_mind: {
    label: 'Sleeping mind',
    icon: Brain,
    tone: 'verdigris',
    hint: 'Found, a mind wakes steadier',
  },
  sealed_realm: {
    label: 'Sealed realm',
    icon: DoorOpen,
    tone: 'warning',
    hint: 'Found, a realm is unsealed',
  },
}

export const MODE: Record<string, string> = {
  explorer: 'an explorer',
  seer: 'a seer',
  miner: 'deep miners',
  mystery: 'a solved mystery',
  player: 'your will',
  son: 'a god',
}

export const ORIGIN: Record<string, string> = {
  land: 'The land hid it',
  player: 'You hid it',
  son: 'A god hid it',
}

export const SACRED: Record<string, Named> = {
  holy: { label: 'Holy', icon: Sparkles, tone: 'gold' },
  notable: { label: 'Notable', icon: Eye, tone: 'verdigris' },
  profane: { label: 'Ordinary', icon: Mountain, tone: 'muted' },
}

export const FIELD: Record<string, string> = {
  kind: 'Kind',
  sacredness: 'Sacredness',
  mystery: 'Mystery',
  terrain: 'Terrain',
  cover: 'Cover',
  water_source: 'Water',
  height_advantage: 'Height advantage',
  chokepoint: 'Chokepoint',
  nexus: 'Ley nexus',
}

export const ICONS = { search: Search, scroll: Scroll, lock: Lock }

export function kindOf(key: string): Named & { hint: string } {
  return KIND[key] ?? { label: plain({}, key), icon: Landmark, hint: '' }
}

export function secretOf(key: string): Named & { hint: string } {
  return SECRET[key] ?? { label: plain({}, key), icon: Sparkles, hint: '' }
}

export function fieldOf(key: string): string {
  return FIELD[key] ?? plain({}, key)
}

export function choices(
  values: readonly string[],
  label: (key: string) => string
): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, label(value)]))
}
