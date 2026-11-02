import { useEffect, useRef } from 'react'
import { ArrowRight } from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { EntityLink } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { MethodGlyph } from './Glyphs'
import { RouteActions } from './RouteActions'
import { RouteStatusChips } from './RouteStatusChips'
import { type RouteRecord } from './api'
import { type CosmosIndex, otherEnd, routeState } from './model/cosmosModel'
import { TRAVEL_METHOD_LABEL } from './model/labels'
import { type RuleBook } from './model/rules'

type RouteListProps = {
  worldId: number
  index: CosmosIndex
  rules: RuleBook
  sonName: (id: number) => string | undefined
  highlightedRouteId?: number
  onSelectWorld: (worldId: number) => void
}

export function RouteList({
  worldId,
  index,
  rules,
  sonName,
  highlightedRouteId,
  onSelectWorld,
}: RouteListProps) {
  const routes = index.routesOf(worldId)
  if (routes.length === 0) return <Muted>No known route to this world.</Muted>
  return (
    <ul className='flex min-w-0 flex-col gap-3'>
      {routes.map((route) => (
        <RouteRow
          key={route.id}
          route={route}
          worldId={worldId}
          index={index}
          rules={rules}
          sonName={sonName}
          highlighted={route.id === highlightedRouteId}
          onSelectWorld={onSelectWorld}
        />
      ))}
    </ul>
  )
}

type RouteRowProps = {
  route: RouteRecord
  worldId: number
  index: CosmosIndex
  rules: RuleBook
  sonName: (id: number) => string | undefined
  highlighted: boolean
  onSelectWorld: (worldId: number) => void
}

function RouteRow({
  route,
  worldId,
  index,
  rules,
  sonName,
  highlighted,
  onSelectWorld,
}: RouteRowProps) {
  const ref = useRef<HTMLLIElement>(null)
  const state = routeState(route)
  const other = otherEnd(route, worldId)
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ block: 'nearest' })
  }, [highlighted])
  const controller = index.entityName(route.controller_entity_id)
  return (
    <li
      ref={ref}
      data-route-id={route.id}
      className={cn(
        'flex min-w-0 flex-col gap-2 rounded-lg border p-3 transition-colors',
        !state.open && 'border-dashed',
        !route.known && 'opacity-80',
        highlighted && 'border-primary bg-accent'
      )}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <MethodGlyph method={route.method} closed={!state.open} />
        <Text as='span' weight='medium' truncate>
          {TRAVEL_METHOD_LABEL[route.method]}
        </Text>
        <ArrowRight
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
        <Button variant='link' size='sm' onClick={() => onSelectWorld(other)}>
          {index.worldName(other)}
        </Button>
      </div>
      <Muted variant='caption'>
        {`${plural(route.duration_epochs, 'epoch')} · danger ${route.danger}`}
        {controller && route.controller_entity_id !== null && (
          <>
            {' · controlled by '}
            <EntityLink kind='entity' id={String(route.controller_entity_id)}>
              {controller}
            </EntityLink>
          </>
        )}
      </Muted>
      <RouteStatusChips
        route={route}
        rules={rules}
        builderName={
          route.builder_son_id !== null
            ? sonName(route.builder_son_id)
            : undefined
        }
      />
      {!state.open && route.description && (
        <Muted variant='caption'>{route.description}</Muted>
      )}
      <RouteActions route={route} index={index} rules={rules} />
    </li>
  )
}
