import { type QuestAim, type QuestTargetKind } from '../api'
import { type CosmosIndex } from './cosmosModel'
import { DEAD_STAR_TYPES } from './labels'

export const LEGENDARY_AIMS: Record<
  'star' | 'route' | 'knowledge' | 'outer_being',
  readonly QuestAim[]
> = {
  star: ['restore'],
  route: ['free', 'bind'],
  knowledge: ['find', 'learn'],
  outer_being: ['destroy', 'bind'],
}

export type LegendaryTarget = keyof typeof LEGENDARY_AIMS

export const LEGENDARY_TARGETS = Object.keys(
  LEGENDARY_AIMS
) as LegendaryTarget[]

export function questBlockers(
  index: CosmosIndex
): Partial<Record<QuestTargetKind, string>> {
  const blockers: Partial<Record<QuestTargetKind, string>> = {}
  if (!index.data.stars.some((star) => DEAD_STAR_TYPES.has(star.star_type)))
    blockers.star = 'No star whose light is out'
  if (!index.data.routes.some((route) => route.closure === 'sealed'))
    blockers.route = 'No sealed route'
  return blockers
}
