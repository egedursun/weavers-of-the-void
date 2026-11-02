import { type components } from '@/api/generated/schema'

export type LanguageNode = components['schemas']['LanguageNode']

export type Family = {
  node: LanguageNode
  children: Family[]
}

export function buildFamilies(nodes: LanguageNode[]): {
  families: Family[]
  loners: LanguageNode[]
} {
  const ids = new Set(nodes.map((node) => node.language.id))
  const byParent = new Map<number, LanguageNode[]>()
  for (const node of nodes) {
    const parent = node.parent_language_id
    if (parent !== null && ids.has(parent))
      byParent.set(parent, [...(byParent.get(parent) ?? []), node])
  }
  const grow = (node: LanguageNode, seen: Set<number>): Family => {
    seen.add(node.language.id)
    return {
      node,
      children: (byParent.get(node.language.id) ?? [])
        .filter((child) => !seen.has(child.language.id))
        .map((child) => grow(child, seen)),
    }
  }
  const roots = nodes.filter(
    (node) =>
      node.parent_language_id === null || !ids.has(node.parent_language_id)
  )
  const seen = new Set<number>()
  const families: Family[] = []
  const loners: LanguageNode[] = []
  for (const root of roots) {
    const family = grow(root, seen)
    if (family.children.length > 0) families.push(family)
    else loners.push(root)
  }
  return { families, loners }
}

export function relativesOf(nodes: LanguageNode[], id: number) {
  const self = nodes.find((node) => node.language.id === id)
  const parent = self?.parent_language_id
    ? nodes.find((node) => node.language.id === self.parent_language_id)
    : undefined
  const daughters = nodes.filter((node) => node.parent_language_id === id)
  return { self, parent, daughters }
}

export function signatureText(signature: LanguageNode['signature']): string {
  if (!signature) return 'No signature yet'
  const parts = [`consonants ${signature.consonants}`]
  if (signature.cluster) parts.push(`cluster ${signature.cluster}`)
  if (signature.ending) parts.push(`ending -${signature.ending}`)
  return parts.join(' · ')
}
