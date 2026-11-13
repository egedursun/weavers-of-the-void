import {
  Anchor,
  Backpack,
  BookOpen,
  Brain,
  Castle,
  Compass,
  Crosshair,
  Eye,
  Flag,
  Flame,
  Footprints,
  Frown,
  Ghost,
  Hand,
  HandHeart,
  HeartPulse,
  Home,
  Landmark,
  Link2,
  type LucideIcon,
  Map as MapIcon,
  Moon,
  Mountain,
  Navigation,
  Package,
  PauseCircle,
  Plane,
  Repeat,
  Route,
  Sailboat,
  Shield,
  ShieldAlert,
  Ship,
  Skull,
  Snowflake,
  Sparkles,
  Swords,
  Tent,
  Target,
  Telescope,
  Truck,
  Users,
  Utensils,
  Waves,
  Wind,
  Zap,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const OPERATIONS_ICON: LucideIcon = Flag

export const ECHELONS: Record<Schema['EchelonLevel'], Named> = {
  army_group: { label: 'Army group', icon: Landmark, tone: 'gold' },
  army: { label: 'Army', icon: Castle, tone: 'info' },
  corps: { label: 'Corps', icon: Flag, tone: 'verdigris' },
  division: { label: 'Division', icon: Shield, tone: 'success' },
  brigade: { label: 'Brigade', icon: Users, tone: 'muted' },
}

export const ORDERS: Record<Schema['EchelonOrder'], Named> = {
  attack: { label: 'Attack', icon: Swords, tone: 'danger' },
  manoeuvre: { label: 'Manoeuvre', icon: Navigation, tone: 'info' },
  resupply: { label: 'Resupply', icon: Package, tone: 'gold' },
  hold: { label: 'Hold', icon: Shield, tone: 'verdigris' },
  standing: { label: 'Standing orders', icon: PauseCircle, tone: 'muted' },
}

export const TRANSPORTS: Record<Schema['CarrierKind'], Named> = {
  wagons: { label: 'Wagons', icon: Truck, tone: 'gold' },
  pack_animals: { label: 'Pack animals', icon: Footprints, tone: 'success' },
  porters: { label: 'Porters', icon: Backpack, tone: 'muted' },
  barges: { label: 'River barges', icon: Waves, tone: 'info' },
  ships: { label: 'Supply ships', icon: Ship, tone: 'verdigris' },
  sky_barges: { label: 'Sky barges', icon: Plane, tone: 'warning' },
}

export const SHOTS: Record<Schema['ShotKind'], Named> = {
  round: { label: 'Round shot', icon: Target, tone: 'danger' },
  chain: { label: 'Chain shot', icon: Link2, tone: 'warning' },
  grape: { label: 'Grapeshot', icon: Crosshair, tone: 'gold' },
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
}

export const POINTS_OF_SAIL: Record<Schema['PointOfSail'], Named> = {
  in_irons: { label: 'In irons', icon: PauseCircle, tone: 'danger' },
  close_hauled: { label: 'Close-hauled', icon: Wind, tone: 'warning' },
  reaching: { label: 'On a reach', icon: Sailboat, tone: 'success' },
  running: { label: 'Running', icon: Navigation, tone: 'info' },
  under_oars: { label: 'Under oars', icon: Repeat, tone: 'gold' },
}

export const STATIONS: Record<Schema['CrewStation'], Named> = {
  gunners: { label: 'Gunners', icon: Target, tone: 'danger' },
  topmen: { label: 'Topmen', icon: Sailboat, tone: 'info' },
  marines: { label: 'Marines', icon: Swords, tone: 'warning' },
  officers: { label: 'Officers', icon: Compass, tone: 'gold' },
  rowers: { label: 'Rowers', icon: Repeat, tone: 'muted' },
}

export const ROLES: Record<Schema['ExpeditionRole'], Named> = {
  scout: { label: 'Scout', icon: Eye, tone: 'info' },
  guide: { label: 'Guide', icon: Compass, tone: 'verdigris' },
  healer: { label: 'Healer', icon: HandHeart, tone: 'success' },
  fighter: { label: 'Fighter', icon: Swords, tone: 'danger' },
  scholar: { label: 'Scholar', icon: BookOpen, tone: 'gold' },
  porter: { label: 'Porter', icon: Backpack, tone: 'muted' },
}

export const GROUNDS: Record<Schema['ExpeditionGround'], Named> = {
  site: { label: 'Into a site', icon: Castle, tone: 'gold' },
  wilds: { label: 'Into the wilds', icon: Mountain, tone: 'success' },
  underworld: { label: 'Into an underworld', icon: Ghost, tone: 'muted' },
  realm: { label: 'Into another realm', icon: Sparkles, tone: 'info' },
}

export const EXPEDITION_STATUS: Record<Schema['ExpeditionStatus'], Named> = {
  underway: { label: 'Under way', icon: Route, tone: 'info' },
  camped: { label: 'Camped', icon: Tent, tone: 'verdigris' },
  returned: { label: 'Returned', icon: Home, tone: 'success' },
  lost: { label: 'Lost', icon: Skull, tone: 'danger' },
}

export const RESOLVES: Record<Schema['ResolveKind'], Named> = {
  steady: { label: 'Steady', icon: Shield, tone: 'muted' },
  paranoid: { label: 'Paranoid', icon: Eye, tone: 'danger' },
  hopeless: { label: 'Hopeless', icon: Frown, tone: 'danger' },
  selfish: { label: 'Selfish', icon: Hand, tone: 'warning' },
  abusive: { label: 'Abusive', icon: Zap, tone: 'danger' },
  courageous: { label: 'Courageous', icon: Flame, tone: 'gold' },
  focused: { label: 'Focused', icon: Target, tone: 'success' },
  stalwart: { label: 'Stalwart', icon: ShieldAlert, tone: 'verdigris' },
}

export const EVENTS: Record<Schema['ExpeditionEvent'], Named> = {
  setout: { label: 'Set out', icon: Flag, tone: 'info' },
  leg: { label: 'A leg travelled', icon: Footprints, tone: 'muted' },
  room: { label: 'A room walked', icon: Castle, tone: 'muted' },
  camp: { label: 'Made camp', icon: Tent, tone: 'verdigris' },
  ambush: { label: 'Ambushed', icon: Moon, tone: 'danger' },
  exposure: { label: 'Exposure', icon: Snowflake, tone: 'warning' },
  affliction: { label: 'Affliction', icon: Brain, tone: 'danger' },
  virtue: { label: 'Virtue', icon: Sparkles, tone: 'gold' },
  quirk: { label: 'A quirk taken', icon: Telescope, tone: 'info' },
  fallen: { label: 'Fallen', icon: Skull, tone: 'danger' },
  return: { label: 'Returned', icon: Home, tone: 'success' },
  loss: { label: 'Lost', icon: Ghost, tone: 'danger' },
}

export const QUIRK_LABELS: Record<Schema['QuirkKind'], Named> = {
  fears_dark: { label: 'Fears the dark', icon: Moon, tone: 'danger' },
  dark_sighted: { label: 'Sees in the dark', icon: Eye, tone: 'success' },
  knows_ways: { label: 'Knows the ways', icon: MapIcon, tone: 'success' },
  eats_anything: { label: 'Eats anything', icon: Utensils, tone: 'success' },
  hardy: { label: 'Hardy', icon: HeartPulse, tone: 'success' },
  frail: { label: 'Frail', icon: Snowflake, tone: 'danger' },
  jumpy: { label: 'Jumpy', icon: Zap, tone: 'warning' },
  steady_nerves: { label: 'Steady nerves', icon: Shield, tone: 'success' },
  keen_eyed: { label: 'Keen-eyed', icon: Telescope, tone: 'success' },
  homesick: { label: 'Homesick', icon: Home, tone: 'warning' },
  restless: { label: 'Restless', icon: Route, tone: 'info' },
  light_fingered: { label: 'Light-fingered', icon: Hand, tone: 'warning' },
}

export const QUIRK_EFFECTS: Record<Schema['QuirkKind'], string> = {
  fears_dark: 'Gains twice the stress on a leg in the dark.',
  dark_sighted: 'Darkness adds no danger to a party it walks with.',
  knows_ways: 'A party it leads needs one leg fewer.',
  eats_anything: 'Eats no provisions on a leg.',
  hardy: 'Takes half the exposure.',
  frail: 'Takes half again the exposure.',
  jumpy: 'Gains twice the stress from an ambush.',
  steady_nerves: 'Gains half the stress on a leg.',
  keen_eyed: 'Scouts for the party whatever its role.',
  homesick: 'Sets out half as often and gains stress on the way.',
  restless: 'Sets out on expeditions twice as often.',
  light_fingered: 'Brings home an extra find and unsettles companions.',
}

export const COMPASS = [
  'north',
  'north-east',
  'east',
  'south-east',
  'south',
  'south-west',
  'west',
  'north-west',
]

export const TAB_ICONS = {
  command: Flag,
  supply: Package,
  sea: Anchor,
  expeditions: Compass,
} as const
