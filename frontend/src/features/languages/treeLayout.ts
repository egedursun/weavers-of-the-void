import { type KnowledgeView } from '@/features/entity/api/types'
import { type Family, type LanguageNode } from './languageFamilies'

export const FAMILY_NODE = {
  width: 196,
  height: 54,
  column: 52,
  row: 12,
  pad: 6,
}
export const TECH_NODE = {
  width: 208,
  height: 70,
  column: 64,
  row: 12,
  pad: 6,
  header: 34,
}

export type Point = { x: number; y: number }

export type FamilyPlaced = Point & { node: LanguageNode; depth: number }

export type FamilyLayout = {
  nodes: FamilyPlaced[]
  links: { from: FamilyPlaced; to: FamilyPlaced }[]
  width: number
  height: number
}

export function layoutFamily(family: Family): FamilyLayout {
  const nodes: FamilyPlaced[] = []
  const links: FamilyLayout['links'] = []
  let row = 0
  let deepest = 0
  const walk = (branch: Family, depth: number): FamilyPlaced => {
    deepest = Math.max(deepest, depth)
    const children = branch.children.map((child) => walk(child, depth + 1))
    const y =
      children.length === 0
        ? FAMILY_NODE.pad + row++ * (FAMILY_NODE.height + FAMILY_NODE.row)
        : (children[0].y + children[children.length - 1].y) / 2
    const placed: FamilyPlaced = {
      node: branch.node,
      depth,
      x: FAMILY_NODE.pad + depth * (FAMILY_NODE.width + FAMILY_NODE.column),
      y,
    }
    nodes.push(placed)
    for (const child of children) links.push({ from: placed, to: child })
    return placed
  }
  walk(family, 0)
  return {
    nodes,
    links,
    width:
      FAMILY_NODE.pad * 2 +
      (deepest + 1) * FAMILY_NODE.width +
      deepest * FAMILY_NODE.column,
    height:
      FAMILY_NODE.pad * 2 +
      row * FAMILY_NODE.height +
      Math.max(0, row - 1) * FAMILY_NODE.row,
  }
}

export function lineageOf(nodes: LanguageNode[], id: number): Set<number> {
  const parentOf = new Map(
    nodes.map((node) => [node.language.id, node.parent_language_id])
  )
  const line = new Set<number>()
  let current: number | null | undefined = id
  while (current !== null && current !== undefined && !line.has(current)) {
    line.add(current)
    current = parentOf.get(current)
  }
  return line
}

export function curve(from: Point, to: Point): string {
  const middle = (from.x + to.x) / 2
  return `M${from.x} ${from.y}C${middle} ${from.y} ${middle} ${to.y} ${to.x} ${to.y}`
}

export type TechPlaced = Point & { item: KnowledgeView; tier: number }

export type TechLayout = {
  tiers: { tier: number; x: number }[]
  nodes: TechPlaced[]
  links: { from: TechPlaced; to: TechPlaced }[]
  width: number
  height: number
}

export function tierOf(item: KnowledgeView): number {
  return Math.max(1, item.level ?? 1)
}

export function layoutTech(items: KnowledgeView[]): TechLayout {
  const tiers = [...new Set(items.map(tierOf))].sort((a, b) => a - b)
  const column = new Map(tiers.map((tier, index) => [tier, index]))
  const placed = new Map<number, TechPlaced>()
  let tallest = 0
  tiers.forEach((tier, index) => {
    const members = items.filter((item) => tierOf(item) === tier)
    const weight = (item: KnowledgeView) => {
      const rows = item.prerequisites
        .map((ref) => placed.get(ref.id)?.y)
        .filter((value): value is number => value !== undefined)
      return rows.length
        ? rows.reduce((sum, value) => sum + value, 0) / rows.length
        : Number.POSITIVE_INFINITY
    }
    members.sort(
      (left, right) =>
        weight(left) - weight(right) ||
        (right.spread ?? 0) - (left.spread ?? 0) ||
        left.knowledge.name.localeCompare(right.knowledge.name)
    )
    members.forEach((item, row) => {
      placed.set(item.knowledge.id, {
        item,
        tier,
        x: TECH_NODE.pad + index * (TECH_NODE.width + TECH_NODE.column),
        y:
          TECH_NODE.header +
          TECH_NODE.pad +
          row * (TECH_NODE.height + TECH_NODE.row),
      })
    })
    tallest = Math.max(tallest, members.length)
  })
  const nodes = [...placed.values()]
  const links = nodes.flatMap((node) =>
    node.item.prerequisites
      .map((ref) => placed.get(ref.id))
      .filter((from): from is TechPlaced => from !== undefined)
      .map((from) => ({ from, to: node }))
  )
  return {
    tiers: tiers.map((tier) => ({
      tier,
      x:
        TECH_NODE.pad +
        (column.get(tier) ?? 0) * (TECH_NODE.width + TECH_NODE.column),
    })),
    nodes,
    links,
    width:
      TECH_NODE.pad * 2 +
      tiers.length * TECH_NODE.width +
      Math.max(0, tiers.length - 1) * TECH_NODE.column,
    height:
      TECH_NODE.header +
      TECH_NODE.pad * 2 +
      tallest * TECH_NODE.height +
      Math.max(0, tallest - 1) * TECH_NODE.row,
  }
}

export function clip(text: string, limit: number): string {
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text
}
