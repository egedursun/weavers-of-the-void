import { type Rarity } from '@/constants/rarity'

export const RARITY_BADGE_CLASS: Record<Rarity, string> = {
  common: 'border-rarity-common/50 bg-rarity-common/10 text-rarity-common',
  uncommon:
    'border-rarity-uncommon/50 bg-rarity-uncommon/10 text-rarity-uncommon',
  rare: 'border-rarity-rare/50 bg-rarity-rare/10 text-rarity-rare',
  epic: 'border-rarity-epic/50 bg-rarity-epic/10 text-rarity-epic',
  legendary:
    'border-rarity-legendary/50 bg-rarity-legendary/10 text-rarity-legendary',
  mythic: 'border-rarity-mythic/50 bg-rarity-mythic/10 text-rarity-mythic',
}

export const RARITY_TEXT_CLASS: Record<Rarity, string> = {
  common: 'text-rarity-common',
  uncommon: 'text-rarity-uncommon',
  rare: 'text-rarity-rare',
  epic: 'text-rarity-epic',
  legendary: 'text-rarity-legendary',
  mythic: 'text-rarity-mythic',
}

export const RARITY_BORDER_CLASS: Record<Rarity, string> = {
  common: 'border-rarity-common',
  uncommon: 'border-rarity-uncommon',
  rare: 'border-rarity-rare',
  epic: 'border-rarity-epic',
  legendary: 'border-rarity-legendary',
  mythic: 'border-rarity-mythic',
}

export const RARITY_WASH_CLASS: Record<Rarity, string> = {
  common: 'from-rarity-common/12',
  uncommon: 'from-rarity-uncommon/14',
  rare: 'from-rarity-rare/16',
  epic: 'from-rarity-epic/18',
  legendary: 'from-rarity-legendary/20',
  mythic: 'from-rarity-mythic/22',
}

export const RARITY_BAR_CLASS: Record<Rarity, string> = {
  common: 'bg-rarity-common',
  uncommon: 'bg-rarity-uncommon',
  rare: 'bg-rarity-rare',
  epic: 'bg-linear-to-r from-rarity-rare via-rarity-epic to-rarity-rare',
  legendary:
    'bg-linear-to-r from-rarity-legendary/60 via-rarity-legendary to-rarity-legendary/60',
  mythic:
    'bg-linear-to-r from-rarity-epic via-rarity-mythic to-rarity-legendary',
}

export const RARITY_FRAME_CLASS: Record<Rarity, string> = {
  common: 'border-rarity-common/30',
  uncommon: 'border-rarity-uncommon/35',
  rare: 'border-rarity-rare/40',
  epic: 'border-rarity-epic/45 shadow-md shadow-rarity-epic/10',
  legendary: 'border-rarity-legendary/55 shadow-lg shadow-rarity-legendary/15',
  mythic: 'border-rarity-mythic/60 shadow-lg shadow-rarity-mythic/20',
}
