export type Silhouette =
  | 'ship'
  | 'sail'
  | 'submarine'
  | 'wheeled'
  | 'tracked'
  | 'walker'
  | 'beast'
  | 'envelope'
  | 'winged'
  | 'starship'
  | 'drill'
  | 'tower'
  | 'keep'
  | 'dome'
  | 'hall'
  | 'spire'
  | 'wall'
  | 'ring'

export type Margins = {
  left: number
  right: number
  top: number
  bottom: number
}

const SNUG: Margins = { left: 10, right: 10, top: 10, bottom: 10 }

export const MARGINS: Record<Silhouette, Margins> = {
  ship: { left: 34, right: 18, top: 12, bottom: 22 },
  sail: { left: 34, right: 18, top: 58, bottom: 22 },
  submarine: { left: 26, right: 26, top: 22, bottom: 10 },
  wheeled: { left: 12, right: 12, top: 10, bottom: 30 },
  tracked: { left: 14, right: 14, top: 10, bottom: 28 },
  walker: { left: 12, right: 12, top: 10, bottom: 38 },
  beast: { left: 24, right: 18, top: 12, bottom: 34 },
  envelope: { left: 28, right: 28, top: 26, bottom: 12 },
  winged: { left: 30, right: 22, top: 30, bottom: 30 },
  starship: { left: 36, right: 24, top: 18, bottom: 18 },
  drill: { left: 38, right: 14, top: 10, bottom: 10 },
  tower: { left: 10, right: 10, top: 30, bottom: 16 },
  keep: { left: 12, right: 12, top: 24, bottom: 16 },
  dome: { left: 12, right: 12, top: 40, bottom: 16 },
  hall: { left: 14, right: 14, top: 34, bottom: 16 },
  spire: { left: 10, right: 10, top: 56, bottom: 16 },
  wall: { left: 10, right: 10, top: 20, bottom: 16 },
  ring: SNUG,
}

const FAMILY_SHAPES: Record<string, Silhouette> = {
  mount: 'beast',
  cart: 'wheeled',
  wagon: 'wheeled',
  chariot: 'wheeled',
  rail: 'wheeled',
  ram: 'wheeled',
  tower: 'wheeled',
  thrower: 'wheeled',
  gun: 'wheeled',
  motor: 'tracked',
  tracked: 'tracked',
  walker: 'walker',
  construct: 'walker',
  boat: 'ship',
  galley: 'sail',
  sailing_ship: 'sail',
  steam_ship: 'ship',
  living: 'ship',
  submarine: 'submarine',
  balloon: 'envelope',
  airship: 'envelope',
  aircraft: 'winged',
  rotorcraft: 'winged',
  spacecraft: 'starship',
  burrower: 'drill',
}

const FORM_SHAPES: Record<string, Silhouette> = {
  tower: 'tower',
  spire: 'spire',
  keep: 'keep',
  dome: 'dome',
  stepped: 'keep',
  pyramid: 'spire',
  wall_line: 'wall',
  ring: 'ring',
  orbital: 'ring',
}

export function vehicleShape(family: string | null | undefined): Silhouette {
  return FAMILY_SHAPES[family ?? ''] ?? 'wheeled'
}

export function buildingShape(form: string | null | undefined): Silhouette {
  return FORM_SHAPES[form ?? ''] ?? 'hall'
}

export const GROUNDED: ReadonlySet<Silhouette> = new Set([
  'wheeled',
  'tracked',
  'walker',
  'beast',
  'tower',
  'keep',
  'dome',
  'hall',
  'spire',
  'wall',
])
export const AFLOAT: ReadonlySet<Silhouette> = new Set(['ship', 'sail'])
