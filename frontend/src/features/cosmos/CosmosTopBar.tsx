import { type ReactNode } from 'react'
import { navItem } from '@/config/navigation'
import { Gem } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { PageHeader } from '@/components/domain'
import { CosmosViewSettings } from './CosmosViewSettings'
import { EpochStarChip } from './EpochStarChip'
import { SkyCalendarChip } from './SkyCalendarChip'
import { type TravelResource } from './api'
import { type CosmosIndex, isUnderway, routeState } from './model/cosmosModel'
import { type RuleBook } from './model/rules'
import {
  type CosmosQuality,
  type CosmosViewMode,
} from './useCosmosViewSettings'

const ITEM = navItem('cosmos')

type CosmosTopBarProps = {
  index: CosmosIndex | undefined
  rules: RuleBook
  epoch: number | undefined
  alignmentUntil: number | null | undefined
  resource: TravelResource | null | undefined
  view: CosmosViewMode
  quality: CosmosQuality
  failure: string | null
  onView: (view: CosmosViewMode) => void
  onQuality: (quality: CosmosQuality) => void
  onOpenResource: () => void
  galaxySwitch?: ReactNode
}

export function CosmosTopBar({
  index,
  rules,
  epoch,
  alignmentUntil,
  resource,
  view,
  quality,
  failure,
  onView,
  onQuality,
  onOpenResource,
  galaxySwitch,
}: CosmosTopBarProps) {
  const routes = index?.data.routes ?? []
  const open = routes.filter((route) => routeState(route).open).length
  const closed = routes.length - open
  const underway = index?.data.journeys.filter(isUnderway).length ?? 0
  return (
    <PageHeader
      title={ITEM.title}
      description={ITEM.description}
      icon={ITEM.icon}
      actions={
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {galaxySwitch}
          <CosmosViewSettings
            view={view}
            quality={quality}
            failure={failure}
            onView={onView}
            onQuality={onQuality}
          />
        </div>
      }
      meta={
        index && (
          <>
            <Badge variant='outline'>{`${plural(index.data.stars.length, 'star', 'stars')}`}</Badge>
            <Badge variant='outline'>{`${plural(index.worlds.length, 'world', 'worlds')}`}</Badge>
            <Badge variant='outline'>{`${open} open routes`}</Badge>
            {closed > 0 && (
              <Badge variant='outline'>{`${closed} closed`}</Badge>
            )}
            <EpochStarChip />
            {underway > 0 && (
              <Badge variant='default'>{`${underway} voyages under way`}</Badge>
            )}
            {index.hasSlingshot && (
              <SkyCalendarChip
                epoch={epoch}
                alignmentUntil={alignmentUntil}
                rules={rules}
              />
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={resource ? 'secondary' : 'outline'}
                  size='sm'
                  onClick={onOpenResource}
                >
                  <Gem />
                  {resource
                    ? `Travel resource: ${resource.name}`
                    : 'Travel resource: not defined'}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {resource
                  ? `${resource.description}${resource.rule ? ` Rule: ${resource.rule}` : ''}`
                  : 'The substance that fuels travel between worlds is not defined yet.'}
              </TooltipContent>
            </Tooltip>
          </>
        )
      }
    />
  )
}
