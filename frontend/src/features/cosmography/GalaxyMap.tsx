import { type ReactNode, Suspense, lazy } from 'react'
import { cn } from '@/lib/utils'
import { Text } from '@/components/typography'
import { hasWebGL2 } from '@/features/cosmos/useCosmosViewSettings'
import { type GalaxyRecord, type StarRecord, type StructureRecord } from './api'
import { type Pick } from './visual/GalaxyScene3D'
import { GalaxyThumb } from './visual/GalaxyThumb'
import { type GalaxyShape } from './visual/galaxyForm'

const GalaxyScene3D = lazy(() => import('./visual/GalaxyScene3D'))

export type { Pick }

type GalaxyMapProps = {
  galaxy: GalaxyRecord
  shape: GalaxyShape
  structures: readonly StructureRecord[]
  stars: readonly StarRecord[]
  selected?: Pick
  placing?: boolean
  portrait?: boolean
  onPick?: (pick: Pick) => void
  onPlace?: (x: number, y: number) => void
  overlay?: ReactNode
  hint?: string
  className?: string
}

export function GalaxyMap({
  galaxy,
  shape,
  structures,
  stars,
  selected = null,
  placing = false,
  portrait = false,
  onPick,
  onPlace,
  overlay,
  hint,
  className,
}: GalaxyMapProps) {
  const still = (
    <GalaxyThumb
      galaxy={galaxy}
      shape={shape}
      label={`Map of ${galaxy.name}`}
      stars={stars.map((star) => ({ id: star.id, x: star.x, y: star.y }))}
      className='h-full w-full'
    />
  )
  return (
    <div
      className={cn(
        'relative min-w-0 overflow-hidden rounded-xl border bg-cosmos-void text-cosmos-label',
        className
      )}
    >
      {hasWebGL2() ? (
        <Suspense fallback={still}>
          <GalaxyScene3D
            galaxy={galaxy}
            shape={shape}
            structures={structures}
            stars={stars}
            selected={selected}
            placing={placing}
            portrait={portrait}
            onPick={onPick}
            onPlace={onPlace}
            fallback={still}
          />
        </Suspense>
      ) : (
        still
      )}
      {overlay && (
        <div className='pointer-events-none absolute inset-x-0 top-0 flex min-w-0 flex-wrap items-start justify-between gap-2 p-3'>
          {overlay}
        </div>
      )}
      {hint && !portrait && (
        <div className='pointer-events-none absolute right-3 bottom-3 hidden max-w-sm md:block'>
          <Text variant='caption' tone='inherit' className='opacity-70'>
            {hint}
          </Text>
        </div>
      )}
    </div>
  )
}
