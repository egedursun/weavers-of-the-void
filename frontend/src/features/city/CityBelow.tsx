import { ArrowDownToLine } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { StatBar } from '@/components/domain/StatBar'
import { Label, Text } from '@/components/typography'
import { STRATUM } from '@/features/entity/environment/geologyLabels'
import { StratumSwatch } from '@/features/map/SwatchMarker'
import { STRATUM_LOOK } from '@/features/map/deepLooks'
import { type CityScene } from './api'

const FULL = 100

export function CityBelow({ scene }: { scene: CityScene }) {
  const below = scene.below
  if (!below) return null
  const look = STRATUM_LOOK[below.stratum]
  const stratum = STRATUM[below.stratum]
  return (
    <div
      role='group'
      aria-label={`${scene.town.name} lies below the surface, in the ${stratum.label.toLowerCase()}`}
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/60 bg-card p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <StratumSwatch fill={look.fill} glow={look.glow} />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label variant='overline'>Below the surface</Label>
          <Text as='span' weight='semibold' truncate>
            {below.cell_name
              ? `${below.cell_name}, ${stratum.label.toLowerCase()}`
              : stratum.label}
          </Text>
        </div>
        {below.region && (
          <Badge variant='outline'>
            <ArrowDownToLine />
            {`Beneath ${below.region.name}`}
          </Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <StatBar label='Light' value={below.light} max={FULL} framed />
        <StatBar label='Extent' value={below.extent} max={FULL} framed />
      </div>
    </div>
  )
}
