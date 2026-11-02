import { type EntityContext } from '../actions/context'
import { PERCENT_MAX } from '../constants'

export type Intervention = 'miracle' | 'disaster' | 'teach_knowledge' | 'curse'

const COST_WORD: Record<Intervention, string> = {
  miracle: 'miracle',
  disaster: 'disaster',
  teach_knowledge: 'teaching',
  curse: 'curse',
}

const BOUNTY_STATS = ['prosperity', 'fertility', 'abundance', 'wealth']
const CURSE_STATS = [
  'prosperity',
  'fertility',
  'strength',
  'defense',
  'wealth',
  'abundance',
  'influence',
]

export function interventionCost(
  text: string | undefined,
  kind: Intervention
): number | null {
  if (!text) return null
  const match = new RegExp(`${COST_WORD[kind]} (\\d+)`).exec(text)
  return match ? Number(match[1]) : null
}

function statsOf(ctx: EntityContext): Record<string, unknown> {
  return ctx.entity.stats as unknown as Record<string, unknown>
}

export function miracleBlock(
  ctx: EntityContext,
  miracle: string
): string | null {
  const stats = statsOf(ctx)
  const name = ctx.entity.name
  if (
    ctx.type === 'cult' &&
    ctx.detail.tags.some((tag) => tag.startsWith('resurrection:'))
  )
    return null
  if (miracle === 'peace') {
    const hostile = ctx.bonds.some(
      (bond) =>
        bond.state === 'active' &&
        (bond.kind === 'enemy' ||
          (bond.kind === 'party_to' && bond.war_id !== null))
    )
    return hostile ? null : `${name} is not hostile to anyone.`
  }
  if (miracle === 'bounty') {
    const present = BOUNTY_STATS.filter((key) => typeof stats[key] === 'number')
    if (present.length === 0)
      return `${name} has nothing that plenty would raise.`
    return present.every((key) => (stats[key] as number) >= PERCENT_MAX)
      ? `${name} is already at its fullest.`
      : null
  }
  if (miracle === 'protection') {
    const defense = stats.defense
    return ctx.flags.has('protected_from_disaster') &&
      (typeof defense !== 'number' || defense >= PERCENT_MAX)
      ? `${name} is already protected.`
      : null
  }
  return null
}

export function curseBlock(ctx: EntityContext): string | null {
  if (!ctx.flags.has('cursed')) return null
  const stats = statsOf(ctx)
  const left = CURSE_STATS.some(
    (key) => typeof stats[key] === 'number' && (stats[key] as number) > 0
  )
  return left
    ? null
    : `${ctx.entity.name} is already cursed and has no stat left to lower.`
}
