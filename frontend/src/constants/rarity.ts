import { type components, rarityValues } from '@/api/generated/schema'

export type Rarity = components['schemas']['Rarity']

export const RARITIES: readonly Rarity[] = rarityValues

export const RARITY_LABEL: Record<Rarity, string> = {
  common: 'Common',
  uncommon: 'Uncommon',
  rare: 'Rare',
  epic: 'Epic',
  legendary: 'Legendary',
  mythic: 'Mythic',
}

export function isRarity(value: unknown): value is Rarity {
  return (
    typeof value === 'string' && (RARITIES as readonly string[]).includes(value)
  )
}
