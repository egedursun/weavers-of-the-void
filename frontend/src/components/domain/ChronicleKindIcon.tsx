import { cn } from '@/lib/utils'
import {
  CHRONICLE_FALLBACK_ICON,
  CHRONICLE_KIND_ICON,
  type ChronicleKind,
} from './chronicleKindIcons'

type ChronicleKindIconProps = {
  kind: string
  size?: 'sm' | 'md'
  className?: string
}

export function ChronicleKindIcon({
  kind,
  size = 'sm',
  className,
}: ChronicleKindIconProps) {
  const Icon =
    CHRONICLE_KIND_ICON[kind as ChronicleKind] ?? CHRONICLE_FALLBACK_ICON
  return (
    <Icon
      aria-hidden='true'
      data-chronicle-kind={kind}
      className={cn(
        'shrink-0',
        size === 'sm' ? 'size-icon-sm' : 'size-icon-md',
        className
      )}
    />
  )
}
