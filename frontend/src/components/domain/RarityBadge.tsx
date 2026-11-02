import { cn } from '@/lib/utils'
import { RARITY_LABEL, type Rarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { RarityIcon } from './RarityIcon'
import { RARITY_BADGE_CLASS } from './rarityClasses'

type RarityBadgeProps = {
  rarity: Rarity
  size?: 'sm' | 'default'
  showIcon?: boolean
}

export function RarityBadge({
  rarity,
  size = 'default',
  showIcon = true,
}: RarityBadgeProps) {
  return (
    <Badge
      variant='outline'
      size={size}
      data-rarity={rarity}
      className={cn(RARITY_BADGE_CLASS[rarity])}
    >
      {showIcon && <RarityIcon rarity={rarity} />}
      {RARITY_LABEL[rarity]}
    </Badge>
  )
}
