import { type BondView } from '../api/types'

export type BondGroup = {
  key: string
  outgoing: boolean
  kind: string
  bonds: BondView[]
}

export function groupBonds(bonds: BondView[]): BondGroup[] {
  const groups = new Map<string, BondGroup>()
  for (const bond of bonds) {
    if (bond.kind === 'inside' && !bond.outgoing) continue
    const key = `${bond.outgoing ? 'out' : 'in'}:${bond.kind}`
    const group = groups.get(key) ?? {
      key,
      outgoing: bond.outgoing,
      kind: bond.kind,
      bonds: [],
    }
    group.bonds.push(bond)
    groups.set(key, group)
  }
  return [...groups.values()].sort(
    (left, right) => right.bonds.length - left.bonds.length
  )
}
