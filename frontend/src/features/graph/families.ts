import { type ThemeColorName } from '@/components/domain/useThemeColors'

export type FamilyShape =
  | 'square'
  | 'circle'
  | 'triangle'
  | 'diamond'
  | 'hexagon'
  | 'ring'
  | 'star'
  | 'plus'

export type FamilyKey =
  | 'places'
  | 'communities'
  | 'objects'
  | 'gods'
  | 'culture'
  | 'living'
  | 'events'
  | 'other'

export type Family = {
  key: FamilyKey
  label: string
  shape: FamilyShape
  token: ThemeColorName
  types: readonly string[]
}

export const FAMILIES: readonly Family[] = [
  {
    key: 'places',
    label: 'Places',
    shape: 'square',
    token: 'chart-3',
    types: ['world', 'region', 'place', 'settlement', 'celestial'],
  },
  {
    key: 'communities',
    label: 'Communities and persons',
    shape: 'circle',
    token: 'chart-2',
    types: ['people', 'mortal', 'cult', 'faction', 'army'],
  },
  {
    key: 'objects',
    label: 'Objects and knowledge',
    shape: 'triangle',
    token: 'chart-5',
    types: ['item', 'knowledge', 'structure', 'resource', 'vessel'],
  },
  {
    key: 'gods',
    label: 'Gods',
    shape: 'diamond',
    token: 'rarity-legendary',
    types: ['son', 'creator', 'foreign_god', 'outer_being'],
  },
  {
    key: 'culture',
    label: 'Culture and belief',
    shape: 'hexagon',
    token: 'chart-4',
    types: [
      'legend',
      'tradition',
      'prophecy',
      'language',
      'artwork',
      'law',
      'natural_law',
    ],
  },
  {
    key: 'living',
    label: 'Living things and spirits',
    shape: 'ring',
    token: 'rarity-uncommon',
    types: ['species', 'spirit'],
  },
  {
    key: 'events',
    label: 'Events',
    shape: 'star',
    token: 'destructive',
    types: ['event'],
  },
]

export const OTHER_FAMILY: Family = {
  key: 'other',
  label: 'Other',
  shape: 'plus',
  token: 'muted-foreground',
  types: [],
}

const BY_TYPE = new Map(
  FAMILIES.flatMap((family) => family.types.map((type) => [type, family]))
)

export function familyOf(type: string): Family {
  return BY_TYPE.get(type) ?? OTHER_FAMILY
}

export const ALL_FAMILIES: readonly Family[] = [...FAMILIES, OTHER_FAMILY]

const NODE_KIND_LABEL: Record<string, string> = {
  son: 'Son',
  creator: 'Creator',
  foreign_god: 'Foreign god',
  world: 'World',
  star: 'Star',
  entity: 'Record',
  galaxy: 'Galaxy',
  cluster: 'Cluster',
  dimension: 'Dimension',
}

export function capitalized(text: string): string {
  return text.replace(/^./, (first) => first.toLocaleUpperCase('en-US'))
}

export function typeLabel(
  type: string,
  entityLabels: ReadonlyMap<string, string>
): string {
  return capitalized(
    NODE_KIND_LABEL[type] ?? entityLabels.get(type) ?? type.replaceAll('_', ' ')
  )
}

export function hollow(shape: FamilyShape): boolean {
  return shape === 'ring'
}

function polygon(sides: number, radius: number, start = -Math.PI / 2) {
  const path = new Path2D()
  for (let index = 0; index < sides; index += 1) {
    const angle = start + (index * 2 * Math.PI) / sides
    const x = radius * Math.cos(angle)
    const y = radius * Math.sin(angle)
    if (index === 0) path.moveTo(x, y)
    else path.lineTo(x, y)
  }
  path.closePath()
  return path
}

const SHAPE_SCALE = {
  square: 0.89,
  triangle: 1.4,
  diamond: 1.25,
  hexagon: 1.1,
  starOuter: 1.32,
  starInner: 0.6,
  plusArm: 0.4,
  plusReach: 1.15,
} as const

const STAR_POINTS = 10

function starPath(radius: number): Path2D {
  const path = new Path2D()
  for (let index = 0; index < STAR_POINTS; index += 1) {
    const angle = -Math.PI / 2 + (index * Math.PI) / (STAR_POINTS / 2)
    const reach =
      index % 2
        ? radius * SHAPE_SCALE.starInner
        : radius * SHAPE_SCALE.starOuter
    const x = reach * Math.cos(angle)
    const y = reach * Math.sin(angle)
    if (index === 0) path.moveTo(x, y)
    else path.lineTo(x, y)
  }
  path.closePath()
  return path
}

function plusPath(radius: number): Path2D {
  const arm = radius * SHAPE_SCALE.plusArm
  const reach = radius * SHAPE_SCALE.plusReach
  const path = new Path2D()
  path.rect(-arm, -reach, arm * 2, reach * 2)
  path.rect(-reach, -arm, reach * 2, arm * 2)
  return path
}

const cache = new Map<string, Path2D>()

export function shapePath(shape: FamilyShape, radius: number): Path2D {
  const key = `${shape}:${radius.toFixed(2)}`
  const found = cache.get(key)
  if (found) return found
  let path: Path2D
  switch (shape) {
    case 'square': {
      const side = radius * SHAPE_SCALE.square
      path = new Path2D()
      path.rect(-side, -side, side * 2, side * 2)
      break
    }
    case 'triangle':
      path = polygon(3, radius * SHAPE_SCALE.triangle)
      break
    case 'diamond':
      path = polygon(4, radius * SHAPE_SCALE.diamond)
      break
    case 'hexagon':
      path = polygon(6, radius * SHAPE_SCALE.hexagon, 0)
      break
    case 'star':
      path = starPath(radius)
      break
    case 'plus':
      path = plusPath(radius)
      break
    default:
      path = new Path2D()
      path.arc(0, 0, radius, 0, Math.PI * 2)
  }
  cache.set(key, path)
  return path
}
