import { type ComponentProps, createElement } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type IconVocabulary, domainIcon } from './domainIcons'

type DomainIconProps = {
  vocabulary: IconVocabulary
  value: string
  size?: 'sm' | 'md'
  className?: string
}

export function DomainIcon({
  vocabulary,
  value,
  size = 'sm',
  className,
}: DomainIconProps) {
  const props: ComponentProps<LucideIcon> & Record<`data-${string}`, string> = {
    'aria-hidden': true,
    'data-icon-vocabulary': vocabulary,
    'data-icon-value': value,
    className: cn(
      'shrink-0',
      size === 'sm' ? 'size-icon-sm' : 'size-icon-md',
      className
    ),
  }
  return createElement(domainIcon(vocabulary, value), props)
}
