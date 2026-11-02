import {
  atmosphereValues,
  climateEraValues,
  disasterValues,
  discoveryValues,
  gravityValues,
  journeyIntentValues,
  legendaryQuestKindValues,
  skyEventKindValues,
  starTypeValues,
  travelMethodValues,
  worldTypeValues,
} from '@/api/generated/schema'
import {
  type Atmosphere,
  type ClimateEra,
  type Disaster,
  type Discovery,
  type ForeignGodStatus,
  type Gravity,
  type HorizonStatus,
  type JourneyIntent,
  type JourneyStatus,
  type LegendaryQuestKind,
  type RouteClosure,
  type SkyEventKind,
  type StarType,
  type TravelMethod,
  type WorldType,
} from '../api'

export const WORLD_TYPES: readonly WorldType[] = worldTypeValues
export const STAR_TYPES: readonly StarType[] = starTypeValues
export const TRAVEL_METHODS: readonly TravelMethod[] = travelMethodValues
export const SKY_EVENTS: readonly SkyEventKind[] = skyEventKindValues
export const DISCOVERIES: readonly Discovery[] = discoveryValues
export const GRAVITIES: readonly Gravity[] = gravityValues
export const ATMOSPHERES: readonly Atmosphere[] = atmosphereValues
export const CLIMATE_ERAS: readonly ClimateEra[] = climateEraValues
export const JOURNEY_INTENTS: readonly JourneyIntent[] = journeyIntentValues
export const LEGENDARY_QUESTS: readonly LegendaryQuestKind[] =
  legendaryQuestKindValues
export const DISASTERS: readonly Disaster[] = disasterValues

export const STAR_TYPE_LABEL: Record<StarType, string> = {
  yellow_dwarf: 'Yellow dwarf',
  red_giant: 'Red giant',
  blue_giant: 'Blue giant',
  binary: 'Twin star',
  white_dwarf: 'White dwarf',
  dead_star: 'Dead star',
  black_sun: 'Black sun',
  broken_star: 'Broken star',
  pulsar: 'Pulsar',
  star_remnant: 'Star remnant',
  reborn_star: 'Reborn star',
}

export const DEAD_STAR_TYPES: ReadonlySet<StarType> = new Set([
  'dead_star',
  'black_sun',
  'star_remnant',
])

export const TRAVEL_METHOD_LABEL: Record<TravelMethod, string> = {
  ancient_gate: 'Ancient gate',
  space_fold: 'Space folding',
  light_sail: 'Light sail',
  cosmic_mount: 'Cosmic mount',
  dream_journey: 'Dream journey',
  river_of_dead: 'River of the dead',
  divine_bridge: 'Divine bridge',
  slingshot_orbit: 'Slingshot orbit',
  swallowed: 'Swallowing',
}

export const SKY_EVENT_LABEL: Record<SkyEventKind, string> = {
  eclipse: 'Eclipse',
  comet: 'Comet',
  alignment: 'Planetary alignment',
  supernova: 'Supernova',
  black_sun: 'Rise of a black sun',
  void_storm: 'Void storm',
}

export const SKY_EVENT_DESCRIPTION: Record<SkyEventKind, string> = {
  eclipse:
    'The light fails for a while; prophets read omens and the faithful tremble.',
  comet: 'A burning wanderer crosses the sky and every people sees a sign.',
  alignment:
    'The worlds stand in a line; slingshot and gate routes open for a time.',
  supernova:
    'A star bursts; nearby worlds are lit and the fabric of the cosmos thins.',
  black_sun: 'A star turns black and eats light; leakage rises in its worlds.',
  void_storm:
    'A storm of the void tears a route apart for a few epochs; voyages on it wait or are lost.',
}

export const DISCOVERY_LABEL: Record<Discovery, string> = {
  known: 'Known',
  legend: 'Legend',
  unknown: 'Unknown',
  forgotten: 'Forgotten',
}

export const GRAVITY_LABEL: Record<Gravity, string> = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
}

export const ATMOSPHERE_LABEL: Record<Atmosphere, string> = {
  none: 'None',
  thin: 'Thin',
  normal: 'Normal',
  dense: 'Dense',
  toxic: 'Toxic',
}

export const CLIMATE_LABEL: Record<ClimateEra, string> = {
  temperate: 'Temperate',
  drought: 'Drought',
  rain: 'Rain age',
  ice_age: 'Ice age',
  scorching: 'Scorching age',
}

export const JOURNEY_INTENT_LABEL: Record<JourneyIntent, string> = {
  colony: 'Colony',
  trade: 'Trade',
  exploration: 'Exploration',
  conquest: 'Conquest',
  pilgrimage: 'Pilgrimage',
}

export const JOURNEY_STATUS_LABEL: Record<JourneyStatus, string> = {
  underway: 'Under way',
  waiting: 'Waiting at the route mouth',
  arrived: 'Arrived',
  lost: 'Lost',
  recalled: 'Recalled',
  stranded: 'Stranded',
}

export const JOURNEY_STATUS_ORDER: Record<JourneyStatus, number> = {
  underway: 0,
  waiting: 1,
  stranded: 2,
  arrived: 3,
  recalled: 4,
  lost: 5,
}

export const ROUTE_CLOSURE_LABEL: Record<RouteClosure, string> = {
  sealed: 'Sealed',
  severed: 'Severed',
  forgotten: 'In oblivion',
  collapsed: 'Collapsed',
  snapped: 'Snapped',
}

export const LEGENDARY_QUEST_LABEL: Record<LegendaryQuestKind, string> = {
  dead_star: 'Re-ignite the dead star',
  sealed_gate: 'Re-open the sealed gate',
  archive: 'Reach the Cosmic Archive',
  expel_outer: 'Expel the Outsider',
}

export const DISASTER_LABEL: Record<Disaster, string> = {
  earthquake: 'Earthquake',
  flood: 'Flood',
  plague: 'Plague',
  drought: 'Drought',
  storm: 'Storm',
}

export const FOREIGN_GOD_STATUS_LABEL: Record<ForeignGodStatus, string> = {
  awake: 'Awake',
  asleep: 'Asleep',
  defeated: 'Defeated',
  dead: 'Dead',
}

export const HORIZON_STATUS_LABEL: Record<HorizonStatus, string> = {
  pending: 'Will be born at epoch end',
  processing: 'Being born now',
  born: 'Born',
  wasted: 'Faded',
}

export function humanize(value: string): string {
  const text = value.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}
