import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, {
  type ForceGraphMethods,
  type LinkObject,
  type NodeObject,
} from 'react-force-graph-2d'
import { type ThemeColors } from '@/components/domain/useThemeColors'
import { drawIcon, typeIcon } from '@/features/map/iconPaths'
import {
  type Box,
  boxAt,
  fitText,
  placeLabels,
} from '@/features/map/labelLayout'
import {
  type PositionMemory,
  clusterForce,
  configureForces,
  knownShare,
} from './graphForces'
import {
  type FilteredGraph,
  type GraphLink,
  type GraphNode,
  nodeRadius,
} from './graphModel'
import {
  type Highlight,
  familyColor,
  highlightActive,
  isLit,
  labelCandidate,
  linkLook,
} from './graphStyle'

type Node = NodeObject<GraphNode & { radius: number }>
type Link = LinkObject<Node, GraphLink>

export type GraphPointer = { x: number; y: number }

type GraphCanvas2DProps = {
  graph: FilteredGraph
  tokens: ThemeColors
  highlight: Highlight
  positions: PositionMemory
  cluster: boolean
  focused: boolean
  linkLabels: ReadonlyMap<string, string>
  label: string
  fitNonce: number
  onSelect: (node: GraphNode | null) => void
  onOpen: (node: GraphNode) => void
  onPathTo: (node: GraphNode) => void
  onFocus: (node: GraphNode) => void
  onHover: (node: GraphNode | null, pointer: GraphPointer) => void
}

const MIN_ZOOM = 0.15
const MAX_ZOOM = 5
const DOUBLE_CLICK_MS = 350
const HALO = 3
const ICON_SHARE = 1.25
const LABEL_ZOOM = 0.6
const LABEL_MAX = 180
const IMPORTANT_LABEL_MAX = 300
const KNOWN_SHARE = 0.6
const FIT_PADDING = 56
const FIT_MS = 500
const EARLY_FIT_MS = 250
const WARMUP_TICKS = 80

function endpoint(value: Link['source']): Node | null {
  return typeof value === 'object' && value !== null ? (value as Node) : null
}

export function GraphCanvas2D(props: GraphCanvas2DProps) {
  const { graph, tokens, positions, cluster } = props
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<ForceGraphMethods<Node, Link> | undefined>(undefined)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const lastClick = useRef<{ id: number; at: number } | null>(null)
  const pointer = useRef<GraphPointer>({ x: 0, y: 0 })
  const freshLayout = useRef(false)
  const propsRef = useRef(props)
  useEffect(() => {
    propsRef.current = props
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const observer = new ResizeObserver(() => {
      const rect = container.getBoundingClientRect()
      setSize({
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      })
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  const data = useMemo(() => {
    const nodes: Node[] = graph.nodes.map((node) => {
      const memory = positions.get(node.id)
      return {
        ...node,
        radius: nodeRadius(node, graph.degree.get(node.id) ?? 0),
        x: memory?.x,
        y: memory?.y,
      }
    })
    const links: Link[] = graph.links.map((link) => ({ ...link }))
    return { nodes, links }
  }, [graph, positions])

  useEffect(() => {
    const instance = graphRef.current
    if (!instance) return
    configureForces(instance, props.focused)
    instance.d3Force(
      'cluster',
      cluster
        ? clusterForce(data.nodes, Math.min(size.width, size.height) * 0.32)
        : null
    )
    instance.d3ReheatSimulation()
    if (knownShare(data.nodes, positions) > KNOWN_SHARE) return
    freshLayout.current = true
    const timer = window.setTimeout(
      () => graphRef.current?.zoomToFit(0, FIT_PADDING),
      EARLY_FIT_MS
    )
    return () => window.clearTimeout(timer)
  }, [data, cluster, props.focused, positions, size.width, size.height])

  useEffect(() => {
    if (props.fitNonce > 0) graphRef.current?.zoomToFit(FIT_MS, FIT_PADDING)
  }, [props.fitNonce])

  const remember = () => {
    for (const node of data.nodes)
      if (node.x !== undefined && node.y !== undefined)
        positions.set(node.id, { x: node.x, y: node.y })
  }

  const drawNode = (
    node: Node,
    context: CanvasRenderingContext2D,
    scale: number
  ) => {
    const current = propsRef.current
    const lit = isLit(node, current.highlight)
    const dim = highlightActive(current.highlight) && !lit
    const color = familyColor(node, current.tokens)
    const radius = node.radius
    context.save()
    context.translate(node.x ?? 0, node.y ?? 0)
    context.globalAlpha = dim
      ? 0.18
      : node.status === 'dead' || node.status === 'destroyed'
        ? 0.45
        : 1
    context.beginPath()
    context.arc(0, 0, radius, 0, Math.PI * 2)
    context.fillStyle = color
    context.fill()
    context.lineWidth = HALO / scale
    context.strokeStyle = current.tokens.background
    context.stroke()
    drawIcon(
      context,
      typeIcon(node.kind === 'entity' ? node.type : node.kind),
      radius * ICON_SHARE,
      current.tokens.background
    )
    const marked =
      node.id === current.highlight.hoverId ||
      node.id === current.highlight.selectedId ||
      node.id === current.highlight.focusId
    if (marked || current.highlight.pathNodes.has(node.id)) {
      context.globalAlpha = 1
      context.beginPath()
      context.arc(0, 0, radius + 3 / scale, 0, Math.PI * 2)
      context.lineWidth = 2 / scale
      context.strokeStyle =
        current.highlight.pathNodes.has(node.id) && !marked
          ? current.tokens['rarity-legendary']
          : current.tokens.foreground
      context.stroke()
    }
    context.restore()
  }

  const drawLink = (
    link: Link,
    context: CanvasRenderingContext2D,
    scale: number
  ) => {
    const source = endpoint(link.source)
    const target = endpoint(link.target)
    if (!source || !target) return
    const current = propsRef.current
    const look = linkLook(link as GraphLink, current.highlight, current.tokens)
    context.save()
    context.globalAlpha = look.alpha
    context.strokeStyle = look.color
    context.lineWidth = look.width / Math.max(1, scale * 0.8)
    if (look.emphasis === 'path') {
      context.shadowColor = look.color
      context.shadowBlur = 8
    }
    context.setLineDash(
      look.dash ? look.dash.map((value) => value / scale) : []
    )
    context.beginPath()
    context.moveTo(source.x ?? 0, source.y ?? 0)
    context.lineTo(target.x ?? 0, target.y ?? 0)
    context.stroke()
    context.restore()
  }

  const drawLabels = (context: CanvasRenderingContext2D, scale: number) => {
    const current = propsRef.current
    const matrix = context.getTransform()
    const ratio = window.devicePixelRatio || 1
    const font = current.tokens.fontBody
    const candidates = []
    const obstacles: Box[] = []
    const meta = new Map<
      string,
      { text: string; size: number; weight: number }
    >()
    for (const node of data.nodes) {
      const look = labelCandidate(node, current.highlight, node.radius, scale)
      if (!look.show || node.x === undefined || node.y === undefined) continue
      const sx = (matrix.a * node.x + matrix.e) / ratio
      const sy = (matrix.d * node.y + matrix.f) / ratio
      if (
        sx < -100 ||
        sy < -40 ||
        sx > size.width + 100 ||
        sy > size.height + 40
      )
        continue
      context.font = `${look.weight} ${look.size}px ${font}`
      const text = fitText(
        context,
        node.name,
        look.important ? IMPORTANT_LABEL_MAX : LABEL_MAX
      )
      const width = context.measureText(text).width
      const id = String(node.id)
      meta.set(id, { text, size: look.size, weight: look.weight })
      candidates.push({
        id,
        x: sx,
        y: sy + node.radius * scale + look.size / 2 + 3,
        width,
        height: look.size + 2,
        priority: (look.important ? 1000 : 0) + node.radius,
        always: look.important,
      })
    }
    for (const node of data.nodes) {
      if (node.x === undefined || node.y === undefined) continue
      const reach = node.radius * scale
      obstacles.push(
        boxAt(
          (matrix.a * node.x + matrix.e) / ratio,
          (matrix.d * node.y + matrix.f) / ratio,
          reach * 2,
          reach * 2
        )
      )
    }
    const placed = placeLabels(candidates, { obstacles })
    context.save()
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.lineJoin = 'round'
    for (const label of placed) {
      const item = meta.get(label.id)
      if (!item) continue
      context.font = `${item.weight} ${item.size}px ${font}`
      context.lineWidth = 3
      context.strokeStyle = current.tokens.background
      context.strokeText(item.text, label.x, label.y)
      context.fillStyle = current.tokens.foreground
      context.fillText(item.text, label.x, label.y)
    }
    const hover = current.highlight.hoverId
    if (hover !== null && scale > LABEL_ZOOM) {
      context.font = `400 10px ${font}`
      context.fillStyle = current.tokens['muted-foreground']
      for (const link of data.links) {
        const source = endpoint(link.source)
        const target = endpoint(link.target)
        if (!source || !target || (source.id !== hover && target.id !== hover))
          continue
        const mx =
          (matrix.a * (((source.x ?? 0) + (target.x ?? 0)) / 2) + matrix.e) /
          ratio
        const my =
          (matrix.d * (((source.y ?? 0) + (target.y ?? 0)) / 2) + matrix.f) /
          ratio
        const text = current.linkLabels.get(link.key) ?? link.kind
        context.strokeText(text, mx, my)
        context.fillText(text, mx, my)
      }
    }
    context.restore()
  }

  return (
    <div
      ref={containerRef}
      className='absolute inset-0 overflow-hidden'
      data-graph-scene
      role='img'
      aria-label={props.label}
      onPointerMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect()
        pointer.current = {
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        }
      }}
    >
      {size.width > 0 && size.height > 0 && (
        <ForceGraph2D<GraphNode & { radius: number }, GraphLink>
          ref={graphRef}
          width={size.width}
          height={size.height}
          graphData={data}
          backgroundColor={tokens.background}
          minZoom={MIN_ZOOM}
          maxZoom={MAX_ZOOM}
          nodeId='id'
          nodeVal={(node) => node.radius}
          nodeRelSize={1}
          nodeCanvasObjectMode={() => 'replace'}
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={(node, color, context) => {
            context.fillStyle = color
            context.beginPath()
            context.arc(
              node.x ?? 0,
              node.y ?? 0,
              node.radius + 2,
              0,
              Math.PI * 2
            )
            context.fill()
          }}
          linkCanvasObjectMode={() => 'replace'}
          linkCanvasObject={drawLink}
          onRenderFramePost={drawLabels}
          cooldownTime={
            knownShare(data.nodes, positions) > KNOWN_SHARE ? 4000 : 15000
          }
          d3AlphaDecay={
            knownShare(data.nodes, positions) > KNOWN_SHARE ? 0.06 : 0.0228
          }
          warmupTicks={
            knownShare(data.nodes, positions) > KNOWN_SHARE ? 0 : WARMUP_TICKS
          }
          onEngineTick={remember}
          onEngineStop={() => {
            remember()
            if (!freshLayout.current) return
            freshLayout.current = false
            graphRef.current?.zoomToFit(FIT_MS, FIT_PADDING)
          }}
          onNodeHover={(node) => props.onHover(node ?? null, pointer.current)}
          onNodeClick={(node, event) => {
            const now = performance.now()
            const previous = lastClick.current
            lastClick.current = { id: node.id, at: now }
            if (
              previous &&
              previous.id === node.id &&
              now - previous.at < DOUBLE_CLICK_MS
            ) {
              props.onOpen(node)
              return
            }
            if (event.shiftKey) props.onPathTo(node)
            else props.onSelect(node)
          }}
          onNodeRightClick={(node) => props.onFocus(node)}
          onBackgroundClick={() => props.onSelect(null)}
          onNodeDragEnd={(node) => {
            if (node.x !== undefined && node.y !== undefined)
              positions.set(node.id, { x: node.x, y: node.y })
          }}
        />
      )}
    </div>
  )
}
