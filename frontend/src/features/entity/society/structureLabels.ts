import {
  Anchor,
  Anvil,
  Archive,
  BookOpen,
  BrickWall,
  Building,
  Castle,
  Church,
  CircleDot,
  Coins,
  Columns3,
  Construction,
  Cross,
  Crown,
  DoorOpen,
  Drama,
  Droplet,
  Droplets,
  Eye,
  Flame,
  Fence,
  FlaskConical,
  Gavel,
  Gem,
  GraduationCap,
  Hammer,
  HardHat,
  Hospital,
  Landmark,
  Layers,
  Library,
  Lock,
  Milestone,
  Mountain,
  Orbit,
  Pickaxe,
  Pyramid,
  Route,
  School,
  Shield,
  Ship,
  Skull,
  Sparkles,
  Sprout,
  Store,
  Swords,
  Telescope,
  Tent,
  TowerControl,
  Trophy,
  Users,
  Warehouse,
  Waypoints,
  Wheat,
  Wind,
  Wrench,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Spec } from './labels'

type Schemas = components['schemas']
export type StructureKind = Schemas['StructureKind']
export type StructureGroup = Schemas['StructureGroup']
export type ConstructionState = Schemas['ConstructionState']
export type BuilderKind = Schemas['BuilderKind']
export type CapacityUnit = Schemas['CapacityUnit']
export type BuildScale = Schemas['BuildScale']
export type StaffScale = Schemas['StaffScale']
export type StructureView = Schemas['StructureView']
export type DesignView = Schemas['DesignView']
export type KindOption = Schemas['KindOptionView']

export const GROUP_SPEC: Record<StructureGroup, Spec> = {
  faith: { label: 'Faith', icon: Church, tone: 'verdigris' },
  knowledge: { label: 'Knowledge', icon: BookOpen, tone: 'info' },
  defence: { label: 'Defence', icon: Shield, tone: 'danger' },
  civic: { label: 'Civic', icon: Gavel, tone: 'gold' },
  commerce: { label: 'Commerce', icon: Coins, tone: 'gold' },
  production: { label: 'Production', icon: Hammer, tone: 'warning' },
  infrastructure: { label: 'Infrastructure', icon: Route, tone: 'info' },
  memory: { label: 'Memory and wonders', icon: Landmark, tone: 'gold' },
  cosmic: { label: 'Cosmic', icon: Orbit, tone: 'verdigris' },
}
export const GROUP_ORDER = Object.keys(GROUP_SPEC) as StructureGroup[]

export const KIND_SPEC: Record<StructureKind, Spec> = {
  temple: {
    label: 'Temple',
    icon: Church,
    tone: 'verdigris',
    hint: 'Holds its people pious; a holy site for its god',
  },
  shrine: {
    label: 'Shrine',
    icon: Sparkles,
    tone: 'verdigris',
    hint: 'A small house of piety',
  },
  monastery: {
    label: 'Monastery',
    icon: Cross,
    tone: 'verdigris',
    hint: 'Piety and patient learning',
  },
  necropolis: {
    label: 'Necropolis',
    icon: Skull,
    tone: 'muted',
    hint: 'The dead get their rites; fewer restless spirits',
  },
  library: {
    label: 'Library',
    icon: Library,
    tone: 'info',
    hint: 'Keeps and deepens knowledge; shields from dark ages',
  },
  school: {
    label: 'School',
    icon: School,
    tone: 'info',
    hint: 'Raises literacy and trains scholars',
  },
  observatory: {
    label: 'Observatory',
    icon: Telescope,
    tone: 'info',
    hint: 'Astronomy, calendars, calmer eclipses, truer omens',
  },
  academy: {
    label: 'Academy',
    icon: GraduationCap,
    tone: 'info',
    hint: 'Deepens learning fastest',
  },
  hospital: {
    label: 'Hospital',
    icon: Hospital,
    tone: 'success',
    hint: 'Fewer infections and wound deaths; trains healers',
  },
  wall: {
    label: 'Walls',
    icon: BrickWall,
    tone: 'danger',
    hint: 'Its level and material become the city walls',
  },
  gate: {
    label: 'Gatehouse',
    icon: DoorOpen,
    tone: 'danger',
    hint: 'Adds gates to the walls',
  },
  tower: {
    label: 'Tower',
    icon: TowerControl,
    tone: 'danger',
    hint: 'Adds towers to the walls',
  },
  citadel: {
    label: 'Citadel',
    icon: Castle,
    tone: 'danger',
    hint: 'Garrison, defense and order',
  },
  watchtower: {
    label: 'Watchtower',
    icon: Eye,
    tone: 'danger',
    hint: 'Sees bandits coming; less crime',
  },
  fort: {
    label: 'Fort',
    icon: Shield,
    tone: 'danger',
    hint: 'Garrison and defense',
  },
  palace: {
    label: 'Palace',
    icon: Crown,
    tone: 'gold',
    hint: 'Lends its realm legitimacy',
  },
  court: {
    label: 'Court',
    icon: Gavel,
    tone: 'gold',
    hint: 'Order and justice; less crime',
  },
  prison: {
    label: 'Prison',
    icon: Lock,
    tone: 'warning',
    hint: 'Order and room to punish',
  },
  market: {
    label: 'Market',
    icon: Store,
    tone: 'gold',
    hint: 'Prosperity; a waystation for passing routes',
  },
  harbour: {
    label: 'Harbour',
    icon: Anchor,
    tone: 'info',
    hint: 'Harbour capacity and sea trade',
  },
  warehouse: {
    label: 'Warehouse',
    icon: Warehouse,
    tone: 'gold',
    hint: 'Stores goods',
  },
  granary: {
    label: 'Granary',
    icon: Wheat,
    tone: 'success',
    hint: 'Stores grain; feeds a siege',
  },
  caravanserai: {
    label: 'Caravanserai',
    icon: Tent,
    tone: 'gold',
    hint: 'A waystation that widens trade routes',
  },
  bank: {
    label: 'Bank',
    icon: Coins,
    tone: 'gold',
    hint: 'Grows the investment pool',
  },
  forge: {
    label: 'Forge',
    icon: Anvil,
    tone: 'warning',
    hint: 'Runs the smithing chains',
  },
  mill: {
    label: 'Mill',
    icon: Wind,
    tone: 'warning',
    hint: 'Grinds more grain into bread',
  },
  tannery: {
    label: 'Tannery',
    icon: Layers,
    tone: 'warning',
    hint: 'Runs the tanning chains',
  },
  mine: {
    label: 'Mine',
    icon: Pickaxe,
    tone: 'warning',
    hint: 'Digs more ore',
  },
  quarry: {
    label: 'Quarry',
    icon: Mountain,
    tone: 'warning',
    hint: 'Cuts more stone',
  },
  shipyard: {
    label: 'Shipyard',
    icon: Ship,
    tone: 'info',
    hint: 'Launches more ships',
  },
  workshop: {
    label: 'Workshop',
    icon: Wrench,
    tone: 'warning',
    hint: 'Craft and wealth',
  },
  alchemist_lab: {
    label: "Alchemist's laboratory",
    icon: FlaskConical,
    tone: 'verdigris',
    hint: 'Runs the alchemy chains',
  },
  road: {
    label: 'Road',
    icon: Route,
    tone: 'info',
    hint: 'Roads, hauling and route capacity',
  },
  bridge: {
    label: 'Bridge',
    icon: Waypoints,
    tone: 'info',
    hint: 'Crossings, passability and route capacity',
  },
  aqueduct: {
    label: 'Aqueduct',
    icon: Droplets,
    tone: 'info',
    hint: 'Water and sanitation',
  },
  sewer: { label: 'Sewers', icon: Droplet, tone: 'info', hint: 'Sanitation' },
  canal: {
    label: 'Canal',
    icon: Milestone,
    tone: 'info',
    hint: 'Water trade and irrigation',
  },
  irrigation: {
    label: 'Irrigation works',
    icon: Sprout,
    tone: 'success',
    hint: 'Watered fields, bigger harvests',
  },
  dam: {
    label: 'Dam',
    icon: Fence,
    tone: 'info',
    hint: 'Turns floods aside; irrigation',
  },
  monument: {
    label: 'Monument',
    icon: Columns3,
    tone: 'gold',
    hint: 'Prestige',
  },
  tomb: {
    label: 'Tomb',
    icon: Pyramid,
    tone: 'muted',
    hint: 'Prestige and funeral rites',
  },
  arena: {
    label: 'Arena',
    icon: Trophy,
    tone: 'danger',
    hint: 'Calms unrest; duels make and break heroes',
  },
  theatre: {
    label: 'Theatre',
    icon: Drama,
    tone: 'gold',
    hint: 'Calms unrest; prestige',
  },
  wonder: {
    label: 'Wonder',
    icon: Gem,
    tone: 'gold',
    hint: 'Great prestige and piety',
  },
  cosmic_gate: {
    label: 'Cosmic gate',
    icon: CircleDot,
    tone: 'verdigris',
    hint: 'Opens ancient gates without blood',
  },
  cosmic_archive: {
    label: 'Cosmic archive',
    icon: Archive,
    tone: 'verdigris',
    hint: 'Knowledge of all worlds',
  },
  firehouse: {
    label: 'Firehouse',
    icon: Flame,
    tone: 'danger',
    hint: 'Puts out fires in the districts it reaches',
  },
  bathhouse: {
    label: 'Bathhouse',
    icon: Droplets,
    tone: 'info',
    hint: 'Keeps the districts it reaches clean and well',
  },
  kontor: {
    label: 'Trading post',
    icon: Store,
    tone: 'gold',
    hint: 'A merchant house abroad: goods, informants and settlers',
  },
  covenant: {
    label: 'Covenant',
    icon: FlaskConical,
    tone: 'verdigris',
    hint: 'A magical order’s house of study, fed by its sites',
  },
}

export const STATE_SPEC: Record<ConstructionState, Spec> = {
  planned: { label: 'Planned', icon: HardHat, tone: 'muted' },
  building: { label: 'Being raised', icon: Construction, tone: 'warning' },
  complete: { label: 'Standing', icon: Building, tone: 'success' },
  damaged: { label: 'Damaged', icon: Wrench, tone: 'warning' },
  ruined: { label: 'Ruined', icon: Skull, tone: 'danger' },
}

export const BUILDER_SPEC: Record<BuilderKind, Spec> = {
  community: { label: 'Its people', icon: Users, tone: 'gold' },
  polity: { label: 'A realm', icon: Crown, tone: 'gold' },
  faction: { label: 'A faction', icon: Swords, tone: 'warning' },
  cult: { label: 'A cult', icon: Church, tone: 'verdigris' },
  patron: { label: 'A patron', icon: Gem, tone: 'gold' },
  god: { label: 'A god', icon: Sparkles, tone: 'verdigris' },
}

export const UNIT_LABEL: Record<CapacityUnit, string> = {
  none: '',
  tons: 'tons',
  volumes: 'volumes',
  garrison: 'soldiers',
  beds: 'beds',
  berths: 'berths',
  seats: 'seats',
  cells: 'cells',
  worshippers: 'worshippers',
  pupils: 'pupils',
  stalls: 'stalls',
  hands: 'hands',
  loads: 'loads',
  travellers: 'travellers',
}

export const SCALE_SPEC: Record<BuildScale, Spec> = {
  minor: { label: 'Minor', icon: Hammer, tone: 'muted' },
  major: { label: 'Major', icon: Building, tone: 'gold' },
  grand: { label: 'Grand', icon: Landmark, tone: 'warning' },
  wonder: { label: 'Wonder', icon: Gem, tone: 'danger' },
}

export const STAFF_SCALE_SPEC: Record<StaffScale, Spec> = {
  none: { label: 'No staff', icon: Users, tone: 'muted' },
  few: { label: 'A few hands', icon: Users, tone: 'muted' },
  some: { label: 'A crew', icon: Users, tone: 'gold' },
  many: { label: 'A great staff', icon: Users, tone: 'warning' },
}

export const STRUCTURE_FIELD: Record<string, string> = {
  kind: 'Kind',
  level: 'Level',
  capacity: 'Capacity',
  condition: 'Condition',
  construction_state: 'State',
  progress: 'Progress',
  fire_resistance: 'Fire resistance',
  effect_pct: 'Working strength',
  staff_pct: 'Staffing',
  upkeep_coin: 'Upkeep in coin',
  upkeep_goods: 'Upkeep in goods',
  unpaid_epochs: 'Unpaid ages',
  on_ley_line: 'On a ley line',
  anchor: 'Anchors its god',
  aesthetic: 'Style',
  builder_kind: 'Builder',
  host_entity_id: 'Serves',
  architect_entity_id: 'Architect',
  builder_entity_id: 'Builder',
  dedicated_son_id: 'Dedicated to',
  design_id: 'Design',
  material: 'Material',
  splendor: 'Splendour',
  durability: 'Durability',
  function: 'Base function',
  staff: 'Staff',
  cost: 'Labour needed',
  work: 'Labour done',
  funds: 'Funds',
}

export function structureField(key: string): string {
  return (
    STRUCTURE_FIELD[key] ??
    key.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase())
  )
}

export const DESIGN_FIELD: Record<string, string> = {
  name: 'Name',
  base_kind: 'Base kind',
  capacity_pct: 'Capacity',
  cost_pct: 'Labour',
  upkeep_pct: 'Upkeep',
  function_pct: 'Function',
  staff_pct: 'Staff',
  staff_class: 'Staffed by',
  staff_scale: 'Staff size',
  scale: 'Scale',
  upkeep_commodity: 'Upkeep in',
  min_tier: 'Smallest town',
  ley: 'Attuned to ley lines',
  description: 'Description',
}
