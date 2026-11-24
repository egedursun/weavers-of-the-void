import { type FamilyTree } from '../api'

function reach(start: number, step: Map<number, number[]>, into: Set<number>) {
  const queue = [start]
  while (queue.length > 0) {
    const current = queue.pop()
    if (current === undefined) break
    for (const next of step.get(current) ?? [])
      if (!into.has(next)) {
        into.add(next)
        queue.push(next)
      }
  }
}

export function bloodLine(tree: FamilyTree, person: number): Set<number> {
  const parents = new Map<number, number[]>()
  const children = new Map<number, number[]>()
  for (const tie of tree.ties) {
    if (tie.kind !== 'parent_of') continue
    parents.set(tie.target_id, [
      ...(parents.get(tie.target_id) ?? []),
      tie.source_id,
    ])
    children.set(tie.source_id, [
      ...(children.get(tie.source_id) ?? []),
      tie.target_id,
    ])
  }
  const line = new Set<number>([person])
  reach(person, parents, line)
  reach(person, children, line)
  return line
}

export function kinCircle(tree: FamilyTree, person: number): Set<number> {
  const circle = bloodLine(tree, person)
  for (const union of tree.unions) {
    if (union.first_id === person) circle.add(union.second_id)
    if (union.second_id === person) circle.add(union.first_id)
  }
  for (const tie of tree.ties) {
    if (tie.kind === 'parent_of') continue
    if (tie.source_id === person) circle.add(tie.target_id)
    if (tie.target_id === person) circle.add(tie.source_id)
  }
  return circle
}
