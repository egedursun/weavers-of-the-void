import { type LegendaryQuestKind } from '../api'
import { type CosmosIndex } from './cosmosModel'
import { DEAD_STAR_TYPES } from './labels'

export function questBlockers(
  index: CosmosIndex
): Partial<Record<LegendaryQuestKind, string>> {
  const blockers: Partial<Record<LegendaryQuestKind, string>> = {}
  if (!index.data.stars.some((star) => DEAD_STAR_TYPES.has(star.star_type)))
    blockers.dead_star = 'No dead star in the cosmos'
  if (!index.data.routes.some((route) => route.closure === 'sealed'))
    blockers.sealed_gate = 'No sealed route'
  return blockers
}
