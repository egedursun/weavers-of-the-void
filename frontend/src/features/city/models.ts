import type { components } from '@/api/generated/schema'
import { type WallModel } from './cityWalls'

type Schema = components['schemas']
type Colour = 'blue' | 'red' | 'yellow' | 'green'

export type Part = {
  model: string
  scale?: number
  offset?: readonly [number, number]
  turn?: number
}
export type Look = readonly Part[]

const HEXAGON = '/models/kaykit/hexagon'
const HALLOWEEN = '/models/kaykit/halloween'
const SPOOKY = 0.4

function hex(path: string): string {
  return `${HEXAGON}/${path}.gltf`
}

function building(name: string, colour: Colour): string {
  return hex(`buildings/${colour}/building_${name}_${colour}`)
}

function neutral(name: string): string {
  return hex(`buildings/neutral/${name}`)
}

function nature(name: string): string {
  return hex(`decoration/nature/${name}`)
}

function prop(name: string): string {
  return hex(`decoration/props/${name}`)
}

function spooky(name: string): string {
  return `${HALLOWEEN}/${name}.gltf`
}

function one(model: string, scale = 1): Look {
  return [{ model, scale }]
}

export const STRUCTURE_LOOK: Record<Schema['StructureKind'], Look> = {
  temple: one(building('church', 'yellow')),
  shrine: one(spooky('shrine'), SPOOKY),
  monastery: [
    { model: building('church', 'green') },
    { model: building('well', 'green'), scale: 0.5, offset: [0.55, 0.45] },
  ],
  necropolis: [
    { model: spooky('crypt'), scale: SPOOKY },
    { model: spooky('gravestone'), scale: SPOOKY, offset: [0.55, 0.4] },
    { model: spooky('grave_A'), scale: SPOOKY, offset: [-0.55, 0.4] },
  ],
  library: [
    { model: building('home_B', 'blue') },
    { model: prop('flag_blue'), scale: 0.6, offset: [0.4, -0.3] },
  ],
  school: [
    { model: building('home_A', 'blue') },
    { model: prop('flag_green'), scale: 0.6, offset: [0.4, -0.3] },
  ],
  observatory: one(building('tower_A', 'blue')),
  academy: [
    { model: building('tower_B', 'blue') },
    { model: building('home_B', 'blue'), scale: 0.7, offset: [0.55, 0.3] },
  ],
  hospital: [
    { model: building('home_B', 'red') },
    { model: prop('flag_red'), scale: 0.6, offset: [0.4, -0.3] },
  ],
  wall: one(neutral('wall_straight')),
  gate: one(neutral('wall_straight_gate')),
  tower: one(building('tower_A', 'red')),
  citadel: one(building('castle', 'red')),
  watchtower: one(building('tower_B', 'red')),
  fort: [
    { model: building('barracks', 'blue') },
    { model: neutral('fence_stone_straight'), scale: 0.6, offset: [0, 0.6] },
  ],
  palace: [
    { model: building('castle', 'yellow') },
    { model: prop('flag_yellow'), scale: 0.8, offset: [0.6, 0.5] },
  ],
  court: [
    { model: building('home_B', 'yellow') },
    { model: prop('flag_yellow'), scale: 0.6, offset: [0.4, -0.3] },
  ],
  prison: [
    { model: building('tower_base', 'blue') },
    { model: neutral('fence_stone_straight'), scale: 0.6, offset: [0, 0.6] },
    { model: neutral('fence_stone_straight'), scale: 0.6, offset: [0, -0.6] },
  ],
  market: one(building('market', 'yellow')),
  harbour: [
    { model: neutral('building_bridge_A') },
    { model: prop('crate_A_big'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  warehouse: [
    { model: building('lumbermill', 'yellow'), scale: 0.8 },
    { model: prop('crate_long_A'), scale: 0.7, offset: [0.5, 0.45] },
  ],
  granary: one(neutral('building_grain')),
  caravanserai: [
    { model: building('market', 'green') },
    { model: prop('tent'), scale: 0.7, offset: [0.55, 0.4] },
  ],
  bank: [
    { model: building('market', 'blue') },
    { model: prop('crate_B_small'), scale: 0.7, offset: [0.5, 0.45] },
  ],
  forge: one(building('blacksmith', 'red')),
  mill: one(building('windmill', 'yellow')),
  tannery: [
    { model: building('home_A', 'red') },
    { model: prop('barrel'), scale: 0.8, offset: [0.5, 0.4] },
  ],
  mine: one(building('mine', 'red')),
  quarry: [
    { model: nature('rock_single_A') },
    { model: prop('resource_stone'), scale: 0.8, offset: [0.5, 0.4] },
  ],
  shipyard: [
    { model: neutral('building_bridge_B') },
    { model: prop('resource_lumber'), scale: 0.8, offset: [0.5, 0.4] },
  ],
  workshop: one(building('lumbermill', 'red')),
  alchemist_lab: [
    { model: building('tower_base', 'green') },
    { model: spooky('candle_triple'), scale: SPOOKY, offset: [0.4, 0.4] },
  ],
  road: one(hex('tiles/roads/hex_road_A'), 0.5),
  bridge: one(neutral('building_bridge_A')),
  aqueduct: one(neutral('wall_straight'), 0.8),
  sewer: one(building('well', 'blue'), 0.6),
  canal: one(hex('tiles/rivers/hex_river_A'), 0.5),
  irrigation: [
    { model: neutral('building_grain'), scale: 0.8 },
    { model: prop('bucket_water'), scale: 0.8, offset: [0.5, 0.4] },
  ],
  dam: one(neutral('wall_straight_gate'), 0.9),
  monument: one(spooky('pillar'), SPOOKY * 1.4),
  tomb: one(spooky('crypt'), SPOOKY),
  arena: one(building('archeryrange', 'red')),
  theatre: [
    { model: prop('tent'), scale: 1.2 },
    { model: prop('flag_yellow'), scale: 0.6, offset: [0.45, -0.3] },
  ],
  wonder: [
    { model: building('castle', 'green'), scale: 1.2 },
    { model: prop('flag_green'), scale: 0.8, offset: [0.6, 0.5] },
  ],
  cosmic_gate: one(spooky('arch_gate'), SPOOKY * 1.4),
  firehouse: [
    { model: building('tower_base', 'red') },
    { model: prop('bucket_water'), scale: 0.8, offset: [0.5, 0.4] },
  ],
  bathhouse: [
    { model: building('well', 'blue') },
    { model: nature('waterplant_A'), scale: 0.8, offset: [0.45, 0.4] },
  ],
  kontor: one(building('market', 'red')),
  covenant: [
    { model: building('tower_B', 'green') },
    { model: spooky('candle_triple'), scale: SPOOKY, offset: [0.45, 0.4] },
  ],
  fountain: one(building('well', 'green')),
  park: [
    { model: nature('trees_A_small') },
    { model: spooky('bench'), scale: SPOOKY, offset: [0.45, 0.45] },
  ],
  slaughterhouse: [
    { model: building('home_B', 'red') },
    { model: neutral('fence_wood_straight'), scale: 0.6, offset: [0, 0.6] },
  ],
  almshouse: [
    { model: building('home_A', 'green') },
    { model: prop('sack'), scale: 0.8, offset: [0.45, 0.4] },
  ],
  brewery: [
    { model: building('tavern', 'green') },
    { model: prop('barrel'), scale: 0.8, offset: [0.5, 0.4] },
    { model: prop('barrel'), scale: 0.8, offset: [0.65, 0.1] },
  ],
  sawmill: [
    { model: building('lumbermill', 'green') },
    { model: prop('resource_lumber'), scale: 0.8, offset: [0.5, 0.45] },
  ],
  fishery: [
    { model: building('home_A', 'blue') },
    { model: prop('crate_B_small'), scale: 0.7, offset: [0.5, 0.4] },
    { model: prop('bucket_water'), scale: 0.8, offset: [-0.5, 0.45] },
  ],
  charcoal_kiln: [
    { model: building('blacksmith', 'green') },
    { model: prop('resource_lumber'), scale: 0.8, offset: [0.5, 0.45] },
  ],
  stables: [
    { model: building('home_A', 'yellow') },
    { model: neutral('fence_wood_straight'), scale: 0.7, offset: [0, 0.65] },
    { model: prop('sack'), scale: 0.8, offset: [0.5, -0.4] },
  ],
  siege_workshop: [
    { model: building('tower_catapult', 'red') },
    { model: prop('crate_long_A'), scale: 0.7, offset: [0.55, 0.45] },
  ],
  mint: [
    { model: building('tower_base', 'yellow') },
    { model: prop('crate_A_small'), scale: 0.7, offset: [0.5, 0.45] },
    { model: prop('flag_yellow'), scale: 0.6, offset: [-0.45, -0.3] },
  ],
  tavern: one(building('tavern', 'yellow')),
  town_hall: [
    { model: building('castle', 'blue'), scale: 0.85 },
    { model: prop('flag_blue'), scale: 0.7, offset: [0.6, 0.5] },
  ],
  guildhall: [
    { model: building('home_B', 'green') },
    { model: prop('flag_green'), scale: 0.6, offset: [0.45, -0.3] },
    { model: prop('crate_long_B'), scale: 0.6, offset: [-0.5, 0.45] },
  ],
  barracks: [
    { model: building('barracks', 'red') },
    { model: prop('weaponrack'), scale: 0.8, offset: [0.55, 0.45] },
  ],
  orphanage: [
    { model: building('home_B', 'green') },
    { model: spooky('bench'), scale: SPOOKY, offset: [0.5, 0.5] },
  ],
  apothecary: [
    { model: building('home_A', 'green') },
    { model: nature('waterplant_C'), scale: 0.8, offset: [0.5, 0.45] },
    { model: prop('bucket_empty'), scale: 0.8, offset: [-0.5, 0.45] },
  ],
  training_ground: [
    { model: building('archeryrange', 'blue') },
    { model: prop('target'), scale: 0.8, offset: [0.55, 0.45] },
    { model: prop('weaponrack'), scale: 0.8, offset: [-0.55, 0.45] },
  ],
  museum: [
    { model: building('church', 'blue') },
    { model: spooky('pillar'), scale: SPOOKY, offset: [0.55, 0.5] },
    { model: spooky('pillar'), scale: SPOOKY, offset: [-0.55, 0.5] },
  ],
  plaza: [
    { model: building('well', 'yellow'), scale: 0.8 },
    { model: spooky('bench'), scale: SPOOKY, offset: [0.55, 0.45] },
    { model: spooky('lantern_standing'), scale: SPOOKY, offset: [-0.55, 0.45] },
  ],
  cosmic_archive: [
    { model: building('tower_A', 'green') },
    { model: spooky('arch'), scale: SPOOKY, offset: [0.5, 0.45] },
  ],
}

export const HOUSING_LOOK: Record<Schema['HousingLevel'], Part> = {
  hut: { model: prop('tent'), scale: 0.45 },
  cottage: { model: building('home_A', 'green'), scale: 0.45 },
  house: { model: building('home_A', 'yellow'), scale: 0.5 },
  townhouse: { model: building('home_B', 'yellow'), scale: 0.5 },
  manor: { model: building('home_B', 'blue'), scale: 0.62 },
}

export const SHELTER: Part = { model: prop('tent'), scale: 0.35 }

export const DISTRICT_DRESS: Partial<Record<Schema['DistrictKind'], Look>> = {
  farmland: [
    { model: neutral('building_grain'), scale: 0.9, offset: [0, 0] },
    { model: neutral('fence_wood_straight'), scale: 0.6, offset: [0, 0.75] },
  ],
  gardens: [
    { model: nature('trees_A_medium'), offset: [0, 0] },
    { model: spooky('bench'), scale: SPOOKY, offset: [0.5, 0.5] },
  ],
  necropolis: [
    { model: spooky('grave_A'), scale: SPOOKY, offset: [0.3, 0.3] },
    { model: spooky('gravestone'), scale: SPOOKY, offset: [-0.3, 0.3] },
    { model: spooky('grave_B'), scale: SPOOKY, offset: [0, -0.35] },
  ],
}

export const GROUND_TILE = hex('tiles/base/hex_grass')
export const WATER_TILE = hex('tiles/base/hex_water')
export const RIVER_TILE = hex('tiles/rivers/hex_river_A')
export const WALL_LOOK: Record<WallModel, (level: number) => Part> = {
  straight: () => ({ model: neutral('wall_straight') }),
  gate: () => ({ model: neutral('wall_straight_gate') }),
  corner_wide: () => ({ model: neutral('wall_corner_A_outside') }),
  corner_sharp: () => ({ model: neutral('wall_corner_B_outside') }),
  tower: () => ({ model: building('tower_A', 'red'), scale: 0.85 }),
  fence: (level) => ({
    model: neutral(level > 1 ? 'fence_stone_straight' : 'fence_wood_straight'),
  }),
  fence_gate: (level) => ({
    model: neutral(
      level > 1 ? 'fence_stone_straight_gate' : 'fence_wood_straight_gate'
    ),
  }),
}

export const STAGE_LOOK: Record<
  'planned' | 'early' | 'middle' | 'late' | 'ruined',
  Part
> = {
  planned: { model: neutral('building_dirt') },
  early: { model: neutral('building_stage_A') },
  middle: { model: neutral('building_stage_B') },
  late: { model: neutral('building_stage_C') },
  ruined: { model: neutral('building_destroyed') },
}

export function stageOf(
  state: Schema['ConstructionState'],
  progress: number
): keyof typeof STAGE_LOOK | null {
  if (state === 'planned') return 'planned'
  if (state === 'ruined') return 'ruined'
  if (state !== 'building') return null
  if (progress < 34) return 'early'
  if (progress < 67) return 'middle'
  return 'late'
}

export const GROUND_LOOK: Record<Schema['LandGround'], Look> = {
  water: [{ model: WATER_TILE }],
  shore: [{ model: hex('tiles/coast/hex_coast_A') }],
  lowland: [{ model: GROUND_TILE }],
  wetland: [
    { model: GROUND_TILE },
    { model: nature('waterplant_B'), scale: 0.8, offset: [0.5, -0.4] },
  ],
  hills: [{ model: GROUND_TILE }, { model: nature('hills_A') }],
  mountains: [{ model: GROUND_TILE }, { model: nature('mountain_A_grass') }],
  peaks: [{ model: GROUND_TILE }, { model: nature('mountain_C') }],
}

export const COVER_LOOK: Record<Schema['LandCover'], Look> = {
  open: [],
  forest: [{ model: nature('trees_A_large') }],
  fields: [{ model: neutral('building_grain') }],
  pasture: [
    { model: neutral('fence_wood_straight'), scale: 0.8, offset: [0, 0.6] },
    { model: nature('tree_single_A'), scale: 0.6, offset: [0.5, -0.4] },
  ],
  marsh: [
    { model: nature('waterplant_A') },
    { model: nature('waterlily_A'), offset: [0.4, 0.4] },
  ],
  cleared: [{ model: nature('trees_A_cut') }],
  built: [{ model: neutral('building_dirt'), scale: 0.8 }],
  mined: [{ model: nature('rock_single_C') }],
}

export const SETTLEMENT_LOOK: Look = [
  { model: building('home_A', 'yellow'), scale: 0.6, offset: [-0.4, 0.2] },
  { model: building('home_B', 'yellow'), scale: 0.6, offset: [0.4, 0.2] },
  { model: building('church', 'yellow'), scale: 0.5, offset: [0, -0.4] },
  { model: building('market', 'yellow'), scale: 0.45, offset: [-0.45, -0.45] },
  { model: building('tower_A', 'yellow'), scale: 0.45, offset: [0.5, -0.45] },
  { model: building('castle', 'yellow'), scale: 0.5, offset: [0, 0.55] },
]

export function resourceLook(commodity: Schema['CommodityKind']): Part {
  if (['ore', 'coal', 'stone', 'siege_materiel'].includes(commodity))
    return { model: prop('resource_stone') }
  if (['timber', 'fuel', 'peat'].includes(commodity))
    return { model: prop('resource_lumber') }
  if (['fish'].includes(commodity)) return { model: prop('bucket_water') }
  if (['grain', 'fodder', 'tubers', 'fruit', 'herbs'].includes(commodity))
    return { model: prop('sack') }
  return { model: prop('crate_A_small') }
}

const PLACE_LOOK: Record<Schema['PlaceKind'], Part> = {
  mountain: { model: nature('mountain_A_grass'), scale: 0.45 },
  peak: { model: nature('mountain_C'), scale: 0.45 },
  cliff: { model: nature('rock_single_D'), scale: 1.2 },
  volcano: { model: nature('mountain_B'), scale: 0.45 },
  crater: { model: nature('rock_single_E'), scale: 1.1 },
  pass: { model: nature('hill_single_A') },
  valley: { model: nature('hill_single_C'), scale: 0.8 },
  forest: { model: nature('trees_B_medium') },
  grove: { model: nature('trees_B_small') },
  river: { model: nature('waterlily_A') },
  ford: { model: prop('bucket_water') },
  lake: { model: nature('waterlily_B') },
  spring: { model: building('well', 'blue'), scale: 0.6 },
  well: { model: building('well', 'yellow'), scale: 0.6 },
  swamp: { model: nature('waterplant_C') },
  cave: { model: nature('rock_single_E'), scale: 1.2 },
  cavern_system: { model: nature('rock_single_C'), scale: 1.3 },
  lair: { model: spooky('ribcage'), scale: SPOOKY },
  ruin: { model: neutral('building_destroyed'), scale: 0.8 },
  battlefield: { model: prop('weaponrack'), scale: 0.8 },
  burial_ground: { model: spooky('gravestone'), scale: SPOOKY },
  island: { model: nature('hill_single_B'), scale: 0.8 },
  nexus: { model: spooky('shrine_candles'), scale: SPOOKY },
  shrine_site: { model: spooky('shrine'), scale: SPOOKY },
  god_corpse: { model: spooky('bone_A'), scale: SPOOKY * 2 },
  mine_site: { model: building('mine', 'red'), scale: 0.6 },
  harbour_site: { model: neutral('building_bridge_A'), scale: 0.6 },
  crossroads: { model: spooky('post_lantern'), scale: SPOOKY },
}

const SACRED: Part = { model: spooky('shrine_candles'), scale: SPOOKY }
const UNKNOWN_PLACE: Part = { model: prop('flag_yellow'), scale: 0.6 }

export function placeLook(
  kind: Schema['PlaceKind'] | null,
  sacred: boolean
): Part {
  if (sacred) return SACRED
  return kind ? PLACE_LOOK[kind] : UNKNOWN_PLACE
}
