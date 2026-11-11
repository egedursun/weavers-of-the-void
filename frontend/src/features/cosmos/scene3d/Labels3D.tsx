import { useCallback } from 'react'
import { useFrame } from '@react-three/fiber'
import { cn } from '@/lib/utils'
import { Portrait } from '@/components/domain'
import { Text } from '@/components/typography'
import { mediaUrl } from '@/features/images/media'
import { type CosmosWorld, type StarRecord } from '../api'
import { type CosmosIndex, isMisty } from '../model/cosmosModel'
import { STAR_TYPE_LABEL } from '../model/labels'
import { labelKey } from './labelKeys'
import { type SceneValue, useScene } from './sceneContext'

const LABEL_COVER_WIDTH = 160

const LABEL_GAP = 6
const STAR_LABEL_REACH = 1.3
const FADE_PLANET: readonly [number, number] = [26, 50]
const FADE_MOON: readonly [number, number] = [22, 40]
const PRIORITY_FOCUS = 0
const PRIORITY_STAR = 2.5
const PRIORITY_PLANET = 2
const PRIORITY_MOON = 3
const PRIORITY_SIZE_CAP = 0.4
const HYSTERESIS = 0.3
const MISTY_FADE = 0.8
const OPACITY_STEPS = 50
const AVATAR_GAP = 8
const DISC_MARGIN = 2

function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)))
  return t * t * (3 - 2 * t)
}

type Rect = { left: number; top: number; right: number; bottom: number }

function overlaps(a: Rect, b: Rect): boolean {
  return (
    a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom
  )
}

type Candidate = {
  key: string
  element: HTMLElement
  priority: number
  opacity: number
  rect: Rect
  x: number
  y: number
  worldId: number | null
}

const sizes = new WeakMap<HTMLElement, { width: number; height: number }>()
const shown = new Set<string>()

function measure(element: HTMLElement) {
  let size = sizes.get(element)
  if (!size || size.width === 0) {
    size = { width: element.offsetWidth, height: element.offsetHeight }
    sizes.set(element, size)
  }
  return size
}

function apply(element: HTMLElement, x: number, y: number, opacity: number) {
  const stepped = Math.round(opacity * OPACITY_STEPS) / OPACITY_STEPS
  element.style.transform = `translate3d(${Math.round(x)}px, ${Math.round(y)}px, 0)`
  if (element.style.opacity !== String(stepped))
    element.style.opacity = String(stepped)
  element.style.visibility = stepped > 0 ? 'visible' : 'hidden'
}

function layoutLabels(scene: SceneValue) {
  const { layout, index, labels } = scene
  const frame = scene.frameRef.current
  const candidates: Candidate[] = []
  const discs: Rect[] = []
  for (const [id, point] of frame.worldScreen) {
    if (!point.visible) continue
    const radius = Math.max(point.radius, 2) + DISC_MARGIN
    discs.push({
      left: point.x - radius,
      top: point.y - radius,
      right: point.x + radius,
      bottom: point.y + radius,
    })
    const element = labels.get(labelKey('world', id))
    const body = layout.worlds.get(id)
    const item = index.world(id)
    if (!element || !body || !item) continue
    const size = measure(element)
    const host =
      body.kind === 'moon'
        ? frame.worldScreen.get(body.parentId ?? 0)
        : body.starId !== null
          ? frame.starScreen.get(body.starId)
          : undefined
    const separation = host
      ? Math.hypot(point.x - host.x, point.y - host.y)
      : Infinity
    const fade = body.kind === 'moon' ? FADE_MOON : FADE_PLANET
    const focused =
      frame.selectedWorld === id ||
      (frame.hover?.kind === 'world' && frame.hover.id === id)
    let opacity = focused ? 1 : smoothstep(fade[0], fade[1], separation)
    if (isMisty(item) && !focused) opacity *= MISTY_FADE
    const key = labelKey('world', id)
    const priority =
      (focused
        ? PRIORITY_FOCUS
        : body.kind === 'moon'
          ? PRIORITY_MOON
          : PRIORITY_PLANET -
            Math.min(body.radius / layout.orb, PRIORITY_SIZE_CAP)) -
      (shown.has(key) ? HYSTERESIS : 0)
    const x = point.x - size.width / 2
    const y = point.y + Math.max(point.radius, 2) + LABEL_GAP
    candidates.push({
      key,
      element,
      priority,
      opacity,
      x,
      y,
      rect: { left: x, top: y, right: x + size.width, bottom: y + size.height },
      worldId: id,
    })
  }
  for (const [id, point] of frame.starScreen) {
    const element = labels.get(labelKey('star', id))
    if (!element || !point.visible) continue
    const size = measure(element)
    const key = labelKey('star', id)
    const focused =
      frame.selectedStar === id ||
      (frame.hover?.kind === 'star' && frame.hover.id === id)
    const x = point.x - size.width / 2
    const y = point.y + point.radius * STAR_LABEL_REACH + LABEL_GAP
    candidates.push({
      key,
      element,
      priority:
        (focused ? PRIORITY_FOCUS : PRIORITY_STAR) -
        (shown.has(key) ? HYSTERESIS : 0),
      opacity: 1,
      x,
      y,
      rect: { left: x, top: y, right: x + size.width, bottom: y + size.height },
      worldId: null,
    })
  }
  candidates.sort((a, b) => a.priority - b.priority)
  const placed: Rect[] = []
  const visibleWorlds = new Set<number>()
  for (const candidate of candidates) {
    const blocked =
      candidate.opacity <= 0 ||
      placed.some((rect) => overlaps(rect, candidate.rect)) ||
      discs.some((disc) => overlaps(disc, candidate.rect))
    if (blocked) {
      shown.delete(candidate.key)
      apply(candidate.element, candidate.x, candidate.y, 0)
      continue
    }
    shown.add(candidate.key)
    placed.push(candidate.rect)
    if (candidate.worldId !== null) visibleWorlds.add(candidate.worldId)
    apply(candidate.element, candidate.x, candidate.y, candidate.opacity)
  }
  for (const [id, point] of frame.worldScreen) {
    const element = labels.get(labelKey('avatars', id))
    if (!element) continue
    const size = measure(element)
    const x = point.x - size.width / 2
    const y = point.y - Math.max(point.radius, 2) - AVATAR_GAP - size.height
    const rect = {
      left: x,
      top: y,
      right: x + size.width,
      bottom: y + size.height,
    }
    const free =
      point.visible &&
      (visibleWorlds.has(id) || frame.selectedWorld === id) &&
      !placed.some((other) => overlaps(other, rect)) &&
      !discs.some((disc) => overlaps(disc, rect))
    if (free) placed.push(rect)
    apply(element, x, y, free ? 1 : 0)
    element.style.pointerEvents = free ? 'auto' : 'none'
  }
}

export function LabelUpdater() {
  const scene = useScene()
  useFrame(() => layoutLabels(scene), 0)
  return null
}

type LabelOverlayProps = {
  index: CosmosIndex
  shownWorlds: readonly CosmosWorld[]
  shownStars: readonly StarRecord[]
  labels: Map<string, HTMLElement>
  selectedWorld: number | undefined
}

export function LabelOverlay({
  index,
  shownWorlds,
  shownStars,
  labels,
  selectedWorld,
}: LabelOverlayProps) {
  const register = useCallback(
    (key: string) => (element: HTMLElement | null) => {
      if (element) labels.set(key, element)
      else labels.delete(key)
    },
    [labels]
  )
  return (
    <div
      aria-hidden='true'
      className='pointer-events-none absolute inset-0 overflow-hidden'
      style={{ color: 'var(--cosmos-label)' }}
    >
      {shownStars.map((star) => (
        <div
          key={`star-${star.id}`}
          ref={register(labelKey('star', star.id))}
          className='absolute top-0 left-0 flex flex-col items-center whitespace-nowrap'
          style={{ opacity: 0, visibility: 'hidden' }}
        >
          {star.cover && (
            <Portrait
              name={star.name}
              src={mediaUrl(star.cover, LABEL_COVER_WIDTH)}
              size='sm'
            />
          )}
          <Text as='span' variant='caption' weight='semibold' tone='inherit'>
            {star.name}
          </Text>
          <Text
            as='span'
            variant='caption'
            tone='inherit'
            className='opacity-70'
          >
            {`${STAR_TYPE_LABEL[star.star_type]} · ${index.planetsOf(star.id).length} worlds`}
          </Text>
        </div>
      ))}
      {shownWorlds.map((item) => {
        const misty = isMisty(item)
        const sub =
          item.world.discovery === 'unknown'
            ? 'Unknown world'
            : item.world.discovery === 'forgotten'
              ? 'Forgotten'
              : item.world.discovery === 'legend'
                ? `${item.type_label} · legend`
                : item.type_label
        return (
          <div
            key={`world-${item.world.id}`}
            ref={register(labelKey('world', item.world.id))}
            className='absolute top-0 left-0 flex flex-col items-center whitespace-nowrap'
            style={{
              opacity: 0,
              visibility: 'hidden',
              color:
                selectedWorld === item.world.id
                  ? 'var(--cosmos-copper)'
                  : misty
                    ? 'var(--cosmos-label-muted)'
                    : undefined,
            }}
          >
            {item.cover && !misty && (
              <Portrait
                name={item.world.name}
                src={mediaUrl(item.cover, LABEL_COVER_WIDTH)}
                size='sm'
              />
            )}
            <Text
              as='span'
              variant='caption'
              weight='medium'
              tone='inherit'
              italic={misty}
              className={cn(item.world.discovery === 'legend' && 'opacity-90')}
            >
              {item.world.name}
            </Text>
            <Text
              as='span'
              variant='caption'
              tone='inherit'
              className='opacity-70'
            >
              {sub}
            </Text>
          </div>
        )
      })}
    </div>
  )
}
