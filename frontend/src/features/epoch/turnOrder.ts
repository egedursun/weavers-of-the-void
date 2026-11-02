import { type SonRecord, type WorldState } from '@/features/pantheon/api'

export function orderedSons(state: WorldState): SonRecord[] {
  const living = state.sons
    .map((item) => item.son)
    .filter((son) => son.status !== 'dead')
  const pinned = living
    .filter((son) => son.turn_rank !== null)
    .sort((left, right) => (left.turn_rank ?? 0) - (right.turn_rank ?? 0))
  const free = living.filter((son) => son.turn_rank === null)
  return [...pinned, ...free]
}
