import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph3D, {
  type ForceGraphMethods,
  type LinkObject,
  type NodeObject,
} from 'react-force-graph-3d'
import {
  CanvasTexture,
  Color,
  DoubleSide,
  Group,
  Mesh,
  MeshLambertMaterial,
  MeshBasicMaterial,
  RingGeometry,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  TorusGeometry,
} from 'three'
import { type ThemeColors, toHex } from '@/components/domain/useThemeColors'
import { drawIcon, typeIcon } from '@/features/map/iconPaths'
import { type GraphPointer } from './GraphCanvas2D'
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

export type Graph3DCommand = { kind: 'fit' | 'relayout'; nonce: number }

export type GraphCanvas3DProps = {
  graph: FilteredGraph
  tokens: ThemeColors
  highlight: Highlight
  positions: PositionMemory
  cluster: boolean
  focused: boolean
  rotate: boolean
  command: Graph3DCommand | null
  label: string
  onSelect: (node: GraphNode | null) => void
  onOpen: (node: GraphNode) => void
  onPathTo: (node: GraphNode) => void
  onFocus: (node: GraphNode) => void
  onHover: (node: GraphNode | null, pointer: GraphPointer) => void
}

const DOUBLE_CLICK_MS = 350
const FLY_MS = 900
const FIT_MS = 700
const FIT_PADDING = 60
const EARLY_FIT_MS = 1400
const ROTATE_SPEED = 0.6
const KNOWN_SHARE = 0.5
const LABEL_PIXEL = 48

const BADGE_PIXEL = 96
const badgeCache = new Map<string, CanvasTexture>()

function badgeTexture(type: string, fill: string, ink: string): CanvasTexture {
  const key = `${type}|${fill}|${ink}`
  const cached = badgeCache.get(key)
  if (cached) return cached
  const canvas = document.createElement('canvas')
  canvas.width = BADGE_PIXEL
  canvas.height = BADGE_PIXEL
  const context = canvas.getContext('2d')
  if (context) {
    const half = BADGE_PIXEL / 2
    context.translate(half, half)
    context.beginPath()
    context.arc(0, 0, half - 3, 0, Math.PI * 2)
    context.fillStyle = fill
    context.fill()
    context.lineWidth = 4
    context.strokeStyle = ink
    context.stroke()
    drawIcon(context, typeIcon(type), BADGE_PIXEL * 0.55, ink, 2.2)
  }
  const texture = new CanvasTexture(canvas)
  badgeCache.set(key, texture)
  return texture
}

function labelSprite(
  text: string,
  size: number,
  weight: number,
  tokens: ThemeColors
) {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  const font = `${weight} ${LABEL_PIXEL}px ${tokens.fontBody}`
  if (context) context.font = font
  const width = Math.ceil((context?.measureText(text).width ?? 0) + 16)
  canvas.width = Math.max(1, width)
  canvas.height = LABEL_PIXEL + 16
  if (context) {
    context.font = font
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.lineJoin = 'round'
    context.lineWidth = 8
    context.strokeStyle = tokens.background
    context.strokeText(text, canvas.width / 2, canvas.height / 2)
    context.fillStyle = tokens.foreground
    context.fillText(text, canvas.width / 2, canvas.height / 2)
  }
  const sprite = new Sprite(
    new SpriteMaterial({
      map: new CanvasTexture(canvas),
      depthWrite: false,
      transparent: true,
    })
  )
  const height = Math.max(4, size)
  sprite.scale.set((height * canvas.width) / canvas.height, height, 1)
  return sprite
}

function nodeObject(node: Node, highlight: Highlight, tokens: ThemeColors) {
  const group = new Group()
  const color = new Color(toHex(familyColor(node, tokens)))
  const dim = highlightActive(highlight) && !isLit(node, highlight)
  const opacity = dim
    ? 0.18
    : node.status === 'dead' || node.status === 'destroyed'
      ? 0.45
      : 0.95
  const material = new MeshLambertMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.18,
    transparent: true,
    opacity,
  })
  const radius = node.radius
  if (node.kind === 'world') {
    const shell = new MeshLambertMaterial({
      color,
      transparent: true,
      opacity: 0.3 * opacity,
    })
    group.add(new Mesh(new SphereGeometry(radius, 24, 16), shell))
    const ring = new Mesh(
      new TorusGeometry(radius * 1.35, radius * 0.06, 8, 48),
      material
    )
    ring.rotation.x = Math.PI / 2.6
    group.add(ring)
  }
  const badge = new Sprite(
    new SpriteMaterial({
      map: badgeTexture(
        node.kind === 'entity' ? node.type : node.kind,
        toHex(familyColor(node, tokens)),
        toHex(tokens.background)
      ),
      transparent: true,
      opacity,
      depthWrite: false,
    })
  )
  badge.scale.set(radius * 2, radius * 2, 1)
  group.add(badge)
  const marked =
    node.id === highlight.hoverId ||
    node.id === highlight.selectedId ||
    node.id === highlight.focusId ||
    highlight.pathNodes.has(node.id)
  if (marked) {
    const ring = new Mesh(
      new RingGeometry(radius * 1.6, radius * 1.6 + 1.2, 32),
      new MeshBasicMaterial({
        color: new Color(
          toHex(
            highlight.pathNodes.has(node.id)
              ? tokens['rarity-legendary']
              : tokens.foreground
          )
        ),
        side: DoubleSide,
        transparent: true,
      })
    )
    ring.userData.billboard = true
    group.add(ring)
  }
  const look = labelCandidate(node, highlight, radius, 1)
  if (
    look.show &&
    (look.important ||
      node.kind === 'world' ||
      node.kind === 'son' ||
      radius >= 9 ||
      (highlightActive(highlight) && !dim))
  ) {
    const sprite = labelSprite(
      node.name,
      Math.max(4, radius * 0.9),
      look.weight,
      tokens
    )
    sprite.position.set(0, radius * 1.8 + 3, 0)
    group.add(sprite)
  }
  return group
}

export default function GraphCanvas3D(props: GraphCanvas3DProps) {
  const { graph, tokens, highlight, positions, cluster } = props
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<ForceGraphMethods<Node, Link> | undefined>(undefined)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const lastClick = useRef<{ id: number; at: number } | null>(null)
  const pointer = useRef<GraphPointer>({ x: 0, y: 0 })
  const objects = useRef<Group[]>([])

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
        z: memory?.z,
      }
    })
    return { nodes, links: graph.links.map((link) => ({ ...link })) as Link[] }
  }, [graph, positions])

  useEffect(() => {
    const instance = graphRef.current
    if (!instance) return
    configureForces(instance, props.focused)
    const radius = Math.max(320, Math.sqrt(data.nodes.length) * 32)
    instance.d3Force(
      'cluster',
      cluster ? clusterForce(data.nodes, radius, 0.3, 0.05) : null
    )
    instance.d3ReheatSimulation()
    if (knownShare(data.nodes, positions) >= KNOWN_SHARE) return
    const timer = window.setTimeout(
      () => graphRef.current?.zoomToFit(FIT_MS, FIT_PADDING),
      EARLY_FIT_MS
    )
    return () => window.clearTimeout(timer)
  }, [data, cluster, props.focused, positions, size.width])

  useEffect(() => {
    const controls = graphRef.current?.controls() as
      { autoRotate?: boolean; autoRotateSpeed?: number } | undefined
    if (!controls) return
    controls.autoRotate = props.rotate
    controls.autoRotateSpeed = ROTATE_SPEED
  }, [props.rotate, size.width])

  const command = props.command
  useEffect(() => {
    const instance = graphRef.current
    if (!command || !instance) return
    if (command.kind === 'fit') instance.zoomToFit(FIT_MS, FIT_PADDING)
    else instance.d3ReheatSimulation()
  }, [command])

  useEffect(() => {
    let handle = 0
    const loop = () => {
      const camera = graphRef.current?.camera()
      if (camera)
        for (const object of objects.current)
          for (const child of object.children)
            if (child.userData.billboard)
              child.quaternion.copy(camera.quaternion)
      handle = requestAnimationFrame(loop)
    }
    handle = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(handle)
  }, [])

  const remember = () => {
    for (const node of data.nodes)
      if (node.x !== undefined && node.y !== undefined)
        positions.set(node.id, { x: node.x, y: node.y, z: node.z })
  }

  const fresh = knownShare(data.nodes, positions) < KNOWN_SHARE

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
        <ForceGraph3D<GraphNode & { radius: number }, GraphLink>
          ref={graphRef}
          width={size.width}
          height={size.height}
          graphData={data}
          backgroundColor={toHex(tokens.background)}
          showNavInfo={false}
          controlType='orbit'
          nodeId='id'
          nodeRelSize={1}
          nodeVal={(node) => node.radius ** 3}
          nodeLabel={() => ''}
          nodeThreeObject={(node: Node) => {
            const object = nodeObject(node, highlight, tokens)
            if (objects.current.length > data.nodes.length * 3)
              objects.current = objects.current.slice(-data.nodes.length)
            objects.current.push(object)
            return object
          }}
          linkColor={(link) => {
            const look = linkLook(link as GraphLink, highlight, tokens)
            return toHex(look.color)
          }}
          linkOpacity={0.55}
          linkWidth={(link) => {
            const look = linkLook(link as GraphLink, highlight, tokens)
            if (look.emphasis === 'path') return 2.4
            if (look.emphasis === 'hover') return 1.4
            return link.kind === 'route' ? 1.6 : 0
          }}
          linkVisibility={(link) =>
            linkLook(link as GraphLink, highlight, tokens).alpha > 0.1
          }
          linkDirectionalParticles={(link) =>
            highlight.pathLinks.has(link.key)
              ? 4
              : link.kind === 'route' && link.open
                ? 2
                : 0
          }
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleWidth={(link) =>
            highlight.pathLinks.has(link.key) ? 2.6 : 1.6
          }
          linkDirectionalParticleColor={(link) =>
            toHex(
              highlight.pathLinks.has(link.key)
                ? tokens['rarity-legendary']
                : tokens['chart-3']
            )
          }
          cooldownTime={fresh ? 15000 : 4000}
          onEngineTick={remember}
          onEngineStop={() => {
            remember()
            if (fresh) graphRef.current?.zoomToFit(FIT_MS, FIT_PADDING)
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
            if (event.shiftKey) {
              props.onPathTo(node)
              return
            }
            props.onSelect(node)
            const distance = 90 + 8 * node.radius
            const length =
              Math.hypot(node.x ?? 0, node.y ?? 0, node.z ?? 0) || 1
            const ratio = 1 + distance / length
            graphRef.current?.cameraPosition(
              {
                x: (node.x ?? 0) * ratio,
                y: (node.y ?? 0) * ratio,
                z: (node.z ?? 0) * ratio,
              },
              { x: node.x ?? 0, y: node.y ?? 0, z: node.z ?? 0 },
              FLY_MS
            )
          }}
          onNodeRightClick={(node) => props.onFocus(node)}
          onBackgroundClick={() => props.onSelect(null)}
          onNodeDragEnd={(node) => {
            if (node.x !== undefined && node.y !== undefined)
              positions.set(node.id, { x: node.x, y: node.y, z: node.z })
          }}
        />
      )}
    </div>
  )
}
