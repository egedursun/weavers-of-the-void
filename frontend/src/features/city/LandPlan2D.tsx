import { cn } from '@/lib/utils'
import { type LandPick } from './LandScene3D'
import { type LandScene } from './api'
import { hexToWorld } from './hex'
import { COVERS, COVER_FILL, GROUNDS, GROUND_FILL } from './labels'

const CORNERS = Array.from({ length: 6 }, (_, index) => {
  const angle = (Math.PI / 3) * index + Math.PI / 6
  return [Math.cos(angle) * 1.15, Math.sin(angle) * 1.15] as const
})
const PAD = 2

function hexPoints(x: number, z: number): string {
  return CORNERS.map(([dx, dz]) => `${x + dx},${z + dz}`).join(' ')
}

export function LandPlan2D({
  scene,
  selected,
  onPick,
  fill = false,
}: {
  scene: LandScene
  selected: LandPick
  onPick: (pick: LandPick) => void
  fill?: boolean
}) {
  const points = scene.tiles.map((tile) => hexToWorld(tile.q, tile.r))
  const xs = points.map(([x]) => x)
  const zs = points.map(([, z]) => z)
  const box = [
    Math.min(0, ...xs) - PAD,
    Math.min(0, ...zs) - PAD,
    Math.max(0, ...xs) - Math.min(0, ...xs) + PAD * 2,
    Math.max(0, ...zs) - Math.min(0, ...zs) + PAD * 2,
  ]
  const marks = [
    ...scene.settlements.map((item) => ({
      kind: 'settlement' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: ${item.detail} people`,
      size: 0.55,
    })),
    ...scene.places.map((item) => ({
      kind: 'place' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: ${item.detail.replaceAll('_', ' ')}`,
      size: 0.35,
    })),
    ...scene.works.map((item) => ({
      kind: 'work' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: level ${item.level}, ${item.state}`,
      size: 0.4,
    })),
    ...scene.resources.map((item) => ({
      kind: 'resource' as const,
      id: item.node.id,
      q: item.q,
      r: item.r,
      text: `${item.node.name}: richness ${item.richness}, ${item.reserve} of ${item.initial_reserve} left`,
      size: 0.2 + (item.richness / 100) * 0.3,
    })),
  ]
  return (
    <svg
      viewBox={box.join(' ')}
      role='img'
      aria-label={`Land of ${scene.region.name}: ${scene.tiles.length} tiles, ${scene.settlements.length} settlements, ${scene.resources.length} deposits`}
      className={fill ? 'block h-full w-full' : 'block h-auto w-full'}
    >
      {scene.tiles.map((tile) => {
        const [x, z] = hexToWorld(tile.q, tile.r)
        const chosen =
          selected?.kind === 'tile' &&
          selected.q === tile.q &&
          selected.r === tile.r
        return (
          <polygon
            key={`tile-${tile.q}-${tile.r}`}
            points={hexPoints(x, z)}
            className={cn(
              tile.cover === 'open'
                ? GROUND_FILL[tile.ground]
                : COVER_FILL[tile.cover],
              'cursor-pointer',
              tile.river ? 'stroke-info' : 'stroke-background',
              chosen && 'stroke-foreground'
            )}
            strokeWidth={tile.river ? 0.3 : 0.1}
            onClick={() => onPick({ kind: 'tile', q: tile.q, r: tile.r })}
          >
            <title>{`${GROUNDS[tile.ground]}, ${COVERS[tile.cover]}${tile.river ? ', river' : ''}`}</title>
          </polygon>
        )
      })}
      {marks.map((mark) => {
        const [x, z] = hexToWorld(mark.q, mark.r)
        const chosen =
          selected !== null &&
          selected.kind === mark.kind &&
          'id' in selected &&
          selected.id === mark.id
        return (
          <circle
            key={`${mark.kind}-${mark.id}`}
            cx={x}
            cy={z}
            r={mark.size}
            className={cn(
              'cursor-pointer stroke-background',
              chosen ? 'fill-primary' : 'fill-foreground'
            )}
            strokeWidth={0.06}
            onClick={() => onPick({ kind: mark.kind, id: mark.id })}
          >
            <title>{mark.text}</title>
          </circle>
        )
      })}
    </svg>
  )
}
