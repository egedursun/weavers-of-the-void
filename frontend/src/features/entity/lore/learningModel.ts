import { type TechGraph } from './api'
import { branchOf } from './model'

export function gateText(
  graph: TechGraph | undefined,
  technique: string
): string | null {
  const spec = graph?.techniques.find((item) => item.technique === technique)
  if (!spec) return null
  const need = (items: readonly { branch: string; level: number }[]) =>
    items.map(
      (item) => `${branchOf(item.branch).label.toLowerCase()} ${item.level}`
    )
  const parts = [
    spec.all_of.length > 0 ? `Needs ${need(spec.all_of).join(' and ')}` : '',
    spec.any_of.length > 0
      ? `${spec.all_of.length > 0 ? 'and' : 'Needs'} one of ${need(spec.any_of).join(', ')}`
      : '',
  ].filter(Boolean)
  return parts.length > 0 ? parts.join(' ') : null
}

export function boostText(
  graph: TechGraph | undefined,
  technique: string
): string | null {
  const triggers = (graph?.triggers ?? []).filter((item) =>
    item.techniques.some((one) => one === technique)
  )
  return triggers.length > 0
    ? `Hastened by ${triggers.map((item) => item.label.toLowerCase()).join(', ')}`
    : null
}
