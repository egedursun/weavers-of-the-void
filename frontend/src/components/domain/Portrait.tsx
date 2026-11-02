import { useState } from 'react'
import { cn, getDisplayNameInitials } from '@/lib/utils'
import { type Rarity } from '@/constants/rarity'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Sigil } from './Sigil'
import { RARITY_BORDER_CLASS } from './rarityClasses'

export type PortraitSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

const SIZE_CLASS: Record<PortraitSize, string> = {
  xs: 'size-portrait-xs',
  sm: 'size-portrait-sm',
  md: 'size-portrait-md',
  lg: 'size-portrait-lg',
  xl: 'size-portrait-xl',
}

const INITIALS_CLASS: Record<PortraitSize, string> = {
  xs: 'text-overline font-semibold',
  sm: 'text-caption font-semibold',
  md: 'text-body font-semibold',
  lg: 'font-display text-title font-semibold',
  xl: 'font-display text-display font-semibold',
}

type PortraitProps = {
  name: string
  src?: string | null
  size?: PortraitSize
  shape?: 'circle' | 'square'
  rarity?: Rarity
}

export function Portrait({
  name,
  src,
  size = 'md',
  shape = 'circle',
  rarity,
}: PortraitProps) {
  const [failed, setFailed] = useState(false)
  const rounded = shape === 'circle' ? 'rounded-full' : 'rounded-lg'
  return (
    <Avatar
      data-domain='portrait'
      data-portrait-size={size}
      className={cn(
        SIZE_CLASS[size],
        rounded,
        'aspect-square bg-muted',
        rarity && ['border-2 p-0.5', RARITY_BORDER_CLASS[rarity]]
      )}
    >
      {src && !failed && (
        <AvatarImage
          src={src}
          alt={name}
          className={cn(rounded, 'object-cover')}
          onLoadingStatusChange={(status) => setFailed(status === 'error')}
        />
      )}
      <AvatarFallback
        className={cn(
          rounded,
          'bg-muted text-muted-foreground select-none',
          INITIALS_CLASS[size]
        )}
        aria-label={name}
      >
        {rarity ? (
          <Sigil seed={name} rarity={rarity} />
        ) : (
          getDisplayNameInitials(name)
        )}
      </AvatarFallback>
    </Avatar>
  )
}
