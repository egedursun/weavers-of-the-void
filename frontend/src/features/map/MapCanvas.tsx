import {
  type KeyboardEvent,
  type PointerEvent,
  type WheelEvent,
  useEffect,
  useMemo,
  useRef,
} from 'react'
import { type ActProp, refusalOf } from '@/api/mutation'
import { type ThemeColors } from '@/components/domain/useThemeColors'
import { type MapView } from './api'
import { buildDeep } from './deepLayer'
import { domainAnchors } from './mapEdges'
import {
  type LayerMode,
  type Overlay,
  type Size,
  type Transform,
  CellIndex,
  FOCUS_ZOOM,
  MAX_ZOOM,
  centreOn,
  fitTransform,
  positionedPoints,
  toMap,
  zoomAt,
} from './mapModel'
import {
  type HitTarget,
  type MarkerFilter,
  type Thresholds,
  drawScene,
  hitAt,
  locate,
} from './mapScene'
import { buildFog, buildTerrain, buildTint } from './terrainLayer'
import { type LayerPalette } from './useLayerPalette'

export type ScreenPoint = { x: number; y: number }

export type MapViewport = { transform: Transform; fit: Transform; size: Size }

export type ZoomCommand =
  | { kind: 'in' | 'out' | 'fit'; nonce: number }
  | { kind: 'at'; x: number; y: number; nonce: number }

type MapCanvasProps = {
  view: MapView
  tokens: ThemeColors
  palette: LayerPalette | null
  mode: LayerMode
  overlays: Record<Overlay, boolean>
  filter: MarkerFilter
  past: boolean
  noteMode: boolean
  thresholds: Thresholds
  trendPct: number
  leakLevel: 0 | 1 | 2
  focusId: number | null
  reducedMotion: boolean
  label: string
  command: ZoomCommand | null
  onActivate: (hit: HitTarget, screen: ScreenPoint) => void
  onHover: (hit: HitTarget | null, screen: ScreenPoint) => void
  onEmptyClick: (map: ScreenPoint, screen: ScreenPoint) => void
  onMove: (hit: HitTarget, map: ScreenPoint) => void
  act?: ActProp
  onViewport: (viewport: MapViewport) => void
}

const DRAG_START_PX = 4
const MOVE_MIN_UNITS = 2
const WHEEL_STEP = 0.0015
const KEY_ZOOM = 1.25
const KEY_PAN = 60
const ENTRANCE_MS = 600
const AT_ZOOM = 2.5
const UNKNOWN = 0
const entered = new Set<number>()

type Gesture = {
  pointers: Map<number, ScreenPoint>
  start: ScreenPoint
  startTransform: Transform
  target: HitTarget | null
  dragging: boolean
  panning: boolean
  pinchDistance: number | null
}

export function MapCanvas(props: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const sizeRef = useRef<Size>({ width: 0, height: 0 })
  const transformRef = useRef<Transform | null>(null)
  const fitRef = useRef<Transform>({ k: 1, x: 0, y: 0 })
  const hitsRef = useRef<HitTarget[]>([])
  const hoverRef = useRef<string | null>(null)
  const dragRef = useRef<{ key: string; x: number; y: number } | null>(null)
  const gestureRef = useRef<Gesture | null>(null)
  const focusStartRef = useRef(0)
  const entranceStartRef = useRef(0)
  const frameRef = useRef(0)
  const propsRef = useRef(props)
  const worldRef = useRef<number | null>(null)

  const { view, palette } = props
  const points = useMemo(() => positionedPoints(view), [view])
  const pointById = useMemo(
    () => new Map(points.map((point) => [point.id, point])),
    [points]
  )
  const below = view.level !== null && view.level !== undefined
  const fog = props.overlays.fog && !below
  const tokens = props.tokens
  const terrain = useMemo(
    () => (below ? buildDeep(view, tokens) : buildTerrain(view.geometry, fog)),
    [below, view, tokens, fog]
  )
  const fogTexture = useMemo(
    () => (fog ? buildFog(view.geometry) : null),
    [view.geometry, fog]
  )
  const tint = useMemo(
    () => (palette ? buildTint(view.geometry, palette) : null),
    [view.geometry, palette]
  )
  const anchors = useMemo(
    () => (palette ? domainAnchors(view.geometry, palette.cellKey) : []),
    [view.geometry, palette]
  )
  const cellIndex = useMemo(() => new CellIndex(view.geometry), [view.geometry])

  const sceneRef = useRef({
    points,
    pointById,
    terrain,
    tint,
    fog: fogTexture,
    anchors,
    cellIndex,
  })
  useEffect(() => {
    propsRef.current = props
    sceneRef.current = {
      points,
      pointById,
      terrain,
      tint,
      fog: fogTexture,
      anchors,
      cellIndex,
    }
  })

  const render = useRef<(time: number) => void>(() => undefined)
  useEffect(() => {
    render.current = (time: number) => {
      const canvas = canvasRef.current
      const context = canvas?.getContext('2d')
      const current = propsRef.current
      const transform = transformRef.current
      if (!canvas || !context || !transform) return
      const size = sizeRef.current
      if (size.width === 0 || size.height === 0) return
      const ratio = window.devicePixelRatio || 1
      context.setTransform(ratio, 0, 0, ratio, 0, 0)
      const animate = !current.reducedMotion
      const elapsed = time - entranceStartRef.current
      const entrance = animate ? Math.min(1, elapsed / ENTRANCE_MS) : 1
      const scene = sceneRef.current
      hitsRef.current = drawScene(context, {
        points: scene.points,
        pointById: scene.pointById,
        terrain: scene.terrain,
        tint: scene.tint,
        fog: scene.fog,
        anchors: scene.anchors,
        palette: current.palette,
        filter: current.filter,
        onImage: () => requestFrame.current(),
        view: current.view,
        size,
        transform,
        fit: fitRef.current,
        tokens: current.tokens,
        mode: current.mode,
        overlays: current.overlays,
        past: current.past,
        noteMode: current.noteMode,
        thresholds: current.thresholds,
        trendPct: current.trendPct,
        hoverKey: hoverRef.current,
        focusId: current.focusId,
        focusStartedAt: focusStartRef.current,
        drag: dragRef.current,
        time,
        animate,
        entrance,
        leakLevel: current.leakLevel,
      })
    }
  })

  const requestFrame = useRef(() => {
    if (frameRef.current) return
    frameRef.current = requestAnimationFrame((time) => {
      frameRef.current = 0
      render.current(time)
    })
  })

  useEffect(() => {
    if (props.reducedMotion) {
      requestFrame.current()
      return
    }
    let handle = 0
    const loop = (time: number) => {
      render.current(time)
      handle = requestAnimationFrame(loop)
    }
    const visible = () => {
      cancelAnimationFrame(handle)
      if (document.visibilityState === 'visible')
        handle = requestAnimationFrame(loop)
    }
    visible()
    document.addEventListener('visibilitychange', visible)
    return () => {
      cancelAnimationFrame(handle)
      document.removeEventListener('visibilitychange', visible)
    }
  }, [props.reducedMotion])

  const publish = useRef(() => {
    const transform = transformRef.current
    if (!transform) return
    propsRef.current.onViewport({
      transform,
      fit: fitRef.current,
      size: sizeRef.current,
    })
  })

  const setTransform = useRef((next: Transform) => {
    transformRef.current = next
    publish.current()
    requestFrame.current()
  })

  useEffect(() => {
    const container = containerRef.current
    const canvas = canvasRef.current
    if (!container || !canvas) return
    const observer = new ResizeObserver(() => {
      const rect = container.getBoundingClientRect()
      const ratio = window.devicePixelRatio || 1
      sizeRef.current = { width: rect.width, height: rect.height }
      canvas.width = Math.max(1, Math.round(rect.width * ratio))
      canvas.height = Math.max(1, Math.round(rect.height * ratio))
      const previous = transformRef.current
      const wasFitted =
        !previous ||
        (previous.k === fitRef.current.k &&
          previous.x === fitRef.current.x &&
          previous.y === fitRef.current.y)
      const fit = fitTransform(propsRef.current.view.geometry, sizeRef.current)
      fitRef.current = fit
      if (wasFitted) transformRef.current = fit
      publish.current()
      render.current(performance.now())
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  const worldId = view.world.id
  useEffect(() => {
    const size = sizeRef.current
    const fit = fitTransform(view.geometry, size)
    fitRef.current = fit
    if (worldRef.current !== worldId) {
      worldRef.current = worldId
      if (size.width > 0) setTransform.current(fit)
      else transformRef.current = null
      entranceStartRef.current = entered.has(worldId)
        ? -ENTRANCE_MS
        : performance.now()
      entered.add(worldId)
    } else {
      publish.current()
    }
    requestFrame.current()
  }, [worldId, view.geometry])

  useEffect(() => {
    requestFrame.current()
  })

  const focusId = props.focusId
  useEffect(() => {
    if (focusId === null) return
    const site = locate({ pointById, view }, focusId)
    const size = sizeRef.current
    if (!site || size.width === 0) return
    focusStartRef.current = performance.now()
    setTransform.current(
      centreOn(site.x, site.y, fitRef.current.k * FOCUS_ZOOM, size)
    )
  }, [focusId, pointById, view])

  const command = props.command
  useEffect(() => {
    if (!command) return
    const transform = transformRef.current ?? fitRef.current
    const size = sizeRef.current
    if (command.kind === 'fit') setTransform.current(fitRef.current)
    else if (command.kind === 'at')
      setTransform.current(
        centreOn(
          command.x,
          command.y,
          Math.min(
            fitRef.current.k * MAX_ZOOM,
            Math.max(transform.k * AT_ZOOM, fitRef.current.k * FOCUS_ZOOM)
          ),
          size
        )
      )
    else
      setTransform.current(
        zoomAt(
          transform,
          fitRef.current,
          command.kind === 'in' ? KEY_ZOOM : 1 / KEY_ZOOM,
          size.width / 2,
          size.height / 2
        )
      )
  }, [command])

  const local = (event: { clientX: number; clientY: number }): ScreenPoint => {
    const rect = canvasRef.current?.getBoundingClientRect()
    return {
      x: event.clientX - (rect?.left ?? 0),
      y: event.clientY - (rect?.top ?? 0),
    }
  }

  const targetAt = (point: ScreenPoint): HitTarget | null => {
    const hit = hitAt(hitsRef.current, point.x, point.y)
    if (hit) return hit
    const current = propsRef.current
    if (current.noteMode) return null
    const transform = transformRef.current ?? fitRef.current
    const at = toMap(transform, point.x, point.y)
    const cell = sceneRef.current.cellIndex.nearest(at.x, at.y)
    if (cell === null) return null
    const cells = current.view.geometry.cells
    if (cells.known[cell] === UNKNOWN && current.overlays.fog) return null
    const region = cells.region[cell]
    if (region === null || region === undefined) return null
    return {
      key: `area:${region}`,
      kind: 'region',
      id: region,
      x: point.x,
      y: point.y,
      radius: 0,
      area: true,
      draggable: false,
    }
  }

  const onPointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0 && event.pointerType === 'mouse') return
    const point = local(event)
    event.currentTarget.setPointerCapture(event.pointerId)
    const existing = gestureRef.current
    if (existing) {
      existing.pointers.set(event.pointerId, point)
      if (existing.pointers.size === 2) {
        const [first, second] = [...existing.pointers.values()]
        existing.pinchDistance = Math.hypot(
          first.x - second.x,
          first.y - second.y
        )
        existing.startTransform = transformRef.current ?? fitRef.current
        existing.target = null
        existing.dragging = false
        dragRef.current = null
      }
      return
    }
    gestureRef.current = {
      pointers: new Map([[event.pointerId, point]]),
      start: point,
      startTransform: transformRef.current ?? fitRef.current,
      target: targetAt(point),
      dragging: false,
      panning: false,
      pinchDistance: null,
    }
  }

  const onPointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const point = local(event)
    const gesture = gestureRef.current
    const current = propsRef.current
    if (!gesture) {
      const hit = targetAt(point)
      const key = hit?.key ?? null
      if (key !== hoverRef.current) {
        hoverRef.current = key
        requestFrame.current()
      }
      event.currentTarget.style.cursor =
        hit && !hit.area && hit.kind !== 'line'
          ? hit.draggable
            ? 'move'
            : 'pointer'
          : current.noteMode
            ? 'crosshair'
            : 'grab'
      current.onHover(hit, point)
      return
    }
    gesture.pointers.set(event.pointerId, point)
    if (gesture.pinchDistance !== null && gesture.pointers.size >= 2) {
      const [first, second] = [...gesture.pointers.values()]
      const distance = Math.hypot(first.x - second.x, first.y - second.y)
      const centre = {
        x: (first.x + second.x) / 2,
        y: (first.y + second.y) / 2,
      }
      setTransform.current(
        zoomAt(
          gesture.startTransform,
          fitRef.current,
          distance / gesture.pinchDistance,
          centre.x,
          centre.y
        )
      )
      return
    }
    const moved = Math.hypot(
      point.x - gesture.start.x,
      point.y - gesture.start.y
    )
    if (!gesture.dragging && !gesture.panning && moved < DRAG_START_PX) return
    const transform = transformRef.current ?? fitRef.current
    if (
      gesture.target?.draggable &&
      !gesture.panning &&
      refusalOf(propsRef.current.act) === null
    ) {
      gesture.dragging = true
      const at = toMap(transform, point.x, point.y)
      dragRef.current = { key: gesture.target.key, x: at.x, y: at.y }
      requestFrame.current()
      return
    }
    gesture.panning = true
    event.currentTarget.style.cursor = 'grabbing'
    setTransform.current({
      ...gesture.startTransform,
      x: gesture.startTransform.x + point.x - gesture.start.x,
      y: gesture.startTransform.y + point.y - gesture.start.y,
    })
  }

  const finish = (
    event: PointerEvent<HTMLCanvasElement>,
    cancelled: boolean
  ) => {
    const gesture = gestureRef.current
    if (!gesture) return
    gesture.pointers.delete(event.pointerId)
    if (gesture.pointers.size > 0) return
    gestureRef.current = null
    const point = local(event)
    const current = propsRef.current
    const transform = transformRef.current ?? fitRef.current
    if (cancelled || gesture.pinchDistance !== null) {
      dragRef.current = null
      requestFrame.current()
      return
    }
    if (gesture.dragging && gesture.target) {
      const drag = dragRef.current
      dragRef.current = null
      const original = toMap(transform, gesture.start.x, gesture.start.y)
      if (
        drag &&
        Math.hypot(drag.x - original.x, drag.y - original.y) > MOVE_MIN_UNITS
      )
        current.onMove(gesture.target, { x: drag.x, y: drag.y })
      requestFrame.current()
      return
    }
    if (gesture.panning) return
    if (gesture.target) {
      current.onActivate(gesture.target, point)
      return
    }
    current.onEmptyClick(toMap(transform, point.x, point.y), point)
  }

  const onWheel = (event: WheelEvent<HTMLCanvasElement>) => {
    const point = local(event)
    const transform = transformRef.current ?? fitRef.current
    setTransform.current(
      zoomAt(
        transform,
        fitRef.current,
        Math.exp(-event.deltaY * WHEEL_STEP),
        point.x,
        point.y
      )
    )
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const prevent = (event: globalThis.WheelEvent) => event.preventDefault()
    canvas.addEventListener('wheel', prevent, { passive: false })
    return () => canvas.removeEventListener('wheel', prevent)
  }, [])

  const onKeyDown = (event: KeyboardEvent<HTMLCanvasElement>) => {
    const transform = transformRef.current ?? fitRef.current
    const size = sizeRef.current
    const centre = { x: size.width / 2, y: size.height / 2 }
    const pan: Record<string, [number, number]> = {
      ArrowLeft: [KEY_PAN, 0],
      ArrowRight: [-KEY_PAN, 0],
      ArrowUp: [0, KEY_PAN],
      ArrowDown: [0, -KEY_PAN],
    }
    if (event.key in pan) {
      const [dx, dy] = pan[event.key]
      setTransform.current({
        ...transform,
        x: transform.x + dx,
        y: transform.y + dy,
      })
    } else if (event.key === '+' || event.key === '=') {
      setTransform.current(
        zoomAt(transform, fitRef.current, KEY_ZOOM, centre.x, centre.y)
      )
    } else if (event.key === '-' || event.key === '_') {
      setTransform.current(
        zoomAt(transform, fitRef.current, 1 / KEY_ZOOM, centre.x, centre.y)
      )
    } else if (event.key === '0') {
      setTransform.current(fitRef.current)
    } else return
    event.preventDefault()
  }

  return (
    <div
      ref={containerRef}
      className='absolute inset-0 isolate overflow-hidden'
      data-map-scene
    >
      <canvas
        ref={canvasRef}
        role='img'
        tabIndex={0}
        aria-label={props.label}
        className='block size-full touch-none outline-none focus-visible:ring-2 focus-visible:ring-ring'
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={(event) => finish(event, false)}
        onPointerCancel={(event) => finish(event, true)}
        onPointerLeave={(event) => {
          if (!gestureRef.current) {
            hoverRef.current = null
            props.onHover(null, local(event))
            requestFrame.current()
          }
        }}
        onWheel={onWheel}
        onKeyDown={onKeyDown}
      />
    </div>
  )
}
