import { type components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { STRATUM } from '@/features/entity/environment/geologyLabels'
import { StratumSwatch } from './SwatchMarker'
import { STRATUM_LOOK } from './deepLooks'

type Stratum = components['schemas']['UndergroundStratum']

export function StratumBadge({
  stratum,
  prefix,
}: {
  stratum: Stratum | null | undefined
  prefix?: string
}) {
  if (!stratum) return null
  const look = STRATUM_LOOK[stratum]
  const label = STRATUM[stratum].label
  return (
    <Badge variant='outline' size='sm' title={STRATUM[stratum].hint}>
      <StratumSwatch fill={look.fill} glow={look.glow} />
      {prefix ? `${prefix} ${label.toLowerCase()}` : label}
    </Badge>
  )
}
