import { type SpeciesCard } from './api'

export type Link = 'pinned' | 'barred' | 'derived'

export function linkOf(card: SpeciesCard, preyId: number): Link {
  if (card.pinned_prey.some((item) => item.id === preyId)) return 'pinned'
  if (card.barred_prey.some((item) => item.id === preyId)) return 'barred'
  return 'derived'
}
