import { cn } from '@/lib/utils'
import { GEM_CLASS } from '@/components/ui/ornate'
import { Text } from '@/components/typography'
import { type AvatarTone } from './types'

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'fill'

const AVATAR_SIZE: Record<AvatarSize, string> = {
  xs: 'size-icon-xl',
  sm: 'size-control-md',
  md: 'size-control-lg',
  lg: 'size-portrait-lg',
  fill: 'size-full',
}

function initialsOf(name: string, letters: number): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  const first = words[0]?.[0] ?? '?'
  const last = words.length > 1 ? (words[words.length - 1]?.[0] ?? '') : ''
  return `${first}${letters > 1 ? last : ''}`.toUpperCase()
}

export function AccountAvatar({
  name,
  tone,
  size = 'sm',
  dimmed = false,
  shape = 'round',
}: {
  name: string
  tone: AvatarTone
  size?: AvatarSize
  dimmed?: boolean
  shape?: 'round' | 'tile'
}) {
  return (
    <span
      role='img'
      aria-label={name}
      data-domain='account-avatar'
      className={cn(
        shape === 'round' ? 'medallion' : 'avatar-tile',
        'shrink-0 font-display',
        AVATAR_SIZE[size],
        GEM_CLASS[tone],
        dimmed && 'opacity-50 grayscale'
      )}
    >
      <Text as='span' weight='semibold' tone='inherit' aria-hidden='true'>
        {initialsOf(name, size === 'xs' || shape === 'tile' ? 1 : 2)}
      </Text>
    </span>
  )
}
