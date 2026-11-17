import {
  atmosphereValues,
  climateEraValues,
  disasterValues,
  discoveryValues,
  gravityValues,
  journeyIntentValues,
  skyEventKindValues,
  starTypeValues,
  travelMethodValues,
  worldTypeValues,
  type components,
} from '@/api/generated/schema'
import {
  type Atmosphere,
  type ClimateEra,
  type Disaster,
  type Discovery,
  type Gravity,
  type HorizonStatus,
  type JourneyIntent,
  type JourneyStatus,
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
export const DISASTERS: readonly Disaster[] = disasterValues

export const STAR_TYPE_LABEL: Record<StarType, string> = {
  yellow_dwarf: 'Yellow dwarf',
  blue_star: 'Blue star',
  blue_white_star: 'Blue-white star',
  white_star: 'White star',
  yellow_white_star: 'Yellow-white star',
  orange_dwarf: 'Orange dwarf',
  red_dwarf: 'Red dwarf',
  brown_dwarf: 'Brown dwarf',
  yellow_giant: 'Yellow giant',
  red_giant: 'Red giant',
  blue_giant: 'Blue giant',
  red_supergiant: 'Red supergiant',
  blue_supergiant: 'Blue supergiant',
  hypergiant: 'Hypergiant',
  wolf_rayet: 'Wolf-Rayet star',
  protostar: 'Protostar',
  carbon_star: 'Carbon star',
  white_dwarf: 'White dwarf',
  binary: 'Twin star',
  trinary: 'Triple star',
  variable_star: 'Variable star',
  neutron_star: 'Neutron star',
  pulsar: 'Pulsar',
  magnetar: 'Magnetar',
  black_hole: 'Black hole',
  dead_star: 'Dead star',
  black_sun: 'Black sun',
  broken_star: 'Broken star',
  star_remnant: 'Star remnant',
  reborn_star: 'Reborn star',
  chained_star: 'Chained star',
  watching_star: 'Watching star',
}

export const DEAD_STAR_TYPES: ReadonlySet<StarType> = new Set([
  'dead_star',
  'black_sun',
  'star_remnant',
  'black_hole',
])

export const TRAVEL_MEDIUM_LABEL: Record<
  components['schemas']['TravelMedium'],
  string
> = {
  space: 'through space',
  dimension: 'between dimensions',
  dream: 'through dreams',
  death: 'through the realm of the dead',
  divine: 'by divine power',
  body: 'carried inside a being',
}

export const TRAVEL_MECHANISM_LABEL: Record<
  components['schemas']['TravelMechanism'],
  string
> = {
  gate: 'by a gate',
  fold: 'by folding the way',
  sail: 'under sail or drive',
  mount: 'on a ridden creature',
  bridge: 'over a bridge',
  current: 'on a current',
  carrier_being: 'within a carrier being',
  orbit: 'along an orbit',
}

export const TRAVEL_METHOD_LABEL: Record<TravelMethod, string> = {
  ancient_gate: 'Ancient gate',
  space_fold: 'Space folding',
  light_sail: 'Light sail',
  carrier_mount: 'Ridden crossing',
  dream_journey: 'Dream journey',
  death_current: 'Crossing of the dead',
  divine_bridge: 'Divine bridge',
  slingshot_orbit: 'Slingshot orbit',
  carried_within: 'Carried within a being',
  wormhole: 'Wormhole',
  void_ark: 'Void ark',
  galactic_gate: 'Galactic gate',
  filament_lane: 'Filament lane',
  dimensional_rift: 'Dimensional rift',
  planar_door: 'Planar door',
  rocketry: 'Rocketry',
}

export const SKY_EVENT_LABEL: Record<SkyEventKind, string> = {
  eclipse: 'Eclipse',
  comet: 'Comet',
  alignment: 'Planetary alignment',
  supernova: 'Supernova',
  black_sun: 'Rise of a black sun',
  void_storm: 'Void storm',
  flare: 'Stellar flare',
  aurora: 'Aurora',
  transit: 'Transit across the star',
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
  flare:
    'A star flares: its worlds lose harvest, auroras burn as omens, and light sails bound to it may be scorched shut.',
  aurora:
    'After a flare, worlds with a strong field glow at night; their peoples read it as a sign.',
  transit:
    'An inner world crosses the face of the star as seen from an outer one; its peoples take note.',
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
  hothouse: 'Hothouse',
  snowball: 'Snowball',
  variable: 'Variable',
  wet_cold: 'Wet cold',
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

export const DISASTER_LABEL: Record<Disaster, string> = {
  earthquake: 'Earthquake',
  flood: 'Flood',
  plague: 'Plague',
  drought: 'Drought',
  storm: 'Storm',
  eruption: 'Eruption',
  volcanic_quake: 'Volcanic earthquake',
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
