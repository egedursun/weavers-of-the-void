import { type ReactNode, type RefObject, useRef, useState } from 'react'
import { formatCompact } from '@/lib/format'
import { TAP_SLOP } from '@/lib/sceneTap'
import { Text } from '@/components/typography'
import { type CosmosIndex, isMisty, routeStateText } from '../model/cosmosModel'
import {
  ATMOSPHERE_LABEL,
  JOURNEY_INTENT_LABEL,
  STAR_TYPE_LABEL,
  TRAVEL_METHOD_LABEL,
} from '../model/labels'
import { METHOD_LOOK, cssVar } from '../model/looks'
import { pick, sameHover } from './picking'
import { type FrameState, type Hover } from './sceneContext'

const CLICK_MS = 600
const TIP_OFFSET = 14
const TIP_EDGE = 280

export type SceneHandlers = {
  onWorld: (worldId: number) => void
  onWorldDouble: (worldId: number) => void
  onStar: (starId: number) => void
  onStarDouble: (starId: number) => void
  onRoute: (routeId: number) => void
  onVoyage: (journeyId: number) => void
  onHover: (hover: Hover) => void
}

type ScenePointerProps = SceneHandlers & {
  frameRef: RefObject<FrameState>
  index: CosmosIndex
  foreignGodOf: (worldId: number) => string | undefined
  children: ReactNode
}

function TipBody({
  hover,
  index,
  foreignGodOf,
}: {
  hover: Hover
  index: CosmosIndex
  foreignGodOf: (worldId: number) => string | undefined
}) {
  if (!hover) return null
  if (hover.kind === 'world') {
    const item = index.world(hover.id)
    if (!item) return null
    const parent = index.world(item.world.parent_world_id)
    const god = foreignGodOf(item.world.id)
    return (
      <>
        <Text weight='semibold' tone='inherit'>
          {item.world.name}
        </Text>
        <Text variant='caption' tone='inherit'>
          {`${isMisty(item) ? 'Unknown world' : item.type_label}${parent ? ` · moon of ${parent.world.name}` : ''}${item.world.discovery === 'legend' ? ' · legend' : ''}`}
        </Text>
        <Text variant='caption' tone='inherit'>
          {`${formatCompact(item.counts.population)} souls · ${item.counts.regions} regions · atmosphere ${ATMOSPHERE_LABEL[item.world.atmosphere].toLowerCase()} · leakage ${item.world.leakage}`}
        </Text>
        {god && (
          <Text variant='caption' tone='inherit'>{`Foreign god: ${god}`}</Text>
        )}
        <Text variant='caption' tone='inherit' className='opacity-70'>
          Click: card · double-click: descend to its map
        </Text>
      </>
    )
  }
  if (hover.kind === 'star') {
    const star = index.star(hover.id)
    if (!star) return null
    return (
      <>
        <Text weight='semibold' tone='inherit'>
          {star.name}
        </Text>
        <Text
          variant='caption'
          tone='inherit'
        >{`${STAR_TYPE_LABEL[star.star_type]} · brightness ${star.brightness}`}</Text>
        {star.description && (
          <Text variant='caption' tone='inherit' truncate={3}>
            {star.description}
          </Text>
        )}
      </>
    )
  }
  if (hover.kind === 'route') {
    const route = index.route(hover.id)
    if (!route) return null
    const controller = index.entityName(route.controller_entity_id)
    return (
      <>
        <span className='flex min-w-0 items-center gap-2'>
          <svg
            aria-hidden='true'
            viewBox='0 0 10 10'
            className='size-icon-xs shrink-0'
          >
            <circle
              cx={5}
              cy={5}
              r={5}
              fill={cssVar(METHOD_LOOK[route.method].token)}
            />
          </svg>
          <Text as='span' weight='semibold' tone='inherit'>
            {TRAVEL_METHOD_LABEL[route.method]}
          </Text>
        </span>
        <Text
          variant='caption'
          tone='inherit'
        >{`${index.worldName(route.world_a_id)} ↔ ${index.worldName(route.world_b_id)}`}</Text>
        <Text variant='caption' tone='inherit'>
          {`${route.duration_epochs} epochs · danger ${route.danger}${controller ? ` · controlled by ${controller}` : ''}${route.known ? '' : ' · unknown route'} · ${routeStateText(route)}`}
        </Text>
        {route.description && (
          <Text variant='caption' tone='inherit' truncate={3}>
            {route.description}
          </Text>
        )}
      </>
    )
  }
  const journey = index.data.journeys.find((item) => item.id === hover.id)
  if (!journey) return null
  return (
    <>
      <Text weight='semibold' tone='inherit'>
        {`${index.entityName(journey.traveller_entity_id) ?? 'Travellers'} → ${index.worldName(journey.destination_world_id)}`}
      </Text>
      <Text variant='caption' tone='inherit'>
        {`${JOURNEY_INTENT_LABEL[journey.intent]}${journey.population > 0 ? ` · ${formatCompact(journey.population)} souls` : ''}`}
      </Text>
      <Text variant='caption' tone='inherit'>
        {journey.epochs_left > 0
          ? `Arrives in ${journey.epochs_left} epochs`
          : 'Arrives this epoch'}
        {journey.vehicle_entity_id !== null
          ? ` · ${index.entityName(journey.vehicle_entity_id) ?? 'a vessel'}`
          : ''}
      </Text>
    </>
  )
}

export function ScenePointer({
  frameRef,
  index,
  foreignGodOf,
  children,
  ...handlers
}: ScenePointerProps) {
  const [hover, setHover] = useState<Hover>(null)
  const tip = useRef<HTMLDivElement>(null)
  const container = useRef<HTMLDivElement>(null)
  const press = useRef<{
    x: number
    y: number
    time: number
    button: number
  } | null>(null)
  const locate = (event: { clientX: number; clientY: number }) => {
    const box = container.current?.getBoundingClientRect()
    return {
      x: event.clientX - (box?.left ?? 0),
      y: event.clientY - (box?.top ?? 0),
      width: box?.width ?? 0,
    }
  }
  const updateHover = (next: Hover) => {
    if (sameHover(next, frameRef.current.hover)) return
    frameRef.current.hover = next
    setHover(next)
    handlers.onHover(next)
  }
  const placeTip = (x: number, y: number, width: number) => {
    const element = tip.current
    if (!element) return
    const flip = x + TIP_EDGE > width
    element.style.transform = `translate3d(${flip ? x - TIP_OFFSET : x + TIP_OFFSET}px, ${y + TIP_OFFSET}px, 0) translateX(${flip ? '-100%' : '0'})`
  }
  const activate = (target: Hover, double: boolean) => {
    if (!target) return
    if (target.kind === 'world')
      (double ? handlers.onWorldDouble : handlers.onWorld)(target.id)
    else if (target.kind === 'star')
      (double ? handlers.onStarDouble : handlers.onStar)(target.id)
    else if (target.kind === 'route') handlers.onRoute(target.id)
    else handlers.onVoyage(target.id)
  }
  return (
    <div
      ref={container}
      className='relative h-full w-full'
      style={{ cursor: hover ? 'pointer' : 'grab' }}
      onPointerMove={(event) => {
        const point = locate(event)
        if (event.buttons !== 0) return
        updateHover(pick(frameRef.current, point.x, point.y))
        placeTip(point.x, point.y, point.width)
      }}
      onPointerLeave={() => updateHover(null)}
      onPointerDown={(event) => {
        const point = locate(event)
        press.current = {
          x: point.x,
          y: point.y,
          time: performance.now(),
          button: event.button,
        }
      }}
      onPointerUp={(event) => {
        const start = press.current
        press.current = null
        if (
          !start ||
          start.button !== 0 ||
          event.ctrlKey ||
          event.metaKey ||
          event.shiftKey
        )
          return
        const point = locate(event)
        if (
          performance.now() - start.time > CLICK_MS ||
          Math.hypot(point.x - start.x, point.y - start.y) > TAP_SLOP
        )
          return
        activate(pick(frameRef.current, point.x, point.y), false)
      }}
      onDoubleClick={(event) => {
        const point = locate(event)
        activate(pick(frameRef.current, point.x, point.y), true)
      }}
    >
      {children}
      <div
        ref={tip}
        role='tooltip'
        className='pointer-events-none absolute top-0 left-0 flex max-w-xs flex-col gap-0.5 rounded-md border bg-popover p-2 text-popover-foreground shadow-md'
        style={{ visibility: hover ? 'visible' : 'hidden' }}
      >
        <TipBody hover={hover} index={index} foreignGodOf={foreignGodOf} />
      </div>
    </div>
  )
}
