import {
  type ThemeColorName,
  type ThemeColors,
} from '@/components/domain/useThemeColors'
import {
  type GraphLink,
  type GraphNode,
  type LinkTone,
  linkTone,
} from './graphModel'

export type Highlight = {
  hoverId: number | null
  hoverNeighbours: ReadonlySet<number>
  pathNodes: ReadonlySet<number>
  pathLinks: ReadonlySet<string>
  family: string | null
  selectedId: number | null
  focusId: number | null
}

export function highlightActive(highlight: Highlight): boolean {
  return (
    highlight.hoverId !== null ||
    highlight.pathNodes.size > 0 ||
    highlight.family !== null
  )
}

export function isLit(node: GraphNode, highlight: Highlight): boolean {
  if (highlight.hoverId !== null)
    return (
      node.id === highlight.hoverId || highlight.hoverNeighbours.has(node.id)
    )
  if (highlight.pathNodes.size > 0) return highlight.pathNodes.has(node.id)
  if (highlight.family !== null) return node.family.key === highlight.family
  return true
}

export function familyColor(node: GraphNode, tokens: ThemeColors): string {
  return tokens[node.family.token]
}

export const TONE_TOKEN: Record<LinkTone, ThemeColorName> = {
  route: 'chart-3',
  inside: 'muted-foreground',
  conflict: 'destructive',
  faith: 'rarity-legendary',
  other: 'chart-2',
}

const TONE_ALPHA: Record<LinkTone, number> = {
  route: 0.85,
  inside: 0.24,
  conflict: 0.5,
  faith: 0.5,
  other: 0.3,
}

const IN_WORLD_ALPHA = 0.16
const CLOSED_ROUTE_ALPHA = 0.3
const PAST_FACTOR = 0.6
const DIM_ALPHA = 0.12
const PATH_DIM_ALPHA = 0.07

export type LinkLook = {
  color: string
  alpha: number
  width: number
  dash: number[] | null
  emphasis: 'path' | 'hover' | 'none'
}

export function linkLook(
  link: GraphLink,
  highlight: Highlight,
  tokens: ThemeColors
): LinkLook {
  const tone = linkTone(link)
  if (highlight.pathLinks.has(link.key))
    return {
      color: tokens['rarity-legendary'],
      alpha: 1,
      width: 3,
      dash: null,
      emphasis: 'path',
    }
  const touchesHover =
    highlight.hoverId !== null &&
    (link.source === highlight.hoverId || link.target === highlight.hoverId)
  if (touchesHover)
    return {
      color: tokens.foreground,
      alpha: 0.95,
      width: 1.6,
      dash: link.past ? [1, 4] : null,
      emphasis: 'hover',
    }
  let alpha = TONE_ALPHA[tone]
  if (link.kind === 'in_world') alpha = IN_WORLD_ALPHA
  if (link.kind === 'route' && !link.open) alpha = CLOSED_ROUTE_ALPHA
  if (link.past) alpha *= PAST_FACTOR
  if (highlightActive(highlight))
    alpha = Math.min(
      alpha,
      highlight.pathNodes.size > 0 ? PATH_DIM_ALPHA : DIM_ALPHA
    )
  return {
    color: tokens[TONE_TOKEN[tone]],
    alpha,
    width: link.kind === 'route' ? 2.4 : 1,
    dash: link.past ? [1, 4] : null,
    emphasis: 'none',
  }
}

export function labelCandidate(
  node: GraphNode,
  highlight: Highlight,
  radius: number,
  zoom: number
): { show: boolean; important: boolean; weight: number; size: number } {
  const important =
    node.id === highlight.hoverId ||
    node.id === highlight.focusId ||
    node.id === highlight.selectedId ||
    highlight.pathNodes.has(node.id)
  const lit = isLit(node, highlight)
  const dimmed = highlightActive(highlight) && !lit
  const show =
    !dimmed &&
    (important ||
      node.kind === 'world' ||
      node.kind === 'son' ||
      zoom > 0.9 ||
      radius >= 9 ||
      (highlightActive(highlight) && lit))
  const size =
    node.kind === 'world' ? 15 : node.kind === 'son' || important ? 13 : 11
  const weight =
    node.kind === 'world' ? 700 : node.kind === 'son' || important ? 600 : 400
  return { show, important, weight, size }
}
