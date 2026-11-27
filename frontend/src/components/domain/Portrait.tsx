import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'
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

const COMPACT = new Set<PortraitSize>(['xs', 'sm'])

const SPINNER_CLASS: Record<PortraitSize, string> = {
  xs: 'size-icon-xs',
  sm: 'size-icon-sm',
  md: 'size-icon-sm',
  lg: 'size-icon-lg',
  xl: 'size-icon-lg',
}

type LoadingStatus = 'idle' | 'loading' | 'loaded' | 'error'

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
  const [status, setStatus] = useState<{
    src: string
    value: LoadingStatus
  } | null>(null)
  const current = src && status?.src === src ? status.value : 'loading'
  const failed = current === 'error'
  const loading = Boolean(src) && !failed && current !== 'loaded'
  const rounded = shape === 'circle' ? 'rounded-full' : 'rounded-lg'
  return (
    <Avatar
      data-domain='portrait'
      data-portrait-size={size}
      className={cn(
        SIZE_CLASS[size],
        rounded,
        'aspect-square bg-muted',
        rarity
          ? ['border-2 p-0.5', RARITY_BORDER_CLASS[rarity]]
          : 'gilded-portrait'
      )}
    >
      {src && !failed && (
        <AvatarImage
          src={src}
          alt={name}
          className={cn(rounded, 'object-cover')}
          onLoadingStatusChange={(value) => setStatus({ src, value })}
        />
      )}
      <AvatarFallback
        className={cn(
          rounded,
          'bg-muted text-muted-foreground select-none',
          INITIALS_CLASS[size],
          !rarity && !COMPACT.has(size) && 'font-display',
          loading && 'animate-skeleton'
        )}
        aria-label={name}
        aria-busy={loading || undefined}
        data-portrait-loading={loading || undefined}
      >
        {loading ? (
          <LoaderCircle
            aria-hidden='true'
            className={cn('animate-spin text-primary', SPINNER_CLASS[size])}
          />
        ) : rarity ? (
          <Sigil seed={name} rarity={rarity} />
        ) : (
          <span className='text-gilded'>
            {COMPACT.has(size)
              ? getDisplayNameInitials(name).slice(0, 1)
              : getDisplayNameInitials(name)}
          </span>
        )}
      </AvatarFallback>
    </Avatar>
  )
}
