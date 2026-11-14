import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { type CityPick } from './CityScene3D'
import { type CityScene } from './api'
import { hexRing, hexToWorld } from './hex'
import { ZONES } from './labels'

const CORNERS = Array.from({ length: 6 }, (_, index) => {
  const angle = (Math.PI / 3) * index + Math.PI / 6
  return [Math.cos(angle) * 1.15, Math.sin(angle) * 1.15] as const
})
const PAD = 3
const NAME_SIZE = 0.55
const CHAR = 0.5

type Name = { id: number; x: number; y: number; text: string }

function names(scene: CityScene): Name[] {
  const taken: [number, number, number, number][] = []
  return [...scene.districts]
    .filter((district) => district.cells.length > 0)
    .sort(
      (first, second) =>
        second.level * 10 +
        second.cells.length -
        (first.level * 10 + first.cells.length)
    )
    .flatMap((district) => {
      const points = district.cells.map((cell) => hexToWorld(cell[0], cell[1]))
      const x = points.reduce((sum, point) => sum + point[0], 0) / points.length
      const y =
        points.reduce((sum, point) => sum + point[1], 0) / points.length - 0.9
      const text = `${DISTRICT_SPEC[district.kind].label} ${district.level}`
      const half = (text.length * NAME_SIZE * CHAR) / 2
      const box: [number, number, number, number] = [
        x - half,
        y - NAME_SIZE,
        x + half,
        y + NAME_SIZE * 0.3,
      ]
      if (
        taken.some(
          (other) =>
            box[0] < other[2] &&
            other[0] < box[2] &&
            box[1] < other[3] &&
            other[1] < box[3]
        )
      )
        return []
      taken.push(box)
      return [{ id: district.id, x, y, text }]
    })
}

function hexPoints(x: number, z: number): string {
  return CORNERS.map(([dx, dz]) => `${x + dx},${z + dz}`).join(' ')
}

export function CityPlan2D({
  scene,
  selected,
  onPick,
  fill = false,
  labels = false,
}: {
  scene: CityScene
  selected: CityPick
  onPick: (pick: CityPick) => void
  fill?: boolean
  labels?: boolean
}) {
  const cells = scene.districts.flatMap((district) =>
    district.cells.map((cell) => ({
      district,
      at: hexToWorld(cell[0], cell[1]),
    }))
  )
  const walls = scene.walls_radius
    ? hexRing(scene.walls_radius).map((cell) => hexToWorld(cell[0], cell[1]))
    : []
  const points = [
    ...cells.map((item) => item.at),
    ...walls,
    [0, 0] as [number, number],
  ]
  const xs = points.map(([x]) => x)
  const zs = points.map(([, z]) => z)
  const box = [
    Math.min(...xs) - PAD,
    Math.min(...zs) - PAD,
    Math.max(...xs) - Math.min(...xs) + PAD * 2,
    Math.max(...zs) - Math.min(...zs) + PAD * 2,
  ]
  return (
    <svg
      viewBox={box.join(' ')}
      role='img'
      aria-label={`Plan of ${scene.town.name}: ${plural(scene.districts.length, 'district', 'districts')} and ${plural(scene.buildings.length, 'building', 'buildings')}`}
      className={fill ? 'block h-full w-full' : 'block h-auto w-full'}
    >
      {walls.map(([x, z], index) => (
        <polygon
          key={`wall-${index}`}
          points={hexPoints(x, z)}
          className='fill-muted stroke-foreground'
          strokeWidth={0.08}
        />
      ))}
      {cells.map(({ district, at: [x, z] }, index) => (
        <polygon
          key={`cell-${district.id}-${index}`}
          points={hexPoints(x, z)}
          className={cn(
            ZONES[district.zone].fill,
            'cursor-pointer stroke-background',
            selected?.kind === 'district' &&
              selected.id === district.id &&
              'stroke-foreground'
          )}
          strokeWidth={0.12}
          onClick={() => onPick({ kind: 'district', id: district.id })}
        >
          <title>{`${district.kind.replaceAll('_', ' ')}: level ${district.level}, ${plural(district.dwellings, 'home', 'homes')}`}</title>
        </polygon>
      ))}
      {scene.buildings.map((building) => {
        const [x, z] = hexToWorld(building.q, building.r)
        return (
          <circle
            key={`building-${building.node.id}`}
            cx={x + (building.slot % 3) * 0.35 - 0.35}
            cy={z + Math.floor(building.slot / 3) * 0.35 - 0.2}
            r={0.28}
            className={cn(
              'cursor-pointer stroke-background',
              building.state === 'complete'
                ? 'fill-foreground'
                : 'fill-muted-foreground',
              selected?.kind === 'building' &&
                selected.id === building.node.id &&
                'fill-primary'
            )}
            strokeWidth={0.06}
            onClick={() => onPick({ kind: 'building', id: building.node.id })}
          >
            <title>{`${building.node.name}: ${building.state}`}</title>
          </circle>
        )
      })}
      {labels &&
        names(scene).map((name) => (
          <text
            key={`name-${name.id}`}
            x={name.x}
            y={name.y}
            textAnchor='middle'
            fontSize={NAME_SIZE}
            className='pointer-events-none fill-foreground stroke-background'
            strokeWidth={0.16}
            paintOrder='stroke'
          >
            {name.text}
          </text>
        ))}
    </svg>
  )
}
