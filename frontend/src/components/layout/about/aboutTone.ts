import { type Rarity } from '@/constants/rarity'

export const RARITY_TONE: Record<
  Rarity,
  { text: string; border: string; wash: string; glow: string }
> = {
  common: {
    text: 'text-rarity-common',
    border: 'border-rarity-common/40',
    wash: 'bg-rarity-common/15',
    glow: 'hover:shadow-rarity-common/30',
  },
  uncommon: {
    text: 'text-rarity-uncommon',
    border: 'border-rarity-uncommon/40',
    wash: 'bg-rarity-uncommon/15',
    glow: 'hover:shadow-rarity-uncommon/30',
  },
  rare: {
    text: 'text-rarity-rare',
    border: 'border-rarity-rare/40',
    wash: 'bg-rarity-rare/15',
    glow: 'hover:shadow-rarity-rare/30',
  },
  epic: {
    text: 'text-rarity-epic',
    border: 'border-rarity-epic/40',
    wash: 'bg-rarity-epic/15',
    glow: 'hover:shadow-rarity-epic/30',
  },
  legendary: {
    text: 'text-rarity-legendary',
    border: 'border-rarity-legendary/50',
    wash: 'bg-rarity-legendary/15',
    glow: 'hover:shadow-rarity-legendary/30',
  },
  mythic: {
    text: 'text-rarity-mythic',
    border: 'border-rarity-mythic/60',
    wash: 'bg-rarity-mythic/15',
    glow: 'hover:shadow-rarity-mythic/40',
  },
}
