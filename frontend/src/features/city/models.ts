import type { components } from '@/api/generated/schema'
import { type RoadModel, type WallModel } from './cityWalls'

type Schema = components['schemas']
type Colour = 'blue' | 'red' | 'yellow' | 'green'

export type Part = {
  model: string
  scale?: number
  offset?: readonly [number, number]
  turn?: number
  token?: string
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
  embassy: [
    { model: building('home_B', 'yellow') },
    { model: prop('flag_blue'), scale: 0.6, offset: [0.45, -0.3] },
    { model: prop('flag_red'), scale: 0.6, offset: [-0.45, -0.3] },
  ],
  lighthouse: [
    { model: building('tower_A', 'yellow') },
    { model: spooky('lantern_standing'), scale: SPOOKY, offset: [0.45, 0.45] },
  ],
  signal_tower: [
    { model: building('tower_B', 'yellow'), scale: 0.8 },
    { model: prop('flag_yellow'), scale: 0.7, offset: [0.35, -0.3] },
  ],
  customs_house: [
    { model: building('market', 'blue'), scale: 0.85 },
    { model: prop('crate_A_small'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  toll_gate: [
    { model: neutral('fence_stone_straight_gate') },
    {
      model: building('tower_base', 'yellow'),
      scale: 0.5,
      offset: [0.55, 0.3],
    },
  ],
  courthouse: [
    { model: building('church', 'blue'), scale: 0.9 },
    { model: prop('flag_blue'), scale: 0.6, offset: [0.45, -0.3] },
  ],
  archive: [
    { model: building('home_B', 'green') },
    { model: prop('crate_long_B'), scale: 0.6, offset: [0.5, 0.45] },
  ],
  printing_house: [
    { model: building('lumbermill', 'blue') },
    { model: prop('pallet'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  laboratory: [
    { model: building('tower_base', 'blue') },
    { model: prop('bucket_water'), scale: 0.7, offset: [0.45, 0.4] },
  ],
  foundry: [
    { model: building('blacksmith', 'blue') },
    { model: prop('resource_stone'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  smelter: [
    { model: building('blacksmith', 'yellow') },
    {
      model: building('tower_base', 'yellow'),
      scale: 0.5,
      offset: [0.55, 0.35],
    },
  ],
  kiln: [
    { model: building('well', 'red'), scale: 0.8 },
    { model: prop('resource_stone'), scale: 0.6, offset: [0.45, 0.4] },
  ],
  glassworks: [
    { model: building('lumbermill', 'blue'), scale: 0.85 },
    { model: prop('crate_B_small'), scale: 0.6, offset: [0.5, 0.4] },
  ],
  textile_mill: [
    { model: building('watermill', 'blue') },
    { model: prop('sack'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  dye_works: [
    { model: building('home_A', 'yellow') },
    { model: prop('barrel'), scale: 0.7, offset: [0.5, 0.4] },
    { model: prop('bucket_water'), scale: 0.7, offset: [-0.5, 0.4] },
  ],
  paper_mill: one(building('watermill', 'yellow')),
  bakery: [
    { model: building('home_A', 'yellow') },
    { model: prop('sack'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  dairy: [
    { model: building('home_B', 'green') },
    { model: neutral('fence_wood_straight'), scale: 0.6, offset: [0, 0.6] },
    { model: prop('bucket_empty'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  distillery: [
    { model: building('tavern', 'blue') },
    { model: prop('barrel'), scale: 0.8, offset: [0.5, 0.4] },
  ],
  refinery: [
    { model: building('tower_base', 'red') },
    { model: building('tower_base', 'red'), scale: 0.6, offset: [0.55, 0.35] },
    { model: prop('barrel'), scale: 0.7, offset: [-0.5, 0.4] },
  ],
  power_plant: [
    { model: building('mine', 'blue'), scale: 1.1 },
    { model: building('tower_base', 'blue'), scale: 0.6, offset: [0.6, 0.35] },
  ],
  silo: [
    { model: building('tower_base', 'yellow'), scale: 0.9 },
    { model: neutral('building_grain'), scale: 0.6, offset: [0.55, 0.35] },
  ],
  cistern: [
    { model: building('well', 'blue'), scale: 0.9 },
    { model: prop('bucket_water'), scale: 0.7, offset: [0.45, 0.4] },
  ],
  reservoir: [
    { model: hex('tiles/rivers/hex_river_A'), scale: 0.55 },
    { model: neutral('wall_straight'), scale: 0.6, offset: [0, 0.55] },
  ],
  canal_lock: [
    { model: hex('tiles/rivers/hex_river_A'), scale: 0.5 },
    { model: neutral('wall_straight_gate'), scale: 0.6, offset: [0, 0.4] },
  ],
  tunnel: [
    { model: nature('hill_single_A') },
    { model: spooky('arch'), scale: SPOOKY, offset: [0, 0.5] },
  ],
  rail_station: [
    { model: building('market', 'red'), scale: 0.9 },
    { model: hex('tiles/roads/hex_road_A'), scale: 0.45, offset: [0, 0.6] },
  ],
  airfield: [
    { model: hex('tiles/roads/hex_road_A'), scale: 0.55 },
    { model: prop('tent'), scale: 0.8, offset: [0.55, 0.35] },
    { model: prop('flag_blue'), scale: 0.6, offset: [-0.5, -0.3] },
  ],
  spaceport: [
    { model: building('tower_A', 'blue') },
    { model: hex('tiles/roads/hex_road_A'), scale: 0.5, offset: [0, 0.6] },
    { model: spooky('arch_gate'), scale: SPOOKY, offset: [0.55, 0.3] },
  ],
  dry_dock: [
    { model: neutral('building_bridge_B') },
    { model: neutral('building_scaffolding'), scale: 0.6, offset: [0.5, 0.4] },
  ],
  arsenal: [
    { model: building('barracks', 'red') },
    { model: prop('weaponrack'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  kennel: [
    { model: building('home_A', 'green'), scale: 0.8 },
    { model: neutral('fence_wood_straight'), scale: 0.6, offset: [0, 0.6] },
  ],
  menagerie: [
    { model: nature('trees_A_small') },
    { model: neutral('fence_stone_straight'), scale: 0.6, offset: [0, 0.6] },
    { model: neutral('fence_stone_straight'), scale: 0.6, offset: [0, -0.6] },
  ],
  botanical_garden: [
    { model: nature('trees_B_small') },
    { model: nature('waterplant_B'), scale: 0.8, offset: [0.45, 0.4] },
    { model: building('well', 'green'), scale: 0.5, offset: [-0.5, 0.4] },
  ],
  cemetery: [
    { model: spooky('gravestone'), scale: SPOOKY },
    { model: spooky('gravemarker_A'), scale: SPOOKY, offset: [0.5, 0.4] },
    { model: spooky('fence'), scale: SPOOKY, offset: [0, 0.6] },
  ],
  gymnasium: [
    { model: building('archeryrange', 'blue') },
    { model: prop('target'), scale: 0.6, offset: [0.5, 0.4] },
  ],
  asylum: [
    { model: building('home_B', 'blue') },
    { model: neutral('fence_stone_straight'), scale: 0.6, offset: [0, 0.6] },
  ],
  quarantine_house: [
    { model: building('home_A', 'blue') },
    { model: neutral('fence_wood_straight'), scale: 0.6, offset: [0, 0.6] },
    { model: prop('flag_yellow'), scale: 0.6, offset: [0.45, -0.3] },
  ],
  inn: [
    { model: building('tavern', 'red') },
    { model: prop('barrel'), scale: 0.7, offset: [0.5, 0.4] },
  ],
  market_hall: [
    { model: building('market', 'yellow'), scale: 1.15 },
    { model: prop('crate_A_big'), scale: 0.6, offset: [0.55, 0.45] },
  ],
  exchange: [
    { model: building('church', 'yellow'), scale: 0.9 },
    { model: prop('crate_B_small'), scale: 0.6, offset: [0.5, 0.4] },
  ],
  university: [
    { model: building('tower_B', 'green') },
    { model: building('home_B', 'green'), scale: 0.7, offset: [0.55, 0.3] },
    { model: building('home_A', 'green'), scale: 0.7, offset: [-0.55, 0.3] },
  ],
  seminary: [
    { model: building('church', 'green') },
    { model: building('home_A', 'green'), scale: 0.6, offset: [0.55, 0.35] },
  ],
  conservatory: [
    { model: building('home_B', 'yellow') },
    { model: prop('flag_green'), scale: 0.6, offset: [0.45, -0.3] },
  ],
  opera_house: [
    { model: building('church', 'red'), scale: 1.1 },
    { model: spooky('pillar'), scale: SPOOKY, offset: [0.55, 0.5] },
    { model: spooky('pillar'), scale: SPOOKY, offset: [-0.55, 0.5] },
  ],
  gallery: [
    { model: building('home_B', 'blue') },
    { model: spooky('plaque'), scale: SPOOKY, offset: [0.5, 0.45] },
  ],
  stadium: [
    { model: building('archeryrange', 'yellow'), scale: 1.2 },
    { model: prop('flag_yellow'), scale: 0.7, offset: [0.6, -0.3] },
    { model: prop('flag_red'), scale: 0.7, offset: [-0.6, -0.3] },
  ],
  orbital_ring: [
    { model: spooky('arch_gate'), scale: SPOOKY * 1.6 },
    {
      model: neutral('wall_corner_A_outside'),
      scale: 0.5,
      offset: [0.55, 0.4],
    },
    {
      model: neutral('wall_corner_A_outside'),
      scale: 0.5,
      offset: [-0.55, 0.4],
      turn: Math.PI,
    },
  ],
  space_elevator: [
    { model: building('tower_B', 'blue'), scale: 1.3 },
    { model: building('tower_base', 'blue'), scale: 0.6, offset: [0.55, 0.35] },
  ],
  space_station: [
    { model: building('tower_A', 'green'), scale: 1.1 },
    { model: spooky('arch'), scale: SPOOKY, offset: [0.55, 0.4] },
  ],
  star_collector: [
    { model: building('windmill', 'blue'), scale: 1.1 },
    { model: spooky('lantern_standing'), scale: SPOOKY, offset: [0.5, 0.45] },
  ],
  beacon: [
    { model: building('tower_A', 'red'), scale: 1.1 },
    { model: spooky('lantern_hanging'), scale: SPOOKY, offset: [0.45, 0.4] },
  ],
  planetary_engine: [
    { model: building('mine', 'green'), scale: 1.3 },
    { model: building('tower_base', 'green'), scale: 0.7, offset: [0.6, 0.35] },
    {
      model: building('tower_base', 'green'),
      scale: 0.7,
      offset: [-0.6, 0.35],
    },
  ],
  habitat_ring: [
    { model: building('castle', 'blue'), scale: 1.1 },
    {
      model: neutral('wall_corner_B_outside'),
      scale: 0.5,
      offset: [0.55, 0.45],
    },
  ],
}

const FORM_BODY: Record<Schema['BuildingForm'], Part> = {
  hall: { model: building('home_B', 'yellow') },
  longhouse: { model: building('home_A', 'green'), scale: 1.15 },
  tower: { model: building('tower_A', 'blue') },
  keep: { model: building('castle', 'red') },
  dome: { model: building('church', 'yellow') },
  spire: { model: building('tower_B', 'green') },
  stepped: { model: neutral('building_stage_C') },
  pyramid: { model: neutral('building_stage_B') },
  courtyard: { model: building('market', 'green') },
  ring: { model: neutral('wall_corner_A_outside') },
  tent: { model: prop('tent'), scale: 1.2 },
  mound: { model: nature('hill_single_A'), scale: 0.8 },
  arcade: { model: neutral('building_bridge_A') },
  terrace: { model: neutral('building_stage_A') },
  platform: { model: neutral('building_dirt') },
  bridge_form: { model: neutral('building_bridge_B') },
  wall_line: { model: neutral('wall_straight') },
  tunnel_form: { model: spooky('arch'), scale: SPOOKY * 1.6 },
  orbital: { model: spooky('arch_gate'), scale: SPOOKY * 1.6 },
}

const STOREY_STEP = 0.06
const STOREY_CAP = 8

export function typedLook(
  kind: Schema['StructureKind'],
  form: Schema['BuildingForm'] | null | undefined,
  storeys: number | null | undefined
): Part[] {
  const base = STRUCTURE_LOOK[kind]
  if (!form) return [...base]
  const body = FORM_BODY[form]
  const lift =
    1 + Math.min(STOREY_CAP, Math.max(0, (storeys ?? 1) - 1)) * STOREY_STEP
  return [{ ...body, scale: (body.scale ?? 1) * lift }, ...base.slice(1)]
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
  farmland: [{ model: neutral('building_grain'), scale: 0.7 }],
  gardens: [{ model: nature('trees_A_medium'), scale: 0.8 }],
  necropolis: [
    { model: spooky('grave_A'), scale: SPOOKY, offset: [0.15, 0.15] },
    { model: spooky('gravestone'), scale: SPOOKY, offset: [-0.15, -0.1] },
  ],
}

export const GROUND_TILE = hex('tiles/base/hex_grass')
export const WATER_TILE = hex('tiles/base/hex_water')
export const RIVER_TILE = hex('tiles/rivers/hex_river_A')
export const ROAD_LOOK: Record<RoadModel, string> = {
  straight: hex('tiles/roads/hex_road_A'),
  bend: hex('tiles/roads/hex_road_B'),
  sharp: hex('tiles/roads/hex_road_C'),
  end: hex('tiles/roads/hex_road_M'),
}

export const ROAD_DRESS: Record<'stone' | 'lantern' | 'cart', Look> = {
  stone: [
    { model: spooky('path_A'), scale: SPOOKY },
    { model: spooky('path_B'), scale: SPOOKY },
    { model: spooky('path_C'), scale: SPOOKY },
  ],
  lantern: [{ model: spooky('lantern_standing'), scale: SPOOKY * 1.1 }],
  cart: [
    { model: prop('wheelbarrow'), scale: 1.6 },
    { model: prop('crate_A_small'), scale: 1.6, offset: [0.28, 0.12] },
    { model: prop('sack'), scale: 1.8, offset: [-0.25, 0.1] },
  ],
}

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

const SIXTH = Math.PI / 3

function pick<T>(items: readonly T[], q: number, r: number): T {
  return items[Math.abs(q * 7 + r * 13) % items.length]
}

function turned(part: Part, q: number, r: number): Part {
  return { ...part, turn: (Math.abs(q * 5 + r * 3) % 6) * SIXTH }
}

const HILLS: readonly Part[] = [
  { model: nature('hills_A') },
  { model: nature('hills_B') },
  { model: nature('hills_C') },
]
const MOUNTAINS: readonly Part[] = [
  { model: nature('mountain_A_grass') },
  { model: nature('mountain_B_grass') },
  { model: nature('mountain_C_grass') },
]
const PEAKS: readonly Part[] = [
  { model: nature('mountain_A') },
  { model: nature('mountain_B') },
  { model: nature('mountain_C') },
]
const FORESTS: readonly Part[] = [
  { model: nature('trees_A_large') },
  { model: nature('trees_B_large') },
  { model: nature('trees_A_medium') },
  { model: nature('trees_B_medium') },
]

export function groundLook(
  ground: Schema['LandGround'],
  q: number,
  r: number,
  shoreline: number | null = null
): Look {
  const base = { model: GROUND_TILE }
  if (ground === 'water') return [{ model: WATER_TILE }]
  if (ground === 'shore')
    return shoreline === null
      ? [{ model: GROUND_TILE, token: '--brand-gold-light' }]
      : [{ model: hex('tiles/coast/hex_coast_A'), turn: shoreline }]
  if (ground === 'wetland')
    return [
      base,
      turned(
        { model: nature('waterplant_B'), scale: 0.8, offset: [0.4, -0.3] },
        q,
        r
      ),
    ]
  if (ground === 'hills') return [base, turned(pick(HILLS, q, r), q, r)]
  if (ground === 'mountains') return [base, turned(pick(MOUNTAINS, q, r), q, r)]
  if (ground === 'peaks') return [base, turned(pick(PEAKS, q, r), q, r)]
  return [base]
}

export function coverLook(
  cover: Schema['LandCover'],
  q: number,
  r: number
): Look {
  if (cover === 'forest') return [turned(pick(FORESTS, q, r), q, r)]
  if (cover === 'fields')
    return [turned({ model: neutral('building_grain') }, q, r)]
  if (cover === 'pasture')
    return [
      turned({ model: neutral('fence_wood_straight'), scale: 0.8 }, q, r),
      { model: nature('tree_single_A'), scale: 0.6, offset: [0.4, -0.3] },
    ]
  if (cover === 'marsh')
    return [
      { model: nature('waterplant_A') },
      { model: nature('waterlily_A'), offset: [0.35, 0.3] },
    ]
  if (cover === 'cleared')
    return [turned({ model: nature('trees_A_cut') }, q, r)]
  if (cover === 'built')
    return [{ model: neutral('building_dirt'), scale: 0.8 }]
  if (cover === 'mined')
    return [turned({ model: nature('rock_single_C') }, q, r)]
  return []
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
  crossroads: { model: nature('rock_single_A'), scale: 0.5 },
}

const SACRED: Part = { model: spooky('shrine_candles'), scale: SPOOKY }
const UNKNOWN_PLACE: Part = { model: nature('rock_single_B'), scale: 0.55 }

export function placeLook(
  kind: Schema['PlaceKind'] | null,
  sacred: boolean
): Part {
  if (sacred) return SACRED
  return kind ? PLACE_LOOK[kind] : UNKNOWN_PLACE
}
